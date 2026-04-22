"""Phase 37 Wave 1: attachments_extract MCP tool tests (GREEN).

Covers FIN-03 SC-1 (抽出) / SC-2 (エラー) / SC-4 (path traversal) / D-13 (truncation) / D-19 (5 error codes).
Plan 03 Task 3: Wave 0 xfail スケルトンを実実装に置き換える。

注意: markitdown は mcp_server 専用依存のためルート環境にない。
      各テストは attachments モジュールの _extract_text をモックして markitdown を呼ばずに検証する。
      password_protected テストでは markitdown.FileConversionException をインポートして使うが、
      mcp_server の sys.path 経由で import するため利用可能。
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
async def test_extract_pdf(tmp_path, monkeypatch):
    """FIN-03 SC-1: attachments_extract_core が content を返す。"""
    from tools import attachments

    thread_dir = tmp_path / "user-a" / "thread-1"
    thread_dir.mkdir(parents=True)
    sample_pdf = thread_dir / "report.pdf"
    sample_pdf.write_bytes(b"%PDF-1.4\ndummy content")

    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

    async def _fake_extract(path: str) -> str:
        return "extracted content"

    monkeypatch.setattr(attachments, "_extract_text", _fake_extract)

    result = await attachments.attachments_extract_core("thread-1", "user-a", "report.pdf")
    assert result["error"] is None
    assert "extracted content" in result["content"]
    assert result["truncated"] is False


@pytest.mark.asyncio
async def test_extract_password_protected(tmp_path, monkeypatch):
    """FIN-03 SC-2 / D-19: パスワード保護 PDF が error.code == 'password' を返す。

    markitdown は mcp_server 依存のため mcp_server sys.path 経由でインポートする。
    """
    from tools import attachments

    # markitdown が利用できない場合はスキップ
    markitdown = pytest.importorskip("markitdown", reason="markitdown not installed in this env")
    FileConversionException = markitdown.FileConversionException

    thread_dir = tmp_path / "u" / "t"
    thread_dir.mkdir(parents=True)
    (thread_dir / "locked.pdf").write_bytes(b"x")
    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

    class _FakeAttempt:
        exc_info = (type("PDFPasswordIncorrect", (), {}), Exception("password required"), None)

    async def _fake_extract(path: str) -> str:
        raise FileConversionException("locked", [_FakeAttempt()])

    monkeypatch.setattr(attachments, "_extract_text", _fake_extract)
    result = await attachments.attachments_extract_core("t", "u", "locked.pdf")
    assert result["error"]["code"] == "password"


@pytest.mark.asyncio
async def test_extract_size_over(tmp_path, monkeypatch):
    """FIN-03 SC-2 / D-09: 100MB 超過で error.code == 'size_over'。"""
    from tools import attachments

    thread_dir = tmp_path / "u" / "t"
    thread_dir.mkdir(parents=True)
    big = thread_dir / "huge.pdf"
    with open(big, "wb") as f:
        f.seek(101 * 1024 * 1024)
        f.write(b"\x00")

    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))
    result = await attachments.attachments_extract_core("t", "u", "huge.pdf")
    assert result["error"]["code"] == "size_over"


@pytest.mark.asyncio
async def test_extract_timeout(tmp_path, monkeypatch):
    """FIN-03 SC-2 / D-19: 60 秒タイムアウトで error.code == 'extract_timeout'。"""
    import asyncio
    from tools import attachments

    thread_dir = tmp_path / "u" / "t"
    thread_dir.mkdir(parents=True)
    (thread_dir / "slow.pdf").write_bytes(b"x")
    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

    async def _fake_extract(path: str) -> str:
        raise asyncio.TimeoutError()

    monkeypatch.setattr(attachments, "_extract_text", _fake_extract)
    result = await attachments.attachments_extract_core("t", "u", "slow.pdf")
    assert result["error"]["code"] == "extract_timeout"


@pytest.mark.asyncio
async def test_path_traversal(tmp_path, monkeypatch):
    """FIN-03 SC-4 / D-18: filename='../../../etc/passwd' が拒否される。"""
    from tools import attachments

    (tmp_path / "u" / "t").mkdir(parents=True)
    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))
    result = await attachments.attachments_extract_core("t", "u", "../../etc/passwd")
    assert result["error"]["code"] == "corrupt"
    assert (
        "traversal" in result["error"]["message"].lower()
        or "invalid" in result["error"]["message"].lower()
    )


@pytest.mark.asyncio
async def test_truncation(tmp_path, monkeypatch):
    """D-13: 50000 文字超の抽出で truncated: True + truncated_chars: N が返る。"""
    from tools import attachments

    thread_dir = tmp_path / "u" / "t"
    thread_dir.mkdir(parents=True)
    (thread_dir / "long.pdf").write_bytes(b"x")
    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

    async def _fake_extract(path: str) -> str:
        return "A" * (attachments.MAX_CHARS_PER_FILE + 1234)

    monkeypatch.setattr(attachments, "_extract_text", _fake_extract)

    result = await attachments.attachments_extract_core("t", "u", "long.pdf")
    assert result["truncated"] is True
    assert result["truncated_chars"] == 1234
    assert len(result["content"]) == attachments.MAX_CHARS_PER_FILE
