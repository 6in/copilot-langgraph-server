"""Phase 36 D-09/D-10/D-14/D-15/D-16/D-18 — provider 配線の unit test.

ChatCopilot wrapper の 3 ヘルパー (_extract_attachments / list_models /
is_vision_model) と _agenerate / _astream への attachments kwarg 配線を検証する.

すべての SDK アクセスは patch / AsyncMock でモックし、実 Copilot 認証情報は要求しない.
"""
from __future__ import annotations

import os.path

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def prov():
    """ChatCopilot インスタンス (token のみ、SDK には触れない)."""
    from app.providers.copilot import ChatCopilot
    return ChatCopilot(github_token="ghu_test", model="claude-sonnet-4.6")


@pytest.fixture
def mock_copilot():
    """test_copilot_bind_tools.py / test_provider.py と同じパターンで SDK をモック.

    CopilotClient / SubprocessConfig / PermissionHandler を app.providers.copilot
    モジュール内で patch し、実 SDK subprocess を起動しない.
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


def _mk_modelinfo(id_, name_, vision, limits_dict=None, mult=None):
    """ModelInfo dataclass の風モック.

    SDK 0.2.0 の ModelInfo 構造を擬似的に再現する MagicMock を返す.
    capabilities.supports.vision / capabilities.limits.vision.to_dict() /
    billing.multiplier の 3 経路を本物っぽく見せかける.
    """
    m = MagicMock()
    m.id = id_
    m.name = name_
    m.capabilities = MagicMock()
    m.capabilities.supports = MagicMock(vision=vision)
    m.capabilities.limits = MagicMock()
    if limits_dict is not None:
        limits_obj = MagicMock()
        limits_obj.to_dict = MagicMock(return_value=limits_dict)
        m.capabilities.limits.vision = limits_obj
    else:
        m.capabilities.limits.vision = None
    if mult is not None:
        m.billing = MagicMock(multiplier=mult)
    else:
        m.billing = None
    return m


# ---------------------------------------------------------------------------
# Test 1-4: _extract_attachments
# ---------------------------------------------------------------------------


def test_extract_attachments_from_last_human_message(prov):
    """最後の HumanMessage の additional_kwargs['attachments'] を SDK dict に変換する.

    旧 turn の attachments は無視し、最新の HumanMessage のみが採用されることを確認.
    """
    messages = [
        SystemMessage(content="sys"),
        HumanMessage(
            content="old",
            additional_kwargs={"attachments": [
                {"kind": "file", "name": "old.txt", "path": "/old"}
            ]},
        ),
        AIMessage(content="ok"),
        HumanMessage(
            content="these",
            additional_kwargs={"attachments": [
                {
                    "kind": "file",
                    "name": "a.txt",
                    "path": "/shared/thread-files/u/t/a.txt",
                    "size": 10,
                    "mime_type": "text/plain",
                    "ext": "txt",
                    "modified_at": "2026-04-23T12:00:00Z",
                    "storage_name": "20260423T120000_a.txt",
                },
                {
                    "kind": "file",
                    "name": "b.png",
                    "path": "/shared/thread-files/u/t/b.png",
                    "size": 999,
                    "mime_type": "image/png",
                    "ext": "png",
                    "modified_at": "2026-04-23T12:00:00Z",
                    "storage_name": "20260423T120000_b.png",
                },
            ]},
        ),
    ]
    result = prov._extract_attachments(messages)
    assert result == [
        {"type": "file", "path": "/shared/thread-files/u/t/a.txt", "displayName": "a.txt"},
        {"type": "file", "path": "/shared/thread-files/u/t/b.png", "displayName": "b.png"},
    ]


def test_extract_attachments_empty_returns_none(prov):
    """additional_kwargs が無い / attachments が空 / HumanMessage が無いケースは None.

    session.send_and_wait は attachments=None を許容するので None を返すのが正しい
    (空リスト [] を渡すと SDK 側で no-op オーバーヘッドが掛かる可能性).
    """
    # ケース 1: HumanMessage はあるが additional_kwargs に attachments が無い
    msgs1 = [HumanMessage(content="hi")]
    assert prov._extract_attachments(msgs1) is None

    # ケース 2: additional_kwargs に attachments が空 list で入っている
    msgs2 = [HumanMessage(content="hi", additional_kwargs={"attachments": []})]
    assert prov._extract_attachments(msgs2) is None

    # ケース 3: HumanMessage が一つもない
    msgs3 = [SystemMessage(content="sys"), AIMessage(content="ok")]
    assert prov._extract_attachments(msgs3) is None

    # ケース 4: 空 messages
    assert prov._extract_attachments([]) is None


def test_extract_attachments_skips_non_file_kinds(prov):
    """kind != "file" の項目 (将来的な BlobAttachment 等) は本 phase では skip."""
    messages = [
        HumanMessage(content="x", additional_kwargs={"attachments": [
            {"kind": "blob", "name": "img.png", "path": "/p/img.png"},  # skip
            {"kind": "file", "name": "ok.txt", "path": "/p/ok.txt"},
            {"kind": "directory", "name": "dir", "path": "/p/dir"},  # skip
        ]}),
    ]
    result = prov._extract_attachments(messages)
    assert result == [{"type": "file", "path": "/p/ok.txt", "displayName": "ok.txt"}]


def test_extract_attachments_skips_missing_path(prov):
    """path フィールドが欠損 / 空 / 非 str の項目は防御的に skip."""
    messages = [
        HumanMessage(content="x", additional_kwargs={"attachments": [
            {"kind": "file", "name": "no_path.txt"},                   # path 欠損
            {"kind": "file", "name": "empty.txt", "path": ""},          # 空文字
            {"kind": "file", "name": "wrong_type.txt", "path": 123},   # 非 str
            {"kind": "file", "name": "ok.txt", "path": "/p/ok.txt"},
            "not-a-dict",                                               # 非 dict
        ]}),
    ]
    result = prov._extract_attachments(messages)
    assert result == [{"type": "file", "path": "/p/ok.txt", "displayName": "ok.txt"}]


def test_extract_attachments_displayname_falls_back_to_path_basename(prov):
    """name 欠損時は path basename を displayName に補完する.

    Wave 0 Plan 01 Task 2 で確認済: SDK 0.2.0 の FileAttachment は
    `__required_keys__ = frozenset({'displayName', 'type', 'path'})` のため
    displayName は必ず埋める必要がある (D-15 の変換ルールで必ず埋める方針).
    """
    messages = [
        HumanMessage(content="x", additional_kwargs={"attachments": [
            {"kind": "file", "path": "/shared/thread-files/u/t/missing-name.csv"},
            {"kind": "file", "name": "", "path": "/p/empty-name.txt"},
            {"kind": "file", "name": 123, "path": "/p/non-str-name.txt"},  # 非 str
        ]}),
    ]
    result = prov._extract_attachments(messages)
    assert result is not None
    # すべての entry に displayName が必ず存在することを確認
    for entry in result:
        assert "displayName" in entry, f"displayName missing in {entry}"
        assert isinstance(entry["displayName"], str) and entry["displayName"]
    # basename へのフォールバックが効いていることを具体検証
    assert result[0]["displayName"] == os.path.basename("/shared/thread-files/u/t/missing-name.csv")
    assert result[1]["displayName"] == os.path.basename("/p/empty-name.txt")
    assert result[2]["displayName"] == os.path.basename("/p/non-str-name.txt")


# ---------------------------------------------------------------------------
# Test 5-6: _agenerate attachments wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agenerate_calls_send_and_wait_with_attachments(mock_copilot):
    """_agenerate が attachments kwarg 付きで session.send_and_wait を呼ぶ."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(model="claude-sonnet-4.6", github_token="ghu_test")
    messages = [
        HumanMessage(
            content="x",
            additional_kwargs={"attachments": [
                {"kind": "file", "name": "a.txt", "path": "/p/a.txt"}
            ]},
        )
    ]
    await provider._agenerate(messages)

    mock_copilot["session"].send_and_wait.assert_awaited_once()
    _, kwargs = mock_copilot["session"].send_and_wait.call_args
    assert kwargs["attachments"] == [
        {"type": "file", "path": "/p/a.txt", "displayName": "a.txt"}
    ]
    assert "timeout" in kwargs


@pytest.mark.asyncio
async def test_agenerate_sends_none_when_no_attachments(mock_copilot):
    """attachments が無い HumanMessage では attachments=None で SDK を呼ぶ."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(model="gpt-4.1", github_token="ghu_test")
    await provider._agenerate([HumanMessage(content="hello")])

    mock_copilot["session"].send_and_wait.assert_awaited_once()
    _, kwargs = mock_copilot["session"].send_and_wait.call_args
    assert kwargs["attachments"] is None


# ---------------------------------------------------------------------------
# Test 7-8: list_models conversion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_models_converts_modelinfo_to_dict():
    """list_models は SDK ModelInfo を D-14 準拠 dict に変換して返す."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(github_token="ghu_test")

    # _client を直接差し替えて list_models() の戻り値を制御
    mock_client = AsyncMock()
    mock_client.list_models = AsyncMock(return_value=[
        _mk_modelinfo(
            "claude-sonnet-4.6", "Claude Sonnet 4.6",
            vision=True,
            limits_dict={
                "max_prompt_images": 5,
                "max_prompt_image_size": 10485760,
                "supported_media_types": ["image/png", "image/jpeg", "image/webp"],
            },
            mult=1.0,
        ),
    ])
    provider._client = mock_client

    result = await provider.list_models()
    assert len(result) == 1
    entry = result[0]
    assert entry["id"] == "claude-sonnet-4.6"
    assert entry["name"] == "Claude Sonnet 4.6"
    assert entry["vision"] is True
    assert entry["vision_limits"] == {
        "max_prompt_images": 5,
        "max_prompt_image_size": 10485760,
        "supported_media_types": ["image/png", "image/jpeg", "image/webp"],
    }
    assert entry["billing_multiplier"] == 1.0


@pytest.mark.asyncio
async def test_list_models_vision_false_returns_none_limits():
    """vision=False のモデルは vision_limits: None を返す (D-14 fail-safe)."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(github_token="ghu_test")
    mock_client = AsyncMock()
    mock_client.list_models = AsyncMock(return_value=[
        _mk_modelinfo("gpt-4.1", "GPT-4.1", vision=False, limits_dict=None, mult=0.0),
    ])
    provider._client = mock_client

    result = await provider.list_models()
    assert len(result) == 1
    assert result[0]["vision"] is False
    assert result[0]["vision_limits"] is None
    assert result[0]["billing_multiplier"] == 0.0


# ---------------------------------------------------------------------------
# Test 9-10: is_vision_model
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_vision_model_lookup():
    """is_vision_model は list_models の vision フラグを参照する."""
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(github_token="ghu_test")
    mock_client = AsyncMock()
    mock_client.list_models = AsyncMock(return_value=[
        _mk_modelinfo("claude-sonnet-4.6", "Claude Sonnet", vision=True, limits_dict={"max_prompt_images": 5}),
        _mk_modelinfo("gpt-4.1", "GPT-4.1", vision=False),
    ])
    provider._client = mock_client

    assert await provider.is_vision_model("claude-sonnet-4.6") is True
    assert await provider.is_vision_model("gpt-4.1") is False
    assert await provider.is_vision_model("unknown-model") is False


@pytest.mark.asyncio
async def test_is_vision_model_failsafe_on_exception():
    """list_models() が例外を上げても is_vision_model は False を返す (fail-safe).

    D-18 の vision drop 判定で利用するので、SDK エラーで「vision 対応」と
    誤判定して画像を送るのを防ぐ.
    """
    from app.providers.copilot import ChatCopilot

    provider = ChatCopilot(github_token="ghu_test")
    mock_client = AsyncMock()
    mock_client.list_models = AsyncMock(side_effect=RuntimeError("SDK down"))
    provider._client = mock_client

    # 例外を上げず False を返すこと
    assert await provider.is_vision_model("claude-sonnet-4.6") is False
