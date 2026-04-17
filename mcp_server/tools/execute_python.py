"""Python サンドボックス実行ツール (Phase 28).

D-01: worker コンテナ内サブプロセスで python3 -c を実行
D-02: タイムアウト + メモリ制限 + 一時ディレクトリでファイルI/O制限
D-03: 60 秒タイムアウト（claude_code.py と同じ）
D-06: stdout + stderr + exit_code を返す
D-09: Python のみ対応
D-10: AST 解析によるインポートホワイトリストチェック
D-11: config/sandbox_allowlist.yaml で許可モジュール管理
"""
from __future__ import annotations

import ast
import asyncio
import os
import resource
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from fastmcp import FastMCP

# D-08 踏襲: 許可リスト env キー — これ以外はサブプロセスに渡さない
ALLOWED_ENV_KEYS: frozenset[str] = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})

# D-03: サブプロセスの最大実行時間 (秒)
TIMEOUT_SECS: int = 60

# claude_code.py 踏襲: SIGTERM 後の猶予時間 (秒) — 超過すると SIGKILL に昇格
SIGTERM_GRACE_SECS: int = 5

# D-06 踏襲: インラインで返す最大文字数
MAX_INLINE_CHARS: int = 4000

# D-02: メモリ上限 512MB
MEMORY_LIMIT_BYTES: int = 512 * 1024 * 1024

# D-11: ホワイトリスト設定ファイルパス（環境変数で上書き可能）
ALLOWLIST_PATH: str = os.environ.get(
    "SANDBOX_ALLOWLIST", "/mcp_server/config/sandbox_allowlist.yaml"
)

# キャッシュ — プロセス起動時に一度だけ読み込む
_cached_allowlist: frozenset[str] | None = None


def _load_allowlist(config_path: str | None = None) -> frozenset[str]:
    """YAML からインポートホワイトリストを読み込む（キャッシュあり）。"""
    global _cached_allowlist
    if _cached_allowlist is not None:
        return _cached_allowlist
    path = config_path or ALLOWLIST_PATH
    try:
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
        _cached_allowlist = frozenset(cfg.get("allowed_modules", []))
    except FileNotFoundError:
        _cached_allowlist = frozenset()
    return _cached_allowlist


def _check_imports(code: str, allowed: frozenset[str]) -> list[str]:
    """AST 解析でインポートされるモジュール名を抽出し、ホワイトリスト外のものを返す。

    SyntaxError は ValueError として re-raise する。
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"SyntaxError: {e}") from e
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in allowed:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top not in allowed:
                    violations.append(node.module)
    return violations


def _set_limits():
    """preexec_fn — 子プロセスの仮想メモリ上限を設定する (D-02).

    注意: 純粋な同期関数のみ使用すること (Pitfall 1)。
    """
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))


async def execute_python(code: str, timeout: int = 60) -> dict:
    """Python コードをサンドボックス実行する (D-01, D-09)。

    Args:
        code: 実行する Python コード文字列
        timeout: タイムアウト秒数（デフォルト 60、D-03）

    Returns:
        {"stdout": str, "stderr": str, "exit_code": int, "truncated": bool}
        エラー時は "error" キーを追加
    """
    # 1. AST インポートホワイトリストチェック (D-10)
    allowlist = _load_allowlist()
    try:
        violations = _check_imports(code, allowlist)
    except ValueError as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": 1,
            "truncated": False,
            "error": str(e),
        }
    if violations:
        msg = f"Blocked imports: {violations}"
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": 1,
            "truncated": False,
            "error": msg,
        }

    # 2. env サニタイズ (claude_code.py D-08 踏襲)
    sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}
    # mcp_helper を import 可能にするため PYTHONPATH に tools ディレクトリを追加
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    sanitized_env["PYTHONPATH"] = tools_dir

    # 3. サブプロセス実行 (D-01, D-02)
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/tmp",
            env=sanitized_env,
            preexec_fn=_set_limits,
        )
    except Exception as e:
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "truncated": False,
            "error": f"spawn failed: {e}",
        }

    # 4. タイムアウト + SIGTERM→SIGKILL エスカレーション (D-03)
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        exit_code = proc.returncode if proc.returncode is not None else 0
    except asyncio.TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=SIGTERM_GRACE_SECS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "truncated": False,
            "error": f"Timeout after {timeout}s",
        }

    stdout = stdout_b.decode(errors="replace")
    stderr = stderr_b.decode(errors="replace")

    # 5. 出力切り捨て (D-06 踏襲)
    truncated = len(stdout) > MAX_INLINE_CHARS
    return {
        "stdout": stdout[:MAX_INLINE_CHARS],
        "stderr": stderr[:500] if stderr else "",
        "exit_code": exit_code,
        "truncated": truncated,
    }


def register_tools(mcp: "FastMCP") -> None:
    """Register execute_python tool on the given FastMCP instance."""
    mcp.tool(execute_python)
