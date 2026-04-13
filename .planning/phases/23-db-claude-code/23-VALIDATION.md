---
phase: 23
slug: db-claude-code
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (既存) |
| **Quick run command** | `docker compose exec app uv run pytest tests/test_mcp_tools.py -x -q` |
| **Full suite command** | `docker compose exec app uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec app uv run pytest tests/test_mcp_tools.py -x -q`
- **After every plan wave:** Run `docker compose exec app uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | DB-01 | T-23-01 | SELECT のみ通過、DDL/DML ブロック | unit | `pytest tests/test_mcp_tools.py::test_db_query_select_ok -x -q` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 1 | DB-02 | T-23-01 | INSERT/UPDATE/DELETE がエラーを返す | unit | `pytest tests/test_mcp_tools.py::test_db_query_write_blocked -x -q` | ❌ W0 | ⬜ pending |
| 23-01-03 | 01 | 2 | DB-01 | — | SELECT が実際の PostgreSQL データを返す | integration | `pytest tests/test_mcp_tools.py::test_db_query_integration -x -q` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 1 | CODE-01 | T-23-02 | claude CLI 実行・出力取得 | unit | `pytest tests/test_mcp_tools.py::test_claude_code_runs -x -q` | ❌ W0 | ⬜ pending |
| 23-02-02 | 02 | 1 | CODE-02 | T-23-02 | CLAUDECODE=1 が子プロセスに継承されない | unit | `pytest tests/test_mcp_tools.py::test_claude_code_env_sanitized -x -q` | ❌ W0 | ⬜ pending |
| 23-02-03 | 02 | 1 | CODE-03 | T-23-02 | 60秒タイムアウトで zombie なし | unit | `pytest tests/test_mcp_tools.py::test_claude_code_timeout -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mcp_tools.py` — DB クエリ + Claude Code 全テストスタブ（DB-01, DB-02, CODE-01, CODE-02, CODE-03）
- [ ] `tests/conftest.py` — PostgreSQL 接続フィクスチャ（既存があれば確認・拡張）

*既存の pytest インフラが存在する場合は追加インストール不要。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| claude CLI がコンテナ内で実行できるか確認 | CODE-01 | コンテナ内バイナリ存在確認はテストで自動化困難 | `docker compose exec mcp-server claude --version` を Wave 0 で手動実行 |
| psycopg_pool の接続プールが mcp-server コンテナ内で正常に起動するか | DB-01 | lifespan 関数の起動ログ確認 | `docker compose logs mcp-server` で `pool opened` メッセージを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
