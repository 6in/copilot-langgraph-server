"""Phase 38 Plan 03: claude_code シグネチャから cwd 引数を削除する変更の signature-level 検証 scaffold。

VALIDATION.md Task ID マッピング:
- 38-03-04 → test_signature_has_no_cwd (Plan 03 で実装、本 plan は skip scaffold)

Pattern source: 38-PATTERNS.md §"Plan 03-B claude_code.py (MODIFY: cwd 引数削除 + post-process rename)"
CONTEXT.md D-09: claude_code は cwd 引数を削除し、常に `_generated/` で実行する固定仕様にする。

GREENFIELD (analog なし) — trivial。`inspect.signature(claude_code).parameters` を直接 assert する。
"""
from __future__ import annotations

import pytest


@pytest.mark.skip(
    reason=(
        "Plan 03 (38-03) で claude_code シグネチャから cwd 削除と同時に green 化 — 38-03-04"
    )
)
def test_signature_has_no_cwd():
    """38-03-04 — `inspect.signature(claude_code).parameters` に `cwd` が含まれないこと。

    期待挙動:
    - claude_code(prompt, headers=None) のシグネチャ。`cwd` 引数は削除済。
    - `headers` 引数経由で `_resolve_generated_folder(headers)` が cwd を解決する。
    """
    import inspect
    import sys
    from pathlib import Path

    mcp_dir = Path(__file__).parent.parent / "mcp_server"
    if str(mcp_dir) not in sys.path:
        sys.path.insert(0, str(mcp_dir))

    from tools.claude_code import claude_code  # noqa: E402, PLC0415

    sig = inspect.signature(claude_code)
    assert "cwd" not in sig.parameters, (
        f"cwd should be removed from claude_code signature, got params: "
        f"{list(sig.parameters.keys())}"
    )
