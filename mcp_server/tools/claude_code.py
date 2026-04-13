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


async def claude_code(prompt: str, cwd: str = "/tmp") -> dict:
    """Claude Code CLI をサブプロセスとして実行する（CODE-01〜03）。

    Args:
        prompt: claude --print に渡すプロンプト文字列
        cwd: claude を実行する作業ディレクトリ（デフォルト /tmp）

    Returns:
        {"output": str, "exit_code": int, "truncated": bool, "file_path": str | None}
        エラー時は "error" キーを追加
    """
    # D-08, D-09: 許可リスト env サニタイズ — CLAUDECODE=1 等を渡さない
    sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}

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
    """Register claude_code tool on the given FastMCP instance."""
    mcp.tool(claude_code)
