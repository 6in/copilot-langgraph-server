"""Chat and thread API routes (CHAT-01, CHAT-02, CHAT-03, CHAT-04, ASYNC-01, ASYNC-04, ASYNC-06).

Endpoints:
- POST   /api/chat                  — enqueue chat job, returns job_id immediately (JWT protected)
- GET    /api/chat/{job_id}/stream  — SSE stream for real-time job completion notification
- POST   /api/threads               — create new thread (returns UUID)
- GET    /api/threads               — list existing threads
- DELETE /api/threads/{thread_id}   — delete a thread and its checkpoints
- GET    /api/threads/{thread_id}/messages — get messages for a thread

NOTE: Thread CRUD routes (list/create/delete/messages) are intentionally NOT
JWT-protected. They operate on local SQLite data only, and this is a personal
tool where server-side access control on thread metadata adds no security value.
"""
import json
import uuid
from datetime import datetime, timezone

import aiosqlite
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.api.models import ChatAsyncResponse, ChatRequest, ChatResponse, ThreadInfo
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

    # Still in progress — register queue and wait
    queue = job_store.register_sse(job_id)

    async def generator():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("status") == "done":
                    break
        finally:
            job_store.unregister_sse(job_id)

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

    Direct SQL against AsyncSqliteSaver's checkpoints table.
    LangGraph's alist() requires a thread_id filter — no 'list all' API.
    """
    db_path = request.app.state.db_path
    threads: list[ThreadInfo] = []

    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                """SELECT thread_id, MAX(checkpoint_id) as latest
                   FROM checkpoints
                   WHERE checkpoint_ns = ''
                   GROUP BY thread_id
                   ORDER BY latest DESC
                   LIMIT 50""",
            ) as cur:
                rows = await cur.fetchall()

        for row in rows:
            thread_id, checkpoint_id = row[0], row[1]
            # checkpoint_id is a ULID-like string — extract timestamp for label
            label = f"Chat {thread_id[:8]}"
            threads.append(ThreadInfo(
                thread_id=thread_id,
                updated_at=str(checkpoint_id),
                label=label,
            ))
    except Exception:
        # DB may not exist yet (no messages sent) — return empty list
        pass

    return threads


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(thread_id: str, request: Request):
    """Delete a thread and all its checkpoints from SQLite.

    Removes rows from both `checkpoints` and `checkpoint_blobs` tables
    (AsyncSqliteSaver schema) for the given thread_id.
    """
    db_path = request.app.state.db_path

    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
            )
            await db.execute(
                "DELETE FROM checkpoint_blobs WHERE thread_id = ?", (thread_id,)
            )
            await db.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = ?", (thread_id,)
            )
            await db.commit()
    except Exception:
        # DB may not exist or tables may differ — silently succeed
        pass


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
