# Phase 35 Integration Check Report

**Date:** 2026-04-23
**Tested by:** Claude (chrome-devtools MCP) + 6in (manual Device Flow login)

## Chrome DevTools Responsive

Plan 07b Task 02 — Chromium remote-debug (:9222) × chrome-devtools MCP で実測。
4 width × 2 theme = 8 パターン + Chat ページ + Drawer 挙動。

| Width | Theme | MenuScreen | Chat | Drawer | Verdict |
|-------|-------|-----------|------|--------|---------|
| 1440  | light | PASS — gradient title / 3 セクション / 4-col grid / 日本語コピー | PASS — InputBar + sidebar 両方表示、slot 空時 DOM 未出現 | N/A | PASS |
| 1440  | dark  | PASS — dark token 瞬時切替 (React 再マウントなし) | PASS | N/A | PASS |
| 1024  | light | PASS — 「モデル:」/「6in」username 非表示、4-col grid | PASS — sidebar drawer 化で main 100% 幅、InputBar 全幅 | CSS `.sidebar-drawer.open` overlay で左 slide in + backdrop 確認。**ただし UI 上の open trigger 未配線（下記 Issues 参照）** | PARTIAL |
| 1024  | dark  | PASS | PASS | 同上 | PARTIAL |
| 768   | light | PASS — 3-col app / 2-col recent | PASS | 同上 | PARTIAL |
| 768   | dark  | PASS — dark surface ヒエラルキー保持 | PASS | 同上 | PARTIAL |
| 375   | light | PASS — hamburger `<details>` 可視 / desktop-actions 非表示 / 1-col grid / 横スクロールなし | PASS | hamburger menu は ログアウト + theme toggle のみ、drawer open 項目なし | PARTIAL |
| 375   | dark  | PASS | PASS | 同上 | PARTIAL |

## Cross-Browser

Plan 07b Task 03 — 実測環境は Linux (Parallels / Chromium) のみ。Edge/Safari 未インストール。

| Browser | MenuScreen | Chat | Drawer | Notes |
|---------|-----------|------|--------|-------|
| Chrome  | PASS | PASS | CSS PASS / trigger gap | Chromium 146.0.7680.164 で 4 幅 × 2 テーマ sweep 済 |
| Edge    | skipped | skipped | skipped | 環境にインストールなし。Chromium ベースなのでレイアウト互換は高い想定。本番環境ユーザー発生時に再確認 |
| Safari  | skipped | skipped | skipped | macOS 不在。WebKit 固有の transform/flex 差異は今回未検証。polish phase 候補 |

## Phase 36 Handoff Contract

10 項目の最終 verification。

| # | 項目 | 方法 | 結果 |
|---|------|------|------|
| 1 | semantic 変数 13+ | grep | PASS (22 件) |
| 2 | dark override | grep | PASS (9 件) |
| 3 | InputBar 存在 + props | grep | PASS (15 件検出、toolbarSlot/previewSlot/onSend 含む) |
| 4 | InputBar slot レイアウト | visual | PASS — slot 空時 DOM 未出現（条件レンダー動作）、textarea 左右のスペース無し |
| 5 | MessageArea UX retain | manual | PASS — Ctrl+Enter placeholder / Send disabled 初期状態 / sidebar collapse トグル・日付グループ (今週/先週) 表示確認 |
| 6 | @media 1024px | grep | PASS (1 ブロック、複数セレクタ) |
| 7 | @media 767px | grep | PASS (1 ブロック、複数セレクタ) |
| 8 | MenuScreen 3 セクション | grep | PASS (section-apps / section-recent / section-other) |
| 9 | #7c6ff7 new hardcode なし | grep | PASS (MenuScreen/MessageArea/ThreadSidebar/Header = 0 件) |
| 10 | Chrome/Edge/Safari 破綻ゼロ | cross-browser | PARTIAL — Chrome PASS / Edge + Safari skipped（環境制約）|

## Issues found

### Issue 1: AuthPanel Start ボタンが light mode で実質見えない（Wave 4 中に修正済）

- **原因:** Plan 35-07a で `#24292e` → `var(--color-bg)` に誤置換。light mode では `--color-bg` = `#f5f5f5` で page bg と同色化、white text が blur
- **修正:** `var(--color-neutral-900)` (#24292e primitive) に再置換（commit `e80666d`）
- **再発防止:** semantic vars が存在しない dark CTA 色には primitive を使う選択肢を PROJECT.md / ADR で言及するのが望ましい
- **Status:** RESOLVED (Wave 4)

### Issue 2: Drawer に UI 上の open trigger が未配線

- **状況:** `ThreadSidebar` は `drawerOpen` state + `onDrawerOpenChange` + Escape ハンドラ + `.sidebar-drawer.open` CSS 全て実装済。chrome-devtools MCP で `.open` class を手動付与すると overlay が正しく slide in + backdrop 表示
- **ギャップ:** hamburger menu (375px) は「ログアウト / theme toggle」の 2 項目のみで drawer を開くボタンが無い。tablet (1024) でも sidebar 全体が off-screen (`transform: translateX(-320px)`) のため、sidebar 内の collapse button (◀) にアクセス不能
- **結果:** tablet/mobile 幅から thread 一覧にアクセスする手段なし
- **Severity:** Medium — 機能ギャップだが Phase 35 の主目的（UX-03 ダッシュボード / UX-04 design system）は達成、drawer の trigger 配線は別 plan (Phase 36 相当) でもよい
- **Status:** OPEN — 後続 phase で drawer open button を Header hamburger (mobile) と tablet 幅の独立 trigger として追加する必要あり
- **Recommended follow-up:** 36.x 系の early plan で `<button onClick={() => setDrawerOpen(true)}>☰ スレッド</button>` を Header に追加、mobile hamburger menu にも drawer open item を追加

## Verdict

- Phase 35 phase gate: **APPROVED WITH MINOR GAPS**
  - Design system（CSS 変数基盤 + 4 コンポーネント token 移行 + MenuScreen ダッシュボード化 + InputBar 分離）は 100% 達成
  - Drawer UI trigger gap は Phase 36 着手時の early fix として記録（Phase 36 Handoff Contract 10 項目は visual + grep 9.5/10 PASS）
  - Cross-browser sweep は環境制約で Edge/Safari skipped、polish phase 候補として残す
