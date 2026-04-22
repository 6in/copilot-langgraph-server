"""Phase 37 Wave 1: attachments_list MCP tool tests (GREEN).

Plan 03 Task 3: Wave 0 xfail スケルトンを実実装に置き換える。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_MCP_SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
if str(_MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER_DIR))

pytest.importorskip("fastmcp", reason="fastmcp not installed in root env")


@pytest.mark.asyncio
async def test_list_returns_metadata(tmp_path, monkeypatch):
    """FIN-03 SC-3: tmp_path に PDF を置いて attachments_list_core がメタデータを返す。"""
    from tools import attachments

    thread_dir = tmp_path / "user-a" / "thread-1"
    thread_dir.mkdir(parents=True)
    (thread_dir / "20260421T120000_report.pdf").write_bytes(b"x" * 100)
    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

    result = await attachments.attachments_list_core("thread-1", "user-a")
    assert len(result) == 1
    assert result[0]["name"] == "20260421T120000_report.pdf"
    assert result[0]["size"] == 100
    assert result[0]["ext"] == ".pdf"
    # S-03: modified_at は float (epoch seconds)
    assert isinstance(result[0]["modified_at"], float)


@pytest.mark.asyncio
async def test_list_empty_folder(tmp_path, monkeypatch):
    """フォルダ不在時は [] を返す。"""
    from tools import attachments

    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))
    result = await attachments.attachments_list_core("nope", "nope")
    assert result == []
