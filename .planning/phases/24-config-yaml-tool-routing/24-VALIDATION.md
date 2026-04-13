---
phase: 24
slug: config-yaml-tool-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_tool_registry.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_tool_registry.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 0 | MCP-03 | — | N/A | unit | `uv run pytest tests/test_tool_registry.py -x --collect-only` | ❌ W0 | ⬜ pending |
| 24-01-02 | 01 | 1 | MCP-03 | — | N/A | unit | `uv run pytest tests/test_tool_registry.py::test_tool_registry_expected_names -x` | ❌ W0 | ⬜ pending |
| 24-01-03 | 01 | 1 | MCP-03 | — | N/A | unit | `uv run pytest tests/test_tool_registry.py::test_tool_registry_validate_pass -x` | ❌ W0 | ⬜ pending |
| 24-01-04 | 01 | 1 | MCP-03 | — | N/A | unit | `uv run pytest tests/test_tool_registry.py::test_tool_registry_validate_fail_missing -x` | ❌ W0 | ⬜ pending |
| 24-01-05 | 01 | 1 | MCP-03 | — | N/A | unit | `uv run pytest tests/test_tool_registry.py::test_tool_registry_validate_fail_extra -x` | ❌ W0 | ⬜ pending |
| 24-01-06 | 01 | 1 | MCP-03 | — | N/A | unit | `uv run pytest tests/test_worker.py::test_startup_tool_registry_validate -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tool_registry.py` — MCP-03 の全テストケース（新規作成）
- [ ] `app/orchestrator/tool_registry.py` — ToolRegistry クラス（新規作成）

*Wave 0 でテストスタブとクラスを同時に作成すること。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| YAML 変更後コンテナ再起動で反映 | MCP-03 | Docker 環境が必要 | `docker compose restart worker` 後、ログで "ToolRegistry validation passed" を確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
