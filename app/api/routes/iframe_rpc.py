"""Iframe JSON-RPC bridge endpoint (Phase 18).

POST /api/iframe-rpc — receives JSON-RPC request from CanvasPane,
enqueues as arq job with task_type='iframe_app_api', returns job_id.
JWT authentication required (parent frame is authenticated).

Flow:
  1. CanvasPane receives postMessage from iframe (origin-validated).
  2. CanvasPane calls POST /api/iframe-rpc with the JSON-RPC body.
  3. This endpoint enqueues an arq job of type 'iframe_app_api'.
  4. CanvasPane polls GET /api/job/{id} (or uses SSE) for completion.
  5. On done, CanvasPane forwards the result back to iframe via postMessage.

Security (T-18-03):
  JWT authentication is enforced via Depends(get_github_token).
  Unauthenticated requests receive 401 before any job is enqueued.
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

    Returns a job_id for polling via GET /api/job/{job_id}.
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
