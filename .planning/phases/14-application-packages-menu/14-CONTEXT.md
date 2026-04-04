# Phase 14: Application Packages + Menu - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

App definition files (APP.md) declare agent subsets. A menu screen lists available applications dynamically. Selecting an app launches an app-scoped chat where only that app's declared agents are candidates for routing. One agent folder can be shared across multiple apps with no definition duplication.

Creating new agents, modifying existing agents, or changing the routing algorithm are out of scope.

</domain>

<decisions>
## Implementation Decisions

### App Definition File Format

- **D-01:** App definition files use YAML frontmatter + markdown body format, stored as `apps/<slug>/APP.md` — same pattern as `agents/<slug>/AGENT.md`. Frontmatter fields: `name`, `description`, `icon`, `agents` (list of agent folder names).
- **D-02:** Example structure:
  ```yaml
  ---
  name: Code Tools
  description: Agents for code review and SQL analysis
  icon: 🛠
  agents:
    - code-reviewer
    - sql-analyst
  ---
  ```
- **D-03:** Agent names in `agents:` list refer to folder names under `agents/`. Shared agents appear in multiple APP.md files — no duplication of the agent definition itself (satisfies APP-04).

### Menu Screen Evolution

- **D-04:** The existing hardcoded "Chat" and "SuperChat" cards are removed. MenuScreen becomes fully dynamic — it fetches app list from `GET /api/apps` and renders one card per discovered APP.md file.
- **D-05:** Chat and SuperChat become regular apps defined in `apps/` folder (e.g., `apps/chat/APP.md`, `apps/superchat/APP.md`). No legacy hardcoded cards remain.
- **D-06:** `GET /api/apps` returns array of `{slug, name, description, icon, agents[]}`. Frontend uses this to render cards.

### Agent Filtering Architecture

- **D-07:** At startup, an `AppRegistry` loads all APP.md files from `apps/`. For each app, it builds a filtered `SubAgentRegistry` (containing only that app's declared agents) and compiles a dedicated `OrchestratorGraph`. Graphs stored by app slug in a dict.
- **D-08:** Per-request routing: look up `app_graphs[app_slug]`, invoke that graph. RouterNode sees only that app's agents as candidates — no runtime filtering needed inside RouterNode (satisfies APP-03).
- **D-09:** The existing single-registry global graph (used by SuperChat today) is replaced by the per-app graph lookup. If an app slug is unknown, return 404.

### App-Scoped Chat UI

- **D-10:** `SuperChatApp.tsx` is reused for app-scoped chat. It receives two new props: `appId` (slug for thread/api scoping) and `appName` (displayed in header as subtitle or title).
- **D-11:** `App.tsx` adds an `activeApp` state field (type: `AppDefinition | null`). When user selects an app card from MenuScreen, `activeApp` is set and `currentScreen` transitions to `'superchat'` (reusing existing routing).
- **D-12:** The Header or chat area shows which application is active, satisfying success criterion #2.

### Claude's Discretion

- Exact AppRegistry Python class structure and module location (suggested: `app/orchestrator/apps.py`)
- How to handle APP.md referencing a non-existent agent (warning log vs error)
- API response caching strategy for `GET /api/apps`
- Icon rendering in menu cards (emoji or SVG)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — APP-01, APP-02, APP-03, APP-04 (full acceptance criteria)

### Existing patterns to follow
- `app/orchestrator/agent.py` — SubAgentRegistry and SubAgent (same loading pattern for AppRegistry)
- `app/orchestrator/graph.py` — `build_orchestrator_graph()` (called per app at startup)
- `agents/code-reviewer/AGENT.md` — reference AGENT.md format (APP.md mirrors this pattern)
- `frontend/src/components/MenuScreen.tsx` — existing static menu (to be replaced with dynamic version)
- `frontend/src/App.tsx` — screen routing state machine (add activeApp state here)
- `frontend/src/components/SuperChatApp.tsx` — reused as app-scoped chat (add appId/appName props)
- `app/api/routes/chat.py` — how app_id flows into thread upsert (must be updated to use app slug)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SubAgentRegistry` (`app/orchestrator/agent.py`) — already loads agents from folder glob; AppRegistry follows same pattern for apps/
- `build_orchestrator_graph()` (`app/orchestrator/graph.py`) — called once today; will be called once per app
- `SuperChatApp.tsx` — multi-agent chat with thread sidebar; add `appId`/`appName` props
- `FeatureCard` component inside `MenuScreen.tsx` — reusable card pattern for dynamic app cards
- `python-frontmatter` library — already used by `SubAgent.from_dir()` for AGENT.md parsing; same for APP.md

### Established Patterns
- AGENT.md frontmatter loading: `post = frontmatter.load(path)`, `meta = post.metadata` — replicate for APP.md
- `app_id` in threads table already exists (Phase 10); app slug becomes the new `app_id` value
- Screen routing via `currentScreen` state in `App.tsx` with `setCurrentScreen()` — extend to carry `activeApp`
- `GET /api/threads?app_id=X` already filters by app_id (Phase 10) — app slug plugs directly into this

### Integration Points
- `app/api/main.py` — mount new `GET /api/apps` route; inject AppRegistry into app state
- `app/orchestrator/graph.py` — `OrchestratorHandler` must look up per-app graph instead of single global graph
- `frontend/src/App.tsx` — MenuScreen `onNavigate` callback must also receive selected app object
- `app/api/routes/chat.py` — `app_id` in thread upsert must use selected app slug (not hardcoded "chat"/"superchat")

</code_context>

<specifics>
## Specific Ideas

- APP.md follows exact same YAML frontmatter + markdown body convention as AGENT.md — developers already know this pattern
- App cards replace the existing "Chat" and "SuperChat" cards entirely — these become first-class apps defined in `apps/` folder
- Per-app compiled graphs at startup (not runtime filtering) — clean isolation with no RouterNode changes needed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- "チャットのコンテキストにてユーザー情報も入れるようにする" — user info in chat context; not scoped to Phase 14
- "Implement Gem and Canvas feature" — separate feature, own phase
- "Investigate Agent-Skills integration mechanism" — separate research topic

</deferred>

---

*Phase: 14-application-packages-menu*
*Context gathered: 2026-04-05*
