"""Phase 38 Plan 03: post-process rename helper `_rename_new_outputs` の unit test。

VALIDATION.md Task ID マッピング:
- 38-03-02 → test_snapshot_diff_renames_only_new
- 38-03-03 → test_skips_already_prefixed
- (補強)   → test_excludes_pyc_files

Pattern source: 38-RESEARCH.md §"Pattern 1: snapshot diff vs mtime 判定"
38-PATTERNS.md §"Plan 03-A execute_python post-process rename"

GREENFIELD (analog なし) — snapshot diff の単体検証は本 phase で初導入。
`_rename_new_outputs(folder, before_set)` は `mcp_server/tools/execute_python.py` に置く。
"""
from __future__ import annotations

import os
import re

from mcp_server.tools.execute_python import (
    _is_already_prefixed,
    _rename_new_outputs,
)


_PREFIX_RE = re.compile(r"^\d{8}T\d{6}_")


def test_snapshot_diff_renames_only_new(tmp_path):
    """38-03-02 — before snapshot に無い新規ファイルだけ {ts}_{name} にリネーム。

    期待挙動:
    - before に含まれるファイルは触らない
    - before に含まれない新規ファイルは UTC timestamp prefix を付与してリネーム
    - リネーム後のファイル名リストを返す
    """
    folder = str(tmp_path)
    # before snapshot: old.png は既に存在
    (tmp_path / "old.png").write_bytes(b"old content")
    before = set(os.listdir(folder))
    assert before == {"old.png"}

    # subprocess 実行を模して新ファイルを 2 つ追加
    (tmp_path / "new.png").write_bytes(b"new image bytes")
    (tmp_path / "another.csv").write_text("a,b,c\n1,2,3\n", encoding="utf-8")

    renamed = _rename_new_outputs(folder, before)

    # old.png はそのまま残る (before に含まれていたため)
    assert os.path.isfile(tmp_path / "old.png")
    # 戻り値には old.png は含まれない (snapshot diff の after - before のみ)
    assert "old.png" not in renamed
    # new.png / another.csv は ts prefix 付きで rename された
    assert len(renamed) == 2
    for name in renamed:
        assert _PREFIX_RE.match(name), f"prefix missing on: {name}"
        assert name.endswith("_new.png") or name.endswith("_another.csv")
    # disk 側でも rename が完了している (raw 名は消えている)
    existing = set(os.listdir(folder))
    assert "new.png" not in existing
    assert "another.csv" not in existing
    assert "old.png" in existing
    # rename 後の物理ファイルも存在
    for name in renamed:
        assert os.path.isfile(tmp_path / name)


def test_skips_already_prefixed(tmp_path):
    """38-03-03 — 既に `YYYYMMDDTHHMMSS_` prefix が付いているファイルは二重 prefix されない。

    期待挙動: prefix 付きのファイルは rename されず、そのままの名前で list に含まれる。
    """
    folder = str(tmp_path)
    # before = 空セット → AI が `20260601T120000_existing.png` を直接生成したケース
    existing_name = "20260601T120000_existing.png"
    (tmp_path / existing_name).write_bytes(b"already prefixed")

    renamed = _rename_new_outputs(folder, set())

    # 二重 prefix `{ts2}_20260601T120000_existing.png` が **出現しない**
    files_on_disk = set(os.listdir(folder))
    assert existing_name in files_on_disk, "既存 prefix 付きファイルは触らないはず"
    # 二重 prefix チェック
    for name in files_on_disk:
        # `{8桁}T{6桁}_{8桁}T{6桁}_existing.png` パターンは出てはならない
        assert not re.match(r"^\d{8}T\d{6}_\d{8}T\d{6}_", name), (
            f"二重 prefix が発生: {name}"
        )
    # 戻り値リストにも prefix 付き名前 1 件のみが含まれる
    assert renamed == [existing_name]

    # 補助: helper の predicate 単体検証
    assert _is_already_prefixed("20260601T120000_foo.png") is True
    assert _is_already_prefixed("foo.png") is False
    assert _is_already_prefixed("2026060T120000_foo.png") is False  # 桁不足


def test_excludes_pyc_files(tmp_path):
    """`.pyc` / 中間ファイルは AI への露出禁止 (RESEARCH §Anti-Patterns)。

    Python subprocess が cwd で実行する中間ファイルを成果物として誤って bundle しないことを保証。
    """
    folder = str(tmp_path)
    (tmp_path / "script.pyc").write_bytes(b"\x42\x42\x42")  # 擬似 pyc
    (tmp_path / "output.txt").write_text("hello", encoding="utf-8")

    renamed = _rename_new_outputs(folder, set())

    # output.txt は ts prefix 付きで rename
    assert len(renamed) == 1
    assert _PREFIX_RE.match(renamed[0]), f"prefix missing on: {renamed[0]}"
    assert renamed[0].endswith("_output.txt")
    # script.pyc は rename も touch もされていない (元のまま)
    files_on_disk = set(os.listdir(folder))
    assert "script.pyc" in files_on_disk
    # ts prefix の付いた pyc も出ない
    for name in files_on_disk:
        assert not name.endswith(".pyc") or name == "script.pyc"
