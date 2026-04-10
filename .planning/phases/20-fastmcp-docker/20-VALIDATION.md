---
phase: 20
slug: fastmcp-docker
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (root) — `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_mcp_server.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_mcp_server.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green + `docker compose up` smoke test
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 0 | MCP-01 | — | N/A | unit | `uv run pytest tests/test_mcp_server.py -x` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | MCP-01 | — | N/A | unit | `uv run pytest tests/test_mcp_server.py::test_health_endpoint -x` | ❌ W0 | ⬜ pending |
| 20-01-03 | 01 | 1 | MCP-02 | — | N/A | unit | `uv run pytest tests/test_mcp_server.py::test_stub_tools -x` | ❌ W0 | ⬜ pending |
| 20-01-04 | 01 | 1 | MCP-02 | — | N/A | unit | `uv run pytest tests/test_mcp_server.py::test_ping_tool -x` | ❌ W0 | ⬜ pending |
| 20-02-01 | 02 | 2 | MCP-01 | — | N/A | integration | `docker compose up --wait && docker compose ps` (manual smoke) | ❌ W0 | ⬜ pending |
| 20-02-02 | 02 | 2 | MCP-02 | — | N/A | integration | `docker compose up --wait` + manual `get_tools()` smoke | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mcp_server.py` — MCP-01/MCP-02 カバレッジ（`/health` 200 OK、`get_tools()` リスト返却、`ping` ツール正常応答）
- [ ] FastMCP ASGI テストパターン確認（httpx での直接テストか subprocess 起動か）

*既存インフラが一部カバーする可能性あり — Wave 0 で確認。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docker compose up` で mcp-server が healthy 起動 | MCP-01 | Docker Compose 環境依存・CI スコープ外 | `docker compose up --wait`; `docker compose ps` で `mcp-server` が `healthy` を確認 |
| worker から `get_tools()` で BaseTool リスト取得 | MCP-02 | Docker ネットワーク統合テスト | worker コンテナ内で `MultiServerMCPClient` → `get_tools()` を実行し非空リストを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
