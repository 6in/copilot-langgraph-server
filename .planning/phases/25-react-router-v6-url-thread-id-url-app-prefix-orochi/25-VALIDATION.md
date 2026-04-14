---
phase: 25
slug: react-router-v6-url-thread-id-url-app-prefix-orochi
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vite.config.ts` |
| **Quick run command** | `cd frontend && bun run type-check` |
| **Full suite command** | `cd frontend && bun run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && bun run type-check`
- **After every plan wave:** Run `cd frontend && bun run build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | URL routing | — | N/A | build | `cd frontend && bun run type-check` | ✅ W0 | ⬜ pending |
| 25-01-02 | 01 | 1 | basename設定 | — | N/A | build | `cd frontend && bun run type-check` | ✅ W0 | ⬜ pending |
| 25-01-03 | 01 | 2 | URL同期 | — | N/A | build | `cd frontend && bun run build` | ✅ W0 | ⬜ pending |
| 25-01-04 | 01 | 2 | 共有リンク | — | N/A | manual | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `cd frontend && bun add react-router` — react-router インストール

*既存の TypeScript 設定で型チェックが利用可能。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| スレッド共有リンクの動作 | URL sharing | ブラウザ実機確認が必要 | URL をコピーして別タブで開き、正しいスレッドが表示されること |
| ブラウザ履歴の動作 | Browser history | ブラウザ実機確認が必要 | 複数画面遷移後に Back/Forward が正しく動作すること |
| nginx での直接アクセス | SPA fallback | 本番環境固有 | `/orochi/chat/abc123` に直接アクセスして SPA が返ること |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
