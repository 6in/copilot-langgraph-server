"""Phase 36 D-07/D-14: attachments upload / raw GET / DELETE routes.

Security (ADR-0014 / ADR-0048 / Phase 37 D-18):
- JWT httpOnly cookie 認証必須
- realpath prefix guard で /shared/thread-files 配下以外への書き込み/読取を拒否
- basename sanitization (os.path.basename + NFC) で path traversal を防ぐ
- chunked size check (1MB 毎) で 100MB / 10MB 上限を段階的に enforce (Pitfall 3)

Plan 02 (Wave 1) で空 router を main.py に include 済. Plan 03 (Wave 2) で
本実装を追加する.
"""
from __future__ import annotations

import logging
import mimetypes
import os
import unicodedata
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.routes.chat import get_jwt_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["attachments"])

# Phase 37 D-01/D-03 踏襲: thread フォルダ base path
THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")

# Phase 36 D-01: text/code 系は 100MB hard cap
MAX_FILE_BYTES = 100 * 1024 * 1024

# Phase 36 D-02: 画像は 10MB hard cap (extension allowlist 経由で適用)
IMAGE_EXTS = frozenset({"png", "jpg", "jpeg", "webp"})
IMAGE_MAX_BYTES = 10 * 1024 * 1024


def _normalize_basename(filename: str | None) -> str:
    """os.path.basename + NFC normalize + 危険文字剥奪。

    Pitfall 8 対策: `..` / `/` / `\\` を含む filename を basename で剥がし、
    さらに NFC 正規化と control char / path separator を reject する。
    """
    if not filename:
        raise HTTPException(status_code=400, detail="filename missing")
    # basename を先に取る (最終的な file 名は basename 相当)
    base = os.path.basename(filename)
    # basename が空 (filename が `/` で終わっている等) はエラー
    if not base:
        raise HTTPException(status_code=400, detail=f"invalid filename: {filename!r}")
    # NFC 正規化 (Unicode 正規化差の吸収)
    base = unicodedata.normalize("NFC", base)
    # path separator / control chars が残ってないことを assert
    for ch in ("/", "\\", "\x00"):
        if ch in base:
            raise HTTPException(status_code=400, detail=f"invalid filename: {filename!r}")
    return base


def _resolve_thread_folder(github_login: str, thread_id: str) -> str:
    """realpath prefix guard で /shared/thread-files/<login>/<tid>/ を返す。

    Phase 37 D-18 パターン踏襲。folder が物理的に存在しなくても realpath は計算可能。
    """
    if not github_login or not thread_id:
        raise HTTPException(status_code=400, detail="missing auth or thread_id")
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    real = os.path.realpath(folder)
    root = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(root + os.sep) and real != root:
        logger.warning(
            "path traversal attempt blocked in attachments route: "
            "thread_id=%r github_login=%r folder=%r",
            thread_id, github_login, folder,
        )
        raise HTTPException(status_code=400, detail="invalid thread path")
    return real


def _safe_resolve_file(thread_folder: str, filename: str) -> str:
    """thread_folder 配下の単一ファイルを realpath で解決。

    filename は既に basename 化されている想定だが、二重防御として再度 basename を取り、
    realpath が thread_folder prefix 以下にあることを確認する。
    """
    basename = _normalize_basename(filename)
    candidate = os.path.join(thread_folder, basename)
    real_file = os.path.realpath(candidate)
    real_folder = os.path.realpath(thread_folder)
    if not real_file.startswith(real_folder + os.sep):
        raise HTTPException(status_code=400, detail="path traversal")
    return real_file


def _utc_timestamp_prefix() -> str:
    """Phase 37 D-02: storage_name の prefix `YYYYMMDDTHHMMSS_` を生成."""
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")


@router.post("/threads/{thread_id}/attachments")
async def upload_attachments(
    request: Request,
    thread_id: str = Path(..., description="Thread ID"),
    files: List[UploadFile] = File(...),
    payload: dict = Depends(get_jwt_payload),
) -> dict:
    """Phase 36 D-03/D-07/D-14: multipart upload → /shared/thread-files/<login>/<tid>/.

    Returns {attachments: [D-14 dict, ...]}
    Errors: 401 auth_required / 400 invalid path|filename / 413 too large
    """
    github_login = payload.get("github_login", "unknown")
    folder = _resolve_thread_folder(github_login, thread_id)
    os.makedirs(folder, exist_ok=True)

    saved: list[dict] = []
    for uf in files:
        base = _normalize_basename(uf.filename)
        ext = os.path.splitext(base)[1].lower().lstrip(".")
        storage_name = f"{_utc_timestamp_prefix()}_{base}"
        dest = os.path.join(folder, storage_name)

        # D-02: 画像は 10MB、D-01: それ以外は 100MB
        size_cap = IMAGE_MAX_BYTES if ext in IMAGE_EXTS else MAX_FILE_BYTES

        total = 0
        try:
            with open(dest, "wb") as fh:
                while True:
                    chunk = await uf.read(1024 * 1024)  # 1MB 毎に累計チェック
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > size_cap:
                        fh.close()
                        try:
                            os.remove(dest)
                        except OSError:
                            pass
                        raise HTTPException(
                            status_code=413,
                            detail=f"{base} exceeds size limit ({size_cap // (1024 * 1024)} MB)",
                        )
                    fh.write(chunk)
        except HTTPException:
            raise
        except OSError as e:
            try:
                os.remove(dest)
            except OSError:
                pass
            logger.warning("upload write failed: thread_id=%r file=%r: %s", thread_id, base, e)
            raise HTTPException(status_code=500, detail=f"failed to save {base}") from e

        mime = uf.content_type or mimetypes.guess_type(base)[0] or "application/octet-stream"
        saved.append({
            # Phase 38 D-30 (案 A): 新規 upload は最新型 'user_upload' で永続化。
            # legacy 'file' 行は API _messages_to_response 側で正規化される。
            "kind": "user_upload",
            "name": base,
            "storage_name": storage_name,
            "path": dest,
            "size": total,
            "mime_type": mime,
            "ext": ext,
            "modified_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        })
    return {"attachments": saved}


@router.get("/threads/{thread_id}/attachments/{name}")
async def get_attachment(
    request: Request,
    thread_id: str = Path(..., description="Thread ID"),
    name: str = Path(..., description="Storage name (including timestamp prefix)"),
    payload: dict = Depends(get_jwt_payload),
):
    """Phase 36 D-07/D-23: raw bytes を JWT 認証下で inline 配信。

    サムネ生成はしない (D-23) — browser の <img> / <a download> に直接渡す。
    realpath guard で other user の thread folder には絶対にアクセスできない。
    """
    github_login = payload.get("github_login", "unknown")
    folder = _resolve_thread_folder(github_login, thread_id)
    safe_path = _safe_resolve_file(folder, name)
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="file not found")
    mime, _ = mimetypes.guess_type(name)
    return FileResponse(
        safe_path,
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{_normalize_basename(name)}"'},
    )


@router.delete("/threads/{thread_id}/attachments/{name}", status_code=204)
async def delete_attachment(
    request: Request,
    thread_id: str = Path(..., description="Thread ID"),
    name: str = Path(..., description="Storage name"),
    payload: dict = Depends(get_jwt_payload),
):
    """Phase 36 D-06 (ケース D)/D-07/D-08: 単一ファイル削除。idempotent。

    realpath guard を通して /shared/thread-files 配下以外は削除しない。
    path traversal は chat.delete_thread と同じく監査ログに残す (HTTPException 経由
    で _normalize_basename / _safe_resolve_file 内 logger.warning)。
    """
    github_login = payload.get("github_login", "unknown")
    try:
        folder = _resolve_thread_folder(github_login, thread_id)
        safe_path = _safe_resolve_file(folder, name)
        if os.path.isfile(safe_path):
            os.remove(safe_path)
    except HTTPException:
        raise
    except OSError as e:
        logger.warning("delete_attachment failed: thread_id=%r name=%r: %s", thread_id, name, e)
        raise HTTPException(status_code=500, detail="failed to delete") from e
    return None  # 204 No Content
