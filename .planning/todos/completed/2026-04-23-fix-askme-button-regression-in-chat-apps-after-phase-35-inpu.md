---
created: 2026-04-23T06:09:19.635Z
resolved: 2026-05-13
resolution: Phase 39 Plan 39-05 (D-07) で完全修正。5 chat apps (Chat/SuperChat/Gem/Canvas/Debate) の `<MessageArea>` に `onAskMe={() => {}}` 配線を復活させ commit `fcd4534` で landed。実機検証も完了 (chrome-devtools で .chat-askme-btn 描画確認済)。
title: AskMe ボタンが全チャットアプリで描画されない regression を修正
area: ui
files:
  - frontend/src/components/InputBar.tsx:15,155-177
  - frontend/src/components/MessageArea.tsx:36,142,188-189,418
  - frontend/src/components/ChatApp.tsx:175
  - frontend/src/components/SuperChatApp.tsx:293
  - frontend/src/components/GemChatApp.tsx:207
  - frontend/src/components/CanvasChatApp.tsx:305
  - frontend/src/components/DebateChatApp.tsx:782
---

## Problem

AskMe ボタン（AskUserQuestion / AUQ 起動用、Phase 27 実装）が全チャットアプリで描画されなくなっている。

**原因:** Phase 35 の `35-03-messagearea-inputbar-split` で InputBar を MessageArea から分離した際、各チャットアプリから MessageArea に `onAskMe` prop を渡す配線が欠落した。

- `InputBar.tsx:15` で `onAskMe?: () => void` 型定義は残っている
- `InputBar.tsx:155-177` の描画条件 `onAskMe && !isThinking` が `onAskMe` undefined で常に false
- `MessageArea.tsx:36,142,188-189,418` で親からの callback を受けて `handleAskMeWrapped` で AUQ suffix 付与する実装は残っている
- **ChatApp / SuperChatApp / GemChatApp / CanvasChatApp / DebateChatApp のいずれも `<MessageArea onAskMe={...} />` を渡していない** — 5 コンポーネント全部

結果として AUQ は LLM 側から呼び出せる経路は存続しているが、ユーザーが手動で起動する UI が消えた状態。Phase 35 VERIFICATION と HUMAN-UAT では拾い切れていない（AUQ ユーザー起動の確認項目がなかった）。

## Solution

### 最小修正（推奨）

5 つのチャットアプリで `useChat` から返る AUQ 起動ハンドラ（または同等の wrapping）を MessageArea に `onAskMe={handler}` として渡す。

- `frontend/src/components/ChatApp.tsx:175` の `<MessageArea ...>` に追加
- `frontend/src/components/SuperChatApp.tsx:293` 同
- `frontend/src/components/GemChatApp.tsx:207` 同
- `frontend/src/components/CanvasChatApp.tsx:305` 同
- `frontend/src/components/DebateChatApp.tsx:782` 同

### 検証手順

1. ChatApp で thread 開いて InputBar に AskMe ボタンが表示される
2. クリックで AUQ suffix 付きの送信が走る（Phase 27 同様）
3. SuperChat / Gem / Canvas / Debate でも同様の挙動
4. `isThinking` 中はボタン非表示になること

### 配置先の選択肢

- **Phase 39（UI バグ潰し + Polish 枠）** の success criteria 4「v6.0 期間中に発覚した小 UI バグが一覧化され、polish 枠で消化」に合致 — 正式な受け皿
- 軽微 fix として `/gsd-quick` 単発処理も可（5 コンポーネントへの 1 行追加）

### 関連

- Phase 35 artifacts: `35-03-messagearea-inputbar-split-SUMMARY.md`（opaque callback pattern 明記）/ `35-UI-SPEC.md:65,95,287,315,316,382`（AskMe ボタン color token 規定）
- Phase 27（AskUserQuestion 実装）の AUQ ハンドラが依然として backend に残っていることを前提
