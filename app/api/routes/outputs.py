"""Phase 38 D-05: GET /api/threads/{thread_id}/outputs/{name} — AI 生成ファイル DL/preview.

worker / MCP tool が `_generated/` サブフォルダに書き出した出力ファイルを、JWT cookie 認証
配下で raw bytes を inline 配信する単一 endpoint。

Design notes:
- attachments.py の `_resolve_thread_folder` / `_safe_resolve_file` / `_normalize_basename`
  helper を import で再利用する。新規 helper は書かない (D-19 — Phase 36 で確立した
  multi-user isolation / realpath guard / path traversal 防御を間接的に継承)。
- `thread_folder` ではなく `os.path.join(thread_folder, "_generated")` を
  `_safe_resolve_file` に渡すことで realpath prefix guard が `_generated/` 配下に絞り込まれ、
  user upload (Phase 36) との混同を物理的に防ぐ (38-RESEARCH.md Pitfall 10)。
- 一覧 endpoint は D-17 により **新設しない** — UI は AIMessage.additional_kwargs.attachments
  の bundle を LangGraph checkpointer 経由で復元し、本 route は単一ファイル取得のみ提供。
"""
from __future__ import annotations

import logging
import mimetypes
import os

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import FileResponse

from app.api.routes.attachments import (
    _normalize_basename,
    _resolve_thread_folder,
    _safe_resolve_file,
)
from app.api.routes.chat import get_jwt_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["outputs"])


@router.get("/threads/{thread_id}/outputs/{name}")
async def get_output(
    request: Request,
    thread_id: str = Path(..., description="Thread ID"),
    name: str = Path(..., description="Storage name (timestamp prefix 付き、例: 20260512T120000_chart.png)"),
    payload: dict = Depends(get_jwt_payload),
):
    """Phase 38 D-05 / D-19: `_generated/` 配下の raw bytes を JWT 認証下で inline 配信。

    認可・realpath guard は Phase 36 の helper を **そのまま再利用** することで、
    isolation / path traversal 防御を新規実装ゼロで継承する (D-19)。
    `{name}` は timestamp prefix 付きの実体名で、AI / UI / API の全レイヤーで
    同一 identity 文字列を扱う (D-05)。
    """
    github_login = payload.get("github_login", "unknown")
    # API route 側 helper の引数順序: (github_login, thread_id)
    thread_folder = _resolve_thread_folder(github_login, thread_id)
    # Pitfall 10 対策: _generated/ サブフォルダを連結したパスを `_safe_resolve_file` に渡す。
    # こうすることで realpath prefix guard が `_generated/` 配下に絞り込まれ、
    # 親 thread フォルダ直下の user upload 領域へのアクセスを物理的に塞ぐ。
    gen_folder = os.path.join(thread_folder, "_generated")
    safe_path = _safe_resolve_file(gen_folder, name)
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="output not found")
    mime, _ = mimetypes.guess_type(name)
    return FileResponse(
        safe_path,
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{_normalize_basename(name)}"'},
    )
