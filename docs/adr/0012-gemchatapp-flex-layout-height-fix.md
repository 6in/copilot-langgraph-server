# 0012. GemChatApp フレックスレイアウト修正 — height:100% から flex:1/minHeight:0 へ

**Date:** 2026-04-07  
**Status:** Accepted

## Context

`GemChatApp` の画面で、チャット入力エリアがビューポート外に押し出されてスクロール不可になる不具合が発生していた。

`App.tsx` では `GemChatApp` を以下の構造で描画している:

```
App div (display: flex, flex-direction: column, height: 100%)
├── <Header /> ← モデル選択・テーマ切替など
└── <GemChatApp /> ← 問題の箇所
```

`GemChatApp` の外側 div に `height: '100%'` を設定していたため、App コンテナの**全高**を占有してしまっていた。フレックス子アイテムにおける `height: 100%` はフレックスコンテナの高さ（= ビューポート全体）を参照するため、`Header` の高さ分だけコンテンツがはみ出してしまう。その結果:

1. `GemChatApp` 内部の `MainContainer` が想定より大きな高さを持つ
2. 入力エリア（`chat-input-bar`）がビューポート外に押し出される
3. メッセージリストのスクロールが機能しない

`ChatApp` および `SuperChatApp` は同じ App 構造内で正常に動作しており、それらは `height: '100%'` ではなく `flex: 1, minHeight: 0` を使っていた。

## Decision

`GemChatApp` の外側 div のスタイルを `ChatApp` と同じパターンに統一する:

```diff
- <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
+ <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
```

- `flex: 1` — フレックスコンテナ内でヘッダーの残りスペースをすべて占有
- `minHeight: 0` — フレックスアイテムのデフォルト `min-height: auto` による無制限伸長を抑制

## Alternatives Considered

**`height: calc(100% - <Header高さ>px)` を使う:** ヘッダーの高さをハードコードする必要があり、ヘッダーサイズが変化した際に壊れる。採用しない。

**`overflow: hidden` を外側 div に追加するだけ:** 高さの問題の根本解決にならない。入力エリアのはみ出しは残る。採用しない。

## Consequences

**良い点:**
- `ChatApp` / `SuperChatApp` / `GemChatApp` の全画面でレイアウトパターンが統一される
- 入力エリアが常にビューポート内に固定表示され、メッセージリストが正常にスクロールする

**注意点:**
- フレックスレイアウトにおける `height: 100%` と `flex: 1` の違いは直感に反しやすい。`height: 100%` はフレックスアイテムとして兄弟要素（ヘッダー等）の存在を無視してコンテナ全高を取ろうとする。`flex: 1` はフレックスアルゴリズムが残余スペースを正しく配分する。
- `minHeight: 0` は必須。省略するとフレックスカラム内で子要素のコンテンツ高さが `min-height: auto` として解決され、コンテナから溢れる場合がある（chatscope の `MessageList` のように内部で高さが積み上がるコンポーネントで顕著）。
- `GemChatApp` は内部に独自ヘッダーバー（48px、`flexShrink: 0`）を持つ。外側 div を `flex: 1, minHeight: 0` にすることで、外部ヘッダー（App.tsx の `<Header>`）との2段ヘッダー構成でも正常に高さが配分される。
