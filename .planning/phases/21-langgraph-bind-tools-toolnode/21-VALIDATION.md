---
phase: 21
slug: langgraph-bind-tools-toolnode
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
validated: 2026-04-20
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `docker compose exec api pytest tests/ -x -q --tb=short 2>&1 | tail -20` |
| **Full suite command** | `docker compose exec api pytest tests/ -q --tb=short 2>&1 | tail -30` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec api pytest tests/ -x -q --tb=short 2>&1 | tail -20`
- **After every plan wave:** Run `docker compose exec api pytest tests/ -q --tb=short 2>&1 | tail -30`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | TOOL-01 | — | N/A | unit | `docker compose exec api pytest tests/test_copilot_bind_tools.py -x -q` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | TOOL-01 | — | N/A | integration | `docker compose exec api pytest tests/test_bind_tools_spike.py -x -q` | ❌ W0 | ⬜ pending |
| 21-02-01 | 02 | 2 | TOOL-02 | — | N/A | unit | `docker compose exec api pytest tests/test_tool_enabled_subagent.py -x -q` | ❌ W0 | ⬜ pending |
| 21-02-02 | 02 | 2 | TOOL-03 | — | N/A | unit | `docker compose exec api pytest tests/test_subagent_registry_tools.py -x -q` | ❌ W0 | ⬜ pending |
| 21-03-01 | 03 | 3 | TOOL-01, TOOL-02, TOOL-03 | — | N/A | e2e | `docker compose exec api pytest tests/test_react_e2e.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_copilot_bind_tools.py` — ChatCopilot.bind_tools() / BoundChatCopilot のユニットテストスタブ（TOOL-01）
- [ ] `tests/test_bind_tools_spike.py` — プロンプトエンジニアリング方式のスパイクテスト（TOOL-01）
- [ ] `tests/test_tool_enabled_subagent.py` — ToolEnabledSubAgent の ReAct ループテストスタブ（TOOL-02）
- [ ] `tests/test_subagent_registry_tools.py` — SubAgentRegistry の tools フラグ読み取りテストスタブ（TOOL-03）
- [ ] `tests/test_react_e2e.py` — end-to-end ReAct ループのスモークテストスタブ（TOOL-01〜03）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Copilot モデルが JSON 形式でツール呼び出しを返す | TOOL-01 | プロンプト遵守率は実際の Copilot API 接続が必要 | `docker compose up` 後、Web UI から "web検索して東京の天気を教えて" を送信し、ToolMessage が表示されることを確認 |
| ToolMessage が PostgreSQL に保存される | TOOL-03 | DB 直接確認が必要 | `docker compose exec postgres psql -U copilot -c "SELECT * FROM checkpoints ORDER BY created_at DESC LIMIT 5;"` でツール呼び出し履歴を確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-04-20 (v5.0 milestone audit cleanup phase 31.1 で backfill)
