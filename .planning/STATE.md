# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、スレッド維持付きのチャット UI から使えること
**Current focus:** Phase 1 — Auth + Provider Foundation

## Current Position

Phase: 1 of 3 (Auth + Provider Foundation)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-31 — Roadmap created, ready for Phase 1 planning

Progress: [░░░░░░░░░░] 0%

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

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: BaseChatModel wrapper required — Copilot SDK uses JSON-RPC, not OpenAI-compatible HTTP
- [Init]: Device Flow only — PAT auth is out of scope
- [Init]: SDK pinned to 0.2.0 exact — Technical Preview, isolate behind app/providers/copilot.py only
- [Research]: Pydantic v2 patterns required — use ConfigDict/PrivateAttr, not class Config

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 risk]: Copilot SDK send_and_wait exact API shape is unverified — validate against pinned 0.2.0 before finalizing _messages_to_prompt() serialization strategy
- [Phase 1 risk]: Device Flow CLIENT_ID (Iv1.b507a08c87ecfe98) is non-official use — validate still functional early

## Session Continuity

Last session: 2026-03-31
Stopped at: Roadmap created, STATE.md initialized
Resume file: None
