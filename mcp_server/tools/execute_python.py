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
import datetime
import os
import resource
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from fastmcp import FastMCP

# D-08 踏襲: 許可リスト env キー — これ以外はサブプロセスに渡さない
ALLOWED_ENV_KEYS: frozenset[str] = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})

# Phase 38 D-08: AI 生成ファイルの永続化 root (Phase 37 D-04 と同 volume)
THREAD_FILES_DIR: str = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")

# Phase 38 D-10 / RESEARCH §Anti-Patterns: post-process rename で除外する中間ファイル拡張子
_PYC_EXCLUDES: frozenset[str] = frozenset({".pyc"})

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


# ─────────────────────────────────────────────────────────────────────────
# Phase 38 D-08 / D-10 / D-11: sandbox cwd 切替 + post-process rename helpers
# ─────────────────────────────────────────────────────────────────────────


def _utc_ts() -> str:
    """UTC 現在時刻を `YYYYMMDDTHHMMSS` 形式の文字列で返す (Phase 37 D-02 命名規約)。"""
    return datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")


def _resolve_generated_folder(headers: dict | None) -> str:
    """Phase 38 D-08: ヘッダから `_generated/` folder path を realpath guard 込みで返す。

    `x-thread-id` / `x-github-login` が両方揃えば
    `{THREAD_FILES_DIR}/<login>/<tid>/_generated` の realpath を返す。
    片方でも欠落、または path traversal で THREAD_FILES_DIR 配下を逸脱した場合は
    `/tmp` に fallback (D-08 fallback policy)。
    """
    h = headers or {}
    tid = h.get("x-thread-id") or ""
    login = h.get("x-github-login") or ""
    if not tid or not login:
        return "/tmp"
    folder = os.path.join(THREAD_FILES_DIR, login, tid, "_generated")
    real = os.path.realpath(folder)
    base = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(base + os.sep):
        return "/tmp"
    return real


def _is_already_prefixed(name: str) -> bool:
    """Phase 38 D-10: 既に `YYYYMMDDTHHMMSS_` 形式の prefix が付いているか判定。

    AI が D-03 規約に従って自前で prefix を書いたケースや、過去 turn で本 helper が
    付与した prefix を **二重 prefix** しないための guard (RESEARCH §Pitfall 5)。
    """
    return (
        len(name) >= 16
        and name[:8].isdigit()
        and name[8] == "T"
        and name[9:15].isdigit()
        and name[15] == "_"
    )


def _rename_new_outputs(folder: str, before: set[str]) -> list[str]:
    """Phase 38 D-10 / D-11: snapshot diff で新規ファイルを `{ts}_{name}` にリネーム。

    Args:
        folder: scan 対象ディレクトリ (絶対パス)。
        before: tool 実行前に取った `set(os.listdir(folder))`。

    Returns:
        rename 後のファイル名リスト (`after - before` のうち rename を経たもの)。
        中間ファイル (`.pyc`) は除外。既に prefix 付きのファイルはそのままの名前で含める。
        folder が存在しなければ空リストを返す。
    """
    if not os.path.isdir(folder):
        return []
    ts = _utc_ts()
    after = set(os.listdir(folder))
    new_files = sorted(after - before)
    renamed: list[str] = []
    for name in new_files:
        # RESEARCH Anti-Patterns: `.pyc` 等の中間ファイルは AI に露出させない
        ext = os.path.splitext(name)[1].lower()
        if ext in _PYC_EXCLUDES:
            continue
        src = os.path.join(folder, name)
        # symlink / dir は対象外 (Pitfall: dir entry / 攻撃的 symlink を握り潰す)
        if os.path.islink(src) or not os.path.isfile(src):
            continue
        if _is_already_prefixed(name):
            renamed.append(name)
            continue
        dst_name = f"{ts}_{name}"
        os.rename(src, os.path.join(folder, dst_name))
        renamed.append(dst_name)
    return renamed


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


async def execute_python(code: str, timeout: int = 60, headers: dict | None = None) -> dict:
    """Python コードをサンドボックス実行する (D-01, D-09)。

    Phase 37 D-17: headers 引数で RPCContext (x-thread-id / x-github-login) を受け取り、
    subprocess 環境変数 X_THREAD_ID / X_GITHUB_LOGIN として伝搬する。
    FastMCP tool として登録する際は CurrentHeaders() DI を使用する。

    Args:
        code: 実行する Python コード文字列
        timeout: タイムアウト秒数（デフォルト 60、D-03）
        headers: HTTP リクエストヘッダー dict (FastMCP CurrentHeaders() から注入)

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

    # Phase 37 D-17: RPCContext を subprocess に伝搬 (attachments_* tool 呼び出し用)
    # headers は FastMCP CurrentHeaders() から注入される (Route A)
    _req_headers = headers or {}
    _thread_id = _req_headers.get("x-thread-id", "")
    _github_login = _req_headers.get("x-github-login", "")
    if _thread_id:
        sanitized_env["X_THREAD_ID"] = _thread_id
    if _github_login:
        sanitized_env["X_GITHUB_LOGIN"] = _github_login

    # 3. サブプロセス実行 (D-01, D-02)
    # Phase 38 D-08: cwd を `_generated/` 配下に切替。headers 不足時は /tmp に fallback。
    # RESEARCH §Pitfall 3: makedirs(exist_ok=True) で folder 初回利用を冪等にする。
    cwd = _resolve_generated_folder(headers)
    os.makedirs(cwd, exist_ok=True)
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
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
    """Register execute_python tool on the given FastMCP instance.

    Phase 37 D-17: execute_python は CurrentHeaders() DI でヘッダーを受け取り、
    subprocess env に X_THREAD_ID / X_GITHUB_LOGIN を伝搬する。
    Phase 38 D-10 / D-11: tool 実行後に snapshot diff で `_generated/` の新規
    ファイルを `{ts}_{name}` に rename し、結果 dict に `generated_files` を追加する。
    """
    from fastmcp.dependencies import CurrentHeaders  # noqa: PLC0415

    async def execute_python_with_headers(code: str, timeout: int = 60,
                                          headers: dict = CurrentHeaders()) -> dict:
        """execute_python の FastMCP tool ラッパー (CurrentHeaders DI + post-process rename)。"""
        folder = _resolve_generated_folder(headers)
        os.makedirs(folder, exist_ok=True)
        before = set(os.listdir(folder)) if os.path.isdir(folder) else set()
        result = await execute_python(code=code, timeout=timeout, headers=headers)
        # Phase 38 D-08 fallback ガード: /tmp 全体の diff になる事故を回避
        if folder != "/tmp":
            result["generated_files"] = _rename_new_outputs(folder, before)
        else:
            result["generated_files"] = []
        return result

    mcp.tool(execute_python_with_headers, name="execute_python")
