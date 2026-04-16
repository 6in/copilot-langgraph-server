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
from copilot import CopilotClient, SubprocessConfig, PermissionHandler  # type: ignore[import-untyped]
from copilot.generated.session_events import SessionEventType  # type: ignore[import-untyped]


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
    send_timeout: float = 120.0

    # Private — not part of the Pydantic schema
    _client: Any = PrivateAttr(default=None)

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

        try:
            session = await self._client.create_session(
                on_permission_request=PermissionHandler.approve_all,
                model=self.model,
            )

            response = await session.send_and_wait(prompt, timeout=self.send_timeout)

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
        except Exception:
            # Reset client so next call will re-initialise cleanly
            try:
                await self._client.stop()
            except Exception:
                pass
            self._client = None
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
                elif event_type == SessionEventType.SESSION_IDLE:
                    # If no deltas arrived, emit the full message as a single chunk
                    if not has_deltas[0] and fallback_content[0]:
                        loop.call_soon_threadsafe(queue.put_nowait, fallback_content[0])
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            # Register handler BEFORE send() to avoid missing early delta events
            session.on(on_event)
            await session.send(prompt)

            # Yield chunks from the queue until completion signal (None)
            while True:
                token = await asyncio.wait_for(queue.get(), timeout=120.0)
                if token is None:
                    break
                yield ChatGenerationChunk(message=AIMessageChunk(content=token))

            await session.disconnect()

        except Exception:
            # Reset client so next call will re-initialise cleanly
            try:
                await self._client.stop()
            except Exception:
                pass
            self._client = None
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

    async def close(self) -> None:
        """Stop the underlying CopilotClient and release resources."""
        if self._client is not None:
            await self._client.stop()
            self._client = None

    # ------------------------------------------------------------------
    # Message formatting
    # ------------------------------------------------------------------

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

For pure conversation, greetings, math, translation, or summarization of already-provided text, \
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

        return None
