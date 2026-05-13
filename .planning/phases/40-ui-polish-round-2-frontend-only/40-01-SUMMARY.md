---
phase: 40-ui-polish-round-2-frontend-only
plan: 01
subsystem: ui
tags: [react, react-router, header, navigation, frontend]

# Dependency graph
requires:
  - phase: 25-react-router
    provides: URL ルーティング基盤 (Routes / Route / useNavigate) と GemsScreenRoute / CanvasScreenRoute ラッパー
  - phase: 35-dashboard-design-system
    provides: 共有 Header コンポーネント (onBackToMenu / appName / Orochi Chat ブランド表示)
provides:
  - GemsScreenRoute / CanvasScreenRoute から Header に onBackToMenu={navigate('/')} と appName を渡すパターン
  - 戻るボタンを画面内重複から共有 Header に統一する画面遷移視覚一貫性
affects: [40-02, 40-03, 40-04, 40-05, 40-06, future-screen-routes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - 戻るナビゲーションは共有 Header の onBackToMenu prop に集約 (画面内ボタン重複を禁止)

key-files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/components/GemsScreen.tsx
    - frontend/src/components/CanvasScreen.tsx

key-decisions:
  - GemsScreen / CanvasScreen の props 型シグネチャは破壊しない (onBack: () => void を残す) — 呼び出し元 App.tsx 互換を保つため
  - 関数本体の destructure では onBack を外し未使用警告 (TS6133) を回避
  - pre-existing lint errors (react-hooks/set-state-in-effect 等) は本プランの scope 外と判断し deferred-items.md に記録

patterns-established:
  - "Screen Route → Header onBackToMenu pattern: Route ラッパーが Header に navigate('/') を渡し、Screen 内には Back ボタンを置かない"

requirements-completed:
  - UI-BACKBUTTON

# Metrics
duration: 約 15min
completed: 2026-05-13
---

# Phase 40 Plan 01: Gems/Canvas 画面の戻るボタン統一 Summary

**GemsScreen / CanvasScreen の画面内 "← Back" ボタンを撤去し、共有 Header の onBackToMenu に Back ナビゲーションを集約。Chat/SuperChat/Debate と同じ viewport 座標 (ヘッダー左端) に戻るボタンを揃えた。**

## Performance

- **Duration:** 約 15 min
- **Started:** 2026-05-13T08:55Z 頃
- **Completed:** 2026-05-13T09:10Z
- **Tasks:** 2/2
- **Files modified:** 3 (App.tsx, GemsScreen.tsx, CanvasScreen.tsx)

## Accomplishments
- `App.tsx` の `GemsScreenRoute` / `CanvasScreenRoute` が Header に `onBackToMenu={() => navigate('/')}` と `appName="Gems"` / `appName="Canvas"` を渡すように更新
- `GemsScreen.tsx` / `CanvasScreen.tsx` 内の独自 "← Back" ボタンを削除し、各画面のヘッダーは h1 (「Gems」「Canvas Apps」) のみに整理
- ChatRoute / DebateRoute / GemsScreenRoute / CanvasScreenRoute の 4 画面で Back ボタンが Header 左端の同座標に表示される状態を達成

## Task Commits

各タスクをアトミックに commit:

1. **Task 1: App.tsx の GemsScreenRoute / CanvasScreenRoute に Header の onBackToMenu / appName 配線を追加** — `ac7feb7` (feat)
2. **Task 2: GemsScreen.tsx / CanvasScreen.tsx から独自 "← Back" ボタンを削除** — `daba1af` (feat)

## Files Created/Modified
- `frontend/src/App.tsx` — GemsScreenRoute / CanvasScreenRoute の Header 呼び出しに onBackToMenu={navigate('/')} と appName を追加
- `frontend/src/components/GemsScreen.tsx` — 画面内 "← Back" ボタン要素を削除、destructure から onBack を外し未使用警告回避 (型は維持)
- `frontend/src/components/CanvasScreen.tsx` — 画面内 "← Back" ボタン要素を削除、destructure から onBack を外し未使用警告回避 (型は維持)
- `.planning/phases/40-ui-polish-round-2-frontend-only/deferred-items.md` — Pre-existing lint errors を out-of-scope として記録 (新規)

## Decisions Made
- **Props 型シグネチャは破壊しない:** プランは「`onBack: () => void` シグネチャを残す (呼び出し元の App.tsx GemsScreenRoute / CanvasScreenRoute が引き続き onBack を渡すため)」と明記。`GemsScreenProps` / `CanvasScreenProps` の型は維持しつつ、関数本体の destructure からのみ `onBack` を外して TS6133 (declared but never read) を回避。これにより App.tsx 側の引き渡しは現状動作のまま追加変更が不要。
- **Lint deferred:** baseline (本変更前) でも `bun run lint` が `✖ 23 problems (22 errors, 1 warning)` を返していたことを `git stash` 経由で確認。本プランの編集は lint エラーを増減させず、すべて pre-existing。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] frontend に `typecheck` npm script が存在しなかった**
- **Found during:** Task 1 verification
- **Issue:** プランは `cd frontend && bun run typecheck` を verify コマンドに指定するが、`frontend/package.json` の scripts には `dev / build / lint / preview` のみで `typecheck` 単独スクリプトが無い (`build` は `tsc -b && vite build`)。
- **Fix:** 代替として `bunx tsc -b --noEmit` を直接実行して型チェックを行った。
- **Files modified:** なし (実行コマンド変更のみ)
- **Verification:** `bunx tsc -b --noEmit` exit 0 を確認
- **Committed in:** N/A (verification commit ではない)

**2. [Rule 3 - Blocking] frontend 依存パッケージが未インストールで `tsc` が型定義を解決できなかった**
- **Found during:** Task 1 verification
- **Issue:** `node_modules/` が初期状態で空のため `error TS2688: Cannot find type definition file for 'vite/client' / 'node'` が発生。
- **Fix:** `cd frontend && bun install` を 1 回実行し依存を揃えた。
- **Files modified:** なし (lockfile / node_modules のみ、コミット対象外)
- **Verification:** 再度 `bunx tsc -b --noEmit` で exit 0
- **Committed in:** N/A

**3. [Rule 1 - Bug] onBack を destructure したまま使わないと TS6133 で typecheck が失敗**
- **Found during:** Task 2 verification
- **Issue:** "← Back" ボタンを削除した直後、`GemsScreen({ onSelectGem, onBack })` / `CanvasScreen({ onBack, onStartChat })` の destructure 内 `onBack` が未使用となり `TS6133: 'onBack' is declared but its value is never read` で typecheck が失敗。
- **Fix:** 関数本体の destructure から `onBack` を外す。`GemsScreenProps` / `CanvasScreenProps` の型定義 (`onBack: () => void;`) は維持し、呼び出し元 (App.tsx) は変更不要のまま `onBack` を渡し続ける (TypeScript は型レベルでのみ受理)。コードコメントで「shared Header に統一したため画面内では使用しない」旨を明記。
- **Files modified:** `frontend/src/components/GemsScreen.tsx`, `frontend/src/components/CanvasScreen.tsx`
- **Verification:** `bunx tsc -b --noEmit` exit 0、acceptance criteria `grep -n 'onBack:.*=>.*void'` も依然マッチ
- **Committed in:** `daba1af` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 blocking infra/tooling, 1 small bug)
**Impact on plan:** scope creep なし。すべてプラン記載のタスク完了に必要な調整。

## Issues Encountered

- **Pre-existing lint failures (out of scope):** プランの acceptance criterion `cd frontend && bun run lint` exit 0 は、本プラン適用前から 22 errors + 1 warning が存在しており満たせない。`git stash` で本変更を退避して再度 lint を流し、エラー件数が変動しないこと (baseline = post-change = 23 problems) を確認したうえで scope boundary に従い deferred-items.md に記録。本プランで触ったファイルのうち、`App.tsx` と `GemsScreen.tsx` には lint エラーが**ない**。`CanvasScreen.tsx` には 1 件あるが L134 の `useEffect` 内 `setLoading(true)` で、本プラン編集前から存在しており Back ボタン撤去とは無関係。

## Known Stubs

なし。新規スタブ・プレースホルダーは導入していない。

## Self-Check

### Files exist
- FOUND: `frontend/src/App.tsx` (modified — Header に onBackToMenu / appName を追加)
- FOUND: `frontend/src/components/GemsScreen.tsx` (modified — "← Back" ボタン削除)
- FOUND: `frontend/src/components/CanvasScreen.tsx` (modified — "← Back" ボタン削除)
- FOUND: `.planning/phases/40-ui-polish-round-2-frontend-only/40-01-SUMMARY.md` (this file)
- FOUND: `.planning/phases/40-ui-polish-round-2-frontend-only/deferred-items.md`

### Commits exist
- FOUND: `ac7feb7` (Task 1 — feat: wire Header onBackToMenu/appName)
- FOUND: `daba1af` (Task 2 — feat: drop in-screen ← Back buttons)

### Acceptance criteria
- `grep -n 'appName="Gems"' frontend/src/App.tsx` → 1 件 (L175) — PASS
- `grep -n 'appName="Canvas"' frontend/src/App.tsx` → 1 件 (L190) — PASS
- `grep "onBackToMenu={() => navigate('/')}" frontend/src/App.tsx` → 5 件 (SuperChatWrapper / ChatRoute / DebateRoute / GemsScreenRoute / CanvasScreenRoute) — PASS (≥4)
- `grep '← Back' frontend/src/components/GemsScreen.tsx` → 0 件 — PASS
- `grep '← Back' frontend/src/components/CanvasScreen.tsx` → 0 件 — PASS
- h1 "Gems" / h1 "Canvas Apps" 残存 — PASS (GemsScreen.tsx L288-297, CanvasScreen.tsx L157)
- `grep 'onBack:.*=>.*void'` 両ファイル — PASS (型シグネチャ維持)
- MenuScreenRoute に `onBackToMenu` 未配線 — PASS
- `bunx tsc -b --noEmit` exit 0 — PASS

## Self-Check: PASSED

## User Setup Required

なし。frontend-only 変更で外部サービス設定不要。

## Next Phase Readiness

- 40-02 以降 (同フェーズの後続プラン) は本プランの共有 Header パターンに依存しない (frontend UI 細部の磨き込みプランが続く想定)
- 戻るボタン統一の手動確認 (docker compose up → /orochi/gems と /orochi/canvas でヘッダー左端の "‹ メニュー" を視認、画面内重複ボタンが無いこと) はフェーズマージ前のレビュー時に実施
- pre-existing react-hooks/set-state-in-effect lint errors は将来の lint-cleanup phase で対応推奨 (deferred-items.md 参照)

---
*Phase: 40-ui-polish-round-2-frontend-only*
*Plan: 01*
*Completed: 2026-05-13*
