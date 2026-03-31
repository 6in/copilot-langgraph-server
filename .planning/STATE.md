---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 03-web-chat-ui 03-03-PLAN.md
last_updated: "2026-03-31T16:53:40.620Z"
last_activity: 2026-03-31
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 9
  completed_plans: 8
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、スレッド維持付きのチャット UI から使えること
**Current focus:** Phase 03 — web-chat-ui

## Current Position

Phase: 03 (web-chat-ui) — EXECUTING
Plan: 3 of 4
Status: Ready to execute
Last activity: 2026-03-31

Progress: [██████░░░░] 67%

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

### Pending Todos

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260331-uy2 | Fix Copilot SDK send_and_wait API: pass prompt string directly instead of dict | 2026-03-31 | 2ce10e7 | [260331-uy2-fix-copilot-sdk-send-and-wait-api-pass-p](.planning/quick/260331-uy2-fix-copilot-sdk-send-and-wait-api-pass-p/) |

### Blockers/Concerns

- [Phase 1 risk]: Device Flow CLIENT_ID (Iv1.b507a08c87ecfe98) is non-official use — validate still functional early

## Session Continuity

Last session: 2026-03-31T16:53:40.618Z
Stopped at: Completed 03-web-chat-ui 03-03-PLAN.md
Resume file: None
