---
phase: 01-auth-provider-foundation
plan: 01
subsystem: auth
tags: [github-copilot-sdk, fernet, cryptography, device-flow, httpx, pytest, pyproject, uv]

# Dependency graph
requires: []
provides:
  - pyproject.toml with all Phase 1 dependencies (langchain-core, github-copilot-sdk==0.2.0, cryptography, httpx)
  - CopilotAuthManager with Device Flow OAuth and Fernet token encryption
  - 9 unit tests covering all auth scenarios with mocked httpx
  - uv.lock for reproducible installs
  - SDK 0.2.0 verified: send_and_wait=True, SubprocessConfig available
affects:
  - 01-02 (ChatCopilot provider uses CopilotAuthManager.get_token())
  - 01-03 (FastAPI app imports from app/auth/manager.py)

# Tech tracking
tech-stack:
  added:
    - github-copilot-sdk==0.2.0
    - langchain-core>=0.3.0
    - cryptography>=46.0.0 (Fernet encryption)
    - httpx>=0.28.0 (async HTTP for Device Flow)
    - pytest>=8.0 + pytest-asyncio>=0.25 (dev)
    - hatchling (build backend)
    - uv 0.8.4 (dependency management)
  patterns:
    - Fernet symmetric encryption with per-install key file at token_path.parent/.enc_key (0o600)
    - Env var override (COPILOT_TOKEN_ENC_KEY) for CI/container deployments
    - Sleep-before-POST polling loop (prevents slow_down feedback loop, Pitfall 7)
    - load_token() returns None on any error — never raises

key-files:
  created:
    - pyproject.toml
    - .gitignore
    - uv.lock
    - app/__init__.py
    - app/auth/__init__.py
    - app/providers/__init__.py
    - app/auth/manager.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_auth.py
  modified: []

key-decisions:
  - "hatchling build target set to packages=['app'] — worktree dir name doesn't match project name so auto-discovery fails"
  - "SDK 0.2.0 send_and_wait=True confirmed — Plan 02 can use send_and_wait() pattern directly, no event-listener fallback needed"
  - "Token polling loop sleeps BEFORE POST to prevent slow_down feedback loop (Pitfall 7 from research doc)"
  - "load_token() swallows all exceptions and returns None — callers must not rely on it raising"

patterns-established:
  - "Rule 3 auto-fix: hatchling packages=['app'] added to pyproject.toml to resolve editable build failure"

requirements-completed: [AUTH-01, AUTH-02]

# Metrics
duration: 4min
completed: 2026-03-31
---

# Phase 1 Plan 01: Project Setup + CopilotAuthManager Summary

**GitHub Device Flow OAuth with Fernet-encrypted token persistence — project scaffolded with pyproject.toml, uv venv, and 9 passing unit tests**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-31T07:21:28Z
- **Completed:** 2026-03-31T07:25:07Z
- **Tasks:** 2
- **Files modified:** 10 created

## Accomplishments
- Project skeleton with pyproject.toml, .gitignore, package directories, and uv.lock committed
- CopilotAuthManager implementing Fernet encryption (save_token/load_token), GitHub Device Flow polling (device_login), and unified get_token() with caching
- 9 unit tests covering: token roundtrip, missing file, corrupted file, key file creation (0o600), env var key override, Device Flow polling, slow_down handling, timeout, and get_token caching
- SDK 0.2.0 verified: `send_and_wait` exists on CopilotSession, `SubprocessConfig` importable — Plan 02 can use send_and_wait pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project skeleton and install dependencies** — `690c74b` (chore)
2. **Task 2: Implement CopilotAuthManager (TDD)** — `ce286c9` (feat)

**Plan metadata:** (docs commit below)

_Note: Task 2 used TDD — tests written and confirmed RED before implementation, then GREEN._

## Files Created/Modified
- `pyproject.toml` — Project metadata, dependencies, hatchling build config, pytest asyncio_mode=auto
- `.gitignore` — Excludes __pycache__, .venv, .enc_key, token.enc
- `uv.lock` — Reproducible dependency lock file
- `app/__init__.py` — Package marker
- `app/auth/__init__.py` — Auth package marker
- `app/providers/__init__.py` — Providers package marker (for Plan 02 ChatCopilot)
- `app/auth/manager.py` — CopilotAuthManager: Fernet encryption + GitHub Device Flow
- `tests/__init__.py` — Test package marker
- `tests/conftest.py` — auth_manager fixture using tmp_path
- `tests/test_auth.py` — 9 unit tests for AUTH-01 and AUTH-02

## SDK 0.2.0 Verification (required by plan output spec)

| Check | Result |
|-------|--------|
| `send_and_wait in dir(CopilotSession)` | **True** |
| `from copilot import CopilotClient, SubprocessConfig` | **OK** |

**Plan 02 decision:** Use `send_and_wait()` directly — no event-listener fallback needed.

## Decisions Made
- `packages = ["app"]` added to `[tool.hatch.build.targets.wheel]` — hatchling cannot auto-discover because the package directory name (`app`) differs from the project name (`copilot_langgraph`)
- Polling loop sleeps BEFORE the POST request (Pitfall 7 from research doc) — prevents slow_down feedback loop where interval never resets
- `load_token()` returns None on all errors (InvalidToken, JSONDecodeError, missing file) — upstream callers must treat None as "not authenticated" and fall through to device_login

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added hatchling wheel packages config to pyproject.toml**
- **Found during:** Task 1 (uv sync)
- **Issue:** hatchling `build_editable` raised `ValueError: Unable to determine which files to ship` because the `app/` directory name doesn't match the `copilot-langgraph` project name, blocking the editable install
- **Fix:** Added `[tool.hatch.build.targets.wheel]` with `packages = ["app"]` to pyproject.toml
- **Files modified:** pyproject.toml
- **Verification:** `uv sync` completed successfully, all 38 packages installed
- **Committed in:** `690c74b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for any `uv sync` to succeed. No scope creep — minimal one-line config addition.

## Issues Encountered
- hatchling editable build failure on first `uv sync` — resolved with packages config (documented as deviation above)

## User Setup Required
None — no external service configuration required for this plan. Device Flow will prompt interactively during first use.

## Next Phase Readiness
- CopilotAuthManager is fully tested and importable as `from app.auth.manager import CopilotAuthManager`
- Plan 02 can use `send_and_wait()` directly (verified against SDK 0.2.0)
- `app/providers/__init__.py` exists, ready for `ChatCopilot` implementation in Plan 02
- No blockers

---
*Phase: 01-auth-provider-foundation*
*Completed: 2026-03-31*

## Self-Check: PASSED

All files verified present. Both task commits verified in git log.
- FOUND: pyproject.toml, .gitignore, app/__init__.py, app/auth/__init__.py, app/providers/__init__.py
- FOUND: app/auth/manager.py, tests/conftest.py, tests/test_auth.py, 01-01-SUMMARY.md
- FOUND commits: 690c74b, ce286c9
