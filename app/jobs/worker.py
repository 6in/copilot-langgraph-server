"""arq worker — routing facade for pluggable async task types.

Run with: uv run arq app.jobs.worker.WorkerSettings

Incoming jobs carry a `task_type` field that selects the handler:
  - "langgraph" (default) — LangGraph chat via ChatCopilot
  - "orchestrator" — OrchestratorGraph multi-agent routing via SubAgentRegistry
  - "iframe_app_api" — iframe JSON-RPC bridge (Phase 18)
  - Future task types are registered in TASK_HANDLERS below.

All handlers implement TaskHandler.handle(ctx, job) -> dict.
Backward compatibility: jobs without task_type default to "langgraph".
"""
import logging
import os

import yaml
from arq.connections import RedisSettings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from app.jobs.handlers.base import TaskHandler
from app.jobs.handlers.debate_handler import DebateHandler
from app.jobs.handlers.iframe_rpc_handler import IframeRpcHandler
from app.jobs.handlers.langgraph_handler import LangGraphHandler
from app.jobs.handlers.orchestrator_handler import OrchestratorHandler
from app.jobs.job_store import JobStore

logger = logging.getLogger(__name__)

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DB_POOLS_CONFIG = os.getenv("DB_POOLS_CONFIG", "config/db_pools.yaml")
MCP_TOOLS_CONFIG = os.getenv("MCP_TOOLS_CONFIG", "config/mcp_tools.yaml")  # Phase 24 (MCP-03)

# Registry: task_type → handler instance
TASK_HANDLERS: dict[str, TaskHandler] = {
    "langgraph": LangGraphHandler(),
    "orchestrator": OrchestratorHandler(),
    "debate": DebateHandler(),  # Phase 17: 討論チャット
    "iframe_app_api": IframeRpcHandler(),  # Phase 18: iframe JSON-RPC bridge
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

    # Phase 18: DB connection pools for iframe-rpc QUERY method
    ctx["db_pools"] = {}
    try:
        with open(DB_POOLS_CONFIG) as f:
            pools_cfg = yaml.safe_load(f) or {}
        for name, cfg in pools_cfg.get("pools", {}).items():
            pool = AsyncConnectionPool(conninfo=cfg["dsn"], open=False, min_size=1, max_size=5)
            await pool.open(wait=True, timeout=30.0)
            ctx["db_pools"][name] = pool
    except FileNotFoundError:
        pass  # No config file — QUERY method unavailable (non-fatal)

    # Phase 21: MCP client Singleton (D-04)
    # Pitfall 5: MCP server may not be running — graceful degradation
    ctx["mcp_tools"] = []
    ctx["mcp_client"] = None
    mcp_tools_loaded: list = []
    mcp_connected = False
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        mcp_url = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001") + "/mcp"
        mcp_client = MultiServerMCPClient({
            "copilot-tools": {
                "transport": "streamable_http",
                "url": mcp_url,
            }
        })
        mcp_tools_loaded = await mcp_client.get_tools()
        ctx["mcp_client"] = mcp_client
        mcp_connected = True
        logger.info("[worker] MCP tools loaded: %s", [t.name for t in mcp_tools_loaded])
    except Exception as e:
        logger.warning("[worker] MCP client init failed (DEGRADED): %s", e)
        # mcp_tools remains [] — ToolEnabledSubAgent will fall back to normal SubAgent

    # Phase 24 (MCP-03): ToolRegistry バリデーション
    # try/except の外で実行。RuntimeError は伝播させて worker 起動を失敗させる (D-03)。
    # MCP 接続失敗時 (DEGRADED) はバリデーションをスキップして既存挙動を維持する。
    if mcp_connected:
        from app.orchestrator.tool_registry import ToolRegistry

        registry = ToolRegistry(MCP_TOOLS_CONFIG)
        await registry.validate(mcp_tools_loaded)  # 不一致なら RuntimeError → worker 起動失敗
        logger.info("[worker] ToolRegistry validation passed (%d tools)", len(mcp_tools_loaded))
        ctx["mcp_tools"] = mcp_tools_loaded


async def shutdown(ctx: dict) -> None:
    """arq on_shutdown: close Redis connection."""
    # Phase 18: Close DB pools
    for pool in ctx.get("db_pools", {}).values():
        await pool.close()
    # Phase 21: MCP client cleanup
    # (MultiServerMCPClient has no explicit close, but keep reference cleanup)
    ctx.pop("mcp_client", None)
    ctx.pop("mcp_tools", None)
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
    gem_id: str | None = None,
    gem_ids: list[str] | None = None,
    # Phase 17: 討論チャット
    participants: list[str] | None = None,
    pattern: str = "debate",
    max_turns: int = 3,
    current_turn: int = 0,
    # Phase 18: iframe JSON-RPC bridge
    rpc_method: str | None = None,
    rpc_params: dict | None = None,
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
        "gem_id": gem_id,
        "gem_ids": gem_ids,
        # Phase 17
        "participants": participants,
        "pattern": pattern,
        "max_turns": max_turns,
        "current_turn": current_turn,
        # Phase 18
        "rpc_method": rpc_method,
        "rpc_params": rpc_params,
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
