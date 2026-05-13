---
created: 2026-05-13T13:42:00Z
title: Gems/Canvas 画面の戻るボタン位置を Chat/SuperChat と揃える
area: ui
files:
  - frontend/src/components/GemsScreen.tsx:289-300
  - frontend/src/components/CanvasScreen.tsx:159-171
  - frontend/src/components/Header.tsx:84-86
  - frontend/src/components/ChatApp.tsx
  - frontend/src/components/SuperChatApp.tsx
---

## Problem

`GemsScreen` と `CanvasScreen` の「← Back」ボタンが、`ChatApp` / `SuperChatApp` の戻るボタンと位置・スタイルが揃っていない。

- ChatApp / SuperChatApp: 共有 `<Header onBackToMenu={...}>` を使用 (`Header.tsx:84-86`) — ヘッダー左端に統一スタイルで配置
- GemsScreen: 画面内に独自実装の `← Back` ボタン (`GemsScreen.tsx:289, 300`) — Header コンポーネントを使っていない
- CanvasScreen: 画面内に独自実装の `← Back` ボタン (`CanvasScreen.tsx:159, 171`) — 同上

結果として、メニュー画面間を移動するたびに戻るボタンが画面上で「飛ぶ」ように見え、UX 上の一貫性を欠く。

## Solution

TBD。検討案:

1. **GemsScreen / CanvasScreen にも `<Header>` を導入** し、`onBackToMenu` 経由で統一する (推奨)
   - GemChatApp / CanvasChatApp は既に Header を使っているので、その上位画面 (Screen) も合わせる
   - Header には `appName` prop で「Gems」「Canvas」を表示できる
2. もしくは GemsScreen / CanvasScreen の独自ボタンを Header と同じ position (top-left, fixed) と style に揃える
3. Chat/SuperChat 側を変える選択肢は採らない (共通 Header 維持)

関連: Phase 35 dashboard design system / Phase 39 UIFIX-04 で polish 枠を確保したが、本件は scope 外として後追い対応。

Phase 39 Code Review WR-02 (Header の dark mode 漏れ) と一緒に修正すると効率的。
