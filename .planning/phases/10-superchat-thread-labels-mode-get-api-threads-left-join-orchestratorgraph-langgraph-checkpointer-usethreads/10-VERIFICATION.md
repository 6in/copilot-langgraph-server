---
phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads
verified: 2026-04-04T01:00:00Z
status: human_needed
score: 9/9 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 7/9
  gaps_closed:
    - "ThreadInfo type includes optional app_id field — app_id?: string added to frontend/src/types.ts line 41"
    - "Test scaffolds exist for all Phase 10 behaviors — Phase 10 tests in test_api_chat.py fully rewritten to use threads table and ?app_id= param with no @pytest.mark.skip; test_orchestrator_handler_uses_checkpointer skip marker removed"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Start docker compose up and verify GET /api/threads?app_id=chat returns only chat threads and GET /api/threads?app_id=superchat returns only superchat threads after sending messages in each mode"
    expected: "Each endpoint returns only threads belonging to the specified app; threads without checkpoints still appear due to LEFT JOIN"
    why_human: "Requires running PostgreSQL, Redis, and the full app stack — cannot verify DB migration outcomes or LEFT JOIN behavior without a live DB"
  - test: "Send a SuperChat message, then send another in the same thread — verify the second message has context from the first"
    expected: "OrchestratorGraph checkpointer preserves conversation history across turns for the same thread_id"
    why_human: "Requires a running Copilot SDK connection and two sequential API calls to verify stateful behavior"
---

# Phase 10: SuperChat Thread Labels Mode Verification Report

**Phase Goal:** Chat と SuperChat をアプリケーション（モード）として捉え、アプリケーション＋ユーザーという単位でスレッドを分離・管理できるようにする。thread_labels を廃止し applications/threads/audit_log に刷新。GET /api/threads を LEFT JOIN + app_id フィルタ対応にし、OrchestratorGraph に checkpointer を接続して SuperChat の会話継続性を実現し、フロント useThreads をアプリ別対応にする。
**Verified:** 2026-04-04T01:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (previous score: 7/9, previous status: gaps_found)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | applications table exists with 'chat' and 'superchat' rows | ✓ VERIFIED | `app/api/main.py` lifespan creates `CREATE TABLE IF NOT EXISTS applications` with seed INSERT for chat/superchat — regression check passed |
| 2 | threads table exists with app_id FK to applications | ✓ VERIFIED | `app/api/main.py` creates `CREATE TABLE IF NOT EXISTS threads` with `app_id TEXT NOT NULL REFERENCES applications(app_id)` (line 78) — regression check passed |
| 3 | audit_log table exists with indexes (no write logic) | ✓ VERIFIED | `app/api/main.py` creates audit_log + two indexes; no `INSERT INTO audit_log` anywhere in `app/` — regression check passed |
| 4 | thread_labels table is dropped | ✓ VERIFIED | `DROP TABLE IF EXISTS thread_labels` at line 54 of `app/api/main.py` — regression check passed |
| 5 | GET /api/threads with app_id filter returns only matching app threads; without filter returns all | ✓ VERIFIED | `app/api/routes/chat.py` `list_threads()` has two SQL branches — with `AND t.app_id = %s` when provided, without when not — regression check passed |
| 6 | Threads without checkpoints appear in GET /api/threads | ✓ VERIFIED | Both SQL branches use `LEFT JOIN checkpoints c ON t.thread_id = c.thread_id AND c.checkpoint_ns = ''` — regression check passed |
| 7 | POST /api/chat upserts app_id into threads table | ✓ VERIFIED | `send_message()` computes `app_id = "superchat" if body.mode == "super" else "chat"` then `INSERT INTO threads ... ON CONFLICT DO UPDATE` preserving app_id — regression check passed |
| 8 | OrchestratorGraph is compiled with a checkpointer and thread_id config | ✓ VERIFIED | `orchestrator_handler.py` uses `async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:`, passes `checkpointer=checkpointer` to `build_orchestrator_graph`, invokes with `config={"configurable": {"thread_id": thread_id}}` — regression check passed |
| 9 | Frontend: ChatApp passes 'chat', SuperChatApp passes 'superchat', useThreads passes appId to listThreads | ✓ VERIFIED | `ChatApp.tsx` calls `useThreads('chat')`. `SuperChatApp.tsx` calls `useThreads('superchat')`. `useThreads.ts` passes `appId` to `listThreads(appId)` with `[appId]` dependency — regression check passed |
| 10 | ThreadInfo type includes optional app_id field | ✓ VERIFIED | `frontend/src/types.ts` line 41: `app_id?: string;` now present in `ThreadInfo` interface. GAP CLOSED — backend `app/api/models.py` and frontend type are now in sync. |
| 11 | Test scaffolds exist for all Phase 10 behaviors | ✓ VERIFIED | `tests/test_api_chat.py` lines 105-280: 4 active (non-skipped) tests using `threads` table and `?app_id=` param — `test_list_threads_app_id_filter`, `test_list_threads_no_app_id_returns_all`, `test_chat_upsert_app_id`, `test_list_threads_left_join`. No `thread_labels` or `?mode=` references. `tests/test_worker.py` `test_orchestrator_handler_uses_checkpointer` at line 159 has no `@pytest.mark.skip`. GAP CLOSED. |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/api/main.py` | DROP thread_labels, CREATE applications/threads/audit_log with seed | ✓ VERIFIED | All 6 SQL statements present; idempotent IF NOT EXISTS; commit called |
| `app/api/routes/chat.py` | LEFT JOIN + app_id filter; threads upsert with app_id | ✓ VERIFIED | LEFT JOIN on both code paths; `INSERT INTO threads` with app_id; delete/rename use threads |
| `app/api/models.py` | ThreadInfo with optional app_id field | ✓ VERIFIED | `app_id: str | None = None` present |
| `app/orchestrator/graph.py` | build_orchestrator_graph with optional checkpointer param | ✓ VERIFIED | Signature `(registry, github_token, checkpointer=None)` with `graph.compile(checkpointer=checkpointer)` |
| `app/jobs/handlers/orchestrator_handler.py` | AsyncPostgresSaver usage + thread_id config in ainvoke | ✓ VERIFIED | Import at line 5; `async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:`; config wired |
| `frontend/src/api/client.ts` | listThreads(appId?) with ?app_id= query param | ✓ VERIFIED | `listThreads = (appId?: string) => apiFetch(...?app_id=...)` |
| `frontend/src/hooks/useThreads.ts` | useThreads(appId?) passing appId to listThreads | ✓ VERIFIED | Signature + dependency array + call verified |
| `frontend/src/components/ChatApp.tsx` | useThreads('chat') call | ✓ VERIFIED | Line 33 |
| `frontend/src/components/SuperChatApp.tsx` | useThreads('superchat') call | ✓ VERIFIED | Line 118 |
| `frontend/src/types.ts` | ThreadInfo with app_id?: string | ✓ VERIFIED | Line 41 — was MISSING, now FIXED |
| `tests/test_api_chat.py` | Phase 10 test scaffolds for new schema behaviors | ✓ VERIFIED | 4 active tests at lines 105-280 using threads table and ?app_id=; no skip markers — was STUB, now FIXED |
| `tests/test_worker.py` | Active test for OrchestratorHandler with checkpointer | ✓ VERIFIED | `test_orchestrator_handler_uses_checkpointer` at line 159, no skip marker — was SKIPPED, now ACTIVE |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/api/main.py` lifespan | PostgreSQL | inline migration DDL | ✓ WIRED | `psycopg.AsyncConnection.connect(DB_URI)` executes all 7 DDL statements + `conn.commit()` |
| `app/api/routes/chat.py list_threads()` | threads table | LEFT JOIN query with optional app_id WHERE | ✓ WIRED | Two SQL branches, both `FROM threads t LEFT JOIN checkpoints c` |
| `app/api/routes/chat.py send_message()` | threads table | INSERT INTO threads with app_id | ✓ WIRED | `INSERT INTO threads (thread_id, app_id, ...)` with `ON CONFLICT DO UPDATE` preserving app_id |
| `app/jobs/handlers/orchestrator_handler.py` | `app/orchestrator/graph.py` | `checkpointer=` keyword argument | ✓ WIRED | `build_orchestrator_graph(registry, github_token, checkpointer=checkpointer)` |
| `app/jobs/handlers/orchestrator_handler.py` | LangGraph checkpointer | AsyncPostgresSaver.from_conn_string context manager | ✓ WIRED | `async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:` + `await checkpointer.setup()` |
| `frontend/src/hooks/useThreads.ts` | `frontend/src/api/client.ts` | `listThreads(appId)` call | ✓ WIRED | `listThreads(appId)` inside `refreshThreads` useCallback |
| `frontend/src/components/ChatApp.tsx` | `frontend/src/hooks/useThreads.ts` | `useThreads('chat')` | ✓ WIRED | Verified at line 33 |
| `frontend/src/components/SuperChatApp.tsx` | `frontend/src/hooks/useThreads.ts` | `useThreads('superchat')` | ✓ WIRED | Verified at line 118 |
| `frontend/src/types.ts` | `frontend/src/hooks/useThreads.ts` | `ThreadInfo` type contract | ✓ WIRED | `ThreadInfo` now includes `app_id?: string`; type contract matches backend `models.py` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `list_threads()` route | threads list | `SELECT FROM threads t LEFT JOIN checkpoints c WHERE github_login = %s` | Yes — parameterized query against real DB | ✓ FLOWING |
| `send_message()` route | app_id | `"superchat" if body.mode == "super" else "chat"` then inserted into threads | Yes — computed from request body | ✓ FLOWING |
| `OrchestratorHandler.handle()` | result["output"] | `graph.ainvoke(initial, config=config)` with checkpointer | Yes — LangGraph invocation with real checkpointer | ✓ FLOWING |
| `useThreads` hook | threads state | `listThreads(appId)` → `GET /api/threads?app_id=...` | Yes — API call with query param forwarded | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Evidence | Status |
|----------|----------|--------|
| Migration DDL present in main.py | `grep -c "CREATE TABLE IF NOT EXISTS applications" app/api/main.py` = 1 | ✓ PASS |
| LEFT JOIN present in list_threads | `grep -c "LEFT JOIN checkpoints" app/api/routes/chat.py` = 2 (both branches) | ✓ PASS |
| No INSERT INTO audit_log in production code | `grep -rn "INSERT INTO audit_log" app/` = 0 results | ✓ PASS |
| No thread_labels in production routes | `grep -c "thread_labels" app/api/routes/chat.py` = 0 | ✓ PASS |
| AsyncPostgresSaver wired in orchestrator_handler | `grep -c "AsyncPostgresSaver" app/jobs/handlers/orchestrator_handler.py` = 2 | ✓ PASS |
| app_id field in ThreadInfo | `grep "app_id" frontend/src/types.ts` — line 41: `app_id?: string;` | ✓ PASS (was FAIL) |
| Phase 10 tests use threads not thread_labels | `grep "thread_labels" tests/test_api_chat.py` = 0 results | ✓ PASS (was FAIL) |
| test_orchestrator_handler_uses_checkpointer is active | `grep "pytest.mark.skip" tests/test_worker.py` = 0 results | ✓ PASS (was FAIL) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| DB-01 | 10-01-PLAN.md | applications + threads tables replacing thread_labels | ✓ SATISFIED | `app/api/main.py` DROP thread_labels + CREATE applications/threads/audit_log |
| DB-02 | 10-01-PLAN.md | audit_log table with indexes | ✓ SATISFIED | `app/api/main.py` audit_log + two indexes |
| API-01 | 10-02-PLAN.md | GET /api/threads LEFT JOIN + optional app_id filter | ✓ SATISFIED | `app/api/routes/chat.py` list_threads() with LEFT JOIN and app_id WHERE branch |
| API-02 | 10-02-PLAN.md | GET /api/threads backward compat (no filter = all threads) | ✓ SATISFIED | No-filter SQL branch returns all threads; test_list_threads_no_app_id_returns_all confirms |
| API-03 | 10-02-PLAN.md | POST /api/chat upserts app_id derived from mode field | ✓ SATISFIED | `app_id = "superchat" if body.mode == "super" else "chat"` + INSERT INTO threads |
| ORC-01 | 10-03-PLAN.md | OrchestratorGraph compiled with AsyncPostgresSaver checkpointer | ✓ SATISFIED | `orchestrator_handler.py` wires AsyncPostgresSaver + thread_id config |
| FE-01 | 10-04-PLAN.md | useThreads(appId?) passes appId to listThreads | ✓ SATISFIED | `useThreads.ts` + `client.ts` listThreads with ?app_id= param |
| FE-02 | 10-04-PLAN.md | ThreadInfo type includes app_id field | ✓ SATISFIED | `frontend/src/types.ts` line 41: `app_id?: string` |

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

---

### Re-verification Summary

**Gaps closed (2/2):**

1. **ThreadInfo app_id field** — `frontend/src/types.ts` line 41 now has `app_id?: string` in the `ThreadInfo` interface. Backend `app/api/models.py` and frontend type are in sync.

2. **Phase 10 test scaffolds** — `tests/test_api_chat.py` Phase 10 section (lines 105-280) fully rewritten with 4 active tests that correctly reference the `threads` table and `?app_id=` query param. No stale `thread_labels` references or `?mode=` params remain. `tests/test_worker.py` `test_orchestrator_handler_uses_checkpointer` is no longer skipped and verifies both checkpointer wiring and thread_id config propagation.

**Regressions:** None. All 9 originally-passing truths re-confirmed through targeted grep checks.

**Overall status:** All automated checks pass. Phase goal is fully implemented in code. Two items require human verification with a live stack (DB migration outcome, SuperChat conversation continuity).

---

_Verified: 2026-04-04T01:00:00Z_
_Verifier: Claude (gsd-verifier) — re-verification after gap closure_
