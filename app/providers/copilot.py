"""ChatCopilot — BaseChatModel wrapper around the GitHub Copilot SDK.

PROV-01: Implements BaseChatModel interface (async-only).
PROV-02: Manages CopilotClient lifecycle (start/stop).
PROV-03: Converts LangChain message list to Copilot prompt string.

Usage:
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(model="gpt-4.1", github_token="ghu_...")
    result = await provider.ainvoke([HumanMessage("Hello")])
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from typing import Any, AsyncIterator, List, Optional, Sequence

logger = logging.getLogger(__name__)

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.tools import BaseTool
from pydantic import ConfigDict, PrivateAttr

# SDK imports are at module top-level so that tests can patch them at
# app.providers.copilot.CopilotClient / SubprocessConfig / PermissionHandler
from copilot import (  # type: ignore[import-untyped]
    CopilotClient,
    SubprocessConfig,
    PermissionHandler,
    FileAttachment,  # Phase 36 D-10/D-15: TypedDict. dict リテラル {"type": "file", "path": ..., "displayName": ...} で組む.
    ModelInfo,       # Phase 36 D-16: list_models() 戻り値、dataclass (capabilities / limits / billing) を持つ.
)
from copilot.generated.session_events import SessionEventType  # type: ignore[import-untyped]


# GitHub OAuth `ghu_` トークン失効時、Copilot SDK subprocess は以下の文字列を
# 含むエラーを上げて即拒否する。Device Flow は refresh token を持たないため
# 自動更新は不可能 — 検出後はユーザーに再ログインを促す必要がある。
_AUTH_EXPIRED_MARKER = "Session was not created with authentication info"


class CopilotAuthExpired(RuntimeError):
    """Copilot の認証セッションが失効した状態で SDK 呼び出しが失敗した時に raise する。

    既定メッセージは UI にそのまま表示される想定。原因例外は ``__cause__`` で
    保持し、トレースが必要な場面 (ログ/トレース) で参照できるようにする。
    """

    DEFAULT_MESSAGE = (
        "Copilot の認証セッションが無効になりました。"
        "一度ログアウトして再ログインしてください。"
    )

    def __init__(self, message: Optional[str] = None, *, cause: Optional[BaseException] = None):
        super().__init__(message or self.DEFAULT_MESSAGE)
        if cause is not None:
            self.__cause__ = cause


def _is_auth_expired(exc: BaseException) -> bool:
    """``exc`` (またはその ``__cause__`` 連鎖) が auth-expired パターンか判定する。"""
    seen: set[int] = set()
    cur: Optional[BaseException] = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if _AUTH_EXPIRED_MARKER in str(cur):
            return True
        cur = cur.__cause__ or cur.__context__
    return False


class ChatCopilot(BaseChatModel):
    """LangChain-compatible wrapper for the GitHub Copilot SDK.

    This is the ONLY file in the project that imports from the ``copilot``
    package. All SDK breaking changes should be isolated here.

    Parameters
    ----------
    model:
        Copilot model identifier forwarded to ``create_session``.
    github_token:
        Raw ``ghu_`` OAuth token. Takes priority over ``auth_manager``.
    auth_manager:
        Optional :class:`~app.auth.manager.CopilotAuthManager` instance.
        Used to retrieve a token when ``github_token`` is not provided.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str = "gpt-4.1"
    github_token: Optional[str] = None
    auth_manager: Optional[Any] = None
    # Copilot SDK send_and_wait timeout (seconds). Default 60s is too short
    # for tool-bound ReAct loops where the second LLM call includes tool
    # results in the prompt, making the context significantly larger.
    # Phase 37.1: extended to 300s to accommodate attachments_extract tool
    # invocations on longer conversation histories with multiple tool schemas
    # (gpt-4.1 occasionally exceeds 120s when deciding among 5+ tools with
    # accumulated context). Configurable via COPILOT_SEND_TIMEOUT env var.
    send_timeout: float = float(os.environ.get("COPILOT_SEND_TIMEOUT", "300"))

    # Private — not part of the Pydantic schema
    _client: Any = PrivateAttr(default=None)

    # Phase 31 Plan 04: last ASSISTANT_USAGE payload (int-cast 4-field dict or None).
    # Populated non-invasively by a session.on() hook in _agenerate / _astream so that
    # SubAgent.run() / ToolEnabledSubAgent.run() / CodeActSubAgent.run() can attach
    # usage attributes to their sub_agent span (docs/phase-31-reasoning-token-spike.md).
    _last_usage: Optional[dict] = PrivateAttr(default=None)

    @property
    def last_usage(self) -> Optional[dict]:
        """Return the last captured ASSISTANT_USAGE dict (or None when never emitted).

        Keys when populated: ``input_tokens`` / ``output_tokens`` /
        ``cache_read_tokens`` / ``cache_write_tokens`` (all ``int``).
        """
        return self._last_usage

    # ------------------------------------------------------------------
    # Phase 31 Plan 04 — token usage capture helpers (non-invasive)
    # ------------------------------------------------------------------

    def _store_usage(self, data: Any) -> None:
        """Normalise an ``ASSISTANT_USAGE`` event payload into ``last_usage``.

        Copilot SDK 0.2.0 emits ``input_tokens`` / ``output_tokens`` /
        ``cache_read_tokens`` / ``cache_write_tokens`` as ``float | None``
        (see docs/phase-31-reasoning-token-spike.md). We int-cast with a
        0 fallback for robustness — the spike confirmed all 3 target models
        (haiku / sonnet / gpt-4.1) emit non-null values but the SDK type is
        permissive. Absolutely never raise — a broken usage event must not
        propagate to the LLM call.
        """
        try:
            if data is None:
                return
            self._last_usage = {
                "input_tokens": int(getattr(data, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(data, "output_tokens", 0) or 0),
                "cache_read_tokens": int(getattr(data, "cache_read_tokens", 0) or 0),
                "cache_write_tokens": int(getattr(data, "cache_write_tokens", 0) or 0),
            }
        except Exception:  # pragma: no cover - defensive
            pass

    def _register_usage_hook(self, session: Any) -> None:
        """Attach a ``session.on`` callback that records ASSISTANT_USAGE.

        Used by ``_agenerate`` (non-streaming path) where the existing code
        did not install an event handler. ``_astream`` embeds the same
        capture inline in its queue-driven ``on_event`` closure so the
        behaviour is uniform across both invocation paths.
        """
        try:
            def _on(event: Any) -> None:
                if getattr(event, "type", None) == SessionEventType.ASSISTANT_USAGE:
                    self._store_usage(getattr(event, "data", None))

            session.on(_on)
        except Exception:  # pragma: no cover - defensive
            pass

    # ------------------------------------------------------------------
    # BaseChatModel required interface
    # ------------------------------------------------------------------

    @property
    def _llm_type(self) -> str:
        return "github-copilot"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError(
            "ChatCopilot is async-only. Use ainvoke() inside an async context."
        )

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Send messages to Copilot and return a ChatResult.

        Creates a new session per call (stateless from the SDK's perspective;
        conversation history is encoded in the prompt string).
        """
        await self._ensure_client()
        prompt = self._messages_to_prompt(messages)
        # Phase 36 D-09/D-10: 最後の HumanMessage の additional_kwargs["attachments"] を
        # SDK FileAttachment TypedDict に変換して send_and_wait に渡す.
        sdk_atts = self._extract_attachments(messages)

        try:
            session = await self._client.create_session(
                on_permission_request=PermissionHandler.approve_all,
                model=self.model,
            )

            # Phase 31 Plan 04: register an ASSISTANT_USAGE hook BEFORE send so we
            # capture the token usage event that the Copilot SDK fires for every
            # turn. Non-blocking — defensively wrapped in try/except so a broken
            # session.on never prevents the actual LLM call.
            self._register_usage_hook(session)

            response = await session.send_and_wait(
                prompt,
                attachments=sdk_atts,
                timeout=self.send_timeout,
            )

            if response is None or response.data.content is None:
                raise RuntimeError(
                    "ChatCopilot: received empty response from Copilot SDK. "
                    "Check that the token is valid and the model is available."
                )

            content: str = response.data.content
            await session.disconnect()

            return ChatResult(
                generations=[
                    ChatGeneration(message=AIMessage(content=content))
                ]
            )
        except Exception as exc:
            # Reset client so next call will re-initialise cleanly
            try:
                await self._client.stop()
            except Exception:
                pass
            self._client = None
            if _is_auth_expired(exc):
                raise CopilotAuthExpired(cause=exc) from exc
            raise

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Stream tokens from Copilot using ASSISTANT_MESSAGE_DELTA events.

        Uses session.on() to register event handlers and session.send() (non-blocking)
        to initiate the request, then yields ChatGenerationChunk for each delta token.

        Falls back to ASSISTANT_MESSAGE full content if no delta events are received
        (e.g. when the SDK version doesn't emit deltas — Technical Preview limitation).

        The handler is registered BEFORE send() to avoid missing early delta events.
        """
        await self._ensure_client()
        prompt = self._messages_to_prompt(messages)
        # Phase 36 D-09/D-10: streaming 経路でも最後の HumanMessage の attachments を抽出して
        # session.send に同じ kwarg で渡す.
        sdk_atts = self._extract_attachments(messages)

        try:
            session = await self._client.create_session(
                on_permission_request=PermissionHandler.approve_all,
                model=self.model,
                streaming=True,
            )

            # asyncio.Queue items: str (token) or None (completion signal)
            queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
            # Capture the running loop here (inside async context) for use in sync callback
            loop = asyncio.get_running_loop()
            # Track whether any delta tokens arrived (for fallback logic)
            has_deltas: list[bool] = [False]
            fallback_content: list[Optional[str]] = [None]

            def on_event(event: Any) -> None:
                event_type = getattr(event, "type", None)
                if event_type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
                    token = getattr(event.data, "delta_content", None)
                    if token:
                        has_deltas[0] = True
                        loop.call_soon_threadsafe(queue.put_nowait, token)
                elif event_type == SessionEventType.ASSISTANT_MESSAGE:
                    # Capture full content as fallback when no deltas are emitted
                    content = getattr(event.data, "content", None)
                    if content:
                        fallback_content[0] = content
                elif event_type == SessionEventType.ASSISTANT_USAGE:
                    # Phase 31 Plan 04: capture usage tokens for SubAgent span emit.
                    self._store_usage(getattr(event, "data", None))
                elif event_type == SessionEventType.SESSION_IDLE:
                    # If no deltas arrived, emit the full message as a single chunk.
                    # 0-chunk fallback: SDK が ASSISTANT_MESSAGE_DELTA も ASSISTANT_MESSAGE も
                    # emit せず SESSION_IDLE で終了するケース (典型例: OAuth token 失効で
                    # SDK subprocess が auth 拒否) では generate_from_stream が
                    # ValueError("No generations found in stream.") を投げてしまうため、
                    # friendly な再ログイン誘導メッセージを 1 chunk yield して救済する。
                    if not has_deltas[0]:
                        if fallback_content[0]:
                            loop.call_soon_threadsafe(queue.put_nowait, fallback_content[0])
                        else:
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                "Copilot から応答が得られませんでした。"
                                "一度ログアウトして再ログインしてください。",
                            )
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            # Register handler BEFORE send() to avoid missing early delta events
            session.on(on_event)
            await session.send(prompt, attachments=sdk_atts)

            # Yield chunks from the queue until completion signal (None)
            while True:
                token = await asyncio.wait_for(queue.get(), timeout=120.0)
                if token is None:
                    break
                yield ChatGenerationChunk(message=AIMessageChunk(content=token))

            await session.disconnect()

        except Exception as exc:
            # Reset client so next call will re-initialise cleanly
            try:
                await self._client.stop()
            except Exception:
                pass
            self._client = None
            if _is_auth_expired(exc):
                raise CopilotAuthExpired(cause=exc) from exc
            raise

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------

    async def _ensure_client(self) -> None:
        """Initialise CopilotClient if not already started."""
        if self._client is not None:
            return

        if self.github_token:
            token = self.github_token
        elif self.auth_manager is not None:
            token = await self.auth_manager.get_token()
        else:
            raise ValueError(
                "ChatCopilot requires a GitHub token. "
                "Provide github_token= or pass an auth_manager=."
            )

        self._client = CopilotClient(
            SubprocessConfig(github_token=token, use_logged_in_user=False)
        )
        await self._client.start()

    # ------------------------------------------------------------------
    # Phase 36 D-16/D-18 — model catalog & vision capability helpers
    # ------------------------------------------------------------------

    async def list_models(self) -> list[dict]:
        """Phase 36 D-16: SDK list_models() を D-14 dict に変換する.

        戻り値: [{id, name, vision, vision_limits, billing_multiplier}, ...]
        - vision: bool — ModelCapabilities.supports.vision
        - vision_limits: dict | None — ModelVisionLimits.to_dict() or None
        - billing_multiplier: float | None — ModelBilling.multiplier

        SDK 型 (ModelInfo / ModelCapabilities / ModelVisionLimits) はこのメソッド内で
        全て dict 化し、route 層 (D-15 SDK 隔離原則) には dict のみを露出する.
        """
        await self._ensure_client()
        models = await self._client.list_models()
        payload: list[dict] = []
        for m in models:
            caps = getattr(m, "capabilities", None)
            supports = getattr(caps, "supports", None) if caps else None
            limits = getattr(caps, "limits", None) if caps else None
            vision_flag = bool(getattr(supports, "vision", False)) if supports else False
            vision_limits_obj = getattr(limits, "vision", None) if limits else None
            vision_limits: dict | None = None
            if vision_limits_obj is not None:
                if hasattr(vision_limits_obj, "to_dict"):
                    vision_limits = vision_limits_obj.to_dict()
                else:
                    # dataclass フィールドをそのまま dict 化 (to_dict が無い旧 SDK 用 fallback)
                    import dataclasses
                    vision_limits = (
                        dataclasses.asdict(vision_limits_obj)
                        if dataclasses.is_dataclass(vision_limits_obj)
                        else None
                    )
            billing = getattr(m, "billing", None)
            multiplier = getattr(billing, "multiplier", None) if billing else None
            payload.append({
                "id": m.id,
                "name": m.name,
                "vision": vision_flag,
                "vision_limits": vision_limits,
                "billing_multiplier": multiplier,
            })
        return payload

    async def is_vision_model(self, model_id: str) -> bool:
        """Phase 36 D-18: worker 側 vision drop 判定ヘルパー.

        list_models() 取得・例外時は False を返す (fail-safe, drop 画像 + SystemMessage 警告
        で graceful 継続するため、SDK エラー時に「vision 対応」と誤判定して画像を送るのを防ぐ).
        """
        try:
            models = await self.list_models()
            for m in models:
                if m.get("id") == model_id:
                    return bool(m.get("vision"))
        except Exception:
            return False
        return False

    async def close(self) -> None:
        """Stop the underlying CopilotClient and release resources."""
        if self._client is not None:
            await self._client.stop()
            self._client = None

    # ------------------------------------------------------------------
    # Message formatting
    # ------------------------------------------------------------------

    def _extract_attachments(
        self,
        messages: Sequence[BaseMessage],
    ) -> Optional[List["FileAttachment"]]:
        """Phase 36 D-10/D-14/D-15: 最後の HumanMessage の additional_kwargs['attachments']
        を SDK FileAttachment TypedDict に変換して返す.

        - 他 BaseMessage 型 (AIMessage / SystemMessage / ToolMessage) は skip
        - additional_kwargs が空 / 不在 / list が空なら None を返す (send_and_wait は None を許容)
        - kind != 'file' は本 phase 未採用なので skip (将来 BlobAttachment 追加時にここを拡張)
        - path が str で非空でない entry は skip (防御的)
        - displayName は SDK 0.2.0 で required (Wave 0 Plan 01 Task 2 で確認).
          name が str で非空ならそれを採用、それ以外は path basename を fallback で必ず埋める.
        """
        import os.path as _ospath

        last_human = None
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_human = m
                break
        if last_human is None:
            return None
        atts_meta = (last_human.additional_kwargs or {}).get("attachments") or []
        sdk_atts: List[FileAttachment] = []
        for a in atts_meta:
            if not isinstance(a, dict):
                continue
            if a.get("kind") != "file":
                continue
            path = a.get("path")
            if not isinstance(path, str) or not path:
                continue
            display_name = a.get("name")
            if not (isinstance(display_name, str) and display_name):
                # Wave 0 Plan 01 Deviation #2: SDK は displayName 必須. fallback で必ず埋める.
                display_name = _ospath.basename(path) or path
            entry: FileAttachment = {
                "type": "file",
                "path": path,
                "displayName": display_name,
            }
            sdk_atts.append(entry)
        return sdk_atts or None

    def _messages_to_prompt(self, messages: Sequence[BaseMessage]) -> str:
        """Convert a LangChain message list to a single prompt string.

        Format::

            [System]: <system content>
            [User]: <user content>
            [Assistant]: <assistant content>
        """
        parts: list[str] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                role = "[System]"
            elif isinstance(msg, HumanMessage):
                role = "[User]"
            elif isinstance(msg, AIMessage):
                role = "[Assistant]"
            else:
                role = "[Unknown]"
            parts.append(f"{role}: {msg.content}")
        return "\n".join(parts)

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        _tool_choice: Optional[str] = None,  # unused; accepted for BaseChatModel compat
        **kwargs: Any,
    ) -> "BoundChatCopilot":
        """Bind tools to this model via prompt engineering (D-01).

        Returns a BoundChatCopilot that injects tool schemas into the system
        prompt and parses JSON responses into AIMessage(tool_calls=[...]).
        """
        base_tools = [t for t in tools if isinstance(t, BaseTool)]
        return BoundChatCopilot(
            tools=base_tools,
            model=self.model,
            github_token=self.github_token,
            auth_manager=self.auth_manager,
        )


# ---------------------------------------------------------------------------
# Tool prompt engineering constants
# ---------------------------------------------------------------------------

TOOL_SYSTEM_PROMPT_TEMPLATE = """\
You have access to the following tools:
{tool_schemas}

To call a tool, respond ONLY with valid JSON (no markdown, no explanation, no preamble):
{{"tool": "<tool_name>", "args": {{...}}}}

Examples:
  {{"tool": "web_search", "args": {{"query": "Tokyo weather tomorrow"}}}}
  {{"tool": "db_query", "args": {{"sql": "SELECT * FROM gems LIMIT 10"}}}}
  {{"tool": "db_query", "args": {{"sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"}}}}

When to call a tool:
- web_search: current events, weather, latest versions, recent news, prices, or anything \
that requires up-to-date information from the internet. \
When results include source_urls, cite them in your final answer.
- db_query: whenever the user asks about database tables, records, data, or anything that \
requires querying the PostgreSQL database. This includes metadata queries such as listing \
tables, showing columns, or describing schema (use information_schema or pg_catalog). \
Convert the user's natural language request into a valid SELECT or WITH query. \
Only SELECT is allowed — never generate INSERT/UPDATE/DELETE.
- execute_python: whenever the user asks to run code, compute something, analyze data, \
create algorithms, process numbers, or any task that benefits from actual code execution. \
Write Python code and call this tool to execute it. Always use this tool instead of \
showing code without executing it.

For pure conversation, greetings, translation, or summarization of already-provided text, \
respond normally without calling a tool.\
"""


# ---------------------------------------------------------------------------
# BoundChatCopilot
# ---------------------------------------------------------------------------


class BoundChatCopilot(ChatCopilot):
    """ChatCopilot subclass that injects tool schemas into the system prompt
    and parses JSON responses into AIMessage(tool_calls=[...]).

    Created by ChatCopilot.bind_tools() — do not instantiate directly in
    application code.
    """

    # _bound_tools is stored as a PrivateAttr to avoid Pydantic schema pollution.
    _bound_tools: list = PrivateAttr(default_factory=list)

    def __init__(self, tools: list, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        object.__setattr__(self, "_bound_tools", tools)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Augment messages with tool schemas, then parse the response.

        If the LLM returns JSON {tool, args}, converts to
        AIMessage(tool_calls=[ToolCall(...)]). Otherwise passes through
        the plain-text response unchanged.
        """
        # Build tool schema JSON and inject as a SystemMessage at the front
        tool_schemas = json.dumps(
            [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.get_input_jsonschema(),
                }
                for t in self._bound_tools
            ],
            ensure_ascii=False,
            indent=2,
        )
        system_msg = SystemMessage(
            content=TOOL_SYSTEM_PROMPT_TEMPLATE.format(tool_schemas=tool_schemas)
        )
        augmented_messages: List[BaseMessage] = [system_msg] + list(messages)

        # Delegate to parent _agenerate with augmented message list
        result = await super()._agenerate(augmented_messages, stop=stop, run_manager=run_manager, **kwargs)

        # Try to parse tool call from the response content
        content = result.generations[0].message.content
        tool_call = self._try_parse_tool_call(content)
        if tool_call is not None:
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content="", tool_calls=[tool_call])
                    )
                ]
            )

        return result

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Bypass Copilot SDK streaming for tool-bound calls.

        Why: LangChain's `BaseChatModel.ainvoke` routes through `_astream`
        whenever it runs inside an `astream_events` context (our orchestrator
        handler does). Token-by-token streaming cannot reliably parse a
        partial JSON tool call, and `ChatCopilot._astream` doesn't inject
        tool schemas into the prompt either. The result is an empty
        `tool_calls` list and the ReAct loop falls through without ever
        invoking a tool.

        Fix: delegate to `_agenerate` (which injects the tool schema,
        awaits the full response, and parses JSON → ToolCall), then yield
        the result as a single chunk. For tool calls we emit
        `tool_call_chunks` so LangChain's message aggregator reconstructs
        `AIMessage.tool_calls` correctly on the receiving end.
        """
        result = await self._agenerate(
            messages, stop=stop, run_manager=run_manager, **kwargs
        )
        message = result.generations[0].message

        chunk_message: AIMessageChunk
        if getattr(message, "tool_calls", None):
            tool_call_chunks = [
                {
                    "name": tc["name"],
                    "args": json.dumps(tc.get("args") or {}, ensure_ascii=False),
                    "id": tc.get("id"),
                    "index": i,
                }
                for i, tc in enumerate(message.tool_calls)
            ]
            chunk_message = AIMessageChunk(
                content=message.content or "",
                tool_call_chunks=tool_call_chunks,
            )
        else:
            chunk_message = AIMessageChunk(content=message.content or "")

        yield ChatGenerationChunk(message=chunk_message)

    def _try_parse_tool_call(self, content: str) -> Optional[ToolCall]:
        """Attempt to parse a tool call from an LLM response string.

        Handles:
        - Plain JSON: {"tool": "name", "args": {...}}
        - Markdown-wrapped JSON: ```json\\n{...}\\n```

        Returns a ToolCall if the content is valid JSON with a "tool" key,
        otherwise returns None (T-21-01: strict parse, "tool" key required).
        """
        stripped = content.strip()

        # Attempt 1: direct JSON parse
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict) and "tool" in parsed:
                return ToolCall(
                    name=parsed["tool"],
                    args=parsed.get("args", {}),
                    id=str(uuid.uuid4())[:8],
                )
        except json.JSONDecodeError:
            pass

        # Attempt 2: strip markdown code block fences and retry
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", stripped)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "tool" in parsed:
                return ToolCall(
                    name=parsed["tool"],
                    args=parsed.get("args", {}),
                    id=str(uuid.uuid4())[:8],
                )
        except json.JSONDecodeError:
            pass

        # Attempt 3: extract {"tool": ...} from mixed text (model outputs JSON + explanation)
        # Use bracket counting to find the complete JSON object starting at {"tool"
        for marker in ('{"tool"', '{ "tool"'):
            idx = stripped.find(marker)
            if idx == -1:
                continue
            depth = 0
            for i, ch in enumerate(stripped[idx:], idx):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            parsed = json.loads(stripped[idx : i + 1])
                            if isinstance(parsed, dict) and "tool" in parsed:
                                return ToolCall(
                                    name=parsed["tool"],
                                    args=parsed.get("args", {}),
                                    id=str(uuid.uuid4())[:8],
                                )
                        except json.JSONDecodeError:
                            pass
                        break

        # Attempt 4: detect Python code block and auto-convert to execute_python tool call.
        # Copilot models often write code in markdown instead of using the JSON tool format.
        # If execute_python is among bound tools and response contains ```python blocks,
        # extract the code and create a tool call automatically.
        if any(t.name == "execute_python" for t in self._bound_tools):
            py_match = re.search(r"```python\s*\n(.*?)```", stripped, re.DOTALL)
            if py_match:
                code = py_match.group(1).strip()
                if code:
                    logger.info("[BoundChatCopilot] Auto-converting markdown python block to execute_python tool call (%d chars)", len(code))
                    return ToolCall(
                        name="execute_python",
                        args={"code": code},
                        id=str(uuid.uuid4())[:8],
                    )

        return None
