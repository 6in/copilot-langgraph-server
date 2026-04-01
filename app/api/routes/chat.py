"""Chat and thread API routes (CHAT-01, CHAT-02, CHAT-03, CHAT-04).

Endpoints:
- POST   /api/chat         — send message, get AI reply
- POST   /api/threads      — create new thread (returns UUID)
- GET    /api/threads      — list existing threads
- DELETE /api/threads/{thread_id} — delete a thread and its checkpoints
- GET    /api/threads/{thread_id}/messages — get messages for a thread
"""
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Request
from langchain_core.messages import AIMessage, HumanMessage

from app.api.models import ChatRequest, ChatResponse, ThreadInfo

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def send_message(request: Request, body: ChatRequest):
    """Send a message and get an AI reply.

    Per D-11: model field in request body — switch takes effect on this send.
    Per Pitfall 4: catch auth errors from SDK, set auth_expired flag.
    """
    graph = request.app.state.graph

    # Override model if frontend sends a different one (D-11)
    llm = request.app.state.llm
    if body.model != llm.model:
        llm.model = body.model

    config = {"configurable": {"thread_id": body.thread_id}}

    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=body.message)]},
            config=config,
        )
    except Exception as e:
        error_msg = str(e).lower()
        # Detect auth-related errors from Copilot SDK
        if any(kw in error_msg for kw in ("auth", "token", "unauthorized", "401")):
            request.app.state.auth_expired = True
            return ChatResponse(
                reply="",
                thread_id=body.thread_id,
                error="auth_expired",
            )
        return ChatResponse(
            reply="",
            thread_id=body.thread_id,
            error=f"Something went wrong: {e}",
        )

    reply_content = result["messages"][-1].content
    return ChatResponse(reply=reply_content, thread_id=body.thread_id)


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
