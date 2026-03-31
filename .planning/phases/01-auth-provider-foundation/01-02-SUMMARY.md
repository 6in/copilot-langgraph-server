---
phase: 01-auth-provider-foundation
plan: 02
subsystem: provider
tags: [langchain-core, github-copilot-sdk, basechatmodel, pydantic-v2, tdd, pytest]

# Dependency graph
requires:
  - 01-01 (pyproject.toml with langchain-core + github-copilot-sdk, CopilotAuthManager)
provides:
  - ChatCopilot(BaseChatModel) wrapping Copilot SDK send_and_wait()
  - 9 unit tests for PROV-01, PROV-02, PROV-03
affects:
  - 01-03 (FastAPI app imports ChatCopilot from app/providers/copilot.py)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pydantic v2: ConfigDict(arbitrary_types_allowed=True) + PrivateAttr(default=None)
    - async-only BaseChatModel: _generate raises NotImplementedError, only _agenerate implemented
    - Client lifecycle: lazy init in _ensure_client, error recovery resets _client to None
    - Module-level SDK import so unittest.mock.patch("app.providers.copilot.CopilotClient") works

key-files:
  created:
    - app/providers/copilot.py
    - tests/test_provider.py
  modified: []

key-decisions:
  - "SDK imports at module top-level (not lazy) so patch('app.providers.copilot.CopilotClient') works in tests"
  - "send_and_wait() used directly — confirmed available in SDK 0.2.0 by Plan 01"
  - "Error recovery: any exception in _agenerate stops and nulls _client before re-raising"

requirements-completed: [PROV-01, PROV-02, PROV-03]

# Metrics
duration: 5min
completed: 2026-03-31
---

# Phase 1 Plan 02: ChatCopilot Provider Summary

**BaseChatModel wrapper around Copilot SDK send_and_wait() — 9 TDD unit tests passing, full async lifecycle management with error recovery**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-31T07:28:00Z
- **Completed:** 2026-03-31T07:33:00Z
- **Tasks:** 1
- **Files modified:** 2 created

## Accomplishments

- `ChatCopilot(BaseChatModel)` implemented with Pydantic v2 patterns (ConfigDict + PrivateAttr)
- `_generate()` raises NotImplementedError ("async-only") — enforces correct usage
- `_agenerate()` creates Copilot session with `model=` kwarg, calls `send_and_wait()`, returns `ChatResult`
- `_ensure_client()` lazy-initialises `CopilotClient(SubprocessConfig(...))`, raises `ValueError` when no token source available
- `close()` stops client cleanly and resets `_client = None`
- Error recovery: any exception in `_agenerate` calls `client.stop()` and resets `_client` before re-raising
- 9 unit tests written RED-first (all failing), then GREEN after implementation — 9/9 passing
- Full test suite (18 tests: 9 auth + 9 provider) passes without regressions

## Task Commits

1. **Task 1: Implement ChatCopilot provider with BaseChatModel interface (TDD)** — `7e3b156` (feat)

## Files Created/Modified

- `app/providers/copilot.py` — ChatCopilot: BaseChatModel wrapper, 145 lines
- `tests/test_provider.py` — 9 unit tests for PROV-01, PROV-02, PROV-03, 195 lines

## Decisions Made

- SDK imports placed at **module top-level** (not inside methods) so `unittest.mock.patch("app.providers.copilot.CopilotClient")` intercepts at import time — lazy imports would require patching inside `_ensure_client` which is more fragile
- `send_and_wait()` used directly — no event-listener fallback — confirmed by Plan 01 SDK verification
- Error recovery resets `_client = None` unconditionally: on any exception the client is stopped (best-effort) and cleared so the next call gets a fresh client

## Deviations from Plan

None — plan executed exactly as written. TDD RED → GREEN completed in one pass.

## Known Stubs

None. `ChatCopilot` is fully wired: `_agenerate` calls real SDK session methods. All tests mock the SDK — there are no hardcoded placeholder values in production code paths.

---
*Phase: 01-auth-provider-foundation*
*Completed: 2026-03-31*

## Self-Check: PASSED

All files verified present. Task commit verified in git log.
- FOUND: app/providers/copilot.py, tests/test_provider.py, 01-02-SUMMARY.md
- FOUND commit: 7e3b156
