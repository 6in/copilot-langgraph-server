"""Unit tests for IframeRpcHandler._handle_ai モデル解決ロジック (quick-260415-mbc).

Canvas iframe apps から ai(prompt, {model}) 経由で呼び出される _handle_ai が
エイリアス解決 / Haiku 既定 / 無効値拒否を正しく行うことを検証する。
silent fallback は行わず、無効値は {"result": False, "error": ...} を返す。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.jobs.handlers.iframe_rpc_handler import IframeRpcHandler


def _mock_llm(content: str = "ok"):
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=content))
    mock_llm.close = AsyncMock()
    return mock_llm


# ---------------------------------------------------------------------------
# Test 1: default (model 未指定) → Haiku
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_ai_default_is_haiku():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"prompt": "hi"}

    mock_llm = _mock_llm("hello")
    with patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot", return_value=mock_llm
    ) as mock_cls:
        result = await handler._handle_ai(job, params)

    assert result["result"] is True
    assert result["responseText"] == "hello"
    # ChatCopilot に Haiku 実 ID が渡されていることを確認
    kwargs = mock_cls.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5-20251001"
    assert kwargs["github_token"] == "ghu_test"
    mock_llm.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 2: alias 'sonnet' → claude-sonnet-4-6
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_ai_alias_sonnet():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"prompt": "hi", "model": "sonnet"}

    mock_llm = _mock_llm()
    with patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot", return_value=mock_llm
    ) as mock_cls:
        result = await handler._handle_ai(job, params)

    assert result["result"] is True
    assert mock_cls.call_args.kwargs["model"] == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Test 3: alias 'haiku' → claude-haiku-4-5-20251001
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_ai_alias_haiku():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"prompt": "hi", "model": "haiku"}

    mock_llm = _mock_llm()
    with patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot", return_value=mock_llm
    ) as mock_cls:
        result = await handler._handle_ai(job, params)

    assert result["result"] is True
    assert mock_cls.call_args.kwargs["model"] == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Test 4: alias 'gpt-4.1' → gpt-4.1 (エイリアス兼実 ID)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_ai_alias_gpt41():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"prompt": "hi", "model": "gpt-4.1"}

    mock_llm = _mock_llm()
    with patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot", return_value=mock_llm
    ) as mock_cls:
        result = await handler._handle_ai(job, params)

    assert result["result"] is True
    assert mock_cls.call_args.kwargs["model"] == "gpt-4.1"


# ---------------------------------------------------------------------------
# Test 5: 実 ID 直指定 (ホワイトリスト済み) は素通り
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_ai_direct_real_id_passthrough():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"prompt": "hi", "model": "claude-sonnet-4-6"}

    mock_llm = _mock_llm()
    with patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot", return_value=mock_llm
    ) as mock_cls:
        result = await handler._handle_ai(job, params)

    assert result["result"] is True
    assert mock_cls.call_args.kwargs["model"] == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Test 6: 未知のエイリアス (例: 'turbo') → silent fallback せず拒否
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_ai_invalid_model_rejected():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"prompt": "hi", "model": "turbo"}

    with patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot"
    ) as mock_cls:
        result = await handler._handle_ai(job, params)

    assert result["result"] is False
    assert "turbo" in result["error"]
    # エラーメッセージに許可された値一覧を含むこと
    assert "haiku" in result["error"]
    assert "sonnet" in result["error"]
    # ChatCopilot は一度も呼ばれない
    mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: 空文字列 → 拒否 (None とは区別)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_ai_empty_string_rejected():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"prompt": "hi", "model": ""}

    with patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot"
    ) as mock_cls:
        result = await handler._handle_ai(job, params)

    assert result["result"] is False
    assert "empty" in result["error"].lower() or "must not" in result["error"].lower()
    mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: 後方互換 — 正常系の返却契約は不変
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_ai_success_contract_unchanged():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"prompt": "Hello!"}  # model 未指定 → Haiku 既定

    mock_llm = _mock_llm("Hi there!")
    with patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot", return_value=mock_llm
    ):
        result = await handler._handle_ai(job, params)

    # 契約: {"result": True, "responseText": str}
    assert set(result.keys()) == {"result", "responseText"}
    assert result["result"] is True
    assert result["responseText"] == "Hi there!"
    mock_llm.close.assert_awaited_once()
