"""Phase 38 Plan 03: post-process rename helper `_rename_new_outputs` の unit test scaffold。

VALIDATION.md Task ID マッピング:
- 38-03-02 → test_snapshot_diff_renames_only_new   (Plan 03 で実装、本 plan は skip scaffold)
- 38-03-03 → test_skips_already_prefixed           (Plan 03 で実装、本 plan は skip scaffold)
- (補強)   → test_excludes_pyc_files                (Plan 03 で実装、本 plan は skip scaffold)

Pattern source: 38-RESEARCH.md §"Pattern 1: snapshot diff vs mtime 判定"
38-PATTERNS.md §"Plan 03-A execute_python post-process rename"

GREENFIELD (analog なし) — snapshot diff の単体検証は本 phase で初導入。
`_rename_new_outputs(folder, before_set)` を `mcp_server/tools/execute_python.py` に置く
(Plan 03 で実装) ことを前提とする。
"""
from __future__ import annotations

import os

import pytest


@pytest.mark.skip(
    reason=(
        "Plan 03 (38-03) で execute_python.py に _rename_new_outputs / _is_already_prefixed "
        "を実装してから green 化 — 38-03-02"
    )
)
def test_snapshot_diff_renames_only_new(tmp_path):
    """38-03-02 — before snapshot に無い新規ファイルだけ {ts}_{name} にリネーム。

    期待挙動:
    - before に含まれるファイルは触らない
    - before に含まれない新規ファイルは UTC timestamp prefix を付与してリネーム
    - リネーム後のファイル名リストを返す
    """
    raise AssertionError("Plan 03 で実装")


@pytest.mark.skip(
    reason=(
        "Plan 03 (38-03) で _is_already_prefixed 実装と同時に green 化 — 38-03-03"
    )
)
def test_skips_already_prefixed(tmp_path):
    """38-03-03 — 既に `YYYYMMDDTHHMMSS_` prefix が付いているファイルは二重 prefix されない。

    期待挙動: prefix 付きのファイルは rename されず、そのままの名前で list に含まれる。
    """
    raise AssertionError("Plan 03 で実装")


@pytest.mark.skip(
    reason=(
        "Plan 03 (38-03) で `.pyc` / `__pycache__/` 除外ロジック実装と同時に green 化"
    )
)
def test_excludes_pyc_files(tmp_path):
    """`.pyc` / `__pycache__/` 配下のファイルは AI への露出禁止 (RESEARCH §Anti-Patterns)。

    Python subprocess が cwd で実行する中間ファイルを成果物として誤って bundle しないことを保証。
    """
    raise AssertionError("Plan 03 で実装")
