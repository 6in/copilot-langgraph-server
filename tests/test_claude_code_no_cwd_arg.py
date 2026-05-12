"""Phase 38 Plan 03: claude_code シグネチャから cwd 引数を削除する変更の signature-level 検証。

VALIDATION.md Task ID マッピング:
- 38-03-04 → test_signature_has_no_cwd

Pattern source: 38-PATTERNS.md §"Plan 03-B claude_code.py (MODIFY: cwd 引数削除 + post-process rename)"
CONTEXT.md D-09: claude_code は cwd 引数を削除し、常に `_generated/` で実行する固定仕様にする。

GREENFIELD (analog なし) — trivial。`inspect.signature(claude_code).parameters` を直接 assert する。
"""
from __future__ import annotations

import inspect

from mcp_server.tools.claude_code import claude_code


def test_signature_has_no_cwd():
    """38-03-04 — `inspect.signature(claude_code).parameters` に `cwd` が含まれないこと。

    期待挙動:
    - claude_code(prompt, headers=None) のシグネチャ。`cwd` 引数は削除済 (D-09)。
    - `headers` 引数経由で `_resolve_generated_folder(headers)` が cwd を解決する。
    """
    sig = inspect.signature(claude_code)
    assert "cwd" not in sig.parameters, (
        f"Phase 38 D-09: cwd 引数は削除されているはずだが残っている: "
        f"{list(sig.parameters.keys())}"
    )
    # headers 引数が追加されていること
    assert "headers" in sig.parameters, (
        f"Phase 38 D-09: headers 引数が追加されているはずだが見つからない: "
        f"{list(sig.parameters.keys())}"
    )
    # prompt は維持
    assert "prompt" in sig.parameters
