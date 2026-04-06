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
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from redis.asyncio import Redis

from app.api.routes import agents, apps, auth, canvas, chat, gems, health, jobs, me
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
        # Schema migration: replace thread_labels with normalized schema
        # (applications, threads, audit_log).
        async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
            # 1. Drop legacy table
            await conn.execute("DROP TABLE IF EXISTS thread_labels")

            # 2. Applications registry
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS applications (
                       app_id       TEXT PRIMARY KEY,
                       display_name TEXT NOT NULL,
                       enabled      BOOLEAN NOT NULL DEFAULT true,
                       created_at   TIMESTAMPTZ DEFAULT now()
                   )"""
            )

            # 3. Seed known applications (idempotent)
            await conn.execute(
                """INSERT INTO applications (app_id, display_name, enabled, created_at) VALUES
                       ('chat',      'Chat',      true, now()),
                       ('superchat', 'SuperChat', true, now())
                   ON CONFLICT DO NOTHING"""
            )

            # 3b. Dynamic seeding from APP.md files (Pitfall 3: FK constraint for new app slugs)
            # Scans APP_DIR for discovered app slugs and upserts into applications table.
            import frontmatter as fm
            app_dir_env = os.getenv("APP_DIR", "./apps")
            for app_md in Path(app_dir_env).glob("*/APP.md"):
                slug = app_md.parent.name
                try:
                    post = fm.load(str(app_md))
                    display_name = post.metadata.get("name", slug)
                    await conn.execute(
                        "INSERT INTO applications (app_id, display_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (slug, str(display_name)),
                    )
                except Exception:
                    pass  # Malformed APP.md — skip, not fatal at startup

            # 4. Thread metadata (replaces thread_labels)
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS threads (
                       thread_id    TEXT PRIMARY KEY,
                       app_id       TEXT NOT NULL REFERENCES applications(app_id),
                       github_login TEXT NOT NULL,
                       label        TEXT NOT NULL,
                       created_at   TIMESTAMPTZ DEFAULT now(),
                       updated_at   TIMESTAMPTZ DEFAULT now()
                   )"""
            )

            # 5. Audit log (schema only — no write logic added here)
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS audit_log (
                       id           BIGSERIAL PRIMARY KEY,
                       github_login TEXT NOT NULL,
                       app_id       TEXT REFERENCES applications(app_id),
                       thread_id    TEXT,
                       action       TEXT NOT NULL,
                       metadata     JSONB,
                       created_at   TIMESTAMPTZ DEFAULT now()
                   )"""
            )

            # 6. Indexes on audit_log
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS audit_log_github_login_idx ON audit_log(github_login)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS audit_log_created_at_idx ON audit_log(created_at)"
            )

            # --- Phase 15: Gem + Canvas tables ---

            # gems テーブル（AI ペルソナ管理）
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS gems (
                       gem_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                       github_login  TEXT NOT NULL,
                       name          TEXT NOT NULL,
                       system_prompt TEXT NOT NULL DEFAULT '',
                       type          TEXT NOT NULL DEFAULT 'default',
                       created_at    TIMESTAMPTZ DEFAULT now(),
                       updated_at    TIMESTAMPTZ DEFAULT now()
                   )"""
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS gems_github_login_idx ON gems(github_login)"
            )

            # Phase 15.1: Gem description / knowledge カラム追加（idempotent）
            await conn.execute(
                "ALTER TABLE gems ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''"
            )
            await conn.execute(
                "ALTER TABLE gems ADD COLUMN IF NOT EXISTS knowledge TEXT NOT NULL DEFAULT ''"
            )

            # Gem 公開共有: is_public フラグ
            await conn.execute(
                "ALTER TABLE gems ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT false"
            )

            # threads テーブルへの gem_id カラム追加（gems テーブル作成後に実行 — Pitfall 2）
            await conn.execute(
                "ALTER TABLE threads ADD COLUMN IF NOT EXISTS gem_id UUID REFERENCES gems(gem_id) ON DELETE SET NULL"
            )

            # canvas_apps テーブル（生成 HTML 保存）
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS canvas_apps (
                       app_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                       thread_id    TEXT REFERENCES threads(thread_id) ON DELETE SET NULL,
                       github_login TEXT NOT NULL,
                       name         TEXT NOT NULL,
                       html         TEXT NOT NULL,
                       source       TEXT NOT NULL DEFAULT 'canvas',
                       deployed     BOOLEAN NOT NULL DEFAULT FALSE,
                       deployed_at  TIMESTAMPTZ,
                       created_at   TIMESTAMPTZ DEFAULT now(),
                       UNIQUE (thread_id, github_login)
                   )"""
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS canvas_apps_thread_id_idx ON canvas_apps(thread_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS canvas_apps_github_login_idx ON canvas_apps(github_login)"
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

        # Phase 12: Build metadata-only agent health for GET /health/agents
        # This does NOT instantiate ChatCopilot -- only parses AGENT.md and checks agent.py importability
        from app.orchestrator.agent import (
            AgentHealth, AgentStatusEnum,
            _check_agent_importable, _INIT_FAILURE_TYPES,
        )
        import frontmatter as fm
        agent_health: list[AgentHealth] = []
        agent_dir_path = os.getenv("AGENT_DIR", "./agents")
        for agent_md in Path(agent_dir_path).glob("*/AGENT.md"):
            agent_name = agent_md.parent.name
            try:
                post = fm.load(str(agent_md))
                name = post.metadata.get("name", agent_name)
                has_code = (agent_md.parent / "agent.py").exists()
                agent_type = "code" if has_code else "folder"
                # For code-type, verify the module is importable (but don't instantiate)
                if has_code:
                    _check_agent_importable(agent_md.parent)
                agent_health.append(AgentHealth(
                    name=name, agent_type=agent_type, status=AgentStatusEnum.HEALTHY
                ))
            except _INIT_FAILURE_TYPES as e:
                agent_health.append(AgentHealth(
                    name=agent_name, agent_type="unknown",
                    status=AgentStatusEnum.FAILED, error=str(e)
                ))
            except Exception as e:
                agent_health.append(AgentHealth(
                    name=agent_name, agent_type="unknown",
                    status=AgentStatusEnum.DEGRADED, error=str(e)
                ))
        app.state.agent_health = agent_health

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
app.include_router(agents.router)
app.include_router(apps.router)
app.include_router(health.router)
app.include_router(gems.router)
app.include_router(canvas.router)

# React UI — mount BEFORE the "/" catch-all or it will never be reached.
# Guard: only mount if frontend/dist/ exists (avoids startup crash before first build).
# Per Pitfall 5 in 07-RESEARCH.md.
if os.path.isdir("frontend/dist"):
    app.mount("/react", StaticFiles(directory="frontend/dist", html=True), name="react")

# Canvas deployed apps — must be before "/" catch-all
os.makedirs("./static/apps", exist_ok=True)
app.mount("/apps", StaticFiles(directory="./static/apps", html=True), name="canvas_apps")

# Static files LAST — serves index.html for any non-API path
app.mount("/", StaticFiles(directory="static", html=True), name="static")
