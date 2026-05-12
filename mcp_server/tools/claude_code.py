"""Claude Code CLI ツール実装 (Phase 23 Plan 02).

CODE-01: claude_code ツール — asyncio.create_subprocess_exec で claude CLI を実行し構造化レスポンスを返す
CODE-02: 許可リスト env サニタイズ — CLAUDECODE=1 等の禁止 env をサブプロセスに渡さない (D-08/D-09)
CODE-03: タイムアウトエスカレーション — SIGTERM → 5s grace → SIGKILL → zombie 回収 (D-10/D-11)
D-06: 4000 文字切り捨て + shared volume 書き出し

23-RESEARCH.md L443-505 のサンプルコードを出発点とした。
"""
from __future__ import annotations

import asyncio
import datetime
import os
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

# D-08: 許可リスト env キー — これ以外は claude サブプロセスに渡さない
ALLOWED_ENV_KEYS: frozenset[str] = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})

# D-10: サブプロセスの最大実行時間 (秒)
TIMEOUT_SECS: int = 60

# D-11: SIGTERM 後の猶予時間 (秒) — 超過すると SIGKILL に昇格
SIGTERM_GRACE_SECS: int = 5

# D-06: インラインで返す最大文字数 — 超過分は shared volume に書き出す
MAX_INLINE_CHARS: int = 4000

# D-07: shared volume のパス — 環境変数で上書き可能
OUTPUT_DIR: str = os.environ.get("CLAUDE_CODE_OUTPUT_DIR", "/shared/claude-code-outputs")


def _save_overflow_output(output: str) -> str:
    """4000 文字超の出力を shared volume に書き出し、ファイルパスを返す。

    Args:
        output: 全文出力（切り捨て前）

    Returns:
        書き出したファイルのフルパス（{OUTPUT_DIR}/{ts}_{uuid8}.txt）
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    uid = uuid.uuid4().hex[:8]
    file_path = os.path.join(OUTPUT_DIR, f"{ts}_{uid}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(output)
    return file_path


async def claude_code(prompt: str, headers: dict | None = None) -> dict:
    """Claude Code CLI をサブプロセスとして実行する（CODE-01〜03）。

    Phase 38 D-09: cwd 引数を削除し、headers 引数 (x-thread-id / x-github-login)
    から `_resolve_generated_folder` で `_generated/` 配下に固定実行する。
    引数 override 不可。
    overflow output (`CLAUDE_CODE_OUTPUT_DIR=/shared/claude-code-outputs`) は
    debug 用 global volume として **現状維持** — `_generated/` にマージしない。

    Args:
        prompt: claude --print に渡すプロンプト文字列
        headers: HTTP リクエストヘッダー dict (FastMCP CurrentHeaders() から注入)。
                 `_resolve_generated_folder` 経由で subprocess の cwd を解決し、
                 sanitized_env に X_THREAD_ID / X_GITHUB_LOGIN を伝搬する。

    Returns:
        {"output": str, "exit_code": int, "truncated": bool, "file_path": str | None}
        エラー時は "error" キーを追加
    """
    # D-08, D-09: 許可リスト env サニタイズ — CLAUDECODE=1 等を渡さない
    sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}

    # Phase 38 D-09: execute_python と同じヘッダ伝搬パターン
    _req_headers = headers or {}
    if _req_headers.get("x-thread-id"):
        sanitized_env["X_THREAD_ID"] = _req_headers["x-thread-id"]
    if _req_headers.get("x-github-login"):
        sanitized_env["X_GITHUB_LOGIN"] = _req_headers["x-github-login"]

    # Phase 38 D-09: cwd を `_generated/` に固定 (execute_python の helper を import 再利用 / DRY)
    from mcp_server.tools.execute_python import _resolve_generated_folder  # noqa: PLC0415

    cwd = _resolve_generated_folder(headers)
    os.makedirs(cwd, exist_ok=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "--print", prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=sanitized_env,
        )
    except FileNotFoundError:
        return {
            "output": "",
            "exit_code": -1,
            "truncated": False,
            "file_path": None,
            "error": "claude CLI not found in PATH",
        }
    except Exception as e:
        return {
            "output": "",
            "exit_code": -1,
            "truncated": False,
            "file_path": None,
            "error": f"claude_code spawn failed: {e}",
        }

    try:
        stdout, _stderr = await asyncio.wait_for(
            proc.communicate(), timeout=TIMEOUT_SECS
        )
        exit_code = proc.returncode if proc.returncode is not None else 0
        output = stdout.decode(errors="replace")
    except asyncio.TimeoutError:
        # D-11: SIGTERM → grace 期間待機 → SIGKILL エスカレーション
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=SIGTERM_GRACE_SECS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        return {
            "output": "",
            "exit_code": -1,
            "truncated": False,
            "file_path": None,
            "error": "Timeout after 60s",
        }

    # D-06: 4000 文字切り捨て + shared volume 書き出し
    if len(output) <= MAX_INLINE_CHARS:
        return {
            "output": output,
            "exit_code": exit_code,
            "truncated": False,
            "file_path": None,
        }

    file_path = _save_overflow_output(output)
    return {
        "output": output[:MAX_INLINE_CHARS],
        "exit_code": exit_code,
        "truncated": True,
        "file_path": file_path,
    }


def register_tools(mcp: "FastMCP") -> None:
    """Register claude_code tool on the given FastMCP instance.

    Phase 38 D-09 / D-10 / D-11: CurrentHeaders DI + post-process rename を
    execute_python wrapper と同じパターンで適用する。`_resolve_generated_folder` /
    `_rename_new_outputs` は execute_python.py を single source of truth として
    import 再利用 (DRY)。
    """
    from fastmcp.dependencies import CurrentHeaders  # noqa: PLC0415

    from mcp_server.tools.execute_python import (  # noqa: PLC0415
        _rename_new_outputs,
        _resolve_generated_folder,
    )

    async def claude_code_with_headers(prompt: str,
                                       headers: dict = CurrentHeaders()) -> dict:
        """claude_code の FastMCP tool ラッパー (CurrentHeaders DI + post-process rename)。"""
        folder = _resolve_generated_folder(headers)
        os.makedirs(folder, exist_ok=True)
        before = set(os.listdir(folder)) if os.path.isdir(folder) else set()
        result = await claude_code(prompt=prompt, headers=headers)
        # Phase 38 D-08 fallback ガード: /tmp 全体の diff になる事故を回避
        if folder != "/tmp":
            result["generated_files"] = _rename_new_outputs(folder, before)
        else:
            result["generated_files"] = []
        return result

    mcp.tool(claude_code_with_headers, name="claude_code")
