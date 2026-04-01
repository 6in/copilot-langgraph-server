# Phase 6: SQLite → PostgreSQL Checkpointer Migration — Research

**Researched:** 2026-04-01
**Domain:** LangGraph checkpointer migration, psycopg 3, Docker Compose
**Confidence:** HIGH

---

## Summary

This phase replaces `AsyncSqliteSaver` (from `langgraph-checkpoint-sqlite`) with `AsyncPostgresSaver` (from `langgraph-checkpoint-postgres`) across two process boundaries: the FastAPI server (`app/api/main.py`) and the arq worker (`app/jobs/worker.py`). A PostgreSQL service is added to `docker-compose.yml`.

The migration scope is well-defined. The checkpointer is injected into both processes via `async with AsyncSqliteSaver.from_conn_string(...)`. The replacement `AsyncPostgresSaver` offers the same `from_conn_string` async context manager factory, so the call-site shape is nearly identical. The critical differences are: (1) `setup()` must be called once after construction to create the tables, (2) `psycopg` (v3) is required — not `psycopg2`, and (3) the connection string format is `postgresql://` not a file path.

There is also a direct-SQL bypass in `app/api/routes/chat.py` that uses `aiosqlite` to query the checkpointer's `checkpoints` table for thread listing and deletion. This must be rewritten to use `asyncpg` or `psycopg` queries against PostgreSQL. This is the most non-trivial part of the migration.

**Primary recommendation:** Use `AsyncPostgresSaver.from_conn_string()` inside the FastAPI lifespan and call `await checkpointer.setup()` once at startup. In the arq worker, open a fresh connection per job (identical pattern to the current SQLite approach). Add `postgres:17-alpine` to Docker Compose with a healthcheck, and inject `DATABASE_URL` as an environment variable to both the `api` and `worker` services.

---

## Runtime State Inventory

> This phase involves migration of stored data — SQLite checkpoints to PostgreSQL.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `data/chat.db` — 96 checkpoints, 96 writes, 7 distinct threads (487 KB) | The existing SQLite data is development/test data. No production migration script required. On first run against PostgreSQL, `setup()` creates fresh tables; SQLite file is abandoned. Document explicitly: historical threads are lost unless manually migrated. |
| Live service config | Docker Compose currently has no postgres service | Add `postgres:17-alpine` service to `docker-compose.yml` |
| OS-registered state | None — app runs via `uvicorn` and `arq`, no OS-level registration | None |
| Secrets/env vars | No `DATABASE_URL` env var exists anywhere in the codebase | Add `DATABASE_URL` to `docker-compose.yml` environment sections and document `.env` usage for local dev |
| Build artifacts | `data/chat.db` will become a stale artifact after migration | Add `data/*.db` to `.gitignore` (already ignored per `260401-f4x` quick task) and document that `data/` directory is no longer used by the checkpointer |

**Historical data decision:** The 7 SQLite threads are development test data, not production user data. The phase should document this and proceed without a data migration script. If future need arises, a one-time migration script can be added.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph-checkpoint-postgres` | 3.0.5 | `AsyncPostgresSaver` — drop-in checkpointer for PostgreSQL | The official LangGraph PostgreSQL checkpointer. Same `BaseCheckpointSaver` interface as `AsyncSqliteSaver`. Verified on PyPI 2026-04-01. |
| `psycopg[binary]` | 3.2.3 | PostgreSQL async driver (psycopg 3) | `langgraph-checkpoint-postgres` requires `psycopg>=3.2.0`. The `[binary]` extra ships a pre-compiled `.so` — avoids needing `libpq-dev` in the container. `psycopg2` is a different package and will not work. |
| `psycopg-pool` | 3.2.8 | `AsyncConnectionPool` for production | Required by `langgraph-checkpoint-postgres` (`psycopg-pool>=3.2.0`). Provides reusable async connection pool shared across requests. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `postgres:17-alpine` (Docker image) | 17 | PostgreSQL server | Added as Docker Compose service. `17-alpine` is the current stable release with smallest footprint. `16-alpine` already pulled locally but 17 is current. |

### Packages to Remove

| Package | Currently Used | Replacement |
|---------|---------------|-------------|
| `langgraph-checkpoint-sqlite` | `AsyncSqliteSaver` | `langgraph-checkpoint-postgres` + `AsyncPostgresSaver` |
| `aiosqlite` | Direct SQL in `chat.py` thread routes | `psycopg` async cursor queries against PostgreSQL |

**Installation:**
```bash
uv add "langgraph-checkpoint-postgres>=3.0.5" "psycopg[binary]>=3.2.0" "psycopg-pool>=3.2.0"
uv remove langgraph-checkpoint-sqlite aiosqlite
```

**Version verification (confirmed 2026-04-01 via PyPI):**
- `langgraph-checkpoint-postgres`: latest = 3.0.5
- `psycopg`: latest = 3.3.3 (use 3.2.x for stability; package requires >=3.2.0)
- `psycopg-pool`: latest = 3.3.0 (use 3.2.x; package requires >=3.2.0)

---

## Architecture Patterns

### Connection String Format

PostgreSQL DSN format used throughout:
```
postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable
```

For Docker Compose inter-container networking (service name `postgres`):
```
postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable
```

Environment variable name: `DATABASE_URL` (conventional).

### Pattern 1: FastAPI Lifespan — `from_conn_string` with setup()

The `from_conn_string` async context manager opens a single connection. Call `await checkpointer.setup()` immediately after construction. This is idempotent — safe to call on every startup (checks `checkpoint_migrations` table and skips already-applied migrations).

```python
# Source: langgraph-checkpoint-postgres 3.0.5 aio.py + termtrix Medium article
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

@asynccontextmanager
async def lifespan(app: FastAPI):
    DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")

    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        await checkpointer.setup()          # MUST be called; idempotent
        app.state.graph = build_graph(llm, checkpointer)
        app.state.checkpointer = checkpointer
        app.state.db_uri = DB_URI
        # ... other state
        yield
    # Connection closed automatically by context manager exit
```

**Why `from_conn_string` over `AsyncConnectionPool` for this project:**
- Single-user personal tool — no concurrent request pressure
- `from_conn_string` is simpler and directly matches the existing SQLite pattern
- `AsyncConnectionPool` is the right choice for multi-user production workloads; documented as alternative below

### Pattern 2: arq Worker — Fresh Connection Per Job

The worker currently opens `AsyncSqliteSaver.from_conn_string(DB_PATH)` inside `process_chat`. This pattern maps directly to `AsyncPostgresSaver.from_conn_string(DB_URI)`.

```python
# Source: analogous to current worker.py pattern + package docs
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")

async def process_chat(ctx, *, job_id, thread_id, prompt, model, github_token, reply_to):
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        # setup() NOT needed here — FastAPI startup already ran it
        graph = build_graph(llm, checkpointer)
        # ... invoke
```

**Note:** `setup()` does not need to be called inside `process_chat`. The tables are created once by the FastAPI lifespan. Worker only needs read/write access.

### Pattern 3: Direct SQL Thread Routes — Rewrite Using psycopg

`app/api/routes/chat.py` currently uses `aiosqlite` for two raw-SQL operations:

**`GET /api/threads`** (list all threads):
```python
# Source: psycopg 3 async docs + equivalent of current aiosqlite query
import psycopg
from psycopg.rows import dict_row

async def list_threads(request: Request):
    db_uri = request.app.state.db_uri
    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT thread_id, MAX(checkpoint_id) as latest
                   FROM checkpoints
                   WHERE checkpoint_ns = ''
                   GROUP BY thread_id
                   ORDER BY latest DESC
                   LIMIT 50"""
            )
            rows = await cur.fetchall()
    # rows are dicts with 'thread_id' and 'latest' keys
```

**`DELETE /api/threads/{thread_id}`** (delete thread):
```python
# PostgreSQL schema uses checkpoint_blobs + checkpoint_writes (not just checkpoints)
async with await psycopg.AsyncConnection.connect(db_uri, autocommit=True, row_factory=dict_row) as conn:
    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
        await cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
        await cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
```

Note the schema difference: SQLite uses `checkpoint_blobs` (same name), but the current `delete_thread` route already deletes from `checkpoint_blobs` and `checkpoint_writes` so this is compatible. However the SQLite `checkpoints` table has a `checkpoint` column (BLOB), while PostgreSQL uses JSONB — this does not affect the DELETE query.

**Alternative using LangGraph's built-in:**

`AsyncPostgresSaver` exposes `await checkpointer.adelete_thread(thread_id)` (verified in source). This eliminates all raw SQL for deletion. For listing threads, there is no built-in "list all threads" API — the raw SQL approach remains necessary.

### Pattern 4: Docker Compose PostgreSQL Service

```yaml
# Source: docker-compose best practices + postgres:17-alpine docs
services:
  postgres:
    image: postgres:17-alpine
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_USER=postgres
      - POSTGRES_DB=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    # ... existing config
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  worker:
    # ... existing config
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

volumes:
  redis-data:
  postgres-data:
```

**Critical:** Use `condition: service_healthy` on postgres to prevent `api` and `worker` from starting before PostgreSQL is ready to accept connections. Without this, `setup()` will fail with a connection refused error.

### Anti-Patterns to Avoid

- **Calling `setup()` inside `process_chat` per job:** Unnecessary round-trip for every job. Call once at `api` lifespan startup.
- **Using `psycopg2` instead of `psycopg`:** `langgraph-checkpoint-postgres` requires `psycopg` (v3). Completely different package. `psycopg2` will not satisfy the dependency.
- **Missing `autocommit=True` on raw connections passed to `AsyncPostgresSaver`:** Only applies when manually constructing `AsyncConnection` and passing to `AsyncPostgresSaver(conn)`. `from_conn_string()` handles this internally. For the raw SQL in `chat.py`, explicit `autocommit` may be needed for DELETE operations.
- **Missing `row_factory=dict_row` on raw connections:** `AsyncPostgresSaver` uses `dict_row` internally. Raw `psycopg` cursor queries also need `dict_row` to access columns by name.
- **Not waiting for postgres healthcheck:** `api` and `worker` will crash on startup if postgres is still initializing. Use `depends_on: condition: service_healthy`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table creation/migrations | Custom SQL migration scripts | `await checkpointer.setup()` | Built-in idempotent migration runner with 10 versioned migrations |
| Thread deletion | Custom DELETE SQL for every table | `await checkpointer.adelete_thread(thread_id)` | Handles all related tables atomically |
| Connection management | Manual `psycopg.AsyncConnection.connect` for checkpointer | `AsyncPostgresSaver.from_conn_string()` | Configures `autocommit=True`, `row_factory=dict_row`, and cleanup automatically |
| Postgres healthcheck | Custom wait loop in Python | Docker Compose `healthcheck` + `condition: service_healthy` | Native Docker orchestration, no app-level retry logic needed |

**Key insight:** The only raw SQL that must remain is `GET /api/threads` (list all threads by latest activity) — LangGraph has no "list all threads" API. The DELETE route can be replaced with `adelete_thread()`.

---

## Common Pitfalls

### Pitfall 1: Forgetting `setup()` Call

**What goes wrong:** `ProgrammingError: relation "checkpoints" does not exist` on first ainvoke.
**Why it happens:** Unlike SQLite (which creates tables implicitly via aiosqlite), PostgreSQL requires explicit table creation. `setup()` runs the 10 versioned migrations.
**How to avoid:** Call `await checkpointer.setup()` immediately after `from_conn_string()` in the FastAPI lifespan. It is idempotent.
**Warning signs:** `ProgrammingError` containing "relation ... does not exist" on startup.

### Pitfall 2: `AsyncConnectionPool` + `pipeline=True` Incompatibility

**What goes wrong:** `ValueError: Pipeline should be used only with a single AsyncConnection, not AsyncConnectionPool.`
**Why it happens:** `from_conn_string(pipeline=True)` cannot be used when the underlying connection is an `AsyncConnectionPool`.
**How to avoid:** For this project's single-user use case, use `from_conn_string()` without `pipeline=True`. Do not pass `pipeline=True`.
**Warning signs:** ValueError at startup before any requests are served.

### Pitfall 3: Worker `setup()` Race Condition

**What goes wrong:** If worker starts before `api` (both start simultaneously in Docker Compose), and worker tries to write a checkpoint before `api` has run `setup()`, it will fail.
**Why it happens:** Worker does not call `setup()`, so if tables don't exist yet, writes fail.
**How to avoid:** Both `api` and `worker` services in Docker Compose should depend on postgres with `condition: service_healthy`. The `api` lifespan calls `setup()` on startup. If both start at the same time, the worker might get a job before the API has run setup — but in practice the arq worker starts idle and only processes jobs enqueued after the API is live. Low risk for this single-user setup, but calling `setup()` in the worker's `startup()` hook too (idempotent, safe) eliminates the race.
**Warning signs:** `ProgrammingError` in worker logs on first job.

### Pitfall 4: Schema Difference — SQLite `writes` vs PostgreSQL `checkpoint_writes`

**What goes wrong:** The current `delete_thread` route deletes from `checkpoint_writes` — this name matches the PostgreSQL schema. But the list query only touches `checkpoints` — also matches. No schema name collision.
**Why it happens:** The SQLite schema (`langgraph-checkpoint-sqlite`) uses `checkpoints` + `writes` (no prefix). The PostgreSQL schema uses `checkpoints` + `checkpoint_blobs` + `checkpoint_writes`. The current delete route already references `checkpoint_blobs` and `checkpoint_writes` which matches the PostgreSQL schema.
**How to avoid:** Use `adelete_thread()` instead of raw SQL for deletion to avoid all schema-name concerns. For list query, only `checkpoints` table is accessed — identical in both schemas.
**Warning signs:** `UndefinedTable` error for `writes` (the bare name used nowhere in current code).

### Pitfall 5: `aiosqlite` Import Remains After Migration

**What goes wrong:** `ImportError: No module named 'aiosqlite'` if `aiosqlite` is removed from dependencies before all `import aiosqlite` and `aiosqlite.connect()` calls are removed from `chat.py`.
**Why it happens:** `chat.py` imports `aiosqlite` directly.
**How to avoid:** Remove `aiosqlite` imports from `chat.py` as part of the same plan that rewrites the thread queries. Remove `aiosqlite` from `pyproject.toml` dependencies after all import sites are cleaned.

### Pitfall 6: `db_path` → `db_uri` State Field Rename

**What goes wrong:** `chat.py` reads `request.app.state.db_path` to get the SQLite path. After migration, this must become `request.app.state.db_uri` (or similar).
**Why it happens:** The lifespan currently sets `app.state.db_path = DB_PATH`. Tests in `conftest.py` set `app.state.db_path = ":memory:"`.
**How to avoid:** Rename the state field to `db_uri` (or `db_dsn`) in both `main.py` and all tests. Update `conftest.py` to set `app.state.db_uri = "..."` (tests mock the graph, so this field is only accessed in the thread-listing routes which are tested separately).

---

## Code Examples

### Minimal AsyncPostgresSaver Lifecycle (FastAPI)

```python
# Source: langgraph-checkpoint-postgres 3.0.5 aio.py + official docs
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("./data").mkdir(exist_ok=True)
    auth_manager = CopilotAuthManager()
    llm = ChatCopilot(auth_manager=auth_manager)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = Redis.from_url(redis_url)
    arq_redis = await create_pool(RedisSettings.from_dsn(redis_url))
    job_store = JobStore(redis_client)

    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        await checkpointer.setup()   # idempotent; creates tables if not exist
        app.state.graph = build_graph(llm, checkpointer)
        app.state.checkpointer = checkpointer
        app.state.auth_manager = auth_manager
        app.state.llm = llm
        app.state.db_uri = DB_URI    # renamed from db_path
        app.state.device_flows = {}
        app.state.redis = redis_client
        app.state.arq_redis = arq_redis
        app.state.job_store = job_store
        yield

    await llm.close()
    await redis_client.aclose()
    await arq_redis.aclose()
```

### Worker Process_Chat Pattern

```python
# Source: current worker.py + AsyncPostgresSaver from_conn_string pattern
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")

async def process_chat(ctx, *, job_id, thread_id, prompt, model, github_token, reply_to):
    job_store: JobStore = ctx["job_store"]
    notifier = build_notifier(reply_to, job_store)
    llm = ChatCopilot(github_token=github_token, model=model)

    try:
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            graph = build_graph(llm, checkpointer)
            config = {"configurable": {"thread_id": thread_id}}
            await notifier.progress("thinking")
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=prompt)]},
                config=config,
            )
            final_text = result["messages"][-1].content
            await job_store.save_result(job_id, final_text)
            await notifier.done()
    except Exception as e:
        await job_store.save_result(job_id, f"Error: {e}")
        await notifier.done()
    finally:
        await llm.close()

    return {"job_id": job_id, "status": "done"}
```

### Thread Listing with psycopg (replaces aiosqlite)

```python
# Source: psycopg 3 async docs — replaces current aiosqlite pattern
import psycopg
from psycopg.rows import dict_row

async def list_threads(request: Request):
    db_uri = request.app.state.db_uri
    threads: list[ThreadInfo] = []
    try:
        async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT thread_id, MAX(checkpoint_id) as latest
                       FROM checkpoints
                       WHERE checkpoint_ns = ''
                       GROUP BY thread_id
                       ORDER BY latest DESC
                       LIMIT 50"""
                )
                rows = await cur.fetchall()
        for row in rows:
            thread_id = row["thread_id"]
            latest = row["latest"]
            threads.append(ThreadInfo(
                thread_id=thread_id,
                updated_at=str(latest),
                label=f"Chat {thread_id[:8]}",
            ))
    except Exception:
        pass
    return threads
```

### Thread Deletion Using `adelete_thread`

```python
# Source: AsyncPostgresSaver.adelete_thread — verified in 3.0.5 aio.py source
@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(thread_id: str, request: Request):
    checkpointer = request.app.state.checkpointer
    try:
        await checkpointer.adelete_thread(thread_id)
    except Exception:
        pass  # Silently succeed if thread doesn't exist
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_worker.py tests/test_api_chat.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PGCK-01 | `AsyncPostgresSaver.from_conn_string` used in main.py lifespan | unit (mock) | `uv run pytest tests/test_api_chat.py -x` | ✅ (update mocks) |
| PGCK-02 | `AsyncPostgresSaver.from_conn_string` used in worker process_chat | unit (mock) | `uv run pytest tests/test_worker.py -x` | ✅ (update patches) |
| PGCK-03 | `GET /api/threads` returns correct list via psycopg query | unit (mock) | `uv run pytest tests/test_api_chat.py::test_list_threads -x` | ✅ |
| PGCK-04 | `DELETE /api/threads/{id}` calls `adelete_thread` | unit (mock) | `uv run pytest tests/test_api_chat.py::test_delete_thread -x` | ✅ |
| PGCK-05 | `docker-compose.yml` includes postgres service with healthcheck | manual | — | ❌ manual verify |
| PGCK-06 | `pyproject.toml` has correct new/removed dependencies | manual | `grep langgraph-checkpoint-postgres pyproject.toml` | ❌ manual verify |

### Key Test Update: `test_worker.py` Patch Targets

The three tests in `test_worker.py` currently patch `app.jobs.worker.AsyncSqliteSaver.from_conn_string`. After migration they must patch `app.jobs.worker.AsyncPostgresSaver.from_conn_string`.

### Key Test Update: `conftest.py`

`app.state.db_path` (set to `":memory:"`) must be renamed to `app.state.db_uri` in `conftest.py` and the `api_client` fixture.

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. Tests need updates (patches + state field names) but no new test files.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Docker Compose postgres service | ✓ | 29.3.1 | — |
| Docker Compose | Multi-service orchestration | ✓ | v5.1.1 | — |
| `postgres:17-alpine` | PostgreSQL server | ✓ (pulled) | 17 | `postgres:16-alpine` already present |
| `langgraph-checkpoint-postgres` | Checkpointer | Not installed (in venv) | 3.0.5 on PyPI | — |
| `psycopg[binary]` | PostgreSQL driver | Not installed | 3.2.3+ | `psycopg` without binary extra (requires libpq-dev in container) |
| `psycopg-pool` | Connection pool | Not installed | 3.2.8+ | — |
| `aiosqlite` | Currently used | Installed | — | Remove after migration |
| `langgraph-checkpoint-sqlite` | Currently used | Installed | — | Remove after migration |

**Missing dependencies with no fallback:** All three PostgreSQL packages (`langgraph-checkpoint-postgres`, `psycopg[binary]`, `psycopg-pool`) must be added via `uv add`. No blocking issues — all are available on PyPI.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `PostgresSaver` (sync) | `AsyncPostgresSaver` (async) | langgraph-checkpoint-postgres 2.x | Must use async variant — this project is fully async |
| `AsyncShallowPostgresSaver` | Deprecated in 2.0.20, removed in 3.0.0 | langgraph-checkpoint-postgres 3.0.0 | Do not use — `AsyncPostgresSaver` is the correct class |
| `psycopg2` | `psycopg` (v3) | Industry shift 2023-2024 | Different package name: `psycopg`, not `psycopg2`. v3 has native async support. |

**Deprecated/outdated:**
- `AsyncShallowPostgresSaver`: deprecated 2.0.20, removed 3.0.0. Any guide showing this class is outdated.
- `from_conn_string` with `pipeline=True` + `AsyncConnectionPool`: raises `ValueError` — documented in 3.0.5 source.

---

## Open Questions

1. **Should `setup()` also be called in the worker startup hook?**
   - What we know: `setup()` is idempotent. If `api` always starts before any worker job runs, tables are guaranteed to exist.
   - What's unclear: Docker Compose does not guarantee `api` finishes its lifespan before `worker` accepts a job from an existing Redis queue.
   - Recommendation: Call `await checkpointer.setup()` once inside the worker's `startup(ctx)` hook as a safety measure. Cost is one extra DB round-trip at worker startup, benefit is no race condition.

2. **Historical SQLite thread data — migrate or abandon?**
   - What we know: 7 threads, 96 checkpoints, development test data.
   - What's unclear: Whether any have sentimental/reference value to the user.
   - Recommendation: Abandon. Document clearly in the plan that existing threads will not be accessible after migration. A one-off migration script is out of scope for this phase.

3. **`psycopg[binary]` vs `psycopg` (pure Python) in Docker container**
   - What we know: The Docker image is `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`. `psycopg[binary]` ships its own libpq — no system dependency. `psycopg` without `[binary]` requires `libpq-dev` installed via `apt-get` in the container.
   - Recommendation: Use `psycopg[binary]` — works in the slim image without apt-get changes.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 6 |
|-----------|------------------|
| Python 3.12 runtime | `psycopg[binary]` has a `cp312` wheel available (verified) |
| `langchain-core` only (no full `langchain`) | No change — checkpointer swap doesn't affect LangChain imports |
| `pyproject.toml` PEP 621 | Use `uv add` / `uv remove` to manage dependencies |
| `uv` for dependency management | Run `uv add` and `uv remove` |
| `langgraph>=1.1.4` | `langgraph-checkpoint-postgres 3.0.5` requires `langgraph-checkpoint>=2.1.2` which is a transitive dep of `langgraph` — no conflict |
| `AsyncSqliteSaver` currently used | Replace with `AsyncPostgresSaver` — same `BaseCheckpointSaver` interface |
| Vanilla JS frontend | No frontend changes needed — this is a backend-only migration |
| GSD Workflow Enforcement | Use `/gsd:execute-phase` for all file changes |

---

## Sources

### Primary (HIGH confidence)
- `langgraph-checkpoint-postgres` 3.0.5 wheel source (inspected directly via pip download) — `aio.py`, `base.py`, `shallow.py`, `_ainternal.py`, `METADATA`
- PyPI registry (2026-04-01) — versions: langgraph-checkpoint-postgres 3.0.5, psycopg 3.3.3, psycopg-pool 3.3.0

### Secondary (MEDIUM confidence)
- https://docs.langchain.com/oss/python/langgraph/add-memory — official LangGraph docs (AsyncPostgresSaver lifecycle pattern)
- https://medium.com/@termtrix/i-built-a-langgraph-fastapi-agent-and-spent-days-fighting-postgres-8913f84c296d — pitfall documentation (lifespan ownership pattern, setup() requirement)
- https://www.psycopg.org/psycopg3/docs/advanced/pool.html — psycopg 3 connection pool docs

### Tertiary (LOW confidence)
- https://forum.langchain.com/t/langgraph-production-connection-pooling-inquiry/1730 — community connection pool patterns (not directly verified against official docs)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via pip download and PyPI registry
- Architecture: HIGH — verified by reading 3.0.5 source + official docs
- Pitfalls: HIGH — sourced from package source code + issue trackers + official METADATA warnings
- Schema comparison: HIGH — read both SQLite schema (via sqlite3 inspection of live DB) and PostgreSQL schema (from base.py MIGRATIONS)

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable libraries; langgraph-checkpoint-postgres has minor releases frequently)
