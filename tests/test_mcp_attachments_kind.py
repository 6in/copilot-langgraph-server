"""Phase 38 Plan 02: attachments_list MCP tool に kind フィールド + `_generated/` scan 拡張。

VALIDATION.md Task ID マッピング:
- 38-02-01 → test_returns_both_kinds (Plan 02 で実装、本 plan は skip scaffold)

Analog: tests/test_attachments_list.py L20-46 (`test_list_returns_metadata`)
Pattern: 38-PATTERNS.md §"Plan 02-B mcp_server/tools/attachments.py" §"Plan 06 Tests"

CONTEXT.md D-06: attachments_list の戻り値に `kind: 'user_upload' | 'generated'` フィールドを追加し、
`_generated/` 配下も含めて返す。SystemMessage prepend (Phase 37 D-11) も両方含めた flat list で送る。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# mcp_server を import path に追加 (tests/test_attachments_list.py L12-14 と同じ仕組み)
_MCP_SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
if str(_MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER_DIR))

pytest.importorskip("fastmcp", reason="fastmcp not installed in root env")


@pytest.mark.asyncio
async def test_returns_both_kinds(tmp_path, monkeypatch):
    """38-02-01 — user_upload (直下) と generated (_generated/) を両方含む list が返る。

    期待挙動 (CONTEXT.md D-06):
    - thread フォルダ直下のファイルは `kind: 'user_upload'`
    - `_generated/` 配下のファイルは `kind: 'generated'`
    - 両者を flat list で返却、order は実装依存 (テスト側で sort して比較する)
    - `_generated/` サブフォルダ scan は 1 段のみ (再帰しない、RESEARCH Pitfall 4)
    """
    from tools import attachments

    # thread フォルダ直下に user upload を 1 件配置
    thread_dir = tmp_path / "user-a" / "t-1"
    thread_dir.mkdir(parents=True)
    (thread_dir / "20260512T120000_input.pdf").write_bytes(b"x" * 50)

    # `_generated/` 配下に worker 生成ファイルを 1 件配置
    gen_dir = thread_dir / "_generated"
    gen_dir.mkdir()
    (gen_dir / "20260512T120100_output.png").write_bytes(b"y" * 30)

    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

    result = await attachments.attachments_list_core("t-1", "user-a")

    # 2 件 (user_upload + generated) が flat list で返ることを確認
    assert len(result) == 2, result
    kinds = sorted([r["kind"] for r in result])
    assert kinds == ["generated", "user_upload"]

    # dict shape の主要フィールドが両方に存在することを確認 (kind 追加で
    # 既存スキーマを壊していないこと)
    for entry in result:
        assert "name" in entry
        assert "size" in entry
        assert "ext" in entry
        assert "mime_type" in entry
        assert "modified_at" in entry
        assert "kind" in entry
        assert entry["kind"] in ("user_upload", "generated")

    # 内訳: name → kind マッピングを確認
    name_to_kind = {r["name"]: r["kind"] for r in result}
    assert name_to_kind["20260512T120000_input.pdf"] == "user_upload"
    assert name_to_kind["20260512T120100_output.png"] == "generated"
