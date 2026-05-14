"""Unit tests for CopilotAuthExpired detection in app.providers.copilot.

Covers quick-260514-djz:
- `_is_auth_expired` correctly identifies the SDK auth-failure marker
- `_agenerate` / `_astream` map auth failures to `CopilotAuthExpired`
- `_astream` SESSION_IDLE 0-chunk path emits a friendly fallback chunk
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from langchain_core.messages import HumanMessage

from app.providers.copilot import (
    ChatCopilot,
    CopilotAuthExpired,
    _is_auth_expired,
)


# ---------------------------------------------------------------------------
# _is_auth_expired
# ---------------------------------------------------------------------------


def test_is_auth_expired_matches_sdk_marker():
    exc = Exception(
        "Session error: Execution failed: Error: Session was not created "
        "with authentication info or custom provider"
    )
    assert _is_auth_expired(exc) is True


def test_is_auth_expired_returns_false_for_unrelated_error():
    assert _is_auth_expired(RuntimeError("timeout waiting for response")) is False
    assert _is_auth_expired(ValueError("No generations found in stream.")) is False


def test_is_auth_expired_follows_cause_chain():
    inner = Exception("Session was not created with authentication info or custom provider")
    outer = RuntimeError("wrapped")
    outer.__cause__ = inner
    assert _is_auth_expired(outer) is True


def test_is_auth_expired_handles_self_referential_chain():
    """A pathological exception chain should not cause infinite loop."""
    exc = RuntimeError("boom")
    exc.__cause__ = exc  # self-loop
    assert _is_auth_expired(exc) is False


# ---------------------------------------------------------------------------
# CopilotAuthExpired
# ---------------------------------------------------------------------------


def test_default_message_is_friendly_japanese():
    exc = CopilotAuthExpired()
    assert "再ログイン" in str(exc)
    assert "Copilot" in str(exc)


def test_cause_is_preserved():
    inner = Exception("Session was not created with authentication info")
    exc = CopilotAuthExpired(cause=inner)
    assert exc.__cause__ is inner


# ---------------------------------------------------------------------------
# _agenerate path: auth-expired SDK error is translated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agenerate_translates_auth_expired_to_typed_exception():
    with (
        patch("app.providers.copilot.CopilotClient") as MockClient,
        patch("app.providers.copilot.SubprocessConfig"),
        patch("app.providers.copilot.PermissionHandler"),
    ):
        client = AsyncMock()
        MockClient.return_value = client
        session = AsyncMock()
        session.send_and_wait = AsyncMock(
            side_effect=Exception(
                "Session error: Execution failed: Error: Session was not created "
                "with authentication info or custom provider"
            )
        )
        client.create_session = AsyncMock(return_value=session)

        provider = ChatCopilot(model="gpt-4.1", github_token="ghu_dummy")
        with pytest.raises(CopilotAuthExpired) as info:
            await provider.ainvoke([HumanMessage("hello")])

        assert "再ログイン" in str(info.value)
        # client must be reset for the next call to re-initialise
        assert provider._client is None


@pytest.mark.asyncio
async def test_agenerate_propagates_non_auth_errors_unchanged():
    with (
        patch("app.providers.copilot.CopilotClient") as MockClient,
        patch("app.providers.copilot.SubprocessConfig"),
        patch("app.providers.copilot.PermissionHandler"),
    ):
        client = AsyncMock()
        MockClient.return_value = client
        session = AsyncMock()
        session.send_and_wait = AsyncMock(side_effect=RuntimeError("network down"))
        client.create_session = AsyncMock(return_value=session)

        provider = ChatCopilot(model="gpt-4.1", github_token="ghu_dummy")
        with pytest.raises(RuntimeError) as info:
            await provider.ainvoke([HumanMessage("hello")])
        assert not isinstance(info.value, CopilotAuthExpired)
        assert "network down" in str(info.value)


# ---------------------------------------------------------------------------
# _astream path: SESSION_IDLE 0-chunk fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_astream_emits_friendly_message_when_no_chunks_arrive():
    """SDK が ASSISTANT_MESSAGE_DELTA も ASSISTANT_MESSAGE も emit せず
    SESSION_IDLE で終了したら、ValueError 由来のスタックではなく友好メッセージを
    1 chunk yield する。"""
    from copilot.generated.session_events import SessionEventType  # type: ignore

    with (
        patch("app.providers.copilot.CopilotClient") as MockClient,
        patch("app.providers.copilot.SubprocessConfig"),
        patch("app.providers.copilot.PermissionHandler"),
    ):
        client = AsyncMock()
        MockClient.return_value = client
        session = AsyncMock()
        captured = {}

        def fake_on(handler):
            captured["handler"] = handler

        session.on = MagicMock(side_effect=fake_on)

        async def fake_send(*args, **kwargs):
            # SDK が IDLE のみを emit するパターンを模倣
            idle = MagicMock()
            idle.type = SessionEventType.SESSION_IDLE
            captured["handler"](idle)

        session.send = AsyncMock(side_effect=fake_send)
        client.create_session = AsyncMock(return_value=session)

        provider = ChatCopilot(model="gpt-4.1", github_token="ghu_dummy")
        chunks = []
        async for chunk in provider._astream([HumanMessage("hello")]):
            chunks.append(chunk.message.content)

        joined = "".join(chunks)
        assert "再ログイン" in joined
        assert "Copilot" in joined
