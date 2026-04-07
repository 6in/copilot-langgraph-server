---
phase: 16
slug: canvas-app
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) / vitest (frontend) |
| **Config file** | `pyproject.toml` / `frontend/vite.config.ts` |
| **Quick run command** | `docker compose exec backend pytest tests/ -x -q` |
| **Full suite command** | `docker compose exec backend pytest tests/ && docker compose exec frontend bun run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec backend pytest tests/ -x -q`
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | TBD | — | Canvas Gem 自動登録の冪等性 | unit | `pytest tests/test_canvas_gem.py -x -q` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | TBD | — | deployed フィルタ正常動作 | unit | `pytest tests/test_canvas_api.py -x -q` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 2 | TBD | — | CanvasChatApp レンダリング | component | `bun run test -- CanvasChatApp` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_canvas_gem.py` — Canvas 専用 Gem 自動登録テスト
- [ ] `tests/test_canvas_api.py` — `/api/canvas/apps?deployed=true` フィルタテスト
- [ ] `frontend/src/components/__tests__/CanvasChatApp.test.tsx` — コンポーネントレンダリングテスト

*既存インフラ (pytest / vitest) でカバー可能。フレームワークの新規インストール不要。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| iframe サンドボックスプレビュー | TBD | ブラウザ sandbox 属性の視覚確認 | localhost で Canvas App 作成後、プレビュー画面を開いて HTML が正しくレンダリングされることを確認 |
| デプロイ URL アクセス | TBD | 実際の URL 発行と疎通確認 | デプロイ実行後、発行された URL にブラウザでアクセスして表示を確認 |
| CanvasChatApp ドラッグリサイズ | TBD | インタラクション UI | drag handle を操作してペインリサイズが機能することを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
