---
phase: 40
plan: 04
subsystem: frontend
tags: [ui, attachments, vision, multimodal]
requires:
  - frontend/src/components/ChatApp.tsx (Phase 36 参照実装)
  - frontend/src/hooks/useAttachments.ts (Phase 36)
  - frontend/src/components/AttachmentButton.tsx (Phase 36)
  - frontend/src/components/AttachmentChips.tsx (Phase 36)
  - frontend/src/components/VisionWarningBanner.tsx (Phase 36)
  - frontend/src/hooks/useChat.ts (getReadyAttachments / onAttachmentsSent options)
  - frontend/src/components/MessageArea.tsx (inputToolbarSlot / inputPreviewSlot / inputWarningSlot props)
provides:
  - SuperChatApp / GemChatApp / CanvasChatApp の AttachmentButton 配線
  - VisionWarningBanner の CTA → onModelChange 経由のモデル切替
affects:
  - frontend/src/App.tsx (SuperChatWrapper / GemChatWrapper / CanvasChatRoute から onModelChange を新規プロップとして注入)
tech-stack:
  added: []
  patterns:
    - "Phase 36 HumanMessage.additional_kwargs サイドカー envelope を 3 アプリで再利用 (backend 変更ゼロ)"
key-files:
  created: []
  modified:
    - frontend/src/components/SuperChatApp.tsx
    - frontend/src/components/GemChatApp.tsx
    - frontend/src/components/CanvasChatApp.tsx
    - frontend/src/App.tsx
decisions:
  - SuperChatAppProps / GemChatAppProps / CanvasChatAppProps の onModelChange は optional (省略可能) で統一 — Debate を含む 4 アプリで signature 揃え、将来 Debate に展開する際の breaking change を回避
  - CanvasChatApp の drop ハンドラは最外コンテナ div (header + MainContainer をラップ) に付与し、drop overlay は zIndex: 100 で CanvasPane 上に被さる (drag-over 中のみ pointer-events: none)
  - Debate Chat は変更なし (debate_handler.py が ChatRequest.attachments を読まないため、UI に出すと黙って捨てられる)
metrics:
  duration: 12min
  completed: 2026-05-13
---

# Phase 40 Plan 04: AttachmentButton + drop/paste を SuperChat / Gem / Canvas に展開 Summary

## One-liner

Phase 36 で ChatApp.tsx にのみ実装された AttachmentButton + useAttachments パイプラインを、SuperChatApp / GemChatApp / CanvasChatApp の 3 アプリへ wiring のみで展開する (Debate は backend 非対応のため Out of Scope)。backend 変更ゼロ、frontend 4 ファイルの 同形パターン複製で完了。

## Status

**Completed:** 3/3 tasks, 0 deviations, 0 deferred items.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | SuperChatApp.tsx + App.tsx に AttachmentButton / drop/paste / VisionWarningBanner を ChatApp.tsx 同形で配線 | `bf61423` | frontend/src/components/SuperChatApp.tsx, frontend/src/App.tsx |
| 2 | GemChatApp.tsx + App.tsx に同じ配線を追加 (Gem ヘッダーバー直下の MainContainer wrapper に drop handlers) | `fcece63` | frontend/src/components/GemChatApp.tsx, frontend/src/App.tsx |
| 3 | CanvasChatApp.tsx + App.tsx に同じ配線を追加 (CanvasPane 競合は drop overlay zIndex: 100 で吸収) | `aecf29d` | frontend/src/components/CanvasChatApp.tsx, frontend/src/App.tsx |

## Verification

- `cd frontend && bun x tsc -b --noEmit` exit 0 (Task 1/2/3 各完了時点)
- Source assertions (acceptance_criteria) すべて満たした:
  - SuperChatApp.tsx: `import { AttachmentButton }` × 1、`useAttachments(` × 1、`getReadyAttachments:` × 1、`onAttachmentsSent:` × 1、`inputToolbarSlot=` × 1、`onDragOver={onDragOver}` × 1、`addEventListener('paste'` × 1、`onModelChange` 参照 6 件 (props interface + props 受け取り + 利用箇所)
  - GemChatApp.tsx: 同上 (`onModelChange={onModelChange}` も `<GemChatApp ...>` 内に確認 — 詳細は下記 "Plan literal note")
  - CanvasChatApp.tsx: 同上、`onModelChange={onModelChange}` が App.tsx CanvasChatRoute に追加 (1 件)
  - DebateChatApp.tsx: `inputToolbarSlot=` 0 件 (Out of Scope 確認)
- App.tsx: `onModelChange={onModelChange}` 出現箇所 10 件 (ChatRoute / CanvasChatRoute / DebateRoute / Menu/Gems/Canvas screen ラッパー + SuperChatWrapper + GemChatWrapper)
- ESLint regression: `setWarningDismissed(false)` を useEffect 内で呼ぶ pattern は ChatApp.tsx (Phase 36 参照実装) から同形で複製。ChatApp.tsx に既存の lint error と完全に同形 (`react-hooks/set-state-in-effect`) のため Phase 40-04 で新規導入された逸脱ではなく、確立済みパターンの propagation。base commit dfbdcdd 時点で frontend 全体に 24 errors + 1 warning が存在し、本 plan 完了時は 26 errors + 1 warning (+2: SuperChat / Gem / Canvas 各 1、ただし1 つは元から存在する `_appName` unused-var)。

## Plan Literal Note (acceptance regex window)

Plan の acceptance_criteria は `grep -A3 'GemChatApp' frontend/src/App.tsx | grep -c 'onModelChange={onModelChange}'` を 1 件以上要求しているが、`<GemChatApp ...>` の props が 5 行に展開されるため、`-A3` の窓では `onModelChange={onModelChange}` 行が含まれない (実体は 5 行目)。`-A6` まで広げると 1 件マッチする。配線そのものは仕様通り完了している。Task 1 の SuperChatWrapper / Task 3 の CanvasChatRoute は `-A3` 内で `onModelChange={onModelChange}` がマッチする。

```text
<GemChatApp                          # line N
  gem={gem}                           # +1
  selectedModel={selectedModel}       # +2
  onBack={() => navigate('/gems')}    # +3  ← -A3 はここまで
  onModelChange={onModelChange}       # +4  ← 実体はここ
/>
```

## Deviations from Plan

None — plan executed exactly as written. 全 3 タスクが Plan の (a)〜(i) ステップに沿って完遂、type-check 全パス。Rule 1-4 の発火なし。

## Authentication Gates

None.

## Files Modified

| File | Change |
|------|--------|
| frontend/src/components/SuperChatApp.tsx | + AttachmentButton/AttachmentChips/VisionWarningBanner/useAttachments/useModels imports、+ onModelChange?: optional prop、+ vision + drop/paste hooks (88 lines)、+ MessageArea slots (33 lines)、+ root div drop handlers + drop overlay + validation banner (72 lines) |
| frontend/src/components/GemChatApp.tsx | 同上 (Gem ヘッダーバー直下の MainContainer wrapper に rootRef / position: relative を付与) |
| frontend/src/components/CanvasChatApp.tsx | 同上 (最外コンテナ div に rootRef を付与、drop overlay zIndex: 100 で CanvasPane 上に表示) |
| frontend/src/App.tsx | SuperChatWrapper / GemChatWrapper / CanvasChatRoute それぞれの子 component 呼び出しに `onModelChange={onModelChange}` を追加 |

## Behavior

After this plan:

- `/orochi/superchat[/:slugOrThreadId[/:threadId]]` で 📎 ボタンが入力欄左に出現
- `/orochi/gemchat/:gemId[/:threadId]` で同じ
- `/orochi/canvaschat[/:threadId]` で同じ (CanvasPane との視覚的競合は drop overlay で吸収)
- 各画面で click / drop / Ctrl+V paste の 3 入り口から staging 可能 (Phase 36 同形)
- vision 非対応モデル + 画像 staging で VisionWarningBanner が表示、CTA で onModelChange 経由でモデル切替
- 送信時 `attachments.getReadyItems()` が ChatRequest body に載り、Phase 36 既存 langgraph_handler / orchestrator_handler のパイプラインで処理 (backend 変更ゼロ)
- 送信成功 (ケース C) で `attachments.clearAll()` が staging を空に、技術失敗 (ケース B) / 明示キャンセル (ケース A) では staging 保持 (D-06 4 ケース挙動を ChatApp と同等で維持)
- Debate Chat (`/orochi/debate[/:threadId]`) には 📎 ボタンが出ない (Out of Scope の意図通り)

## Threat Flags

None — backend に新規 surface ゼロ、`useAttachments` / `postAttachments` 等は Phase 36 で既に確立済みの認証境界 (JWT cookie / per-thread storage + path traversal 防御) を利用するのみ。

## Known Stubs

None — 既存の Phase 36 パイプラインを 3 アプリで参照するだけで、新規の placeholder / TODO / empty state は導入していない。

## Self-Check: PASSED

- frontend/src/components/SuperChatApp.tsx: FOUND
- frontend/src/components/GemChatApp.tsx: FOUND
- frontend/src/components/CanvasChatApp.tsx: FOUND
- frontend/src/App.tsx: FOUND
- commit bf61423 (Task 1): FOUND in git log
- commit fcece63 (Task 2): FOUND in git log
- commit aecf29d (Task 3): FOUND in git log
- Debate untouched: frontend/src/components/DebateChatApp.tsx に inputToolbarSlot 出現なし (0 件)
