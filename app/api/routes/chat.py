"""Chat and thread API routes (CHAT-01, CHAT-02, CHAT-03, CHAT-04, ASYNC-01, ASYNC-04, ASYNC-06).

Endpoints:
- POST   /api/chat                  — enqueue chat job, returns job_id immediately (JWT protected)
- GET    /api/chat/{job_id}/stream  — SSE stream for real-time job completion notification
- POST   /api/threads               — create new thread (returns UUID)
- GET    /api/threads               — list existing threads
- DELETE /api/threads/{thread_id}   — delete a thread and its checkpoints
- GET    /api/threads/{thread_id}/messages — get messages for a thread

NOTE: Thread CRUD routes (list/create/delete/messages) are intentionally NOT
JWT-protected. They operate on local PostgreSQL data only, and this is a personal
tool where server-side access control on thread metadata adds no security value.
"""
import json
import uuid
from datetime import datetime, timezone

import jwt
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from psycopg.rows import dict_row

from app.api.models import ChatAsyncResponse, ChatRequest, ChatResponse, RenameThreadRequest, ThreadInfo
from app.auth.jwt_utils import decode_jwt, decrypt_github_token

router = APIRouter(prefix="/api", tags=["chat"])


async def get_github_token(request: Request) -> str:
    """FastAPI dependency: extract and decrypt GitHub token from JWT session cookie.

    Raises HTTPException 401 with detail:
    - "auth_required" if no session cookie is present
    - "auth_expired"  if JWT has expired
    - "auth_invalid"  if JWT is malformed or revoked
    """
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="auth_required")
    try:
        payload = decode_jwt(session_cookie)
        return decrypt_github_token(payload["github_token"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="auth_expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="auth_invalid")


@router.post("/chat", response_model=ChatAsyncResponse)
async def send_message(
    request: Request,
    body: ChatRequest,
    github_token: str = Depends(get_github_token),
):
    """Enqueue chat job and return job_id immediately (ASYNC-01).

    The actual LangGraph execution happens in the arq worker process.
    Frontend uses SSE or polling to get the result.

    Auth is enforced via JWT cookie through get_github_token dependency.
    """
    from arq import ArqRedis
    arq_redis: ArqRedis = request.app.state.arq_redis
    job_id = str(uuid.uuid4())

    await arq_redis.enqueue_job(
        "process_chat",
        job_id=job_id,
        thread_id=body.thread_id,
        prompt=body.message,
        model=body.model,
        github_token=github_token,
        reply_to={"type": "web", "job_id": job_id},
    )
    return ChatAsyncResponse(job_id=job_id, thread_id=body.thread_id)


@router.get("/chat/{job_id}/stream")
async def stream_job(job_id: str, request: Request):
    """SSE endpoint for real-time job completion notification (ASYNC-04, ASYNC-06).

    1. Check if job already done (reload/reconnect case) — return immediate done event
    2. Otherwise register SSE queue, yield events until done signal
    3. Always unregister in finally block (prevent dangling queues)
    """
    job_store = request.app.state.job_store

    # Check if already done (ASYNC-06: immediate done for completed jobs)
    saved = await job_store.get(job_id)
    if saved and saved.get("status") == "done":
        async def immediate():
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
        return StreamingResponse(
            immediate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Still in progress — poll Redis until done (cross-process safe)
    async def generator():
        import asyncio
        while True:
            if await request.is_disconnected():
                break
            result = await job_store.get(job_id)
            if result and result.get("status") == "done":
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
                break
            yield f"data: {json.dumps({'status': 'thinking'})}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/threads")
async def create_thread():
    """Create a new conversation thread (CHAT-04).

    Returns a new UUID4 thread_id. The thread is implicitly created
    in the checkpoints table when the first message is sent via /api/chat.
    """
    thread_id = str(uuid.uuid4())
    label = f"Chat {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    return {"thread_id": thread_id, "label": label}


@router.get("/threads")
async def list_threads(request: Request):
    """List existing threads sorted by latest activity (SESS-02 front-loaded).

    Direct SQL against AsyncPostgresSaver's checkpoints table.
    LangGraph's alist() requires a thread_id filter — no 'list all' API.
    """
    db_uri = request.app.state.db_uri
    threads: list[ThreadInfo] = []

    try:
        async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT c.thread_id, MAX(c.checkpoint_id) as latest, tl.label, tl.updated_at
                       FROM checkpoints c
                       LEFT JOIN thread_labels tl ON c.thread_id = tl.thread_id
                       WHERE c.checkpoint_ns = ''
                       GROUP BY c.thread_id, tl.label, tl.updated_at
                       ORDER BY latest DESC
                       LIMIT 50"""
                )
                rows = await cur.fetchall()

        for row in rows:
            thread_id = row["thread_id"]
            checkpoint_id = row["latest"]
            label = row["label"] or f"Chat {thread_id[:8]}"
            threads.append(ThreadInfo(
                thread_id=thread_id,
                updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                label=label,
            ))
    except Exception:
        # DB may not be reachable yet (no messages sent) — return empty list
        pass

    return threads


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(thread_id: str, request: Request):
    """Delete a thread and all its checkpoints from PostgreSQL.

    Uses AsyncPostgresSaver.adelete_thread() which atomically removes
    all related rows from checkpoints, checkpoint_blobs, and checkpoint_writes.
    """
    checkpointer = request.app.state.checkpointer

    try:
        await checkpointer.adelete_thread(thread_id)
    except Exception:
        # Silently succeed if thread doesn't exist
        pass


@router.patch("/threads/{thread_id}")
async def rename_thread(thread_id: str, body: RenameThreadRequest, request: Request):
    """Update the display label for a thread.

    Uses INSERT ... ON CONFLICT DO UPDATE (upsert) so both new and existing
    threads can have their label set without a separate check.
    """
    label = body.label.strip()
    if not label:
        raise HTTPException(status_code=422, detail="label must not be empty")

    db_uri = request.app.state.db_uri
    async with await psycopg.AsyncConnection.connect(db_uri) as conn:
        await conn.execute(
            """INSERT INTO thread_labels (thread_id, label)
               VALUES (%s, %s)
               ON CONFLICT (thread_id)
               DO UPDATE SET label = EXCLUDED.label, updated_at = now()""",
            (thread_id, label),
        )
        await conn.commit()

    return {"thread_id": thread_id, "label": label}


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, request: Request):
    """Get all messages for a specific thread.

    Uses graph.aget_state() to retrieve the full message list from the checkpoint.
    """
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = await graph.aget_state(config)
        if state.values and "messages" in state.values:
            messages = []
            for msg in state.values["messages"]:
                role = "user" if isinstance(msg, HumanMessage) else "ai"
                messages.append({"role": role, "content": msg.content})
            return {"messages": messages, "thread_id": thread_id}
    except Exception:
        pass

    return {"messages": [], "thread_id": thread_id}
