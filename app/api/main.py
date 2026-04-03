"""FastAPI application entry point.

Lifespan manages:
- CopilotAuthManager instance
- ChatCopilot LLM provider
- AsyncPostgresSaver checkpointer (PostgreSQL, async context manager)
- Compiled LangGraph graph
- Redis client, arq pool, JobStore (Phase 4)

All shared via app.state for route access.
"""
import os
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from redis.asyncio import Redis

from app.api.routes import auth, chat, jobs, me
from app.auth.manager import CopilotAuthManager
from app.graph.builder import build_graph
from app.jobs.job_store import JobStore
from app.providers.copilot import ChatCopilot

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")

# root_path tells FastAPI its public URL prefix (for OpenAPI docs /docs, /redoc).
# nginx strips the prefix before forwarding, so all routes stay at /api/...
APP_PREFIX = os.getenv("APP_PREFIX", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down shared resources."""
    auth_manager = CopilotAuthManager()
    llm = ChatCopilot(auth_manager=auth_manager)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = Redis.from_url(redis_url)
    arq_redis = await create_pool(RedisSettings.from_dsn(redis_url))
    job_store = JobStore(redis_client)

    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        await checkpointer.setup()
        # Custom table for user-defined thread labels (editable via PATCH /api/threads/{id})
        async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS thread_labels (
                       thread_id TEXT PRIMARY KEY,
                       label     TEXT NOT NULL,
                       updated_at TIMESTAMPTZ DEFAULT now()
                   )"""
            )
            await conn.commit()
        app.state.graph = build_graph(llm, checkpointer)
        app.state.checkpointer = checkpointer
        app.state.auth_manager = auth_manager
        app.state.llm = llm
        app.state.db_uri = DB_URI
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


app = FastAPI(title="Copilot Chat", lifespan=lifespan, root_path=APP_PREFIX)

# CORS for Vite dev server — must be registered BEFORE include_router calls.
# Per Pitfall 3 in 07-RESEARCH.md: middleware added after routes may not wrap them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes FIRST — before static mount (Pitfall 3: mount order matters)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(jobs.router)
app.include_router(me.router)

# React UI — mount BEFORE the "/" catch-all or it will never be reached.
# Guard: only mount if frontend/dist/ exists (avoids startup crash before first build).
# Per Pitfall 5 in 07-RESEARCH.md.
if os.path.isdir("frontend/dist"):
    app.mount("/react", StaticFiles(directory="frontend/dist", html=True), name="react")

# Static files LAST — serves index.html for any non-API path
app.mount("/", StaticFiles(directory="static", html=True), name="static")
