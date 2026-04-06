"""Chat and thread API routes (CHAT-01, CHAT-02, CHAT-03, CHAT-04, ASYNC-01, ASYNC-04, ASYNC-06).

Endpoints:
- POST   /api/chat                       — enqueue chat job, returns job_id immediately (JWT protected)
- GET    /api/chat/{job_id}/stream       — SSE stream for real-time job completion notification
- POST   /api/threads                    — create new thread (JWT protected)
- GET    /api/threads                    — list threads owned by the authenticated user (JWT protected)
- DELETE /api/threads/{thread_id}        — delete a thread and its checkpoints (JWT protected)
- PATCH  /api/threads/{thread_id}        — rename thread label (JWT protected)
- GET    /api/threads/{thread_id}/messages — get messages for a thread (JWT protected)
"""
import json
import uuid
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

import jwt
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from psycopg.rows import dict_row

from app.api.models import ChatAsyncResponse, ChatRequest, ChatResponse, RenameThreadRequest, ThreadInfo
from app.auth.jwt_utils import decode_jwt, decrypt_github_token

router = APIRouter(prefix="/api", tags=["chat"])


async def get_jwt_payload(request: Request) -> dict:
    """FastAPI dependency: decode JWT session cookie and return the full payload dict.

    Use this when you need JWT claims (e.g. github_login) without decrypting the token.

    Raises HTTPException 401 with detail:
    - "auth_required" if no session cookie is present
    - "auth_expired"  if JWT has expired
    - "auth_invalid"  if JWT is malformed or revoked
    """
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="auth_required")
    try:
        return decode_jwt(session_cookie)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="auth_expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="auth_invalid")


async def get_github_token(payload: dict = Depends(get_jwt_payload)) -> str:
    """FastAPI dependency: extract and decrypt GitHub token from JWT session cookie.

    Depends on get_jwt_payload so JWT decode is cached per-request by FastAPI.
    """
    return decrypt_github_token(payload["github_token"])


@router.post("/chat", response_model=ChatAsyncResponse)
async def send_message(
    request: Request,
    body: ChatRequest,
    github_token: str = Depends(get_github_token),
    payload: dict = Depends(get_jwt_payload),
):
    """Enqueue chat job and return job_id immediately (ASYNC-01).

    The actual LangGraph execution happens in the arq worker process.
    Frontend uses SSE or polling to get the result.

    Auth is enforced via JWT cookie through get_github_token dependency.
    After enqueuing, upserts github_login and app_id into threads table (first writer wins).
    app_id is derived from mode: 'super' -> 'superchat', 'simple' -> 'chat'.
    app_id is never overwritten on conflict — first message determines the application.
    """
    from arq import ArqRedis
    arq_redis: ArqRedis = request.app.state.arq_redis
    job_id = str(uuid.uuid4())

    # Mode -> task_type translation (D-04, D-05)
    # mode='super' overrides task_type to 'orchestrator'
    # mode='simple' preserves the existing task_type field (default 'langgraph')
    task_type = "orchestrator" if body.mode == "super" else body.task_type

    # Extract github_login before enqueue_job so it flows into the arq job payload
    # (CONTEXT-01: correlation chain requires user_id at job intake)
    # Prefer explicit app_id from frontend; fall back to mode-derived for backward compat (Pitfall 2 fix)
    if body.app_id:
        app_id = body.app_id
    else:
        app_id = "superchat" if body.mode == "super" else "chat"
    github_login = payload.get("github_login", "unknown")

    await arq_redis.enqueue_job(
        "process_chat",
        job_id=job_id,
        thread_id=body.thread_id,
        prompt=body.message,
        model=body.model,
        github_token=github_token,
        reply_to={"type": "web", "job_id": job_id},
        task_type=task_type,
        agents=body.agents,
        github_login=github_login,
        app_id=app_id,
        gem_ids=body.gem_ids,
        # Phase 17: 討論チャット
        participants=body.participants,
        pattern=body.pattern,
        max_turns=body.max_turns,
        current_turn=body.current_turn,
    )

    # Upsert threads table with app_id and github_login (first writer wins via COALESCE)
    # app_id is NOT overwritten on conflict — first message determines the application
    label = f"Chat {datetime.now(tz=JST).strftime('%Y-%m-%d %H:%M')}"
    db_uri = request.app.state.db_uri
    gem_id = body.gem_id  # Phase 15: Gem association (may be None)
    try:
        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            await conn.execute(
                """INSERT INTO threads (thread_id, app_id, github_login, label, gem_id, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s::uuid, now(), now())
                   ON CONFLICT (thread_id)
                   DO UPDATE SET github_login = COALESCE(threads.github_login, EXCLUDED.github_login),
                                 gem_id = COALESCE(threads.gem_id, EXCLUDED.gem_id),
                                 updated_at = now()""",
                (body.thread_id, app_id, github_login, label, gem_id),
            )
            await conn.commit()
    except Exception:
        pass  # Non-fatal: threads upsert failure should not block the chat job

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
async def create_thread(payload: dict = Depends(get_jwt_payload)):
    """Create a new conversation thread (CHAT-04).

    Returns a new UUID4 thread_id. The thread is implicitly created
    in the checkpoints table when the first message is sent via /api/chat.
    JWT protection ensures only authenticated users can create threads.
    """
    thread_id = str(uuid.uuid4())
    label = f"Chat {datetime.now(tz=JST).strftime('%Y-%m-%d %H:%M')}"
    return {"thread_id": thread_id, "label": label}


@router.get("/threads")
async def list_threads(request: Request, app_id: str | None = None, gem_id: str | None = None, payload: dict = Depends(get_jwt_payload)):
    """List threads owned by the authenticated user, sorted by latest activity.

    Filters by github_login from JWT — each user sees only their own threads.
    Uses LEFT JOIN from threads to checkpoints so threads without checkpoints are still visible.
    Optionally filters by app_id (e.g. 'chat' or 'superchat') when provided.
    Optionally filters by gem_id (UUID) when provided — used by GemChatApp to show only threads for a specific Gem.
    gem_id takes precedence over app_id when both are provided.
    Sorting uses t.updated_at DESC — checkpoint_id is NULL for new threads (LEFT JOIN), which
    would break sort order if used. updated_at from threads table is always reliable.
    LangGraph's alist() requires a thread_id filter — no 'list all' API; direct SQL used.
    """
    db_uri = request.app.state.db_uri
    github_login = payload.get("github_login", "")
    threads: list[ThreadInfo] = []

    try:
        async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                if gem_id is not None:
                    await cur.execute(
                        """SELECT t.thread_id, t.app_id, t.label, t.updated_at
                           FROM threads t
                           LEFT JOIN checkpoints c ON t.thread_id = c.thread_id AND c.checkpoint_ns = ''
                           WHERE t.github_login = %s
                             AND t.gem_id = %s::uuid
                           GROUP BY t.thread_id, t.app_id, t.label, t.updated_at
                           ORDER BY t.updated_at DESC
                           LIMIT 50""",
                        (github_login, gem_id),
                    )
                elif app_id is not None:
                    await cur.execute(
                        """SELECT t.thread_id, t.app_id, t.label, t.updated_at
                           FROM threads t
                           LEFT JOIN checkpoints c ON t.thread_id = c.thread_id AND c.checkpoint_ns = ''
                           WHERE t.github_login = %s
                             AND t.app_id = %s
                           GROUP BY t.thread_id, t.app_id, t.label, t.updated_at
                           ORDER BY t.updated_at DESC
                           LIMIT 50""",
                        (github_login, app_id),
                    )
                else:
                    await cur.execute(
                        """SELECT t.thread_id, t.app_id, t.label, t.updated_at
                           FROM threads t
                           LEFT JOIN checkpoints c ON t.thread_id = c.thread_id AND c.checkpoint_ns = ''
                           WHERE t.github_login = %s
                           GROUP BY t.thread_id, t.app_id, t.label, t.updated_at
                           ORDER BY t.updated_at DESC
                           LIMIT 50""",
                        (github_login,),
                    )
                rows = await cur.fetchall()

        for row in rows:
            thread_id = row["thread_id"]
            label = row["label"] or f"Chat {thread_id[:8]}"
            threads.append(ThreadInfo(
                thread_id=thread_id,
                app_id=row["app_id"],
                updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                label=label,
            ))
    except Exception:
        # DB may not be reachable yet (no messages sent) — return empty list
        pass

    return threads


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(thread_id: str, request: Request, payload: dict = Depends(get_jwt_payload)):
    """Delete a thread and all its checkpoints from PostgreSQL.

    JWT-protected. Verifies ownership via threads table before deleting.
    Returns 404 if thread does not belong to the authenticated user.
    Uses AsyncPostgresSaver.adelete_thread() which atomically removes
    all related rows from checkpoints, checkpoint_blobs, and checkpoint_writes.
    """
    github_login = payload.get("github_login", "")
    db_uri = request.app.state.db_uri

    # Verify ownership
    try:
        async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT github_login FROM threads WHERE thread_id = %s",
                    (thread_id,),
                )
                row = await cur.fetchone()

        if row is None or row["github_login"] != github_login:
            raise HTTPException(status_code=404, detail="Thread not found")
    except HTTPException:
        raise
    except Exception:
        pass  # If DB check fails, proceed with delete (non-blocking ownership check)

    checkpointer = request.app.state.checkpointer
    try:
        await checkpointer.adelete_thread(thread_id)
    except Exception:
        # Silently succeed if thread doesn't exist
        pass


@router.patch("/threads/{thread_id}")
async def rename_thread(thread_id: str, body: RenameThreadRequest, request: Request, payload: dict = Depends(get_jwt_payload)):
    """Update the display label for a thread.

    JWT-protected. Updates the label in the threads table.
    Only called on existing threads from the UI — if thread doesn't exist, UPDATE affects 0 rows (acceptable).
    """
    label = body.label.strip()
    if not label:
        raise HTTPException(status_code=422, detail="label must not be empty")

    db_uri = request.app.state.db_uri
    async with await psycopg.AsyncConnection.connect(db_uri) as conn:
        await conn.execute(
            "UPDATE threads SET label = %s, updated_at = now() WHERE thread_id = %s",
            (label, thread_id),
        )
        await conn.commit()

    return {"thread_id": thread_id, "label": label}


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, request: Request, payload: dict = Depends(get_jwt_payload)):
    """Get all messages for a specific thread.

    JWT-protected. Uses graph.aget_state() to retrieve the full message list from the checkpoint.
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
