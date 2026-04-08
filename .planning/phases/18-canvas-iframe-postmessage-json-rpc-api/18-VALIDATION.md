---
phase: 18
slug: canvas-iframe-postmessage-json-rpc-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) / vitest (frontend) |
| **Config file** | pyproject.toml (pytest) / frontend/vite.config.ts (vitest) |
| **Quick run command** | `docker compose exec api pytest tests/ -x -q` |
| **Full suite command** | `docker compose exec api pytest tests/ -q && cd frontend && bun run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec api pytest tests/ -x -q`
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | — | T-18-01 | SELECT 以外のクエリを拒否する | unit | `uv run pytest tests/test_iframe_rpc_handler.py -k test_is_select_only -q` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | — | T-18-02 | QUERY ハンドラが正しい rows フォーマットで返す | unit | `uv run pytest tests/test_iframe_rpc_handler.py -k test_handle_query -q` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | — | — | AI ハンドラが responseText を返す | unit | `uv run pytest tests/test_iframe_rpc_handler.py -k test_handle_ai -q` | ❌ W0 | ⬜ pending |
| 18-01-04 | 01 | 1 | — | — | 不明メソッドでエラーを返す | unit | `uv run pytest tests/test_iframe_rpc_handler.py -k test_handle_unknown -q` | ❌ W0 | ⬜ pending |
| 18-02-01 | 01 | 1 | — | T-18-03 | POST /api/iframe-rpc が JWT 認証付きで job_id を返す | integration | `uv run pytest tests/test_iframe_rpc_route.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_iframe_rpc_handler.py` — SQL バリデーション・QUERY/AI ハンドラのスタブ
- [ ] `tests/test_iframe_rpc_route.py` — POST /api/iframe-rpc エンドポイントのスタブ
- [ ] `tests/conftest.py` — 既存の共有フィクスチャを拡張（mock JobStore 等）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CanvasPane の postMessage → SSE → iframe 返信の E2E フロー | D-04, D-05 | ブラウザの iframe 間通信は自動テスト困難 | 1. Canvas アプリをデプロイ 2. CanvasChatApp で表示 3. iframe から `window.parent.postMessage({jsonrpc:'2.0',method:'AI',params:{prompt:'Hello'},id:1}, '*')` を実行 4. レスポンスが iframe に届くことを確認 |
| db_pools.yaml が正しく読み込まれる | D-15, D-16 | Docker Compose ボリュームマウントの確認が必要 | `docker compose exec worker python -c "from app.jobs.db_pool_manager import DBPoolManager; import asyncio; asyncio.run(DBPoolManager.init())"` でエラーなし |
| srcDoc iframe（null origin）の動作確認 | D-01, D-02 | Preview タブ固有の動作 | Canvas プレビューで iframe が表示された状態で postMessage を送り、origin 警告がコンソールに出ないことを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
