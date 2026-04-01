---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: TBD
status: milestone_complete
stopped_at: Completed v1.0 milestone
last_updated: "2026-04-02T15:37:56.000Z"
last_activity: 2026-04-02
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-02 after v1.0)

**Core value:** Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、スレッド維持付きのチャット UI から使えること
**Current focus:** Planning next milestone (v2.0) — run `/gsd:new-milestone`

## Current Position

Milestone v1.0 shipped 2026-04-02. All 6 phases complete.
Ready to plan next milestone.

Progress: [██████████] 100% (v1.0 complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: -

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P02 | 5min | 1 tasks | 2 files |
| Phase 01 P03 | 2min | 2 tasks | 1 files |
| Phase 02-graph-layer P01 | 7min | 2 tasks | 5 files |
| Phase 02-graph-layer P02 | 1min | 1 tasks | 1 files |
| Phase 03-web-chat-ui P01 | 2min | 3 tasks | 8 files |
| Phase 03-web-chat-ui P02 | 3min | 3 tasks | 8 files |
| Phase 03-web-chat-ui P03 | 3min | 2 tasks | 3 files |
| Phase 03-web-chat-ui P04 | 2min | 1 tasks | 0 files |
| Phase 04-sse-redis-worker-jobstore-notifier P01 | 12min | 2 tasks | 10 files |
| Phase 04-sse-redis-worker-jobstore-notifier P02 | 2min | 1 tasks | 7 files |
| Phase 04-sse-redis-worker-jobstore-notifier P03 | 8min | 2 tasks | 8 files |
| Phase 04-sse-redis-worker-jobstore-notifier P04 | 1min | 1 tasks | 1 files |
| Phase 05-github-api-me-ui P02 | 3min | 2 tasks | 2 files |
| Phase 06-sqlite-postgresql-checkpointer P02 | 2min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: BaseChatModel wrapper required — Copilot SDK uses JSON-RPC, not OpenAI-compatible HTTP
- [Init]: Device Flow only — PAT auth is out of scope
- [Init]: SDK pinned to 0.2.0 exact — Technical Preview, isolate behind app/providers/copilot.py only
- [Research]: Pydantic v2 patterns required — use ConfigDict/PrivateAttr, not class Config
- [Phase 01]: SDK imports at module top-level in app/providers/copilot.py so unittest.mock.patch works at import time
- [Phase 01]: send_and_wait() used directly in _agenerate — no event-listener fallback (confirmed SDK 0.2.0)
- [Phase 01]: Error recovery in _agenerate: any exception stops and nulls _client before re-raising
- [Phase 01]: E2E script uses ainvoke() public interface not _agenerate() — tests full LangChain dispatch path
- [Phase 01]: close() in finally block is unconditional — guarantees CopilotClient subprocess terminates on success and error
- [Phase 02-graph-layer]: build_graph(llm, checkpointer) factory: compile once at startup, checkpointer lifecycle owned by caller
- [Phase 02-graph-layer]: ToolNode extension point documented in docstring, not as dead code — clean separation of v1 and v2 concerns
- [Phase 02-graph-layer]: MemorySaver sufficient for single-run validation scripts — caller-owned checkpointer pattern means tests pick the right impl
- [Phase 03-web-chat-ui]: start_device_flow/check_device_flow split: web routes cannot use blocking device_login() — initiate + single-poll split for web compatibility
- [Phase 03-web-chat-ui]: check_device_flow() calls save_token() on success to persist token before returning to caller
- [Phase 03-web-chat-ui]: API models in app/api/models.py; test stubs define mock contract now, full HTTP assertions in Plan 02
- [Phase 03-web-chat-ui]: device_flows dict uses 'current' key — single-user app, one active Device Flow at a time
- [Phase 03-web-chat-ui]: app.state.auth_expired flag: chat route sets on SDK auth errors, auth/status route reads — decoupled detection from surfacing
- [Phase 03-web-chat-ui]: ASGITransport in tests bypasses lifespan — inject mocks directly into app.state fields
- [Phase 03-web-chat-ui]: marked.js UMD globals via globalThis.marked.Marked — CDN UMD builds expose this path in v17
- [Phase 03-web-chat-ui]: XSS boundary enforced in appendMessage(): user textContent, AI innerHTML+prose
- [Phase 03-web-chat-ui]: Input lockout in sendMessage(): disabled in try, re-enabled in finally — guarantees unlock on error
- [Phase 03-web-chat-ui]: Auto-approved checkpoint: user pre-approved visual verification, automated tests (36 pass) confirm functional correctness
- [Quick 260401-lkq]: JWT HS256 with secret from env var or ~/.copilot_sdk/.jwt_secret — zero-config for local use
- [Quick 260401-lkq]: device_flows keyed by uuid4().hex flow_id: multi-user capable, replaces single "current" key
- [Quick 260401-lkq]: In-memory JTI blocklist: clears on restart, no Redis dependency — acceptable for personal tool
- [Quick 260401-lkq]: Per-request github_token injection via llm.close() on token change — safe for sequential personal tool use
- [Quick 260401-lkq]: Thread CRUD routes intentionally unprotected: local SQLite, personal tool, no auth value
- [Phase 04-sse-redis-worker-jobstore-notifier]: redis[asyncio]>=4.2.0 not >=7.0: arq 0.27.0 pins redis[hiredis]<6; redis 5.3.1 resolves with full asyncio support
- [Phase 04-sse-redis-worker-jobstore-notifier]: build_notifier(reply_to, job_store) takes job_store as arg: avoids module-level singleton, testable
- [Phase 04-sse-redis-worker-jobstore-notifier]: Wave 0 stubs: pytest.mark.skip with plan reference so CI tracks future test intent
- [Phase 04-sse-redis-worker-jobstore-notifier]: save_result BEFORE notifier.done in process_chat — guarantees SSE client can fetch result on done signal
- [Phase 04-sse-redis-worker-jobstore-notifier]: arq WorkerSettings job_timeout=300 — 5 minutes matches Copilot SDK send_and_wait timeout
- [Phase 04-sse-redis-worker-jobstore-notifier]: POST /api/chat enqueues via arq.enqueue_job, returns ChatAsyncResponse(job_id, thread_id) immediately — gateway no longer blocks on LangGraph execution
- [Phase 04-sse-redis-worker-jobstore-notifier]: SSE immediate-done check: job_store.get() before queue registration handles reload/reconnect (ASYNC-06)
- [Phase 04-sse-redis-worker-jobstore-notifier]: sendMessage() async flow: POST gets job_id, EventSource for done signal, result from GET /api/job/{id}, polling fallback on SSE disconnect
- [Phase 05-github-api-me-ui]: loadUserInfo() called without await — non-blocking so 'Authenticated' text shows immediately while avatar loads
- [Phase 05-github-api-me-ui]: login rendered via textContent, not innerHTML — enforces XSS prevention convention from project
- [Phase 06-sqlite-postgresql-checkpointer]: AsyncMock() used for checkpointer in conftest — MagicMock() does not support await on adelete_thread
- [Phase 06-sqlite-postgresql-checkpointer]: test_delete_thread_calls_adelete does NOT manually reassign adelete_thread — AsyncMock auto-creates awaitable children; manual reassignment masks regressions

### Roadmap Evolution

- Phase 4 added: 非同期ジョブキュー + SSE ストリーミング移行（Redis Worker / JobStore / Notifier パターン）
- Phase 5 added: GitHubユーザー情報取得＆ヘッダー表示（/api/me エンドポイント追加 + UI）
- Phase 6 added: SQLiteからPostgreSQLへのCheckpointer移行（langgraph-checkpoint-postgres + Docker Compose）
- Phase 7 added: React製チャットUI — chat-ui-kit-react + Vite + Bun で frontend/ ディレクトリに独立モジュールとして実装し、既存 Vanilla JS版と並存

### Pending Todos

- 今回の仕組みの説明資料をPowerPointで作成する — docs
- React製チャットUIの分離 — chat-ui-kit-react + Vite + Bun — ui

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260331-uy2 | Fix Copilot SDK send_and_wait API: pass prompt string directly instead of dict | 2026-03-31 | 2ce10e7 | [260331-uy2-fix-copilot-sdk-send-and-wait-api-pass-p](.planning/quick/260331-uy2-fix-copilot-sdk-send-and-wait-api-pass-p/) |
| 260401-f4x | Update .gitignore: add data/, .claude/, IDE/tool caches, SQLite, env files | 2026-04-01 | 6ed3d26 | [260401-f4x-gitignore](.planning/quick/260401-f4x-gitignore/) |
| 260401-fwh | Enable SDK tools: PermissionHandler.approve_all + remove SystemMessage workaround | 2026-04-01 | 32fa1a3 | [260401-fwh-option-a](.planning/quick/260401-fwh-option-a/) |
| 260401-h36 | Fix re-auth after logout without server restart: reset ChatCopilot client + update UX | 2026-04-01 | 1b4bf70 | [260401-h36-fix-re-auth-after-logout-without-server-](.planning/quick/260401-h36-fix-re-auth-after-logout-without-server-/) |
| 260401-lkq | Migrate to per-user JWT auth: Device Flow issues JWT cookie, blocklist logout, JWT-protected chat route | 2026-04-01 | 13c5b86 | [260401-lkq-jwt](.planning/quick/260401-lkq-jwt/) |
| 260401-stv | Enable pgvector in postgres container: switch to pgvector/pgvector:pg17 image + initdb script | 2026-04-01 | 818f9d3 | [260401-stv-rag-pgvector](.planning/quick/260401-stv-rag-pgvector/) |
| 260401-t47 | Add loadThreads() at all 3 job completion points so sidebar refreshes after new thread creation | 2026-04-01 | 6a3ab24 | [260401-t47-add-loadthreads-after-job-completion-to-](.planning/quick/260401-t47-add-loadthreads-after-job-completion-to-/) |

### Blockers/Concerns

- [Phase 1 risk]: Device Flow CLIENT_ID (Iv1.b507a08c87ecfe98) is non-official use — validate still functional early

## Session Continuity

Last session: 2026-04-01T11:20:11.000Z
Stopped at: Completed quick 260401-t47-PLAN.md
Resume file: None
