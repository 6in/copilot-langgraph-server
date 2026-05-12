"""Phase 37: attachments_list / attachments_extract MCP tools.

FIN-03: PDF/Office テキスト抽出  /  FIN-04: MCP ツール参照
設計: CONTEXT.md D-06..D-21 / RESEARCH.md Pattern 1-6.

Route A: MultiServerMCPClient headers → CurrentHeaders() dependency injection
(Plan 01 Verdict: Route A 採用確定)
"""
from __future__ import annotations

import asyncio
import mimetypes
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

TIMEOUT_SECS: int = 60
MAX_FILE_BYTES: int = 100 * 1024 * 1024        # D-09: 100 MB
MAX_CHARS_PER_FILE: int = 50_000               # D-13
MAX_CHARS_TOTAL: int = 200_000                 # D-13 (session 合算。本モジュールでは参考値)
SUPPORTED_EXTS: frozenset[str] = frozenset({".pdf", ".docx", ".xlsx", ".pptx"})  # D-07
THREAD_FILES_DIR: str = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")  # D-01/D-04


# ─────────────────────────────────────────────
# Thread folder 解決 + path traversal 防御
# ─────────────────────────────────────────────

def _resolve_thread_folder(thread_id: str, github_login: str) -> str:
    """thread_id / github_login からスレッドフォルダパスを組み立てる。

    MEDIUM-01 (Phase 37 Code Review): realpath prefix guard を追加。
    `github_login` や `thread_id` に `../` が含まれていた場合、
    `/shared/thread-files/../../etc/passwd/` のようなフォルダ組み立てを拒否する。
    `delete_thread` 側（app/api/routes/chat.py）の realpath prefix assert と対称。
    """
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    real = os.path.realpath(folder)
    base = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(base + os.sep):
        raise ValueError(f"path traversal in thread folder: {folder!r}")
    return real


def _safe_resolve(thread_folder: str, filename: str) -> str:
    """ファイル名を安全に解決し、thread_folder 外へのアクセスを拒否する。

    W-04 対応: basename 抽出後に realpath prefix assert で path traversal / symlink 攻撃を防ぐ。
    """
    basename = os.path.basename(filename)
    if not basename or basename != filename:
        raise ValueError(f"Invalid filename: {filename!r}")
    candidate = os.path.join(thread_folder, basename)
    real = os.path.realpath(candidate)
    real_folder = os.path.realpath(thread_folder)
    # W-04 対応: PATTERNS.md と揃える — real.startswith(real_folder + os.sep) のみで十分。
    # basename 抽出後は real == real_folder にはならないため、そのケースは不要。
    if not real.startswith(real_folder + os.sep):
        raise ValueError(f"Path traversal detected: {filename!r}")
    return real


# ─────────────────────────────────────────────
# MarkItDown 抽出 + エラー分類
# ─────────────────────────────────────────────

async def _extract_text(path: str) -> str:
    """MarkItDown でファイルをテキスト変換する (asyncio.to_thread + wait_for).

    MarkItDown インスタンスは per-call 生成 — magika が stateful のため singleton 化禁止。
    lazy import により onnxruntime 初回ロードを tool 呼び出し時点まで遅延する。
    """
    from markitdown import MarkItDown  # noqa: PLC0415 — lazy import intentional

    md = MarkItDown(enable_plugins=False)

    def _sync() -> str:
        result = md.convert(path)
        return result.text_content or ""

    return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=TIMEOUT_SECS)


def _classify_error(exc: BaseException) -> tuple[str, str]:
    """例外を 5 種類のエラーコードに分類する (D-19).

    Returns:
        (error_code, human_readable_message)
        error_code: password | corrupt | size_over | unsupported | extract_timeout
    """
    if isinstance(exc, asyncio.TimeoutError):
        return ("extract_timeout", "抽出が 60 秒でタイムアウトしました")

    from markitdown import FileConversionException, UnsupportedFormatException  # noqa: PLC0415

    if isinstance(exc, UnsupportedFormatException):
        return ("unsupported", "サポート外のファイル形式です")
    if isinstance(exc, FileConversionException):
        for attempt in (getattr(exc, "attempts", None) or []):
            info = getattr(attempt, "exc_info", None)
            if not info:
                continue
            exc_type = info[0] if len(info) > 0 else None
            exc_val = info[1] if len(info) > 1 else None
            type_name = (getattr(exc_type, "__name__", "") or "").lower()
            msg = (str(exc_val) if exc_val else "").lower()
            if "password" in type_name or "encrypt" in type_name or "password" in msg:
                return ("password", "パスワード保護されたファイルです")
        # LOW-01 (Phase 37 Code Review): 内部例外オブジェクトを str() で埋め込むと
        # ファイルパスやスタックトレース片が LLM のコンテキストに漏れうる。
        # 型名のみ公開し、詳細は省略する。
        return ("corrupt", f"ファイル変換に失敗しました ({type(exc).__name__})")
    return ("corrupt", f"ファイル処理エラー ({type(exc).__name__})")


# ─────────────────────────────────────────────
# Core 関数 (headers 非依存) — 純関数として MCP tool 引数から分離
# MCP tool 引数に thread_id を含めない (T-37-03-02 / D-17 対応)
# ─────────────────────────────────────────────

async def attachments_list_core(thread_id: str, github_login: str) -> list[dict]:
    """添付ファイル + AI 生成ファイル一覧を返す (core 関数、RPCContext 解決済み引数を受け取る).

    Phase 38 D-06: thread フォルダ直下 (user upload) と `_generated/` サブフォルダ
    (worker / MCP tool が生成) を **flat list** で返し、各エントリに
    `kind: "user_upload" | "generated"` discriminator を付与する。新規 `outputs_list`
    tool は作らない (Phase 30 SSoT のツール数膨張回避)。

    Args:
        thread_id: スレッド ID (HTTP ヘッダーまたは sandbox env 経由で解決済み)
        github_login: GitHub ログイン名 (同上)

    Returns:
        [{"name": "...", "size": N, "modified_at": <float epoch sec>, "ext": "...",
          "mime_type": "...", "kind": "user_upload" | "generated"}, ...]
        ファイルが存在しない場合は []
    """
    if not thread_id or not github_login:
        return []
    try:
        folder = _resolve_thread_folder(thread_id, github_login)
    except ValueError:
        # MEDIUM-01: folder path traversal 検出時は空リスト扱い。
        # list tool は副作用がないため single-path behavior として [] を返す。
        return []
    if not os.path.isdir(folder):
        return []
    out: list[dict] = []
    # ── (1) thread フォルダ直下 = user upload (Phase 36) ──
    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        # LOW-04 (Phase 37 Code Review): シンボリックリンクを除外する。
        # os.path.isfile はリンク先を参照するため、thread フォルダ外のファイルの
        # メタデータが返りうる。islink でリンクそのものを拒否する。
        if os.path.islink(fpath):
            continue
        if not os.path.isfile(fpath):
            continue
        stat = os.stat(fpath)
        ext = os.path.splitext(fname)[1].lower()
        mime_type, _ = mimetypes.guess_type(fname)
        out.append({
            "name": fname,
            "size": stat.st_size,
            "modified_at": float(stat.st_mtime),  # S-03 対応: float epoch seconds
            "ext": ext,
            "mime_type": mime_type or "application/octet-stream",
            "kind": "user_upload",  # D-06: discriminator (input)
        })
    # ── (2) `_generated/` サブフォルダ = worker / MCP tool 生成 (Phase 38) ──
    # サブフォルダ 1 段のみ降りる (RESEARCH Pitfall 4 — 再帰しない、`__pycache__/*.pyc`
    # 等の中間ファイル漏出を防ぐ責務はあるが、フィルタは post-process rename 側で扱う)。
    gen_folder = os.path.join(folder, "_generated")
    if os.path.isdir(gen_folder):
        for fname in sorted(os.listdir(gen_folder)):
            fpath = os.path.join(gen_folder, fname)
            if os.path.islink(fpath):  # LOW-04: symlink 除外
                continue
            if not os.path.isfile(fpath):
                continue
            stat = os.stat(fpath)
            ext = os.path.splitext(fname)[1].lower()
            mime_type, _ = mimetypes.guess_type(fname)
            out.append({
                "name": fname,
                "size": stat.st_size,
                "modified_at": float(stat.st_mtime),
                "ext": ext,
                "mime_type": mime_type or "application/octet-stream",
                "kind": "generated",  # D-06: discriminator (output)
            })
    return out


async def attachments_extract_core(thread_id: str, github_login: str, filename: str) -> dict:
    """添付ファイルのテキストを抽出する (core 関数、RPCContext 解決済み引数を受け取る).

    Args:
        thread_id: スレッド ID (HTTP ヘッダーまたは sandbox env 経由で解決済み)
        github_login: GitHub ログイン名 (同上)
        filename: ファイル名 (basename のみ。パス区切り文字不可)

    Returns:
        {"filename": "...", "content": "...", "error": null, "truncated": false, "truncated_chars": 0}
        エラー時: {"filename": "...", "content": null, "error": {"code": "...", "message": "..."}, ...}
        error.code: password | corrupt | size_over | unsupported | extract_timeout
    """
    empty = {"filename": filename, "content": None, "truncated": False, "truncated_chars": 0}
    if not thread_id or not github_login:
        return {**empty, "error": {"code": "corrupt", "message": "context missing"}}

    # MEDIUM-01: folder path 自体に traversal が混入していれば拒否。
    try:
        folder = _resolve_thread_folder(thread_id, github_login)
    except ValueError as e:
        return {**empty, "error": {"code": "corrupt", "message": str(e)}}

    # D-18 path traversal 防御
    try:
        safe_path = _safe_resolve(folder, filename)
    except ValueError as e:
        return {**empty, "error": {"code": "corrupt", "message": str(e)}}

    if not os.path.isfile(safe_path):
        return {**empty, "error": {"code": "unsupported", "message": "file not found"}}

    ext = os.path.splitext(safe_path)[1].lower()
    if ext not in SUPPORTED_EXTS:
        return {**empty, "error": {"code": "unsupported", "message": f"ext {ext} not supported"}}

    size = os.path.getsize(safe_path)
    if size > MAX_FILE_BYTES:
        return {**empty, "error": {"code": "size_over", "message": f"file size {size} exceeds 100MB"}}

    try:
        text = await _extract_text(safe_path)
    except asyncio.CancelledError:
        # HIGH-02 (Phase 37 Code Review): CancelledError は BaseException サブクラスなので
        # 旧コード `except BaseException` は arq worker からのキャンセルを握り潰していた。
        # 協調的マルチタスクを壊さないよう必ず再 raise する。
        raise
    except Exception as e:
        code, msg = _classify_error(e)
        return {**empty, "error": {"code": code, "message": msg}}

    # D-08: テキスト 0 文字は error ではなく content:"" で返す
    truncated = False
    truncated_chars = 0
    if len(text) > MAX_CHARS_PER_FILE:
        truncated = True
        truncated_chars = len(text) - MAX_CHARS_PER_FILE
        text = text[:MAX_CHARS_PER_FILE]

    return {
        "filename": filename,
        "content": text,
        "error": None,
        "truncated": truncated,
        "truncated_chars": truncated_chars,
    }


# ─────────────────────────────────────────────
# FastMCP tool ラッパー (Route A: CurrentHeaders() DI)
# thread_id は tool 引数に含めない — RPCContext は HTTP ヘッダーで解決 (D-17 / T-37-03-02)
# ─────────────────────────────────────────────

from fastmcp.dependencies import CurrentHeaders  # noqa: E402


async def attachments_list(headers: dict = CurrentHeaders()) -> list[dict]:
    """現在の thread に添付されたファイルの一覧を返す。

    引数なし (thread_id / github_login は HTTP ヘッダー x-thread-id / x-github-login で解決)。

    Returns:
        [{"name": "report.pdf", "size": 1234, "modified_at": <float epoch sec>, "ext": ".pdf", "mime_type": "..."}, ...]
        ファイルが存在しない場合は []
    """
    thread_id = headers.get("x-thread-id", "")
    github_login = headers.get("x-github-login", "")
    return await attachments_list_core(thread_id, github_login)


async def attachments_extract(filename: str, headers: dict = CurrentHeaders()) -> dict:
    """指定ファイル (PDF/docx/xlsx/pptx) のテキストを MarkItDown で抽出して返す。

    Args:
        filename: ファイル名 (basename のみ。パス区切り文字不可)

    Returns:
        {"filename": "...", "content": "...", "error": null, "truncated": false, "truncated_chars": 0}
        エラー時: {"filename": "...", "content": null, "error": {"code": "...", "message": "..."}, ...}
        error.code: password | corrupt | size_over | unsupported | extract_timeout
    """
    thread_id = headers.get("x-thread-id", "")
    github_login = headers.get("x-github-login", "")
    return await attachments_extract_core(thread_id, github_login, filename)


def register_tools(mcp: "FastMCP") -> None:
    """FastMCP インスタンスに attachments_list / attachments_extract を登録する。"""
    mcp.tool(attachments_list)
    mcp.tool(attachments_extract)
