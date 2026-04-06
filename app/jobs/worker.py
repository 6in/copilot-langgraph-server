"""arq worker — routing facade for pluggable async task types.

Run with: uv run arq app.jobs.worker.WorkerSettings

Incoming jobs carry a `task_type` field that selects the handler:
  - "langgraph" (default) — LangGraph chat via ChatCopilot
  - "orchestrator" — OrchestratorGraph multi-agent routing via SubAgentRegistry
  - Future task types are registered in TASK_HANDLERS below.

All handlers implement TaskHandler.handle(ctx, job) -> dict.
Backward compatibility: jobs without task_type default to "langgraph".
"""
import os

from arq.connections import RedisSettings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from redis.asyncio import Redis

from app.jobs.handlers.base import TaskHandler
from app.jobs.handlers.debate_handler import DebateHandler
from app.jobs.handlers.langgraph_handler import LangGraphHandler
from app.jobs.handlers.orchestrator_handler import OrchestratorHandler
from app.jobs.job_store import JobStore

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Registry: task_type → handler instance
TASK_HANDLERS: dict[str, TaskHandler] = {
    "langgraph": LangGraphHandler(),
    "orchestrator": OrchestratorHandler(),
    "debate": DebateHandler(),  # Phase 17: 討論チャット
}


async def startup(ctx: dict) -> None:
    """arq on_startup: init Redis client, JobStore, and run checkpointer setup.

    Calls checkpointer.setup() to prevent race condition: if api lifespan
    hasn't completed setup() before the first job arrives, this ensures tables exist.
    setup() is idempotent — safe to call multiple times.
    """
    ctx["redis_client"] = Redis.from_url(REDIS_URL)
    ctx["job_store"] = JobStore(ctx["redis_client"])
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        await checkpointer.setup()


async def shutdown(ctx: dict) -> None:
    """arq on_shutdown: close Redis connection."""
    await ctx["redis_client"].aclose()


async def process_chat(
    ctx: dict,
    *,
    job_id: str,
    thread_id: str,
    prompt: str,
    model: str = "claude-sonnet-4.5",
    github_token: str,
    reply_to: dict,
    task_type: str = "langgraph",
    agents: list[str] | None = None,
    github_login: str = "unknown",
    app_id: str | None = None,
    gem_ids: list[str] | None = None,
    # Phase 17: 討論チャット
    participants: list[str] | None = None,
    pattern: str = "debate",
    max_turns: int = 3,
    current_turn: int = 0,
) -> dict:
    """arq job function: route to the appropriate handler by task_type.

    The job payload is forwarded as a dict so each handler can extract
    only the fields it needs. New task types are added to TASK_HANDLERS
    without touching this function.

    Critical ordering is delegated to each handler:
    save_result() BEFORE notifier.done() so SSE clients can fetch immediately.
    """
    handler = TASK_HANDLERS.get(task_type)
    if handler is None:
        job_store: JobStore = ctx["job_store"]
        await job_store.save_result(job_id, f"Error: unknown task_type '{task_type}'")
        return {"job_id": job_id, "status": "error", "reason": f"unknown task_type '{task_type}'"}

    job = {
        "job_id": job_id,
        "thread_id": thread_id,
        "prompt": prompt,
        "model": model,
        "github_token": github_token,
        "reply_to": reply_to,
        "task_type": task_type,
        "agents": agents,
        "github_login": github_login,
        "app_id": app_id,
        "gem_ids": gem_ids,
        # Phase 17
        "participants": participants,
        "pattern": pattern,
        "max_turns": max_turns,
        "current_turn": current_turn,
    }
    return await handler.handle(ctx, job)


class WorkerSettings:
    """arq worker configuration.

    Start worker: uv run arq app.jobs.worker.WorkerSettings
    """

    functions = [process_chat]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    job_timeout = 300  # 5 minutes — matches send_and_wait timeout
