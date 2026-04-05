# Phase 14: Application Packages + Menu — Research

**Researched:** 2026-04-05
**Domain:** Python app registry + FastAPI route + React dynamic menu with app-scoped multi-agent graphs
**Confidence:** HIGH

## Summary

Phase 14 wires together four distinct subsystems: a file-based `AppRegistry` that scans `apps/*/APP.md` using
`python-frontmatter` (already in the project), a new `GET /api/apps` FastAPI route analogous to `GET /api/agents`,
per-app compiled `OrchestratorGraph` instances stored in a dict at startup, and a dynamic React `MenuScreen` that
fetches the app list and routes the user into an app-scoped `SuperChatApp`.

All four building blocks already have direct precedents in the codebase. `SubAgentRegistry` is the exact loader
pattern to replicate for `AppRegistry`. `app/api/routes/agents.py` is the exact route pattern for `GET /api/apps`.
`build_orchestrator_graph()` is already callable with any `SubAgentRegistry` — calling it N times (once per app) is
all that changes in startup. `MenuScreen.tsx` and `App.tsx` already carry the state-machine structure that needs
extending with `activeApp`.

The highest-risk area is the startup path in `app/api/main.py`. Today it builds a single graph via `build_graph()`
(the simple LangGraph graph). For orchestrator mode, graphs are built per-job inside `OrchestratorHandler`. Phase 14
requires moving to per-app compiled graphs in a dict on `app.state`, which is a new startup-time architecture.
`OrchestratorHandler` must look up the right graph instead of building one per job.

**Primary recommendation:** Implement in four sequential waves: (W0) test scaffolding, (W1) backend AppRegistry +
`GET /api/apps` route, (W2) startup integration with per-app graph dict + OrchestratorHandler lookup, (W3) frontend
dynamic MenuScreen + `activeApp` state + SuperChatApp props.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** App definition files: `apps/<slug>/APP.md`, YAML frontmatter + markdown body.
  Fields: `name`, `description`, `icon`, `agents` (list of agent folder names).
- **D-02:** Example YAML structure defined in CONTEXT.md.
- **D-03:** `agents:` entries refer to folder names under `agents/`. Shared agents appear in multiple
  APP.md files — no duplication of the agent definition.
- **D-04:** Existing hardcoded "Chat" and "SuperChat" cards removed. `MenuScreen` becomes fully dynamic,
  fetching from `GET /api/apps`.
- **D-05:** Chat and SuperChat become regular apps: `apps/chat/APP.md`, `apps/superchat/APP.md`. No legacy
  hardcoded cards.
- **D-06:** `GET /api/apps` returns `{slug, name, description, icon, agents[]}`.
- **D-07:** At startup, `AppRegistry` loads all APP.md files. For each app it builds a filtered
  `SubAgentRegistry` (only that app's declared agents) and compiles a dedicated `OrchestratorGraph`.
  Graphs stored by app slug in `app_graphs: dict[str, CompiledGraph]`.
- **D-08:** Per-request routing: look up `app_graphs[app_slug]`, invoke that graph. RouterNode sees only
  that app's agents — no runtime filtering inside RouterNode.
- **D-09:** Single-registry global graph replaced by per-app graph lookup. Unknown app slug → 404.
- **D-10:** `SuperChatApp.tsx` reused. Two new props: `appId` (slug) and `appName` (display).
- **D-11:** `App.tsx` adds `activeApp: AppDefinition | null`. Selecting a card sets `activeApp` and
  transitions to `'superchat'` screen.
- **D-12:** Header or chat area shows active application name (satisfies success criterion #2).

### Claude's Discretion

- Exact `AppRegistry` Python class structure and module location (suggested: `app/orchestrator/apps.py`)
- How to handle APP.md referencing a non-existent agent (warning log vs error)
- API response caching strategy for `GET /api/apps`
- Icon rendering in menu cards (emoji or SVG)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. The following are out of scope for Phase 14:
- User info in chat context
- Gem and Canvas feature
- Agent-Skills integration mechanism
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| APP-01 | Developer declares agent subset in app definition file; 50-agent packaging | AppRegistry.load_all() + filtered SubAgentRegistry per app |
| APP-02 | User selects app from menu screen; app-scoped chat UI launches | Dynamic MenuScreen + App.tsx activeApp state + SuperChatApp props |
| APP-03 | RouterNode sees only app-assigned agents as candidates | Per-app compiled graph at startup (D-07/D-08); SubAgentRegistry filtered before graph compile |
| APP-04 | One agent folder shared across multiple apps without duplication | AppRegistry references agent folder names; SubAgentRegistry loaded per app from shared agents/ dir |
</phase_requirements>

---

## Standard Stack

### Core (all already in pyproject.toml)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-frontmatter` | installed | Parse APP.md YAML frontmatter | Already used for AGENT.md parsing in `SubAgent.from_dir()`; same import `import frontmatter` |
| `fastapi` | 0.135.2 | `GET /api/apps` route | Existing pattern in `agents.py` |
| `pydantic` v2 | bundled with FastAPI | `AppInfo` response model | `AgentInfo` model is the direct template |
| React 19 + TypeScript | 19.2 / 5.9 | Dynamic MenuScreen | Already the project's frontend stack |

[VERIFIED: codebase grep — `python-frontmatter` is used in `app/orchestrator/agent.py` line 2; `import frontmatter`]

### No New Dependencies

This phase adds **zero new packages**. Every required capability is already installed:
- File-system glob: `pathlib.Path.glob()` — used in `SubAgentRegistry.__init__`
- YAML frontmatter: `python-frontmatter` — used in `SubAgent.from_dir()`
- FastAPI router: pattern from `app/api/routes/agents.py`
- React fetch + state: pattern from `useAgents` hook (existing)

[VERIFIED: codebase scan]

---

## Architecture Patterns

### Recommended Module Locations

```
app/
  orchestrator/
    apps.py           — AppRegistry (new, mirrors agent.py structure)
    agent.py          — SubAgentRegistry (existing, unchanged)
    graph.py          — build_orchestrator_graph() (existing, unchanged)
  api/
    routes/
      apps.py         — GET /api/apps route (new, mirrors agents.py)
    main.py           — updated lifespan: build app_graphs dict
  jobs/
    handlers/
      orchestrator_handler.py — updated: lookup graph from app_graphs
apps/
  chat/APP.md         — new app definition for Chat
  superchat/APP.md    — new app definition for SuperChat
frontend/src/
  types.ts            — add AppDefinition interface
  components/
    MenuScreen.tsx    — fetch + render dynamic cards
    SuperChatApp.tsx  — add appId/appName props
    Header.tsx        — add appName? optional prop
  App.tsx             — add activeApp state
```

### Pattern 1: AppRegistry (mirrors SubAgentRegistry)

**What:** Scans `apps/*/APP.md`, parses frontmatter, builds one `SubAgentRegistry` + one compiled graph per app.
**When to use:** Once at startup in `lifespan`.

```python
# Source: app/orchestrator/agent.py lines 124-184 (SubAgentRegistry pattern)
# Adapt for AppRegistry in app/orchestrator/apps.py

import frontmatter
import logging
from dataclasses import dataclass
from pathlib import Path
from app.orchestrator.agent import SubAgentRegistry
from app.orchestrator.graph import build_orchestrator_graph

logger = logging.getLogger(__name__)

@dataclass
class AppDefinition:
    slug: str
    name: str
    description: str
    icon: str
    agents: list[str]  # agent folder names

class AppRegistry:
    def __init__(self, apps_dir: str, agents_dir: str, github_token: str, checkpointer=None):
        self.apps: dict[str, AppDefinition] = {}
        self.graphs: dict[str, Any] = {}  # slug -> compiled OrchestratorGraph

        for path in Path(apps_dir).glob("*/APP.md"):
            slug = path.parent.name
            try:
                post = frontmatter.load(path)
                meta = post.metadata
                app_def = AppDefinition(
                    slug=slug,
                    name=meta["name"],
                    description=meta.get("description", ""),
                    icon=meta.get("icon", ""),
                    agents=meta.get("agents", []),
                )
                # Build filtered SubAgentRegistry for this app
                full_registry = SubAgentRegistry(agents_dir, github_token)
                # Filter to only this app's declared agents
                full_registry.agents = {
                    k: v for k, v in full_registry.agents.items()
                    if k in app_def.agents
                }
                if not full_registry.agents:
                    logger.warning("[apps] app '%s' has no valid agents after filtering", slug)
                graph = build_orchestrator_graph(full_registry, github_token, checkpointer)
                self.apps[slug] = app_def
                self.graphs[slug] = graph
                logger.info("[apps] loaded app: %s (agents=%s)", slug, app_def.agents)
            except Exception as e:
                logger.warning("[apps] failed to load app '%s': %s", slug, e)

    def all(self) -> list[AppDefinition]:
        return list(self.apps.values())

    def get_graph(self, slug: str):
        return self.graphs.get(slug)
```

[ASSUMED] — pattern derived from codebase reading, specific class API is Claude's discretion per CONTEXT.md.

### Pattern 2: GET /api/apps route (mirrors GET /api/agents)

**What:** Scans `apps/*/APP.md`, returns array of `{slug, name, description, icon, agents[]}`.
**When to use:** Called at MenuScreen mount.

```python
# Source: app/api/routes/agents.py (direct template)
# New file: app/api/routes/apps.py

import os
from pathlib import Path
import frontmatter
from fastapi import APIRouter, Depends
from app.api.routes.chat import get_jwt_payload

APP_DIR = os.getenv("APP_DIR", "./apps")
router = APIRouter(prefix="/api", tags=["apps"])

@router.get("/apps")
async def list_apps(_payload: dict = Depends(get_jwt_payload)) -> list[dict]:
    apps = []
    for app_md in sorted(Path(APP_DIR).glob("*/APP.md")):
        try:
            post = frontmatter.load(str(app_md))
            slug = app_md.parent.name
            meta = post.metadata
            apps.append({
                "slug": slug,
                "name": meta.get("name", slug),
                "description": meta.get("description", ""),
                "icon": meta.get("icon", ""),
                "agents": meta.get("agents", []),
            })
        except Exception:
            continue
    return apps
```

[VERIFIED: pattern match with `app/api/routes/agents.py`]

### Pattern 3: main.py lifespan update

**What:** Build `AppRegistry` (which compiles per-app graphs) and store in `app.state`.
**Critical:** `SubAgentRegistry` instances are built inside `AppRegistry.__init__` per app.
They instantiate `ChatCopilot` per agent — this happens N_apps × N_agents times at startup.
For a 200-user system with a handful of apps this is acceptable (apps loaded once, not per-request).

```python
# In lifespan(), after checkpointer.setup():
from app.orchestrator.apps import AppRegistry
import os
apps_dir = os.getenv("APP_DIR", "./apps")
agent_dir_path = os.getenv("AGENT_DIR", "./agents")
github_token = auth_manager.load_token()  # available after auth_manager init
app_registry = AppRegistry(apps_dir, agent_dir_path, github_token, checkpointer)
app.state.app_registry = app_registry
```

[ASSUMED] — exact lifespan wiring is Claude's discretion; pattern consistent with Phase 12 agent_health build.

### Pattern 4: OrchestratorHandler — graph lookup not build

**What:** Instead of building a new `SubAgentRegistry` + graph per job, look up the pre-built graph.

```python
# In OrchestratorHandler.handle():
# BEFORE (current):
#   registry = SubAgentRegistry(AGENT_DIR, github_token)
#   graph = build_orchestrator_graph(registry, github_token, checkpointer=checkpointer)

# AFTER:
# app_registry is not available in the arq worker context (different process).
# Two options:
# Option A: Keep per-job build, add agents filter via app slug instead of UI chip list
# Option B: Pass app_slug in job payload; worker rebuilds filtered registry from APP.md

# The arq worker is a SEPARATE PROCESS from FastAPI — it cannot share app.state.
# Therefore, OrchestratorHandler must still build its own SubAgentRegistry per job.
# The change is HOW it filters: instead of filtering by UI chip names, it reads the
# app's APP.md to get the canonical agent list.
```

**IMPORTANT FINDING:** The arq worker runs in a separate process. `app.state.app_registry` is NOT
accessible from the worker. The worker must independently resolve the app's agent list.

Two valid approaches:
1. Pass `agents[]` list in job payload (current mechanism — UI chips populate this). For app-scoped
   chat, the `agents[]` in the job payload becomes the app's declared agents (read from APP.md at
   request time in the API route, then passed to enqueue_job).
2. Pass `app_slug` in job payload; worker reads APP.md to get agents list.

Option 1 is lower risk — it reuses the existing `agents` field in the job payload. The API route
(`POST /api/chat`) reads APP.md to get the app's declared agent list and injects it into the
`enqueue_job` call.

[VERIFIED: `app/jobs/worker.py` imports show it runs independently; `OrchestratorHandler` builds
its own `SubAgentRegistry` per job — lines 34-55 of `orchestrator_handler.py`]

### Pattern 5: Frontend — App.tsx activeApp state

```typescript
// Source: frontend/src/App.tsx (existing screen state machine pattern)
// Add alongside currentScreen:

import type { AppDefinition } from './types';

const [activeApp, setActiveApp] = useState<AppDefinition | null>(null);

// MenuScreen onNavigate receives AppDefinition (not plain string):
<MenuScreen
  onNavigate={(app: AppDefinition) => {
    setActiveApp(app);
    setCurrentScreen('superchat');
  }}
/>

// SuperChatApp now receives appId + appName:
<SuperChatApp
  selectedModel={selectedModel}
  appId={activeApp?.slug ?? ''}
  appName={activeApp?.name ?? ''}
/>
```

[VERIFIED: App.tsx lines 22-73]

### Pattern 6: Dynamic MenuScreen

```typescript
// Source: MenuScreen.tsx (existing FeatureCard pattern)
// Replace hardcoded cards with fetched AppDefinition list

import { useState, useEffect } from 'react';
import type { AppDefinition } from '../types';

export function MenuScreen({ onNavigate }: MenuScreenProps) {
  const [apps, setApps] = useState<AppDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('./api/apps', { credentials: 'include' })
      .then(r => r.ok ? r.json() : Promise.reject(r))
      .then((data: AppDefinition[]) => { setApps(data); setLoading(false); })
      .catch(() => { setError('Could not load applications. Please refresh the page.'); setLoading(false); });
  }, []);
  // ...render skeleton / error / empty / cards based on state
}
```

[VERIFIED: pattern consistent with `useAgents` hook and `apiFetch` in `frontend/src/api/client.ts`]

### Anti-Patterns to Avoid

- **Building SubAgentRegistry inside AppRegistry with shared github_token:** The token may be stale or
  change between users. At startup there may not be a valid token (Device Flow not yet completed).
  Recommendation: AppRegistry builds metadata-only at startup; graphs are built with the user's token
  per-job (Option 1 above). Keep the existing per-job build pattern in OrchestratorHandler.
- **Compiling graphs at startup with a github_token:** ChatCopilot instances are token-bound. If the
  user re-authenticates, the compiled graph still holds old ChatCopilot instances. Per-job graph build
  avoids this. [VERIFIED: `orchestrator_handler.py` line 34 — registry built per job with job's token]
- **Using `**` glob in `apps/` scanner:** `SubAgentRegistry` changed from `**/AGENT.md` to `*/AGENT.md`
  (flat structure) in Phase 12. Use `*/APP.md` for consistency.
  [VERIFIED: Phase 12 decision in STATE.md — "Glob changed from **/AGENT.md to */AGENT.md"]
- **Hardcoding 'superchat' as app_id in chat.py:** Current code has `app_id = "superchat" if body.mode == "super" else "chat"`. This must use the selected app's slug instead.
  [VERIFIED: `app/api/routes/chat.py` line 86]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | Custom YAML parser | `python-frontmatter` (`frontmatter.load()`) | Already used for AGENT.md; identical format |
| Pydantic model for API response | Custom dict serialization | `AppInfo` Pydantic model (new) or inline `dict` | FastAPI serializes automatically |
| App slug → graph lookup dict | Custom registry class with complex logic | Plain `dict[str, CompiledGraph]` | Slug is unique per directory name; dict is sufficient |

**Key insight:** Every primitive needed already exists in the project. This phase is wiring, not invention.

---

## Common Pitfalls

### Pitfall 1: Worker Process Cannot Access FastAPI app.state
**What goes wrong:** Code tries to use `app.state.app_registry` or `app.state.app_graphs` from inside
`OrchestratorHandler`. This crashes at runtime because the arq worker is a separate process.
**Why it happens:** It's easy to forget the worker/API split when both use the same Python module.
**How to avoid:** Keep the per-job graph build in `OrchestratorHandler`. Inject the app's agent list via
the job payload (read from APP.md in the API route before enqueue). The job payload already carries
`agents: list[str]`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'app_registry'` in worker logs.

### Pitfall 2: app_id Hardcoded to 'superchat' in chat.py
**What goes wrong:** All threads sent from app-scoped chat are tagged `app_id='superchat'` regardless of
which app the user selected.
**Why it happens:** `chat.py` line 86 has `app_id = "superchat" if body.mode == "super" else "chat"`.
**How to avoid:** Add `app_id` field to `ChatRequest` model. Frontend passes `activeApp.slug` in the
request body. Backend uses `body.app_id` instead of the hardcoded mode-to-string logic.
**Warning signs:** All threads from any app appear in the 'superchat' thread list.

### Pitfall 3: applications Table FK Constraint Breaks New App Slugs
**What goes wrong:** `threads` table has `app_id TEXT NOT NULL REFERENCES applications(app_id)`. New
app slugs (e.g., `apps/code-tools/APP.md` → slug `code-tools`) are not seeded in the `applications`
table at startup, so INSERT into `threads` fails with FK violation.
**Why it happens:** `main.py` seeds only `'chat'` and `'superchat'` at startup.
**How to avoid:** In lifespan, after loading APP.md files, upsert all discovered app slugs into
`applications`. Or: relax the FK (make it nullable / defer) — but upsert is cleaner.
**Warning signs:** 500 errors on first message in a new app; FK constraint violation in logs.
[VERIFIED: `app/api/main.py` lines 67-73 — applications table seeded with hardcoded values]

### Pitfall 4: APP.md References Non-Existent Agent Folder
**What goes wrong:** `agents:` list in APP.md includes a folder that doesn't exist under `agents/`.
`SubAgentRegistry` will not have that agent, so the filtered registry is unexpectedly smaller.
**Why it happens:** Typos in APP.md, or agent folder was renamed.
**How to avoid:** Log a warning (not error) at startup listing the missing agent names. Do not crash.
This is consistent with the DEGRADED/FAILED pattern in SubAgentRegistry.

### Pitfall 5: MenuScreen onNavigate Type Change Breaks App.tsx
**What goes wrong:** `MenuScreen.onNavigate` signature changes from `(screen: string) => void` to
`(app: AppDefinition) => void`. The existing caller in `App.tsx` casts to `string` — TypeScript will
catch this at compile time, but the cast `(s) => setCurrentScreen(s as ...)` will silently mis-route.
**Why it happens:** The existing cast in `App.tsx` line 40: `onNavigate={(s) => setCurrentScreen(s as 'menu' | 'chat' | 'superchat')}`.
**How to avoid:** Update the interface AND the call-site together in the same task. TypeScript strict
mode will surface the mismatch.

### Pitfall 6: useThreads('superchat') hardcode in SuperChatApp
**What goes wrong:** `useThreads` is called with hardcoded `'superchat'` as the mode argument. In
app-scoped chat, threads should be filtered by the app's slug, not by `'superchat'`.
**Why it happens:** `SuperChatApp.tsx` line 118: `useThreads('superchat')`.
**How to avoid:** Pass `appId` prop into `SuperChatApp`, use `useThreads(appId)` so threads are
filtered to the selected app.
[VERIFIED: `SuperChatApp.tsx` line 118]

---

## Code Examples

### APP.md format (from CONTEXT.md D-02)

```yaml
---
name: Code Tools
description: Agents for code review and SQL analysis
icon: 🛠
agents:
  - code-reviewer
  - sql-analyst
---

This application groups coding-focused agents for developers.
```

### Existing frontmatter load pattern (replicate exactly)

```python
# Source: app/orchestrator/agent.py lines 97-107 (SubAgent.from_dir)
post = frontmatter.load(agent_dir / "AGENT.md")
meta = post.metadata
name = meta["name"]
description = meta["description"]
keywords = meta.get("keywords", [])
```

### Existing agent health check pattern at startup

```python
# Source: app/api/main.py lines 123-153
# AppRegistry loader follows this same try/except pattern for fault tolerance
for agent_md in Path(agent_dir_path).glob("*/AGENT.md"):
    agent_name = agent_md.parent.name
    try:
        post = fm.load(str(agent_md))
        # ... process
    except _INIT_FAILURE_TYPES as e:
        # log FAILED
    except Exception as e:
        # log DEGRADED
```

### Existing agents route (GET /api/agents — template for GET /api/apps)

```python
# Source: app/api/routes/agents.py (full file)
# GET /api/apps follows identical structure with APP_DIR env var
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded 'Chat' + 'SuperChat' cards | Dynamic `GET /api/apps` list | Phase 14 | MenuScreen renders any number of apps |
| app_id derived from `mode` field ('simple'→'chat', 'super'→'superchat') | app_id = selected app slug | Phase 14 | app_id in threads table carries real app identity |
| Single global graph (`app.state.graph`) for simple chat | Single global graph remains; per-app routing through OrchestratorHandler | Phase 14 | No change to simple chat path |
| OrchestratorHandler builds registry per job with agents filter from UI | OrchestratorHandler builds registry per job with agents filter from APP.md (via job payload) | Phase 14 | Agent set is now app-defined, not UI-selected |

**Deprecated/outdated:**
- `mode='super'→'superchat'` app_id derivation in `chat.py` — replaced by `body.app_id` from frontend.
- Hardcoded `applications` seed in `main.py` (`'chat'`, `'superchat'`) — must be superseded by dynamic app slug upserts.

---

## Open Questions

1. **Startup token availability for AppRegistry**
   - What we know: `CopilotAuthManager` loads token via `auth_manager.load_token()`. This can return `None` if Device Flow hasn't been completed (first run).
   - What's unclear: Should AppRegistry build graphs (with ChatCopilot instances) at startup, or only load metadata?
   - Recommendation: Load metadata only at startup (no ChatCopilot instantiation). Graph builds happen per-job as today. `GET /api/apps` reads APP.md files directly (no ChatCopilot needed for listing apps). This avoids the startup-token problem entirely.

2. **applications table FK — how many app slugs to seed**
   - What we know: `threads.app_id` has FK → `applications.app_id`. New app slugs must exist in `applications` before threads can be inserted.
   - Recommendation: In lifespan, after scanning APP.md files, upsert all discovered slugs into `applications`. This is idempotent and self-maintaining.

3. **AgentSelector chips in app-scoped chat**
   - What we know: `SuperChatApp.tsx` shows `AgentSelector` chips that let users sub-select agents. In app-scoped mode, the chip list should only show that app's declared agents (not all agents).
   - What's unclear: Should the chips still be interactive (user can deselect within the app's subset), or be fixed/hidden?
   - Recommendation: Keep chips interactive but populate them from `appId`-filtered agent list. Pass `appId` to `useAgents` hook to filter.

---

## Environment Availability

Step 2.6: All dependencies are existing project stack. No new external tools required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python-frontmatter` | AppRegistry APP.md parsing | Yes | installed | — |
| `pathlib` | File glob for apps/ | Yes | stdlib | — |
| `fastapi` | GET /api/apps route | Yes | 0.135.2 | — |
| `apps/` directory | App definitions | No — must be created | — | Wave 1 creates it with chat/superchat APP.md files |
| PostgreSQL `applications` table | Thread FK constraint | Yes — exists, seeded with chat/superchat | — | Must upsert new slugs at startup |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- `apps/` directory does not exist — Wave 1 creates `apps/chat/APP.md` and `apps/superchat/APP.md`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"`, `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_apps.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| APP-01 | AppRegistry scans apps/ and returns AppDefinition list | unit | `uv run pytest tests/test_apps.py::test_app_registry_loads_apps -x` | Wave 0 |
| APP-01 | AppRegistry builds filtered SubAgentRegistry per app | unit | `uv run pytest tests/test_apps.py::test_app_registry_filters_agents -x` | Wave 0 |
| APP-02 | GET /api/apps returns list of app definitions | integration | `uv run pytest tests/test_api_apps.py::test_list_apps -x` | Wave 0 |
| APP-03 | OrchestratorHandler uses app-filtered agent list from job payload | unit | `uv run pytest tests/test_worker.py::test_orchestrator_uses_app_agents -x` | Wave 0 |
| APP-04 | Same agent folder in two APP.md files; both apps load successfully | unit | `uv run pytest tests/test_apps.py::test_shared_agent_across_apps -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_apps.py tests/test_api_apps.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_apps.py` — AppRegistry unit tests (APP-01, APP-04)
- [ ] `tests/test_api_apps.py` — GET /api/apps integration tests (APP-02)
- [ ] `tests/test_worker.py` needs new test for app-slug agent filtering (APP-03) — file exists, add test

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing JWT httpOnly cookie — `get_jwt_payload` dependency applied to `GET /api/apps` |
| V3 Session Management | no | No session changes |
| V4 Access Control | no | No per-user app access control in this phase |
| V5 Input Validation | yes | APP.md frontmatter is developer-controlled; no user input in app definitions. `app_slug` from URL path validated by dict lookup (unknown slug → 404). |
| V6 Cryptography | no | No new crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in APP_DIR glob | Tampering | `Path(APP_DIR).glob("*/APP.md")` — `*` matches only one directory level; no `..` escape possible |
| Unauthorized app listing | Information Disclosure | `GET /api/apps` requires JWT — `Depends(get_jwt_payload)` |
| app_slug injection in thread insert | Tampering | Slug comes from validated `AppDefinition.slug` (derived from directory name, not user input) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | AppRegistry builds metadata only at startup (no ChatCopilot instantiation); graphs built per-job in worker | Architecture Patterns / Open Questions | If graphs must be pre-built, startup needs valid github_token and more complex lifecycle management |
| A2 | `GET /api/apps` is JWT-protected (mirrors GET /api/agents) | Security Domain | If left unprotected, app list is publicly readable — low severity for internal tool |
| A3 | `app_id` field added to `ChatRequest` body to replace mode-derived hardcode | Pitfall 2 | If approach differs, threads table app_id may be wrong |

---

## Sources

### Primary (HIGH confidence)
- `app/orchestrator/agent.py` — SubAgentRegistry loader pattern (direct template for AppRegistry)
- `app/api/routes/agents.py` — GET /api/agents route (direct template for GET /api/apps)
- `app/api/main.py` — lifespan pattern + applications table FK constraint
- `app/jobs/handlers/orchestrator_handler.py` — per-job registry build + agent filter pattern
- `frontend/src/components/MenuScreen.tsx` — existing card rendering (FeatureCard)
- `frontend/src/App.tsx` — screen state machine (currentScreen)
- `frontend/src/components/SuperChatApp.tsx` — useThreads('superchat') hardcode (Pitfall 6)
- `.planning/STATE.md` — Phase 12/13 decisions affecting glob pattern and routing
- `14-CONTEXT.md` — all locked decisions D-01 through D-12

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — APP-01 through APP-04 acceptance criteria

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, verified by codebase read
- Architecture: HIGH — all patterns are direct mirrors of existing code
- Pitfalls: HIGH — all identified from reading actual source lines with concrete line references
- Test map: MEDIUM — test file names are proposed; existing test patterns verified

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable stack — no fast-moving dependencies)
