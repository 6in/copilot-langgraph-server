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


# ---------------------------------------------------------------------------
# Phase 38 D-18 拡張: scan に _generated/ サブフォルダ + kind discriminator を追加
# ---------------------------------------------------------------------------


def test_scan_includes_kind_user_upload_for_direct_files(tmp_path, monkeypatch):
    """直下のファイルには kind='user_upload' が必ず付く (Phase 38 D-18)。"""
    from app.jobs.handlers import attachments_helper

    folder = tmp_path / "user-a" / "t-1"
    folder.mkdir(parents=True)
    (folder / "20260512T120000_input.pdf").write_bytes(b"x" * 50)
    monkeypatch.setattr(attachments_helper, "THREAD_FILES_DIR", str(tmp_path))

    result = attachments_helper.scan_thread_attachments("t-1", "user-a")
    assert len(result) == 1
    assert result[0]["kind"] == "user_upload"


def test_scan_includes_generated_subfolder_with_kind_generated(tmp_path, monkeypatch):
    """_generated/ サブフォルダの entry には kind='generated' が付く (Phase 38 D-18)。"""
    from app.jobs.handlers import attachments_helper

    folder = tmp_path / "user-a" / "t-2"
    gen = folder / "_generated"
    gen.mkdir(parents=True)
    (folder / "20260512T120000_input.pdf").write_bytes(b"a" * 10)
    (gen / "20260512T130000_chart.png").write_bytes(b"\x89PNG" + b"x" * 6)

    monkeypatch.setattr(attachments_helper, "THREAD_FILES_DIR", str(tmp_path))

    result = attachments_helper.scan_thread_attachments("t-2", "user-a")
    # 2 entries: input.pdf (user_upload) + chart.png (generated)
    assert len(result) == 2
    kinds_by_name = {r["name"]: r["kind"] for r in result}
    assert kinds_by_name["20260512T120000_input.pdf"] == "user_upload"
    assert kinds_by_name["20260512T130000_chart.png"] == "generated"


def test_scan_does_not_recurse_below_generated(tmp_path, monkeypatch):
    """`_generated/` の更にサブフォルダは scan しない (Pitfall 4)。"""
    from app.jobs.handlers import attachments_helper

    folder = tmp_path / "user-a" / "t-3"
    nested = folder / "_generated" / "nested"
    nested.mkdir(parents=True)
    (nested / "20260512T140000_deep.txt").write_bytes(b"deep")

    monkeypatch.setattr(attachments_helper, "THREAD_FILES_DIR", str(tmp_path))
    result = attachments_helper.scan_thread_attachments("t-3", "user-a")
    # nested/ の中身は出ない
    names = [r["name"] for r in result]
    assert "20260512T140000_deep.txt" not in names


def test_scan_handles_missing_generated_subfolder(tmp_path, monkeypatch):
    """`_generated/` が存在しない場合でも例外を投げずに user_upload のみ返す。"""
    from app.jobs.handlers import attachments_helper

    folder = tmp_path / "user-a" / "t-4"
    folder.mkdir(parents=True)
    (folder / "20260512T120000_a.txt").write_bytes(b"a")

    monkeypatch.setattr(attachments_helper, "THREAD_FILES_DIR", str(tmp_path))
    result = attachments_helper.scan_thread_attachments("t-4", "user-a")
    assert len(result) == 1
    assert result[0]["kind"] == "user_upload"


def test_build_hint_shows_kind_labels():
    """build_attachments_hint が kind='generated' → '[AI 生成]'、それ以外 → '[添付]' を表示する。"""
    from app.jobs.handlers import attachments_helper

    meta = [
        {"name": "report.pdf", "size": 1500, "modified_at": 0.0, "ext": ".pdf",
         "kind": "user_upload"},
        {"name": "chart.png", "size": 2048, "modified_at": 1.0, "ext": ".png",
         "kind": "generated"},
    ]
    hint = attachments_helper.build_attachments_hint(meta)
    # 添付チップ
    assert "report.pdf" in hint
    assert "[添付]" in hint
    # AI 生成チップ
    assert "chart.png" in hint
    assert "[AI 生成]" in hint
    # tool 案内文も維持
    assert "attachments_extract" in hint
    assert "attachments_list" in hint


def test_build_hint_legacy_entry_without_kind_defaults_to_attached_label():
    """kind フィールド欠落の entry は '[添付]' で防御的に処理する (legacy 互換)."""
    from app.jobs.handlers import attachments_helper

    meta = [{"name": "legacy.pdf", "size": 100, "modified_at": 0.0, "ext": ".pdf"}]
    hint = attachments_helper.build_attachments_hint(meta)
    assert "legacy.pdf" in hint
    assert "[添付]" in hint
    assert "[AI 生成]" not in hint
