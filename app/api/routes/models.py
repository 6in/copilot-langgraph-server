"""Phase 36 D-07/D-16: GET /api/models — SDK list_models() のラッパー + TTL 1h キャッシュ.

JWT 認証必須 (ADR-0014). SDK 隔離原則 (D-15) により SDK 型は ChatCopilot.list_models()
内で dict に変換済 — route layer は dict のみを扱う.

戻り値スキーマ (D-14):
    [{id, name, vision, vision_limits, billing_multiplier}, ...]
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.routes.chat import get_jwt_payload

router = APIRouter(prefix="/api", tags=["models"])

_TTL_SECS = 3600  # 1 時間 (D-16)


@dataclass
class _Cache:
    at: float = 0.0
    payload: list[dict] = field(default_factory=list)


_cache = _Cache()


@router.get("/models")
async def list_models(
    request: Request,
    _payload: dict = Depends(get_jwt_payload),  # JWT 認証のみ、github_token は app.state.llm 経由
) -> list[dict]:
    """TTL 1h キャッシュ付きで GET /api/models を返す.

    - キャッシュ hit 時: キャッシュ payload をそのまま返す
    - キャッシュ miss 時: ``llm.list_models()`` を呼び結果を cache に保存して返す
    - ``llm.list_models()`` 例外時: キャッシュが残っていれば古い payload を返す
      (graceful), なければ 503 で具体エラーを返す
    """
    now = time.time()
    if now - _cache.at < _TTL_SECS and _cache.payload:
        return _cache.payload
    llm = request.app.state.llm
    try:
        payload = await llm.list_models()
    except Exception as e:
        # キャッシュが残っていれば古い payload を返して UI 継続. なければ 503.
        if _cache.payload:
            return _cache.payload
        raise HTTPException(
            status_code=503, detail=f"models list unavailable: {e}"
        ) from e
    _cache.at = now
    _cache.payload = payload
    return payload
