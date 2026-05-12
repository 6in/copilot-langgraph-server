"""Phase 38 Plan 03: execute_python の cwd 切替 + /tmp fallback + mkdir 冪等 の unit test scaffold。

VALIDATION.md Task ID マッピング:
- 38-03-01 → test_writes_to_generated_folder        (Plan 03 で実装、本 plan は skip scaffold)
- (補強)   → test_falls_back_to_tmp_without_headers (Plan 03 で実装、本 plan は skip scaffold)

Pattern source: 38-PATTERNS.md §"Plan 03-A execute_python (MODIFY: cwd 切替 + post-process rename)"
38-RESEARCH.md §"Pattern 5: sandbox cwd 切替"

GREENFIELD (analog なし) — `_resolve_generated_folder(headers)` を mock 化 subprocess で検証する。
Plan 03 で `mcp_server/tools/execute_python.py` に `_resolve_generated_folder` を実装することを前提とする。
"""
from __future__ import annotations

import pytest


@pytest.mark.skip(
    reason=(
        "Plan 03 (38-03) で _resolve_generated_folder + cwd 切替実装と同時に green 化 — 38-03-01"
    )
)
@pytest.mark.asyncio
async def test_writes_to_generated_folder(tmp_path, monkeypatch):
    """38-03-01 — execute_python が x-thread-id / x-github-login ヘッダから解決した
    `_generated/` cwd 配下で subprocess を実行する。

    期待挙動:
    - THREAD_FILES_DIR/<login>/<tid>/_generated/ を realpath で解決
    - 親フォルダが無ければ mkdir -p で冪等に作成
    - subprocess の cwd 引数として渡される
    """
    raise AssertionError("Plan 03 で実装")


@pytest.mark.skip(
    reason=(
        "Plan 03 (38-03) で headers 不足時の /tmp fallback 実装と同時に green 化"
    )
)
@pytest.mark.asyncio
async def test_falls_back_to_tmp_without_headers():
    """ヘッダ不在 or path traversal 検出時に `/tmp` に fallback する。

    期待挙動:
    - x-thread-id / x-github-login が空 → `/tmp`
    - realpath が THREAD_FILES_DIR 配下に収まらない → `/tmp`
    - `/tmp` cwd では post-process rename を実行しない (wrapper 側で skip)
    """
    raise AssertionError("Plan 03 で実装")
