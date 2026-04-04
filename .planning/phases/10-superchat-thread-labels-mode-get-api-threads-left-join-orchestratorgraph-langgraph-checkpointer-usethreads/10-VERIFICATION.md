---
phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads
verified: 2026-04-04T05:00:00Z
status: human_needed
score: 10/10 must-haves verified
re_verification:
  previous_status: human_needed
  previous_score: 9/9
  gaps_closed:
    - "RouterNode can route general SuperChat messages — agents/general-assistant/AGENT.md added; SubAgentRegistry auto-loads it; valid routing set now includes general-assistant"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Start docker compose up and verify GET /api/threads?app_id=chat returns only chat threads and GET /api/threads?app_id=superchat returns only superchat threads after sending messages in each mode"
    expected: "Each endpoint returns only threads belonging to the specified app; threads without checkpoints still appear due to LEFT JOIN"
    why_human: "Requires running PostgreSQL, Redis, and the full app stack — cannot verify DB migration outcomes or LEFT JOIN behavior without a live DB"
  - test: "Send a SuperChat message, then send another in the same thread — verify the second message has context from the first"
    expected: "OrchestratorGraph checkpointer preserves conversation history across turns for the same thread_id"
    why_human: "Requires a running Copilot SDK connection and two sequential API calls to verify stateful behavior"
  - test: "Send a general message in SuperChat (e.g. '今日の天気は？') after docker compose restart worker — verify the response is a natural AI answer, not '対応できるエージェントが見つかりませんでした。'"
    expected: "general-assistant agent handles the message and returns an AI-generated response"
    why_human: "Requires running worker service to load SubAgentRegistry from agents/ volume mount and invoke RouterNode with live LLM"
---

# Phase 10: SuperChat Thread Labels Mode Verification Report

**Phase Goal:** Chat と SuperChat をアプリケーション（モード）として捉え、アプリケーション＋ユーザーという単位でスレッドを分離・管理できるようにする。thread_labels を廃止し applications/threads/audit_log に刷新。GET /api/threads を LEFT JOIN + app_id フィルタ対応にし、OrchestratorGraph に checkpointer を接続して SuperChat の会話継続性を実現し、フロント useThreads をアプリ別対応にする。
**Verified:** 2026-04-04T05:00:00Z
**Status:** human_needed
**Re-verification:** Yes — third pass, after 10-06 gap closure (general-assistant agent addition). Previous score: 9/9 human_needed.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | applications table exists with 'chat' and 'superchat' rows | ✓ VERIFIED | `app/api/main.py` lifespan creates `CREATE TABLE IF NOT EXISTS applications` with seed INSERT for chat/superchat — regression check passed |
| 2 | threads table exists with app_id FK to applications | ✓ VERIFIED | `app/api/main.py` creates `CREATE TABLE IF NOT EXISTS threads` with `app_id TEXT NOT NULL REFERENCES applications(app_id)` — regression check passed |
| 3 | audit_log table exists with indexes (no write logic) | ✓ VERIFIED | `app/api/main.py` creates audit_log + two indexes; no `INSERT INTO audit_log` anywhere in `app/` — regression check passed |
| 4 | thread_labels table is dropped | ✓ VERIFIED | `DROP TABLE IF EXISTS thread_labels` in `app/api/main.py`; zero references in `app/api/routes/chat.py` — regression check passed |
| 5 | GET /api/threads with app_id filter returns only matching app threads; without filter returns all | ✓ VERIFIED | `app/api/routes/chat.py` `list_threads()` has two SQL branches — with `AND t.app_id = %s` when provided, without when not — regression check passed |
| 6 | Threads without checkpoints appear in GET /api/threads | ✓ VERIFIED | Both SQL branches use `LEFT JOIN checkpoints c ON t.thread_id = c.thread_id AND c.checkpoint_ns = ''` — regression check passed |
| 7 | POST /api/chat upserts app_id into threads table | ✓ VERIFIED | `send_message()` computes `app_id = "superchat" if body.mode == "super" else "chat"` then `INSERT INTO threads ... ON CONFLICT DO UPDATE` preserving app_id — regression check passed |
| 8 | OrchestratorGraph is compiled with a checkpointer and thread_id config | ✓ VERIFIED | `orchestrator_handler.py` uses `async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:`, passes `checkpointer=checkpointer` to `build_orchestrator_graph`, invokes with `config={"configurable": {"thread_id": thread_id}}` — regression check passed |
| 9 | Frontend: ChatApp passes 'chat', SuperChatApp passes 'superchat', useThreads passes appId to listThreads | ✓ VERIFIED | `ChatApp.tsx` calls `useThreads('chat')`. `SuperChatApp.tsx` calls `useThreads('superchat')`. `useThreads.ts` passes `appId` to `listThreads(appId)` with `[appId]` dependency — regression check passed |
| 10 | RouterNode can route general SuperChat messages to an AI agent (not fallback) | ✓ VERIFIED | `agents/general-assistant/AGENT.md` exists with `name: general-assistant`, `model: claude-sonnet-4-6`, non-empty description and system_prompt. `SubAgentRegistry` globs `**/AGENT.md` and builds `valid = {a.name for a in agents}` — general-assistant is now in the valid set. Committed at `0085f02`. GAP CLOSED. |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/api/main.py` | DROP thread_labels, CREATE applications/threads/audit_log with seed | ✓ VERIFIED | All DDL statements present; idempotent IF NOT EXISTS; commit called |
| `app/api/routes/chat.py` | LEFT JOIN + app_id filter; threads upsert with app_id | ✓ VERIFIED | LEFT JOIN on both code paths; `INSERT INTO threads` with app_id; delete/rename use threads |
| `app/api/models.py` | ThreadInfo with optional app_id field | ✓ VERIFIED | `app_id: str | None = None` present |
| `app/orchestrator/graph.py` | build_orchestrator_graph with optional checkpointer param | ✓ VERIFIED | Signature `(registry, github_token, checkpointer=None)` with `graph.compile(checkpointer=checkpointer)` |
| `app/jobs/handlers/orchestrator_handler.py` | AsyncPostgresSaver usage + thread_id config in ainvoke | ✓ VERIFIED | Import present; `async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:`; config wired |
| `frontend/src/api/client.ts` | listThreads(appId?) with ?app_id= query param | ✓ VERIFIED | `listThreads = (appId?: string) => apiFetch(...?app_id=...)` |
| `frontend/src/hooks/useThreads.ts` | useThreads(appId?) passing appId to listThreads | ✓ VERIFIED | Signature + dependency array + call verified |
| `frontend/src/components/ChatApp.tsx` | useThreads('chat') call | ✓ VERIFIED | Line 33 |
| `frontend/src/components/SuperChatApp.tsx` | useThreads('superchat') call | ✓ VERIFIED | Line 118 |
| `frontend/src/types.ts` | ThreadInfo with app_id?: string | ✓ VERIFIED | `app_id?: string;` present |
| `tests/test_api_chat.py` | Phase 10 test scaffolds for new schema behaviors | ✓ VERIFIED | 4 active tests using threads table and ?app_id=; no skip markers |
| `tests/test_worker.py` | Active test for OrchestratorHandler with checkpointer | ✓ VERIFIED | `test_orchestrator_handler_uses_checkpointer` has no `@pytest.mark.skip` |
| `agents/general-assistant/AGENT.md` | Catch-all agent: name=general-assistant, description, system_prompt | ✓ VERIFIED | File exists at `agents/general-assistant/AGENT.md`; `name: general-assistant`; `model: claude-sonnet-4-6`; description is catch-all; system_prompt non-empty. Commit `0085f02`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/api/main.py` lifespan | PostgreSQL | inline migration DDL | ✓ WIRED | `psycopg.AsyncConnection.connect(DB_URI)` executes all DDL statements + `conn.commit()` |
| `app/api/routes/chat.py list_threads()` | threads table | LEFT JOIN query with optional app_id WHERE | ✓ WIRED | Two SQL branches, both `FROM threads t LEFT JOIN checkpoints c` |
| `app/api/routes/chat.py send_message()` | threads table | INSERT INTO threads with app_id | ✓ WIRED | `INSERT INTO threads (thread_id, app_id, ...)` with `ON CONFLICT DO UPDATE` |
| `app/jobs/handlers/orchestrator_handler.py` | `app/orchestrator/graph.py` | `checkpointer=` keyword argument | ✓ WIRED | `build_orchestrator_graph(registry, github_token, checkpointer=checkpointer)` |
| `app/jobs/handlers/orchestrator_handler.py` | LangGraph checkpointer | AsyncPostgresSaver.from_conn_string context manager | ✓ WIRED | `async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:` + `await checkpointer.setup()` |
| `frontend/src/hooks/useThreads.ts` | `frontend/src/api/client.ts` | `listThreads(appId)` call | ✓ WIRED | `listThreads(appId)` inside `refreshThreads` useCallback |
| `frontend/src/components/ChatApp.tsx` | `frontend/src/hooks/useThreads.ts` | `useThreads('chat')` | ✓ WIRED | Verified at line 33 |
| `frontend/src/components/SuperChatApp.tsx` | `frontend/src/hooks/useThreads.ts` | `useThreads('superchat')` | ✓ WIRED | Verified at line 118 |
| `frontend/src/types.ts` | `frontend/src/hooks/useThreads.ts` | `ThreadInfo` type contract | ✓ WIRED | `ThreadInfo` includes `app_id?: string`; matches backend `models.py` |
| `agents/general-assistant/AGENT.md` | `app/orchestrator/agent.py SubAgentRegistry` | glob `**/AGENT.md` auto-discovery | ✓ WIRED | `SubAgentRegistry.__init__` globs `Path(agent_dir).glob("**/AGENT.md")`; `general-assistant/AGENT.md` is in scope; `agent.name` is added to `valid` set used by `RouterNode` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `list_threads()` route | threads list | `SELECT FROM threads t LEFT JOIN checkpoints c WHERE github_login = %s` | Yes — parameterized query against real DB | ✓ FLOWING |
| `send_message()` route | app_id | `"superchat" if body.mode == "super" else "chat"` then inserted into threads | Yes — computed from request body | ✓ FLOWING |
| `OrchestratorHandler.handle()` | result["output"] | `graph.ainvoke(initial, config=config)` with checkpointer | Yes — LangGraph invocation with real checkpointer | ✓ FLOWING |
| `useThreads` hook | threads state | `listThreads(appId)` → `GET /api/threads?app_id=...` | Yes — API call with query param forwarded | ✓ FLOWING |
| `RouterNode.__call__()` | `chosen` agent name | `registry.all()` → `valid = {a.name for a in agents}`; general-assistant now in valid set | Yes — agent name resolved from registry; general-assistant is a real agent node | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Evidence | Status |
|----------|----------|--------|
| Migration DDL present in main.py | `grep -c "CREATE TABLE IF NOT EXISTS applications" app/api/main.py` = 1 | ✓ PASS |
| LEFT JOIN present in list_threads | `grep -c "LEFT JOIN checkpoints" app/api/routes/chat.py` = 2 (both branches) | ✓ PASS |
| No INSERT INTO audit_log in production code | `grep -rn "INSERT INTO audit_log" app/` = 0 results | ✓ PASS |
| No thread_labels in production routes | `grep -c "thread_labels" app/api/routes/chat.py` = 0 | ✓ PASS |
| AsyncPostgresSaver wired in orchestrator_handler | `grep -c "AsyncPostgresSaver" app/jobs/handlers/orchestrator_handler.py` = 2 | ✓ PASS |
| app_id field in ThreadInfo | `grep "app_id" frontend/src/types.ts` = `app_id?: string;` | ✓ PASS |
| Phase 10 tests use threads not thread_labels | `grep "thread_labels" tests/test_api_chat.py` = 0 results | ✓ PASS |
| test_orchestrator_handler_uses_checkpointer is active | `grep "pytest.mark.skip" tests/test_worker.py` = 0 results | ✓ PASS |
| general-assistant AGENT.md exists with correct name | `grep "name:" agents/general-assistant/AGENT.md` = `name: general-assistant` | ✓ PASS (new — 10-06) |
| agents/ directory contains all 3 expected agents | `ls agents/` = code-reviewer, general-assistant, sql-analyst | ✓ PASS (new — 10-06) |
| general-assistant committed to git | `git show 0085f02 --stat` shows `agents/general-assistant/AGENT.md` added | ✓ PASS (new — 10-06) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| DB-01 | 10-01-PLAN.md | applications + threads tables replacing thread_labels | ✓ SATISFIED | `app/api/main.py` DROP thread_labels + CREATE applications/threads/audit_log |
| DB-02 | 10-01-PLAN.md | audit_log table with indexes | ✓ SATISFIED | `app/api/main.py` audit_log + two indexes |
| API-01 | 10-02-PLAN.md | GET /api/threads LEFT JOIN + optional app_id filter | ✓ SATISFIED | `app/api/routes/chat.py` list_threads() with LEFT JOIN and app_id WHERE branch |
| API-02 | 10-02-PLAN.md | GET /api/threads backward compat (no filter = all threads) | ✓ SATISFIED | No-filter SQL branch returns all threads |
| API-03 | 10-02-PLAN.md | POST /api/chat upserts app_id derived from mode field | ✓ SATISFIED | `app_id = "superchat" if body.mode == "super" else "chat"` + INSERT INTO threads |
| ORC-01 | 10-03-PLAN.md / 10-06-PLAN.md | OrchestratorGraph compiled with AsyncPostgresSaver checkpointer; RouterNode routes general messages | ✓ SATISFIED | `orchestrator_handler.py` wires AsyncPostgresSaver + thread_id config; `agents/general-assistant/AGENT.md` provides catch-all routing target |
| FE-01 | 10-04-PLAN.md | useThreads(appId?) passes appId to listThreads | ✓ SATISFIED | `useThreads.ts` + `client.ts` listThreads with ?app_id= param |
| FE-02 | 10-04-PLAN.md | ThreadInfo type includes app_id field | ✓ SATISFIED | `frontend/src/types.ts`: `app_id?: string` |

All 8 requirements satisfied.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | — |

No anti-patterns found. No stale placeholder comments, no empty implementations, no residual thread_labels references in production code.

---

### Human Verification Required

#### 1. App-isolated thread listing (live DB)

**Test:** Run `docker compose up`, send a chat message (mode=simple) and a superchat message (mode=super) in different threads, then call `GET /api/threads?app_id=chat` and `GET /api/threads?app_id=superchat`.
**Expected:** Each endpoint returns only threads belonging to the specified app. A newly created thread with no checkpoints yet should still appear (LEFT JOIN behavior).
**Why human:** Requires live PostgreSQL, Redis, and full app stack. DB migration idempotency and LEFT JOIN behavior can only be confirmed against a real database.

#### 2. SuperChat conversation continuity (live Copilot SDK)

**Test:** Send a SuperChat message establishing context (e.g., "My name is Taro"). In the same thread, send a second message ("What is my name?"). Verify the AI replies with "Taro".
**Expected:** OrchestratorGraph checkpointer preserves conversation history across turns via LangGraph thread_id.
**Why human:** Requires a running Copilot SDK connection and two sequential API calls against a real LangGraph checkpointer.

#### 3. SuperChat general message routing (live worker + LLM)

**Test:** After `docker compose restart worker`, send a general message in SuperChat (e.g. "今日の天気は？"). Verify the response is a natural AI-generated answer, not "対応できるエージェントが見つかりませんでした。".
**Expected:** `SubAgentRegistry` loads `general-assistant` from the volume-mounted `agents/` directory. `RouterNode` routes the message to `general-assistant`, which invokes `ChatCopilot` and returns a real answer.
**Why human:** Requires the worker service to be running with the `agents/` directory volume-mounted, and a live Copilot SDK connection to invoke the LLM.

---

### Re-verification Summary

**Gaps closed (1/1) — from 10-06 gap closure:**

1. **RouterNode general message routing (ORC-01 sub-gap)** — `agents/general-assistant/AGENT.md` added at commit `0085f02`. `SubAgentRegistry` auto-discovers it via glob. `RouterNode` builds `valid = {a.name for a in agents}` which now includes `general-assistant`. The fallback error string is no longer the only path for general messages.

**Regressions:** None. All 9 previously-passing truths re-confirmed through targeted grep checks. No code files modified — only a new agent definition file added.

**Overall status:** All automated checks pass. Phase 10 is fully implemented in code. Three items require human verification with a live stack: DB migration outcome, SuperChat conversation continuity, and general-message routing with the new general-assistant agent.

---

_Verified: 2026-04-04T05:00:00Z_
_Verifier: Claude (gsd-verifier) — re-verification after 10-06 gap closure (general-assistant agent)_
