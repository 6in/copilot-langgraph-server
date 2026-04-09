"""Iframe JSON-RPC bridge endpoint (Phase 18, updated Phase 19).

POST /api/iframe-rpc — receives JSON-RPC request from parent frame (CanvasPane or
hosted shell), enqueues as arq job with task_type='iframe_app_api', returns job_id.

Phase 19 change (D-07): JWT authentication removed. The endpoint is now publicly
accessible so that hosted Canvas apps at /apps/{app_id} can call it without a
session cookie. The github_token is retrieved from auth_manager on the server side.

Flow:
  1. iframe-rpc.js (in iframe) sends postMessage to parent frame.
  2. parent-bridge.js (in parent frame) POSTs to /api/iframe-rpc.
  3. This endpoint enqueues an arq job of type 'iframe_app_api'.
  4. parent-bridge.js polls GET /api/job/{id} via SSE for completion.
  5. On done, parent-bridge.js replies to the iframe via postMessage.

Security note (T-19-04):
  JWT auth removed as an accepted risk (D-07). Only SELECT + AI one-shot
  operations are supported; write operations are rejected by IframeRpcHandler.
"""
import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel

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
):
    """Enqueue a JSON-RPC request from an iframe Canvas app.

    Accepts a JSON-RPC style body (id, method, params) and dispatches to the
    arq worker as task_type='iframe_app_api'. The worker's IframeRpcHandler
    processes QUERY (SELECT-only DB) and AI (ChatCopilot one-shot) methods.

    Returns a job_id for polling via GET /api/job/{job_id}.

    No JWT auth required (D-07). github_token fetched from auth_manager.
    """
    from arq import ArqRedis

    arq_redis: ArqRedis = request.app.state.arq_redis
    auth_manager = request.app.state.auth_manager
    job_id = str(uuid.uuid4())
    github_login = "anonymous"  # D-07: JWT 認証不要化、ログ用固定値
    github_token = auth_manager.load_token() or ""

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
