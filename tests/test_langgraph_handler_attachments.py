"""Phase 37: thread フォルダ scan + SystemMessage prepend の unit test.

Phase 37.1 で attachments_helper.py に抽出された scan/build を検証する。
"""
from __future__ import annotations


def test_scan_returns_sorted_metadata(tmp_path, monkeypatch):
    """scan_thread_attachments が name/size/modified_at/ext を返す。"""
    from app.jobs.handlers import attachments_helper
    folder = tmp_path / "user-a" / "t-1"
    folder.mkdir(parents=True)
    (folder / "20260421T120000_report.pdf").write_bytes(b"x" * 100)
    (folder / "20260421T120500_data.xlsx").write_bytes(b"y" * 200)
    monkeypatch.setattr(attachments_helper, "THREAD_FILES_DIR", str(tmp_path))

    result = attachments_helper.scan_thread_attachments("t-1", "user-a")
    assert len(result) == 2
    names = [r["name"] for r in result]
    assert names == sorted(names)   # 時系列 prefix により sorted と一致
    assert result[0]["size"] == 100
    assert result[0]["ext"] == ".pdf"
    # S-03: modified_at は float (epoch seconds)
    assert isinstance(result[0]["modified_at"], float)


def test_scan_empty_folder(tmp_path, monkeypatch):
    """フォルダ不在時は [] を返す。"""
    from app.jobs.handlers import attachments_helper
    monkeypatch.setattr(attachments_helper, "THREAD_FILES_DIR", str(tmp_path))
    assert attachments_helper.scan_thread_attachments("nope", "nope") == []


def test_scan_missing_context():
    """thread_id/github_login が空文字の場合は即 []。"""
    from app.jobs.handlers import attachments_helper
    assert attachments_helper.scan_thread_attachments("", "user") == []
    assert attachments_helper.scan_thread_attachments("t", "") == []


def test_build_hint_empty():
    from app.jobs.handlers import attachments_helper
    assert attachments_helper.build_attachments_hint([]) == ""


def test_build_hint_contains_filename_and_tool_instruction():
    from app.jobs.handlers import attachments_helper
    meta = [{"name": "report.pdf", "size": 1500, "modified_at": 0.0, "ext": ".pdf"}]
    hint = attachments_helper.build_attachments_hint(meta)
    assert "report.pdf" in hint
    assert "attachments_extract" in hint
    assert "attachments_list" in hint
