---
phase: 40
plan: 05
subsystem: frontend
tags: [ui, routing, thread-lifecycle, ux]
requires:
  - frontend/src/hooks/useThreads.ts (createNewThread)
  - frontend/src/App.tsx (buildSuperChatPath / DEFAULT_SUPERCHAT_SLUG — Plan 40-03)
  - frontend/src/components/ChatApp.tsx (Phase 25 URL sync useEffect)
  - frontend/src/components/SuperChatApp.tsx (Plan 40-03 適用後)
provides:
  - ChatApp 初回 mount で自動的に新規 thread を作成し /chat/{uuid} に遷移
  - SuperChatApp 初回 mount で自動的に新規 thread を作成し /superchat/{uuid} (default app 短縮形) に遷移
affects:
  - frontend/src/components/ChatApp.tsx (auto-create useEffect + initThreadInFlightRef)
  - frontend/src/components/SuperChatApp.tsx (auto-create useEffect + initThreadInFlightRef)
tech-stack:
  added: []
  patterns:
    - "AND 3 条件 + useRef in-flight gate による初回 mount 限定の副作用パターン (リロード/ブラウザバックで再発火しない)"
    - "navigate(replace: true) で auto-create による URL 変更を履歴に残さない (前段 /chat と作成後 /chat/{uuid} で戻る押下が機能しなくなる事象を回避)"
key-files:
  created: []
  modified:
    - frontend/src/components/ChatApp.tsx
    - frontend/src/components/SuperChatApp.tsx
decisions:
  - "auto-create useEffect は既存の URL sync useEffect (Phase 25) の直後に配置し、URL/state の同期完了後に発火させる — マウント時点で URL に threadId が含まれる場合は switchThread 経由で activeThreadId が即セットされるため、auto-create の `activeThreadId !== null` ガードが通って二重作成を防ぐ"
  - "SuperChat 側の navigate 先は buildSuperChatPath(appId || DEFAULT_SUPERCHAT_SLUG, tid) を経由 — Plan 40-03 の default app 短縮 URL (/superchat/{uuid}) を維持し、/superchat/superchat/{uuid} のような冗長 path への回帰を防ぐ"
  - "Gem / Canvas / Debate は Plan の Out of Scope — todo #10 が `Chat / SuperChat のみ` と明示しており、加えて Debate は backend の thread 復元未対応 (todo `Debate Chat で URL 直接アクセス時に過去スレッドの履歴を復元する` が未着手) のため auto-create の前提が成立しない"
  - "depencency array に messages.length のみを入れる (messages 配列そのものを入れない) — 再 render 時に参照が変わる array literal で再発火させない最小依存"
metrics:
  duration: 18min
  tasks: 2
  files: 2
  completed: 2026-05-13
---

# Phase 40 Plan 05: Chat/SuperChat 初回表示時に新規 thread を自動作成 Summary

## One-liner

ChatApp / SuperChatApp の初回 mount (URL に threadId なし + activeThreadId null + messages 空) で `createNewThread()` + `navigate(..., { replace: true })` を自動実行する useEffect を追加し、ThreadSidebar の「+ 新しいチャット」を押した状態と同等の UX に揃える。リロード・ブラウザバック・既存 thread 切替時の二重作成は `initThreadInFlightRef` + AND 3 条件で防ぐ。SuperChat 側は Plan 40-03 の `buildSuperChatPath` 経由で default app 短縮 URL を保つ。

## Status

**Completed:** 2/2 tasks, 1 plan-side acceptance criterion off-by-one observation, 0 Rule 1-4 deviations.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | ChatApp.tsx に auto-create useEffect + `initThreadInFlightRef` を追加 (URL sync useEffect の直後) | `9022584` | frontend/src/components/ChatApp.tsx |
| 2 | SuperChatApp.tsx に同形の auto-create useEffect (buildSuperChatPath 経由) | `3b79019` | frontend/src/components/SuperChatApp.tsx |

## Verification

### Automated

- `cd frontend && bunx tsc -b --noEmit` → exit 0 (Task 1 / Task 2 各完了時点)
- `cd frontend && bun run lint` → 26 problems (25 errors, 1 warning) — base commit `9aae212` と**完全に同数**。本 plan で**新規 lint error は導入していない**ことを `git stash` 前後の差分で確認 (詳細は Out-of-Scope セクション)。

### Source assertions (per task)

**Task 1 (ChatApp.tsx):**

```
initThreadInFlightRef:      4 (>=2 OK — declaration + read + write + finally の reset)
urlThreadId !== undefined:  1 (>=1 OK)
activeThreadId !== null:    2 (>=1 OK — auto-create guard + URL sync コメント)
messages.length !== 0:      1 (>=1 OK)
navigate(`/chat/:           4 (>=2 OK — 既存 handleNewChat + handleSend + auto-create の合計)
replace: true:              3 (>=2 OK — handleNewChat + handleSend + auto-create)
Phase 40 UI-INIT-THREAD:    1 (>=1 OK)
```

**Task 2 (SuperChatApp.tsx):**

```
initThreadInFlightRef:      4 (>=2 OK)
urlThreadId !== undefined:  1 (>=1 OK)
activeThreadId !== null:    2 (>=1 OK)
messages.length !== 0:      1 (>=1 OK)
buildSuperChatPath(:        4 (>=4 OK — Plan 03 の handleNewChat/handleSelectThread/handleSend + Plan 05 auto-create)
replace: true:              3  (Plan 期待値は >=4 だが実体は 3 — 後述 "Plan-side acceptance off-by-one" 参照)
Phase 40 UI-INIT-THREAD:    1 (>=1 OK)
```

**Scope negation (Out-of-Scope 確認):**

```
Phase 40 UI-INIT-THREAD in GemChatApp.tsx:     0 (期待 0 OK)
Phase 40 UI-INIT-THREAD in CanvasChatApp.tsx:  0 (期待 0 OK)
Phase 40 UI-INIT-THREAD in DebateChatApp.tsx:  0 (期待 0 OK)
```

### Manual verification (must_haves.truths)

手動 Test 1〜6 は frontend-only 変更のため、`docker compose up` 後にユーザーが UI で観察すべき要素。Plan の `must_haves.truths` 6 件すべてのソース条件は本 plan の useEffect 構造で保証される:

| Truth | 充足理由 |
|-------|---------|
| `/orochi/chat` (threadId なし) 初回ロードで /chat/{uuid} に自動遷移 | ChatApp auto-create useEffect: AND 3 条件すべて初回 mount で `true` (urlThreadId undefined + 初期 activeThreadId null + 初期 messages 空) |
| `/orochi/superchat` (Plan 03 短縮 URL) 初回ロードで /superchat/{uuid} に自動遷移 (default app 短縮形維持) | SuperChatApp auto-create useEffect: navigate 先が `buildSuperChatPath(appId \|\| DEFAULT_SUPERCHAT_SLUG, tid)` のため、default app の場合 `/superchat/{uuid}` を生成 (Plan 40-03 `buildSuperChatPath` 実装による) |
| 既存 thread (URL に threadId あり) では自動作成されない | `urlThreadId !== undefined` ガードで return |
| リロード (F5) で URL に threadId あれば自動作成されない | リロード時 URL sync useEffect が switchThread 実行 → activeThreadId が即セット → auto-create の `activeThreadId !== null` ガードで return |
| ブラウザバックで /chat に戻った時に二重作成されない | back で /chat に遷移しても`activeThreadId !== null` (back 時点ではまだ前 thread が active) → ガード成立。仮にレース条件で通過しても `initThreadInFlightRef.current` が他の発火で `true` のため return |
| sidebar 削除後 activeThreadId null + URL が /chat になった時に再発火 | removeThread が activeThreadId を null に + navigate('/chat') すると、AND 3 条件すべて再度成立 → auto-create が起動 (期待する挙動) |

## Deviations from Plan

### Observation 1: Plan-side acceptance criterion `replace: true >= 4` is an off-by-one

Task 2 の acceptance_criteria が `grep -c 'replace: true' frontend/src/components/SuperChatApp.tsx` を **4 件以上**と要求しているが、Plan 40-03 完了時点の実態は 2 件 (handleNewChat + handleSend) であり、handleSelectThread は意図的に `replace: true` を付けない (ユーザーが履歴から thread をクリックする操作はブラウザ履歴に積まれるべき)。Plan 05 で 1 件追加 → 合計 3 件。

- 種類: Plan-side acceptance criterion の計算違い (Rule 1-4 のどれにも該当しない、コード側の defect ではない)
- 影響: 機能 spec (must_haves.truths) はすべて満たすため UX として regress なし
- 対応: 修正不要。SUMMARY に記載のみ。

### Rule 1-4 deviations

なし — 両タスクとも Plan の (a)〜(d) ステップ通りに実装。

## Authentication Gates

なし — frontend-only 変更、auth 触らず。

## Files Modified

| File | Change |
|------|--------|
| frontend/src/components/ChatApp.tsx | + URL sync useEffect の説明コメント (Phase 40 言及)、+ `initThreadInFlightRef` 宣言、+ auto-create useEffect (15 行) |
| frontend/src/components/SuperChatApp.tsx | + URL sync useEffect の説明コメント (Phase 40 言及)、+ `initThreadInFlightRef` 宣言、+ auto-create useEffect (15 行、`buildSuperChatPath` 経由) |

## Behavior

### Before

- `/orochi/chat` を初めて開くと sidebar に空 thread リストが表示されるが、画面中央のメッセージリストは「中ぶらりん」(activeThreadId null、入力欄は有効だが thread 未紐付けでメッセージ送信時に初めて作成)。
- ユーザーは「`+ 新しいチャット`」を能動的に押さないと thread が作られず、UX が直感に反する。
- SuperChat 側も同様で、Plan 40-03 で短縮 URL (`/orochi/superchat`) を導入したが、これも同じ中ぶらりん状態に遭遇する。

### After

- `/orochi/chat` 初回 mount → `createNewThread()` → URL が `/orochi/chat/{uuid}` に置換 (history pollute せず) → ThreadSidebar に新規 thread が表示 → メッセージリストは空、入力欄 enabled → 「`+ 新しいチャット`」を押した状態と同等。
- `/orochi/superchat` 初回 mount → `createNewThread()` → URL が `/orochi/superchat/{uuid}` (`/orochi/superchat/superchat/{uuid}` ではない) に置換 → 以下同様。
- リロード / ブラウザバック / 既存 thread 切替時は AND 3 条件で auto-create が return → 二重作成なし。

## Out-of-Scope Discoveries

### Pre-existing lint errors (deferred)

`cd frontend && bun run lint` は base commit `9aae212` 時点で既に **26 problems (25 errors, 1 warning)** を報告する。内訳は主に `react-hooks/set-state-in-effect` と `react-hooks/purity`:

- `ChatApp.tsx:119:5` — `setWarningDismissed(false)` を useEffect 内で呼ぶパターン (Phase 36 由来)
- `SuperChatApp.tsx:168:5` — 同上 (Phase 40-04 で同形 propagate)
- `useThreads.ts:44:5` — `refreshThreads()` を mount useEffect で呼ぶ (Phase 7 由来)
- `useModels.ts:17:15` + `useModels.ts:25:7` — let-based cache pattern (Phase 36)
- 他 CanvasChatApp / CanvasPane / GemChatApp / Header / MessageArea / preview/* / useAgents / useAttachments / useChat / useGems で同種の警告

**Scope 判断:** これらはすべて事前から存在する違反であり、本 plan の AND 条件 useEffect とは異なる pattern (本 plan は `setState` を effect 本体に置かず async IIFE 内で `navigate` を呼ぶのみ — `initThreadInFlightRef.current = true` は ref mutation で setState ではない)。base と本 plan 完了後で問題数 26 が**完全一致**することは `git stash` で確認済 (lint 出力同一)。

**対応:** 本 plan では fix しない。v6.1+ の lint cleanup phase または専用 quick task で `useEffectEvent` への移行を検討するのが妥当 (todo backlog 候補)。

## Key Decisions

1. **AND 3 条件 + useRef gate のレイヤード防御** — Plan の context block で示唆された通り、`urlThreadId !== undefined` (URL に既に thread), `activeThreadId !== null` (state 上 active thread あり), `messages.length !== 0` (既存メッセージ復元中) のいずれか 1 つでも成立すれば return。さらに React 19 strict-mode の useEffect 二重発火対策として `initThreadInFlightRef` で同期的に発火回数を 1 回に固定。
2. **`navigate(replace: true)`** — auto-create で `/chat` → `/chat/{uuid}` の URL 遷移を**履歴に積まない**ことで、ユーザーがブラウザバックで `/chat` (空 URL) に戻った瞬間に再度 auto-create が走る挙動を回避 (Plan 30-02 で確立した pattern を再利用)。
3. **`buildSuperChatPath(appId || DEFAULT_SUPERCHAT_SLUG, tid)`** — Plan 40-03 で導入された default app 短縮 URL 生成関数を auto-create でも経由することで、`/orochi/superchat/superchat/{uuid}` という冗長 path への regression を防ぐ。`appId` が `'superchat'` の場合は `buildSuperChatPath` 側で `DEFAULT_SUPERCHAT_SLUG` チェックが働き、自動的に短縮形が生成される。

## Self-Check: PASSED

- ChatApp.tsx に auto-create useEffect が存在: `grep -c 'Phase 40 UI-INIT-THREAD' frontend/src/components/ChatApp.tsx` → 1 ✓
- SuperChatApp.tsx に auto-create useEffect が存在: `grep -c 'Phase 40 UI-INIT-THREAD' frontend/src/components/SuperChatApp.tsx` → 1 ✓
- SuperChat の auto-create が `buildSuperChatPath` 経由 (Plan 03 regression なし): `grep -A 14 'initThreadInFlightRef = useRef' frontend/src/components/SuperChatApp.tsx | grep -c 'buildSuperChatPath'` → 1 ✓ (auto-create block 内に navigate(buildSuperChatPath(...)) が確認できる)
- Gem / Canvas / Debate に変更なし: `git diff 9aae212..HEAD --name-only frontend/src/components/` → `ChatApp.tsx` と `SuperChatApp.tsx` のみ ✓
- Commit 9022584 存在: ✓
- Commit 3b79019 存在: ✓
- typecheck exit 0: ✓
