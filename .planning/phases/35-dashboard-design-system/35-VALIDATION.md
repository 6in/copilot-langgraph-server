---
phase: 35
slug: dashboard-design-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 35-RESEARCH.md §Validation Architecture (L1078-1137)

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | なし（frontend に test runner 未導入） — Phase 35 で新規導入しない方針 (UI-SPEC §Registry Safety, CONTEXT.md D-01) |
| **Config file** | なし |
| **Quick run command** | `bun run --cwd frontend lint && bun run --cwd frontend build` (ESLint 9 + tsc -b) |
| **Full suite command** | 上記 + `bash scripts/check-phase-35.sh` (Wave 0 で新規作成) + manual checker sweep |
| **Estimated runtime** | quick: ~15 秒 / full: ~30 秒 + manual sweep |

---

## Sampling Rate

- **After every task commit:** Run `bun run --cwd frontend lint && bun run --cwd frontend build`
- **After every plan wave:** Run `bash scripts/check-phase-35.sh` + 該当 Wave の grep-verifiable requirements
- **Before `/gsd-verify-work`:** Full suite + manual 4 項目 (UX-03-4 / UX-04-8 / UX-04-9 / Phase 36 Handoff visual) を checker が承認
- **Max feedback latency:** 15 秒 (lint + build)

---

## Per-Task Verification Map

> Planner が PLAN.md 生成後に task_id を確定させた段階で埋める。現時点では phase requirement 単位のマップを提示する。

| Req ID | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|--------|------|-------------|-----------|-------------------|-------------|--------|
| UX-03-1 | 2 | MenuScreen が 3 セクション (アプリ/最近/その他) を持つ | static (grep) | `grep -c 'aria-labelledby="section-' frontend/src/components/MenuScreen.tsx` → ≥3 | ❌ W0→W2 | ⬜ pending |
| UX-03-2 | 2 | 最近のスレッドが 5 件以下に slice されている | static (grep) | `grep -n 'slice(0, 5)' frontend/src/components/MenuScreen.tsx` → ≥1 | ❌ W0→W2 | ⬜ pending |
| UX-03-3 | 2 | 日本語セクション見出し 3 種が存在 | static (grep) | `grep -cE 'アプリケーション\|最近のスレッド\|その他' frontend/src/components/MenuScreen.tsx` → ≥3 | ❌ W0→W2 | ⬜ pending |
| UX-03-4 | 3 | 初見ユーザー向けに最初に使うアプリが判別可能 | manual | UI checker 目視 (説明文/アイコン密度) | manual | ⬜ pending |
| UX-04-1 | 0 | `:root` に 13+ semantic 変数定義 | static (grep) | `grep -cE '^\s*--color-(bg\|surface\|border\|text\|accent\|destructive\|success\|header)' frontend/src/theme.css` → ≥13 | ❌ W0 | ⬜ pending |
| UX-04-2 | 0 | `[data-theme="dark"]` ブロック内で semantic override | static (grep) | `awk '/\[data-theme="dark"\]\s*{/,/^\}$/' frontend/src/theme.css \| grep -cE '^\s*--color-'` → ≥9 | ❌ W0 | ⬜ pending |
| UX-04-3 | 2 | `@media (max-width: 1024px)` が theme.css に存在 | static (grep) | `grep -c '@media (max-width: 1024px)' frontend/src/theme.css` → ≥1 | ❌ W0→W2 | ⬜ pending |
| UX-04-4 | 2 | `@media (max-width: 767px)` が theme.css に存在 | static (grep) | `grep -c '@media (max-width: 767px)' frontend/src/theme.css` → ≥1 | ❌ W0→W2 | ⬜ pending |
| UX-04-5 | 1 | `#7c6ff7` hardcode が 4 対象ファイルに 0 件 | static (grep) | `grep -c '#7c6ff7' frontend/src/components/{MenuScreen,MessageArea,ThreadSidebar,Header}.tsx` → すべて 0 | ❌ W1 | ⬜ pending |
| UX-04-6 | 1 | `isDark ?` 三項分岐が 4 対象ファイルに 0 件 | static (grep) | `grep -cE 'isDark \?' frontend/src/components/{MenuScreen,MessageArea,ThreadSidebar,Header}.tsx` → すべて 0 | ❌ W1 | ⬜ pending |
| UX-04-7 | 1 | `InputBar.tsx` が存在し必須 props を受け取る | static (grep) | `test -f frontend/src/components/InputBar.tsx && grep -cE 'toolbarSlot\|previewSlot\|onSend' frontend/src/components/InputBar.tsx` → ≥3 | ❌ W1 | ⬜ pending |
| UX-04-8 | 3 | ダーク/ライト × desktop/tablet 4 画面で破綻ゼロ | manual (screenshot) | Chrome DevTools Responsive で 375/768/1024/1440 × light/dark | manual | ⬜ pending |
| UX-04-9 | 3 | Chrome / Edge / Safari で MenuScreen/Chat/Drawer 破綻ゼロ | manual (cross-browser) | 各ブラウザで `/orochi/`, `/orochi/chat`, drawer 開閉 | manual | ⬜ pending |
| UX-04-10 | all | TypeScript 型エラー 0 | automated | `bun run --cwd frontend build` | ✅ 既存 | ⬜ pending |
| UX-04-11 | all | ESLint エラー 0 | automated | `bun run --cwd frontend lint` | ✅ 既存 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/check-phase-35.sh` — grep-based 検証ハーネス (UX-03-1〜3, UX-04-1〜7 の連続実行)
- [ ] `frontend/src/utils/threadGroups.ts` — `getDateGroup` ユーティリティを ThreadSidebar.tsx から切り出し (MenuScreen 最近セクションで再利用するため)
- [ ] ConfirmModal 既存 z-index 調査 (drawer backdrop z-index 確定用、Pitfall 7 対応)
- [ ] ThreadInfo 型定義 (`frontend/src/types.ts`) 確認 — `app_id`/`gem_id` の有無で最近スレッドクリック時のルーティング規則を確定 (Assumption A1)
- [ ] `GET /api/threads` 全アプリ横断返却可否の確認 (`app/api/routes/threads.py` read、Assumption A2)
- [ ] `:root` primitive + semantic 変数定義を theme.css 先頭に追加 (既存 hex はまだ置換しない、追加のみ)
- [ ] `[data-theme="dark"]` ブロックに semantic dark override を追加

**Framework install:** 不要 (Vitest / Jest / Playwright は Phase 35 では導入しない、v6.1+ で別 phase 化)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 初見ユーザーが最初に使うアプリを判別可能 | UX-03 | 情報設計の妥当性は人間判断 | MenuScreen を未学習ユーザーに見せ「最初にどのアプリを使うか」の回答と理由を聞く (checker が代理判断可) |
| 4 画面 × 2 テーマで破綻ゼロ | UX-04 | 視覚破綻判定は目視 | Chrome DevTools Responsive 375/768/1024/1440 × light/dark の 8 画面で MenuScreen / Chat / Drawer をスクリーンショット、checker が承認 |
| Chrome/Edge/Safari 最新 で破綻ゼロ | UX-04 | cross-browser は automated なし | 各ブラウザで `/orochi/`, `/orochi/chat`, drawer 開閉、chatscope バルーン幅を目視 |
| Phase 36 Handoff Contract 10 項目の visual 部分 (項目 4, 10) | UX-03/UX-04 | slot 配置と cross-browser は目視 | UI-SPEC §Phase 36 Handoff Contract 4 (InputBar slot レイアウト), 10 (cross-browser 4 パターン) を目視 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s (quick) / < 30s (full)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
