"""FastAPI application entry point.

Lifespan manages:
- CopilotAuthManager instance
- ChatCopilot LLM provider
- AsyncSqliteSaver checkpointer (async context manager)
- Compiled LangGraph graph
- Redis client, arq pool, JobStore (Phase 4)

All shared via app.state for route access.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from redis.asyncio import Redis

from app.api.routes import auth, chat, jobs
from app.auth.manager import CopilotAuthManager
from app.graph.builder import build_graph
from app.jobs.job_store import JobStore
from app.providers.copilot import ChatCopilot

DB_PATH = "./data/chat.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down shared resources."""
    Path("./data").mkdir(exist_ok=True)

    auth_manager = CopilotAuthManager()
    llm = ChatCopilot(auth_manager=auth_manager)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = Redis.from_url(redis_url)
    arq_redis = await create_pool(RedisSettings.from_dsn(redis_url))
    job_store = JobStore(redis_client)

    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        app.state.graph = build_graph(llm, checkpointer)
        app.state.checkpointer = checkpointer
        app.state.auth_manager = auth_manager
        app.state.llm = llm
        app.state.db_path = DB_PATH
        # Temporary storage for in-flight Device Flow sessions (keyed by flow_id)
        app.state.device_flows = {}
        # Phase 4: Redis + arq + JobStore
        app.state.redis = redis_client
        app.state.arq_redis = arq_redis
        app.state.job_store = job_store
        yield

    await llm.close()
    await redis_client.aclose()
    await arq_redis.aclose()


app = FastAPI(title="Copilot Chat", lifespan=lifespan)

# API routes FIRST — before static mount (Pitfall 3: mount order matters)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(jobs.router)

# Static files LAST — serves index.html for any non-API path
app.mount("/", StaticFiles(directory="static", html=True), name="static")
