"""Phase 38 Plan 03: execute_python の cwd 切替 + /tmp fallback + mkdir 冪等 の unit test。

VALIDATION.md Task ID マッピング:
- 38-03-01 → test_writes_to_generated_folder
- (補強)   → test_falls_back_to_tmp_without_headers

Pattern source: 38-PATTERNS.md §"Plan 03-A execute_python (MODIFY: cwd 切替 + post-process rename)"
38-RESEARCH.md §"Pattern 5: sandbox cwd 切替"

GREENFIELD (analog なし) — `_resolve_generated_folder(headers)` を mock 化 subprocess で検証する。
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

import mcp_server.tools.execute_python as ep


@pytest.mark.asyncio
async def test_writes_to_generated_folder(tmp_path, monkeypatch):
    """38-03-01 — execute_python が x-thread-id / x-github-login ヘッダから解決した
    `_generated/` cwd 配下で subprocess を実行する。

    期待挙動:
    - THREAD_FILES_DIR/<login>/<tid>/_generated/ を realpath で解決
    - 親フォルダが無ければ mkdir -p で冪等に作成
    - subprocess の cwd 引数として渡される
    """
    # THREAD_FILES_DIR を tmp_path に差し替え (realpath guard 内の base prefix も追随)
    fake_root = tmp_path / "thread-files"
    fake_root.mkdir()
    monkeypatch.setattr(ep, "THREAD_FILES_DIR", str(fake_root))
    # allowlist チェックを通過させるため、無害な `pass` 相当の単純コードを渡す
    code = "x = 1"

    # subprocess を mock 化 (実際に python3 を spawn しない)
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_proc.returncode = 0
    captured = {}

    async def fake_spawn(*args, **kwargs):
        captured.update(kwargs)
        return mock_proc

    with patch("mcp_server.tools.execute_python.asyncio.create_subprocess_exec",
               side_effect=fake_spawn):
        result = await ep.execute_python(
            code=code,
            timeout=5,
            headers={"x-thread-id": "tid-abc", "x-github-login": "alice"},
        )

    # subprocess 呼び出しの cwd を確認
    assert "cwd" in captured, "cwd が subprocess に渡されていない"
    cwd_passed = captured["cwd"]
    # _generated/ で終わるパスであること
    assert cwd_passed.endswith("_generated"), f"unexpected cwd: {cwd_passed}"
    # alice / tid-abc が path に含まれていること
    assert "alice" in cwd_passed
    assert "tid-abc" in cwd_passed
    # フォルダが mkdir -p で作成済 (冪等性)
    assert os.path.isdir(cwd_passed)
    # 結果 dict の形状確認 (regression 防止)
    assert result["exit_code"] == 0


@pytest.mark.asyncio
async def test_falls_back_to_tmp_without_headers():
    """ヘッダ不在 or path traversal 検出時に `/tmp` に fallback する。

    期待挙動:
    - x-thread-id / x-github-login が空 → `/tmp`
    - realpath が THREAD_FILES_DIR 配下に収まらない → `/tmp`
    """
    # 1. headers=None
    assert ep._resolve_generated_folder(None) == "/tmp"
    # 2. headers={} (空 dict)
    assert ep._resolve_generated_folder({}) == "/tmp"
    # 3. 片方欠落
    assert ep._resolve_generated_folder({"x-thread-id": "tid"}) == "/tmp"
    assert ep._resolve_generated_folder({"x-github-login": "alice"}) == "/tmp"
    # 4. path traversal (THREAD_FILES_DIR の外を指す login / tid)
    traverse = ep._resolve_generated_folder(
        {"x-thread-id": "../../etc", "x-github-login": "alice"}
    )
    assert traverse == "/tmp", f"path traversal should fallback to /tmp, got: {traverse}"
