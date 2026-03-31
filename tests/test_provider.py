"""Unit tests for ChatCopilot (app/providers/copilot.py).

Covers PROV-01, PROV-02, PROV-03 requirements.
All Copilot SDK interactions are mocked — tests do NOT require SDK credentials.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_copilot():
    """Mock CopilotClient, SubprocessConfig, and PermissionHandler at the
    module level inside app.providers.copilot so that ChatCopilot never
    touches the real SDK during tests.
    """
    with (
        patch("app.providers.copilot.CopilotClient") as MockClient,
        patch("app.providers.copilot.SubprocessConfig") as MockConfig,
        patch("app.providers.copilot.PermissionHandler") as MockHandler,
    ):
        client_instance = AsyncMock()
        MockClient.return_value = client_instance

        session = AsyncMock()
        client_instance.create_session = AsyncMock(return_value=session)

        response = MagicMock()
        response.data.content = "mocked response"
        session.send_and_wait = AsyncMock(return_value=response)

        yield {
            "client_cls": MockClient,
            "config_cls": MockConfig,
            "handler": MockHandler,
            "client": client_instance,
            "session": session,
            "response": response,
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_instantiation():
    """ChatCopilot instantiates without error given a github_token."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(model="gpt-4.1", github_token="ghu_test")
    assert provider is not None
    assert provider.model == "gpt-4.1"
    assert provider.github_token == "ghu_test"


def test_llm_type():
    """_llm_type property returns 'github-copilot'."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(github_token="ghu_test")
    assert provider._llm_type == "github-copilot"


def test_sync_raises():
    """_generate() raises NotImplementedError with 'async-only' in message."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(github_token="ghu_test")
    with pytest.raises(NotImplementedError) as exc_info:
        provider._generate([HumanMessage(content="hi")])
    assert "async-only" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_agenerate_mocked(mock_copilot):
    """_agenerate returns ChatResult with AIMessage containing 'mocked response'."""
    from app.providers.copilot import ChatCopilot
    from langchain_core.outputs import ChatResult

    provider = ChatCopilot(model="gpt-4.1", github_token="ghu_test")
    result = await provider._agenerate([HumanMessage(content="hello")])

    assert isinstance(result, ChatResult)
    assert len(result.generations) == 1
    assert isinstance(result.generations[0].message, AIMessage)
    assert result.generations[0].message.content == "mocked response"


@pytest.mark.asyncio
async def test_model_param(mock_copilot):
    """create_session is called with model= keyword arg matching ChatCopilot.model."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(model="gpt-4.1", github_token="ghu_test")
    await provider._agenerate([HumanMessage(content="test")])

    mock_copilot["client"].create_session.assert_called_once()
    call_kwargs = mock_copilot["client"].create_session.call_args.kwargs
    assert call_kwargs.get("model") == "gpt-4.1"


@pytest.mark.asyncio
async def test_close(mock_copilot):
    """close() awaits client.stop() and resets _client to None."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(github_token="ghu_test")
    # Force a client to be set
    await provider._agenerate([HumanMessage(content="hello")])
    assert provider._client is not None

    await provider.close()

    mock_copilot["client"].stop.assert_awaited_once()
    assert provider._client is None


@pytest.mark.asyncio
async def test_error_resets_client(mock_copilot):
    """When _agenerate raises (e.g., send_and_wait fails), _client is reset to None."""
    from app.providers.copilot import ChatCopilot

    mock_copilot["session"].send_and_wait = AsyncMock(
        side_effect=RuntimeError("SDK error")
    )

    provider = ChatCopilot(github_token="ghu_test")

    with pytest.raises(RuntimeError, match="SDK error"):
        await provider._agenerate([HumanMessage(content="hello")])

    assert provider._client is None


def test_messages_to_prompt():
    """_messages_to_prompt converts message list to formatted string."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(github_token="ghu_test")
    messages = [
        SystemMessage(content="sys"),
        HumanMessage(content="hi"),
        AIMessage(content="resp"),
    ]
    result = provider._messages_to_prompt(messages)
    assert result == "[System]: sys\n[User]: hi\n[Assistant]: resp"


def test_ensure_client_no_token_no_manager():
    """_ensure_client raises ValueError when no github_token and no auth_manager."""
    import asyncio
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot()  # No token, no manager

    with pytest.raises(ValueError):
        asyncio.get_event_loop().run_until_complete(provider._ensure_client())


@pytest.mark.asyncio
async def test_send_and_wait_called_with_string(mock_copilot):
    """send_and_wait must receive the prompt as a plain str, not a dict."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(model="gpt-4.1", github_token="ghu_test")
    await provider._agenerate([HumanMessage(content="hello")])

    mock_copilot["session"].send_and_wait.assert_called_once_with("[User]: hello")
