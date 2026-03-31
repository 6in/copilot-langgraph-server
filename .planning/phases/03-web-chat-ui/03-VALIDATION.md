---
phase: 3
slug: web-chat-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (Wave 0 installs) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | — | infra | `uv run pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 3-xx-01 | xx | 1 | AUTH-03 | integration | `uv run pytest tests/test_auth_api.py -x -q` | ❌ W0 | ⬜ pending |
| 3-xx-02 | xx | 1 | CHAT-01 | integration | `uv run pytest tests/test_chat_api.py -x -q` | ❌ W0 | ⬜ pending |
| 3-xx-03 | xx | 1 | CHAT-02 | integration | `uv run pytest tests/test_chat_api.py -x -q` | ❌ W0 | ⬜ pending |
| 3-xx-04 | xx | 1 | CHAT-03 | integration | `uv run pytest tests/test_chat_api.py::test_multi_turn -x -q` | ❌ W0 | ⬜ pending |
| 3-xx-05 | xx | 1 | CHAT-04 | integration | `uv run pytest tests/test_chat_api.py::test_new_chat -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — async client fixture, lifespan test setup
- [ ] `tests/test_auth_api.py` — stubs for AUTH-03 (device flow start/poll/status endpoints)
- [ ] `tests/test_chat_api.py` — stubs for CHAT-01/02/03/04 (send message, multi-turn, new chat)
- [ ] `pytest-asyncio` added to dev dependencies (`uv add --dev pytest-asyncio httpx`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Device Flow browser link clickable | AUTH-03 | Requires real browser + GitHub OAuth | Open app, click Login, verify link is clickable and code is displayed with Copy button |
| Markdown renders in browser | CHAT-02 | DOM rendering — no headless pytest | Send message with `**bold** and \`\`\`code\`\`\`` — verify rendered HTML, not raw markup |
| Re-authenticate button on token expiry | AUTH-03 | Requires expired token state | Manually expire token, send message, verify header shows "期限切れ — Click to re-auth" |
| Typing indicator animation | CHAT-01 | CSS animation — not pytest-testable | Send message, observe "..." bubble appears before reply |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
