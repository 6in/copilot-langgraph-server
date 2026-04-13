---
phase: 22
slug: web-search-tavily
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `mcp_server/pyproject.toml` ([tool.pytest.ini_options]) |
| **Quick run command** | `pytest tests/test_mcp_server.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_mcp_server.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 0 | SEARCH-01 | — | N/A | unit | `pytest tests/test_mcp_server.py::test_web_search_normal -x` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 0 | SEARCH-02 | — | N/A | unit | `pytest tests/test_mcp_server.py::test_web_search_truncates_content -x` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 0 | — | — | エラー時に {"error": ...} を返し、ジョブ失敗にならない | unit | `pytest tests/test_mcp_server.py::test_web_search_error_handling -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mcp_server.py` — `test_web_search_normal`, `test_web_search_truncates_content`, `test_web_search_error_handling` スタブ（SEARCH-01, SEARCH-02）
- [ ] `langchain-community>=0.4.1` を `mcp_server/pyproject.toml` に追加（`uv add langchain-community`）

*既存の pytest + pytest-asyncio インフラは test_mcp_server.py にて整備済み。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docker compose up` 後に general-assistant に「最新の〇〇を教えて」と聞くと Tavily 検索結果が返る | SEARCH-01 | 実 API キーが必要 / Docker 環境依存 | 1. `.env` に `TAVILY_API_KEY` を設定 2. `docker compose up` 3. SuperChat で general-assistant を選択 4. 「最新のPythonバージョンを教えて」と入力 5. 回答に Tavily から取得した情報が含まれることを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
