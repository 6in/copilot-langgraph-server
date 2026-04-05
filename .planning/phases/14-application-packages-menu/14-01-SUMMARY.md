---
phase: 14-application-packages-menu
plan: 01
subsystem: api
tags: [fastapi, python-frontmatter, app-registry, jwt, app-packages, orchestrator]

requires:
  - phase: 11-rpccontext-integration
    provides: RPCContext, OrchestratorHandler with app_id field
  - phase: 09-superchat
    provides: SubAgentRegistry, OrchestratorHandler base pattern

provides:
  - AppDefinition dataclass and AppRegistry class (app/orchestrator/apps.py)
  - GET /api/apps endpoint returning app definitions from APP.md files
  - apps/chat/APP.md and apps/superchat/APP.md package definition files
  - app_id field in ChatRequest model (Pydantic)
  - app_id propagation through enqueue_job -> OrchestratorHandler -> RPCContext
  - Dynamic seeding of applications table from APP.md files at startup
  - agents list resolved from APP.md in OrchestratorHandler (D-08 REVISED)

affects:
  - 14-02-frontend-menu (consumes GET /api/apps)
  - 14-03-agent-scoping (consumes app_id in job payload)

tech-stack:
  added: []
  patterns:
    - "APP.md frontmatter scan pattern: Path(apps_dir).glob('*/APP.md') + frontmatter.load()"
    - "Metadata-only registry at startup: no ChatCopilot instantiation, no github_token needed"
    - "app_id preference chain: explicit body.app_id > mode-derived fallback (backward compat)"

key-files:
  created:
    - app/orchestrator/apps.py
    - app/api/routes/apps.py
    - apps/chat/APP.md
    - apps/superchat/APP.md
    - tests/test_app_registry.py
    - tests/test_apps_route.py
  modified:
    - app/api/models.py
    - app/api/main.py
    - app/api/routes/chat.py
    - app/jobs/handlers/orchestrator_handler.py
    - docker-compose.yml

key-decisions:
  - "AppRegistry is metadata-only at startup: no ChatCopilot or token needed (D-07/D-08 REVISED)"
  - "app_id preference: body.app_id takes priority over mode-derived mapping for Pitfall 2 fix"
  - "OrchestratorHandler reads APP.md directly from filesystem (APP_DIR env) when no UI chip override"
  - "Dynamic applications table seeding from APP.md at startup handles Pitfall 3 (FK constraint)"
  - "apps/ volume mount not added separately — root .:/app mount already covers it"

patterns-established:
  - "APP.md scan: sorted(Path(apps_dir).glob('*/APP.md')) — alphabetical, single-level only"
  - "Malformed APP.md: log warning + skip, never crash startup or request handler (T-14-05)"
  - "Agent folder warning: startup check only, informational, does not block app registration"

requirements-completed: [APP-01, APP-02, APP-03, APP-04]

duration: 65min
completed: 2026-04-05
---

# Phase 14 Plan 01: Application Packages Backend Summary

**AppRegistry module scanning apps/*/APP.md frontmatter, GET /api/apps endpoint (JWT-protected), app_id plumbing through ChatRequest to OrchestratorHandler with dynamic agents resolution from APP.md**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-04-05T00:00:00Z
- **Completed:** 2026-04-05T02:05:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- `AppRegistry` class scans `apps/*/APP.md`, parses YAML frontmatter, returns `AppDefinition` objects — malformed files logged and skipped (T-14-05)
- `GET /api/apps` endpoint returns `{slug, name, description, icon, agents[]}` per app (APP-02 backend); JWT-protected (T-14-01)
- `app_id` field added to `ChatRequest`; propagated through `enqueue_job` kwargs and used in `OrchestratorHandler` instead of hardcoded `"superchat"` (APP-03, D-08 REVISED)
- `applications` table dynamically seeded from APP.md files at startup — fixes FK constraint for new app slugs (Pitfall 3)
- `apps/chat/APP.md` and `apps/superchat/APP.md` created with `agents:` lists; `general-assistant` appears in both (APP-04 shared agent verified)

## Task Commits

1. **Task 1: APP.md files + AppRegistry module + tests** - `d610a41` (feat)
2. **Task 2: GET /api/apps route + chat.py app_id + OrchestratorHandler update + lifespan seeding** - `55a1594` (feat)

_TDD: both tasks followed RED (test created, fails) → GREEN (implementation) → commit pattern._

## Files Created/Modified

- `app/orchestrator/apps.py` — AppDefinition dataclass + AppRegistry class (metadata-only scan)
- `app/api/routes/apps.py` — GET /api/apps endpoint, JWT-protected, reads APP_DIR env var
- `apps/chat/APP.md` — Chat app package definition (general-assistant agent)
- `apps/superchat/APP.md` — SuperChat app package definition (3 agents including shared general-assistant)
- `app/api/models.py` — Added AppInfo model; added `app_id: str | None` to ChatRequest
- `app/api/main.py` — Import + register apps router; dynamic APP.md seeding of applications table
- `app/api/routes/chat.py` — app_id preference chain (body.app_id > mode fallback); pass app_id to enqueue_job
- `app/jobs/handlers/orchestrator_handler.py` — Read app_id from job; resolve agents from APP.md when no UI chips; use app_id in RPCContext
- `docker-compose.yml` — APP_DIR=/app/apps env var for api and worker services
- `tests/test_app_registry.py` — 6 unit tests for AppRegistry (TDD, all green)
- `tests/test_apps_route.py` — 5 integration tests for GET /api/apps + app_id (TDD, all green)

## Decisions Made

- **AppRegistry metadata-only at startup:** GitHub Copilot token is per-user (Device Flow), not available at startup. AppRegistry reads only frontmatter — no ChatCopilot instantiation, no token needed (D-07/D-08 REVISED).
- **app_id preference chain:** `body.app_id` takes priority; falls back to mode-derived mapping (`"superchat"` / `"chat"`) for backward compatibility with existing frontend clients.
- **OrchestratorHandler APP.md read:** Worker reads `APP_DIR/app_id/APP.md` directly from filesystem — avoids Pitfall 1 (worker cannot access app.state). Conditional: only when no UI chip override (`agents_filter` is None).
- **Dynamic applications seeding:** Startup scans APP_DIR and upserts slugs into `applications` table. Keeps hardcoded seed for `chat`/`superchat` as backward-compat baseline.
- **Volume mount coverage:** `apps/` directory is under root `.:/app` mount in docker-compose — no separate volume entry needed.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `uv run pytest` failed due to missing `.venv` (permission issue in worktree). Used `python -m pytest` with system Python 3.12 instead — functionally equivalent.
- `arq`, `psycopg[binary]`, `langgraph-checkpoint-postgres` not installed in system Python — installed via `pip install` for test execution. These are already declared in `pyproject.toml` and present in Docker environment.

## Known Stubs

None — all APP.md files have valid data, AppRegistry returns real AppDefinition objects, GET /api/apps returns live data from filesystem scan.

## Threat Flags

None — all threats in plan's threat model were addressed:
- T-14-01: JWT required on GET /api/apps via `Depends(get_jwt_payload)`
- T-14-05: Malformed APP.md try/except in AppRegistry._scan() and GET /api/apps handler

## User Setup Required

None — no external service configuration required. `APP_DIR` env var defaults to `./apps` (present in repo).

## Next Phase Readiness

- **Plan 02 (frontend menu):** `GET /api/apps` returns `{slug, name, description, icon, agents[]}` — ready for React `MenuScreen` consumption
- **Plan 03 (agent scoping):** `app_id` in job payload and `OrchestratorHandler` APP.md read are wired — agent filtering by app slug is live
- All 11 tests pass (6 unit + 5 integration); existing test suite regression count unchanged

---
*Phase: 14-application-packages-menu*
*Completed: 2026-04-05*
