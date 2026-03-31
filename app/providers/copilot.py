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

from typing import Any, List, Optional, Sequence

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict, PrivateAttr

# SDK imports are at module top-level so that tests can patch them at
# app.providers.copilot.CopilotClient / SubprocessConfig / PermissionHandler
from copilot import CopilotClient, SubprocessConfig, PermissionHandler  # type: ignore[import-untyped]


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

            response = await session.send_and_wait({"prompt": prompt})

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
