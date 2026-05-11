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
import os
import shutil
import uuid
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

import jwt
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from psycopg.rows import dict_row

from app.api.models import ChatAsyncResponse, ChatRequest, RenameThreadRequest, ThreadInfo
from app.auth.jwt_utils import decode_jwt, decrypt_github_token, async_is_blocked

router = APIRouter(prefix="/api", tags=["chat"])

# Phase 37 D-01/D-03/D-04: thread フォルダ base path。api:RW mount で削除可能。
THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")


def _normalize_content(content) -> str:
    """Normalize BaseMessage.content to a string for UI rendering.

    Copilot SDK usually returns str, but structured content (list[dict])
    appears when tool_use blocks or CodeAct results are included in the
    AIMessage. ReactMarkdown requires a string children prop — passing
    an object crashes the entire chat UI (assertion error).

    - str                  -> return as-is
    - list[dict] (LC v2)   -> concatenate "text" blocks, skip non-text blocks
    - anything else        -> json.dumps fallback (never return non-str)
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                # LangChain structured content: {"type": "text", "text": "..."}
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    parts.append(block["text"])
                # tool_use / tool_result / image_url などは履歴 UI には出さない
            elif isinstance(block, str):
                parts.append(block)
        if parts:
            return "\n".join(parts)
        # 構造化ブロックがあるが text が無い場合は JSON ダンプで可視化
        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)
    # dict / その他型 — JSON ダンプ
    try:
        return json.dumps(content, ensure_ascii=False)
    except Exception:
        return str(content)


async def get_jwt_payload(request: Request) -> dict:
    """FastAPI dependency: decode JWT session cookie and return the full payload dict.

    Use this when you need JWT claims (e.g. github_login) without decrypting the token.
    Checks the Redis blocklist (shared with arq worker) for revoked JTIs.

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
        # Check Redis blocklist (survives restarts and is shared with arq worker)
        jti = payload.get("jti", "")
        if jti:
            redis = getattr(request.app.state, "redis_client", None)
            if redis and await async_is_blocked(jti, redis):
                raise jwt.InvalidTokenError("Token revoked")
        return payload
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

    # Upsert threads table BEFORE enqueuing the job.
    # The worker calls _get_gem_info(thread_id) immediately on pickup — if the thread
    # row isn't committed yet, gem_type comes back None and the system prompt is skipped.
    # Inserting first eliminates this race condition (fix for canvas/gem system prompt bug).
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
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("threads upsert failed: %s", e, exc_info=True)
        # Non-fatal: threads upsert failure should not block the chat job

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
        gem_id=body.gem_id,
        gem_ids=body.gem_ids,
        context_messages=[m.model_dump() for m in body.context_messages] if body.context_messages else None,
        # Phase 17: 討論チャット
        participants=body.participants,
        pattern=body.pattern,
        max_turns=body.max_turns,
        current_turn=body.current_turn,
        # Phase 36 (D-14): forward per-turn attachments to worker
        attachments=body.attachments,
    )

    return ChatAsyncResponse(job_id=job_id, thread_id=body.thread_id)


@router.get("/chat/{job_id}/stream")
async def stream_job(job_id: str, request: Request, payload: dict = Depends(get_jwt_payload)):
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

    # Still in progress — poll Redis list for debate turns + Redis key for completion
    async def generator():
        import asyncio
        seen_turns = 0
        seen_tokens = 0
        while True:
            if await request.is_disconnected():
                break
            # 新しいターンをポーリング
            turns = await job_store.get_turns(job_id, since=seen_turns)
            for turn in turns:
                yield f"data: {json.dumps({'status': 'message', 'turn': turn})}\n\n"
                seen_turns += 1
            # 新しいストリーミングトークンを drain
            tokens = await job_store.get_tokens(job_id, since=seen_tokens)
            for tok in tokens:
                yield f"data: {json.dumps({'status': 'token', 'token': tok})}\n\n"
                seen_tokens += 1
            # 完了チェック
            result = await job_store.get(job_id)
            if result and result.get("status") == "done":
                # 残っているトークンを最後に flush
                tokens = await job_store.get_tokens(job_id, since=seen_tokens)
                for tok in tokens:
                    yield f"data: {json.dumps({'status': 'token', 'token': tok})}\n\n"
                    seen_tokens += 1
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
                break
            tool_info = await job_store.get_tool_event(job_id)
            if tool_info:
                yield f"data: {json.dumps({'status': 'tool_executing', 'tool': tool_info['tool'], 'query': tool_info.get('query', '')})}\n\n"
            elif not tokens:
                yield f"data: {json.dumps({'status': 'thinking'})}\n\n"
            await asyncio.sleep(0.15)

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
                    # gem_id IS NULL を追加: gem専用スレッド（Canvas含む旧app_id='chat'）を除外
                    await cur.execute(
                        """SELECT t.thread_id, t.app_id, t.label, t.updated_at
                           FROM threads t
                           LEFT JOIN checkpoints c ON t.thread_id = c.thread_id AND c.checkpoint_ns = ''
                           WHERE t.github_login = %s
                             AND t.app_id = %s
                             AND t.gem_id IS NULL
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

    # Verify ownership and delete from threads table
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

                await cur.execute(
                    "DELETE FROM threads WHERE thread_id = %s AND github_login = %s",
                    (thread_id, github_login),
                )
            await conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e

    checkpointer = request.app.state.checkpointer
    try:
        await checkpointer.adelete_thread(thread_id)
    except Exception:
        # Silently succeed if thread doesn't exist
        pass

    # Phase 37 D-03 + D-18 W-01: thread フォルダを同期削除 (RW mount, api container)。
    # パストラバーサルを遮断するため必ず realpath prefix assert を通す。
    thread_folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    try:
        real_folder = os.path.realpath(thread_folder)
        root = os.path.realpath(THREAD_FILES_DIR)
        if not real_folder.startswith(root + os.sep):
            # path traversal 検出: github_login / thread_id に `..` 等が混入した場合
            # 204 は返すが削除はしない
            raise ValueError(f"path traversal attempt: {thread_folder}")
        shutil.rmtree(real_folder, ignore_errors=True)
    except ValueError as ve:
        # MEDIUM-03 (Phase 37 Code Review): traversal 検出を監査ログに残す。
        # セキュリティイベントはログなしで握り潰してはならない。thread の論理削除は完了済み。
        import logging
        logging.getLogger(__name__).warning(
            "path traversal attempt blocked in delete_thread: "
            "thread_id=%r github_login=%r reason=%s",
            thread_id, github_login, ve,
        )
    except Exception:
        pass   # 予期せぬエラーも握り潰す


@router.patch("/threads/{thread_id}")
async def rename_thread(thread_id: str, body: RenameThreadRequest, request: Request, payload: dict = Depends(get_jwt_payload)):
    """Update the display label for a thread.

    JWT-protected. Updates the label in the threads table.
    Only called on existing threads from the UI — if thread doesn't exist, UPDATE affects 0 rows (acceptable).
    """
    label = body.label.strip()
    if not label:
        raise HTTPException(status_code=422, detail="label must not be empty")

    github_login = payload.get("github_login", "")
    db_uri = request.app.state.db_uri
    async with await psycopg.AsyncConnection.connect(db_uri) as conn:
        result = await conn.execute(
            "UPDATE threads SET label = %s, updated_at = now() WHERE thread_id = %s AND github_login = %s",
            (label, thread_id, github_login),
        )
        await conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Thread not found")

    return {"thread_id": thread_id, "label": label}


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, request: Request, payload: dict = Depends(get_jwt_payload)):
    """Get all messages for a specific thread.

    JWT-protected. Determines thread type (chat/orchestrator/debate) from threads table
    and uses the matching state schema to read the checkpoint correctly.
    - chat threads: MessagesState (default graph)
    - orchestrator/superchat threads: AgentState (preserves AIMessage.name for agent badges)
    - debate threads: DebateState (preserves per-agent turns)
    """
    config = {"configurable": {"thread_id": thread_id}}
    db_uri = request.app.state.db_uri

    # Determine thread type to select the correct state schema
    thread_app_id: str | None = None
    try:
        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT app_id FROM threads WHERE thread_id = %s", (thread_id,)
                )
                row = await cur.fetchone()
                thread_app_id = row[0] if row else None
    except Exception:
        pass

    # Helper: convert BaseMessage list to API response format
    def _messages_to_response(raw_messages: list) -> list[dict]:
        messages = []
        for msg in raw_messages:
            # System prompts and internal tool results are not shown in chat history UI
            if isinstance(msg, (SystemMessage, ToolMessage)):
                continue
            role = "user" if isinstance(msg, HumanMessage) else "ai"
            entry: dict = {"role": role, "content": _normalize_content(msg.content)}
            sender = getattr(msg, "name", None)
            if sender:
                entry["senderName"] = sender
            # Phase 36 D-22: additional_kwargs を透過的に返す (現時点は attachments のみ公開).
            # Pitfall 10 None-guard: legacy メッセージでは additional_kwargs が None / 欠損 / 空 dict.
            kw = getattr(msg, "additional_kwargs", None) or {}
            if kw:
                public_kw: dict = {}
                atts = kw.get("attachments")
                if isinstance(atts, list) and atts:
                    public_kw["attachments"] = atts
                if public_kw:
                    entry["additional_kwargs"] = public_kw
            messages.append(entry)
        return messages

    # --- Orchestrator/SuperChat threads: read with AgentState schema ---
    if thread_app_id and thread_app_id not in ("chat", "debate"):
        try:
            from app.orchestrator.state import AgentState
            from langgraph.graph import StateGraph as _SG
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            async with AsyncPostgresSaver.from_conn_string(db_uri) as ckpt:
                minimal = _SG(AgentState)
                minimal.add_node("_r", lambda s: s)
                minimal.set_entry_point("_r")
                compiled = minimal.compile(checkpointer=ckpt)
                orch_state = await compiled.aget_state(config)

            if orch_state and orch_state.values and "messages" in orch_state.values:
                messages = _messages_to_response(orch_state.values["messages"])
                # AgentState stores agent_name at state level; apply to last AI message
                # if AIMessage.name was lost during checkpoint serialization
                agent_name = orch_state.values.get("agent_name")
                if agent_name and messages:
                    for i in range(len(messages) - 1, -1, -1):
                        if messages[i]["role"] == "ai" and "senderName" not in messages[i]:
                            messages[i]["senderName"] = agent_name
                            break
                if messages:
                    return {"messages": messages, "thread_id": thread_id}
        except Exception:
            pass

    # --- Default: chat threads with MessagesState ---
    if thread_app_id in (None, "chat"):
        graph = request.app.state.graph
        try:
            state = await graph.aget_state(config)
            if state.values and "messages" in state.values:
                messages = _messages_to_response(state.values["messages"])
                if messages:
                    # Canvas threads: replace last AI message with canvas JSON
                    try:
                        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
                            async with conn.cursor() as cur:
                                await cur.execute(
                                    "SELECT app_id, name, html FROM canvas_apps WHERE thread_id = %s LIMIT 1",
                                    (thread_id,),
                                )
                                row = await cur.fetchone()
                        if row:
                            app_id_c, name_val, html_val = row
                            canvas_json = json.dumps({
                                "type": "canvas",
                                "app_id": str(app_id_c),
                                "name": name_val or "Canvas App",
                                "html": html_val or "",
                            })
                            for i in range(len(messages) - 1, -1, -1):
                                if messages[i]["role"] == "ai":
                                    messages[i] = {**messages[i], "content": canvas_json}
                                    break
                    except Exception:
                        pass
                    return {"messages": messages, "thread_id": thread_id}
        except Exception:
            pass

    # --- Debate threads: read with DebateState schema ---
    try:
        if thread_app_id == "debate":
            from app.orchestrator.debate_graph import DebateState
            from langgraph.graph import StateGraph as _SG
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            async with AsyncPostgresSaver.from_conn_string(db_uri) as ckpt:
                minimal = _SG(DebateState)
                minimal.add_node("_r", lambda s: s)
                minimal.set_entry_point("_r")
                compiled = minimal.compile(checkpointer=ckpt)
                debate_state = await compiled.aget_state(config)

            if debate_state and debate_state.values:
                debate_msgs = debate_state.values.get("messages", [])
                messages = _messages_to_response(debate_msgs)
                return {"messages": messages, "thread_id": thread_id}
    except Exception:
        pass

    return {"messages": [], "thread_id": thread_id}
