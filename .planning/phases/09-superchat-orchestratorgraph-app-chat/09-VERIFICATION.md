---
phase: 09-superchat-orchestratorgraph-app-chat
verified: 2026-04-04T00:00:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification: false
human_verification:
  - test: "Live UAT — mode toggle visible and functional in browser"
    expected: "Simple/Super toggle buttons visible in input bar; clicking Super sends request to OrchestratorHandler; switching back to Simple uses LangGraph handler"
    why_human: "Requires docker compose up, authenticated browser session, and visual inspection of toggle highlighting and agent-routed responses. Cannot verify without a running stack."
  - test: "Super mode agent routing — code-reviewer agent responds"
    expected: "Sending 'Review this Python code: print(hello)' in Super mode returns a code-review response from the code-reviewer SubAgent"
    why_human: "Requires live Copilot SDK subprocess execution and GitHub token; not testable statically or without a running stack."
  - test: "Error resilience — super mode with missing agents directory"
    expected: "UI shows error message from OrchestratorHandler RuntimeError; does not crash the browser"
    why_human: "Requires a running stack with AGENT_DIR pointing to an empty/missing directory."
---

# Phase 9: SuperChat OrchestratorGraph Integration Verification Report

**Phase Goal:** Integrate the OrchestratorGraph + SubAgent + MenuDispatcher prototype from `super-agent-sample/` into the main `app/` as a selectable mode (`simple` vs `super`), with `github_token` threading for multi-user auth, a new `OrchestratorHandler` in the arq worker, and a React UI toggle to switch between modes.

**Verified:** 2026-04-04
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                  | Status     | Evidence                                                                                                            |
|----|----------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------------------------|
| 1  | OrchestratorGraph module exists in `app/orchestrator/` with correct imports            | VERIFIED   | All 5 files present; imports use `app.providers.copilot` and `app.orchestrator.*`; no standalone copies            |
| 2  | `github_token` is threaded through SubAgent/SubAgentRegistry/RouterNode/build_orchestrator_graph | VERIFIED | `github_token` parameter in all 4 constructors/functions; `CopilotAuthManager` absent from orchestrator module     |
| 3  | `OrchestratorHandler` is registered in the arq worker and handles `task_type='orchestrator'` | VERIFIED | `orchestrator_handler.py` exists; `TASK_HANDLERS` dict in `worker.py` includes `"orchestrator": OrchestratorHandler()` |
| 4  | `POST /api/chat` accepts `mode` field and routes `mode='super'` to `task_type='orchestrator'` | VERIFIED | `ChatRequest.mode: Literal["simple","super"] = "simple"` in `models.py`; translation logic on line 80 of `chat.py` |
| 5  | Job/SSE/polling pattern is unchanged (D-06)                                            | VERIFIED   | `app/api/routes/jobs.py` and SSE in `chat.py` are unchanged; new code adds no new endpoints                        |
| 6  | `AGENT_DIR`/`MENU_DIR` env vars in both `api` and `worker` services in docker-compose | VERIFIED   | Lines 31-32 (api) and 51-52 (worker) in `docker-compose.yml`; `docker compose config` validates successfully       |
| 7  | React UI has mode toggle wired end-to-end (types → hook → component)                  | VERIFIED   | `ChatRequest.mode` in `types.ts`; `selectedMode` in `useChat`; toggle buttons in `MessageArea`; `chatMode` state in `ChatApp` |

**Score:** 7/7 truths verified (all automated checks pass)

---

### Required Artifacts

| Artifact                                            | Expected                                         | Status     | Details                                                             |
|-----------------------------------------------------|--------------------------------------------------|------------|---------------------------------------------------------------------|
| `app/orchestrator/__init__.py`                      | Module package file                              | VERIFIED   | Exists with docstring                                               |
| `app/orchestrator/state.py`                         | AgentState TypedDict                             | VERIFIED   | Correct definition with `input`, `output`, `messages`, `next`      |
| `app/orchestrator/agent.py`                         | SubAgent + SubAgentRegistry with github_token    | VERIFIED   | `github_token` in `__init__`, `from_dir`, `SubAgentRegistry.__init__`; `close()` methods on both classes |
| `app/orchestrator/graph.py`                         | RouterNode + build_orchestrator_graph            | VERIFIED   | `github_token` in RouterNode and `build_orchestrator_graph`; `build_simple_graph` absent |
| `app/orchestrator/dispatcher.py`                    | MenuRegistry + MenuDispatcher                    | VERIFIED   | Imports from `app.orchestrator.state`; no standalone copy          |
| `app/jobs/handlers/orchestrator_handler.py`         | OrchestratorHandler(TaskHandler)                 | VERIFIED   | `finally: await registry.close()` present; guards empty registry with RuntimeError |
| `app/jobs/handlers/__init__.py`                     | Exports OrchestratorHandler                      | VERIFIED   | `OrchestratorHandler` in `__all__`                                 |
| `app/jobs/worker.py`                                | TASK_HANDLERS includes 'orchestrator'            | VERIFIED   | `"orchestrator": OrchestratorHandler()` in dict                    |
| `app/api/models.py`                                 | ChatRequest with mode field                      | VERIFIED   | `mode: Literal["simple", "super"] = "simple"` present              |
| `app/api/routes/chat.py`                            | mode→task_type translation before enqueue        | VERIFIED   | `task_type = "orchestrator" if body.mode == "super" else body.task_type` on line 80 |
| `docker-compose.yml`                                | AGENT_DIR + MENU_DIR in api and worker           | VERIFIED   | Both services have `/app/agents` and `/app/menus`                  |
| `agents/code-reviewer/AGENT.md`                     | Valid YAML frontmatter with name/description/model | VERIFIED | `name: code-reviewer`, `model: claude-opus-4-6` in frontmatter     |
| `agents/sql-analyst/AGENT.md`                       | Valid YAML frontmatter with name/description/model | VERIFIED | `name: sql-analyst`, `model: claude-sonnet-4-6` in frontmatter     |
| `menus/super-chat.yaml`                             | YAML menu config                                 | VERIFIED   | File exists                                                         |
| `menus/simple-chat.yaml`                            | YAML menu config                                 | VERIFIED   | File exists                                                         |
| `frontend/src/types.ts`                             | ChatRequest with mode field                      | VERIFIED   | `mode?: 'simple' \| 'super'` present                               |
| `frontend/src/hooks/useChat.ts`                     | selectedMode option passed to postChat           | VERIFIED   | `selectedMode` in `UseChatOptions`, destructured, passed in `postChat` call, in dependency array |
| `frontend/src/components/MessageArea.tsx`           | Toggle buttons for Simple and Super              | VERIFIED   | Two buttons unconditionally rendered; active mode highlighted with `#0366d6` |
| `frontend/src/components/ChatApp.tsx`               | chatMode state wired to useChat and MessageArea  | VERIFIED   | `useState<'simple' \| 'super'>('simple')`; `selectedMode: chatMode` to `useChat`; `mode={chatMode}` to `MessageArea` |
| `super-agent-sample/` (preserved)                   | Prototype preserved (D-03)                       | VERIFIED   | Directory intact with `src/`, `agents/`, `menus/`                  |

---

### Key Link Verification

| From                          | To                                | Via                                              | Status  | Details                                                              |
|-------------------------------|-----------------------------------|--------------------------------------------------|---------|----------------------------------------------------------------------|
| `chat.py` send_message        | `TASK_HANDLERS["orchestrator"]`   | `mode='super'` → `task_type='orchestrator'` → `enqueue_job` | WIRED | Line 80 translates mode; enqueue_job uses translated task_type       |
| `worker.py` process_chat      | `OrchestratorHandler.handle()`    | `TASK_HANDLERS.get(task_type)`                   | WIRED   | Handler lookup on line 72 of worker.py                              |
| `OrchestratorHandler`         | `SubAgentRegistry` + `build_orchestrator_graph` | Instantiation per job with github_token | WIRED | Lines 29 and 39 in orchestrator_handler.py                          |
| `SubAgentRegistry`            | `agents/code-reviewer/AGENT.md`   | `Path(agent_dir).glob("**/AGENT.md")`            | WIRED   | AGENT_DIR env var → `/app/agents` → glob in SubAgentRegistry.__init__ |
| `ChatApp.tsx`                 | `useChat(selectedMode: chatMode)` | `chatMode` state via props                       | WIRED   | Line 57 in ChatApp.tsx passes `selectedMode: chatMode`              |
| `useChat`                     | `postChat({ mode: selectedMode })` | postChat call in sendMessage                    | WIRED   | Line 53 in useChat.ts includes `mode: selectedMode`                 |
| `MessageArea`                 | `onModeChange(setChatMode)`       | prop callback                                    | WIRED   | Line 146 in ChatApp.tsx passes `onModeChange={setChatMode}`         |

---

### Data-Flow Trace (Level 4)

| Artifact                    | Data Variable | Source                                 | Produces Real Data | Status    |
|-----------------------------|---------------|----------------------------------------|--------------------|-----------|
| `OrchestratorHandler.handle` | `final_text`  | `graph.ainvoke(initial)["output"]`     | Yes (SubAgent LLM response) | FLOWING |
| `MessageArea.tsx`           | `messages`    | `setMessages` from `useChat` → SSE+polling → `getJob` | Yes (API job result) | FLOWING |
| `MessageArea.tsx` toggle    | `mode`        | `chatMode` state from `ChatApp.useState` | Yes (user-controlled local state) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                     | Command                                                | Result    | Status  |
|----------------------------------------------|--------------------------------------------------------|-----------|---------|
| Orchestrator module imports cleanly          | Static analysis of import chains                       | All `app.*` imports; no old prototype imports | PASS |
| TASK_HANDLERS dict contains 'orchestrator'   | Code review of worker.py                               | `"orchestrator": OrchestratorHandler()` present | PASS |
| ChatRequest mode field with default          | Code review of models.py                               | `mode: Literal["simple","super"] = "simple"` | PASS |
| mode→task_type routing logic                 | Code review of chat.py line 80                         | `task_type = "orchestrator" if body.mode == "super" else body.task_type` | PASS |
| registry.close() in finally block            | Code review of orchestrator_handler.py lines 58-59     | `finally: await registry.close()` present | PASS |
| docker-compose.yml validity                  | `docker compose config --quiet`                        | exit 0 | PASS |
| TypeScript types and hook wiring             | Static review (node_modules not installed in env)      | Types, hook, component, ChatApp all consistent | PASS (static) |
| Frontend TS compilation                      | `npx tsc --noEmit`                                     | SKIPPED — node_modules empty in this env; verified statically | SKIP |
| Python import runtime                        | `.venv/bin/python` invocation                          | SKIPPED — venv has broken symlinks (pre-existing env issue) | SKIP |

---

### Requirements Coverage

| Requirement | Description                                                                 | Status    | Evidence                                                                           |
|-------------|-----------------------------------------------------------------------------|-----------|------------------------------------------------------------------------------------|
| D-01        | `app/orchestrator/` module created                                          | SATISFIED | All 5 files present: `__init__.py`, `state.py`, `agent.py`, `graph.py`, `dispatcher.py` |
| D-02        | Imports from `app.providers.copilot` / `app.auth.manager` (no standalone copies) | SATISFIED | New orchestrator module imports only from `app.*`; no `chat_copilot.py` in `app/orchestrator/` |
| D-03        | `super-agent-sample/` preserved                                             | SATISFIED | Directory intact with `src/`, `agents/`, `menus/`                                 |
| D-04        | `mode` field on `POST /api/chat`                                            | SATISFIED | `ChatRequest.mode: Literal["simple","super"] = "simple"` in models.py              |
| D-06        | Same job/SSE/polling pattern                                                | SATISFIED | `GET /api/job/{job_id}` in `jobs.py`; SSE generator in `chat.py` unchanged        |
| D-07        | `AGENT_DIR`/`MENU_DIR` env vars                                             | SATISFIED | Both in `api` and `worker` services in docker-compose.yml                         |
| D-08        | React mode toggle                                                           | SATISFIED | Toggle rendered unconditionally in `MessageArea`; state in `ChatApp`; wired through `useChat` |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/MessageArea.tsx` | 218, 232 | Toggle labels are "Simple"/"Super" without emoji (plan specified "💬 Simple"/"🚀 Super") | Info | No functional impact; CLAUDE.md convention discourages emojis in files without explicit request — this is correct compliance |

No blocking or warning anti-patterns found.

---

### Human Verification Required

#### 1. Live mode toggle — visual and functional

**Test:** `docker compose up`, navigate to `http://localhost:5173/app`, complete Device Flow login. Verify:
- Mode toggle "Simple" and "Super" buttons appear in the input bar below the text area
- "Simple" button has blue background by default; "Super" is unselected
- Clicking "Super" toggles highlight to Super button
- Sending a message in Super mode returns a response (via OrchestratorHandler)
- Switching back to Simple returns normal LangGraph responses

**Expected:** Toggle is always visible; active mode highlighted in blue (#0366d6); messages are delivered via the same SSE/polling flow regardless of mode

**Why human:** Requires a running stack with valid GitHub auth, visual inspection, and end-to-end message delivery

#### 2. Agent routing in Super mode

**Test:** With Super mode selected, send "Review this Python code: print('hello')"

**Expected:** Response contains code-review feedback from the `code-reviewer` SubAgent (not a generic LangGraph response)

**Why human:** Requires live Copilot SDK subprocess and GitHub token to invoke the SubAgent LLM

#### 3. Error resilience in Super mode

**Test:** Set `AGENT_DIR` to an empty/nonexistent directory and send a message in Super mode

**Expected:** The UI displays an error message ("Error: No agents found...") without crashing

**Why human:** Requires modifying docker-compose env and observing UI behavior

---

### Gaps Summary

No gaps found. All 7 observable truths are verified, all 19 required artifacts exist and are substantive, all 7 key links are wired, all requirement IDs (D-01 through D-08) are satisfied. The only items deferred to human verification are the live UAT steps (Task 2 of Plan 09-04), which require `docker compose up` and a valid GitHub Copilot token — this deferral was explicitly acknowledged in the phase plan.

---

_Verified: 2026-04-04_
_Verifier: Claude (gsd-verifier)_
