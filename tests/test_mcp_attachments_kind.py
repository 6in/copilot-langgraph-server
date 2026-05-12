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


@pytest.mark.skip(
    reason=(
        "Plan 02 (38-02) で attachments_list_core 拡張 (kind フィールド + _generated/ scan) "
        "と同時に green 化 — 38-02-01"
    )
)
@pytest.mark.asyncio
async def test_returns_both_kinds(tmp_path, monkeypatch):
    """38-02-01 — user_upload (直下) と generated (_generated/) を両方含む list が返る。

    期待挙動:
    - thread フォルダ直下のファイルは `kind: 'user_upload'`
    - `_generated/` 配下のファイルは `kind: 'generated'`
    - 両者を flat list で返却、order は実装依存 (テスト側で sort して比較する)
    """
    raise AssertionError("Plan 02 で実装")
