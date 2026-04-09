"""Iframe JSON-RPC bridge endpoint (Phase 18, updated Phase 19).

POST /api/iframe-rpc — receives JSON-RPC request from parent frame (CanvasPane or
hosted shell), enqueues as arq job with task_type='iframe_app_api', returns job_id.

JWT Cookie 認証を使用。parent-bridge.js が credentials: 'include' でリクエストするため、
ブラウザが自動的に JWT Cookie を送信する。github_token は JWT ペイロードから復号して取得。

Flow:
  1. iframe-rpc.js (in iframe) sends postMessage to parent frame.
  2. parent-bridge.js (in parent frame) POSTs to /api/iframe-rpc (with JWT Cookie).
  3. This endpoint enqueues an arq job of type 'iframe_app_api'.
  4. parent-bridge.js polls GET /api/chat/{id}/stream via SSE for completion.
  5. On done, parent-bridge.js replies to the iframe via postMessage.

Security note (T-19-04):
  JWT Cookie 認証により、呼び出し元ユーザーの Copilot トークンを使用。
  Only SELECT + AI one-shot operations are supported; write operations are
  rejected by IframeRpcHandler.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.routes.chat import get_github_token, get_jwt_payload

router = APIRouter(prefix="/api", tags=["iframe-rpc"])


class IframeRpcRequest(BaseModel):
    id: str
    method: str
    params: dict | None = None


class IframeRpcResponse(BaseModel):
    job_id: str


@router.post("/iframe-rpc", response_model=IframeRpcResponse)
async def iframe_rpc(
    request: Request,
    body: IframeRpcRequest,
    github_token: str = Depends(get_github_token),
    payload: dict = Depends(get_jwt_payload),
):
    """Enqueue a JSON-RPC request from an iframe Canvas app.

    Accepts a JSON-RPC style body (id, method, params) and dispatches to the
    arq worker as task_type='iframe_app_api'. The worker's IframeRpcHandler
    processes QUERY (SELECT-only DB) and AI (ChatCopilot one-shot) methods.

    Returns a job_id for polling via GET /api/chat/{job_id}/stream.

    JWT Cookie 認証。parent-bridge.js が credentials: 'include' で送信するため
    ブラウザが自動的に Cookie を付与する。
    """
    from arq import ArqRedis

    arq_redis: ArqRedis = request.app.state.arq_redis
    job_id = str(uuid.uuid4())
    github_login = payload.get("github_login", "unknown")

    await arq_redis.enqueue_job(
        "process_chat",
        job_id=job_id,
        thread_id="",  # iframe-rpc does not use LangGraph threads
        prompt="",     # not used by IframeRpcHandler
        github_token=github_token,
        reply_to={"type": "web", "job_id": job_id},
        task_type="iframe_app_api",
        github_login=github_login,
        rpc_method=body.method,
        rpc_params=body.params or {},
    )

    return IframeRpcResponse(job_id=job_id)
