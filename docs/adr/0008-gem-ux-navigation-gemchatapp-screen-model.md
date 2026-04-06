# 0008. Gem UX ナビゲーション — GemsScreen・GemChatApp・4画面スクリーンモデル

**Date:** 2026-04-06  
**Status:** Accepted

## Context

Phase 15 で Gem（AI ペルソナ）と Canvas アプリ機能を実装した際、Gem の選択 UI は `GemSelector` チップとして `ChatApp` / `SuperChatApp` の入力エリアに埋め込まれていた。しかし以下の問題があった:

1. **UX の断片化:** Gem の作成・編集・削除は別の管理画面 (`/gems` API) を想定していたが、フロントエンドに管理 UI がなく、Gem を CRUD する手段がなかった。
2. **コンテキスト汚染:** Gem を選択した状態で ChatApp を使うと、スレッドが Gem スコープなのか通常スコープなのかが不明確だった。
3. **GemSelector の配置問題:** MessageArea の入力エリアに GemSelector チップを置く設計は、チャット中に誤って Gem を切り替えるリスクがあった。

Phase 15.1 の目標は「Gem を独立した管理・チャット画面として切り出し、MenuScreen からエントリーポイントを提供する」こと。

## Decision

**スクリーンモデルを4画面に拡張し、Gem 専用フローを独立させる。**

- `App.tsx` の `Screen` 型を `'menu' | 'chat' | 'superchat' | 'gems' | 'gemchat'` に拡張
- `GemsScreen` — Gem の CRUD 管理ハブ。カードリスト + インライン編集 + 削除確認 + 新規作成フォームを1コンポーネントに収める
- `GemChatApp` — Gem スコープのチャット専用コンポーネント。`useThreads('gem-{gem_id}')` でスレッドを Gem 単位に分離し、`useChat({ gemId })` で `gem_id` をバックエンドに渡す
- `MenuScreen` に Gems 固定カードを追加（`apps.map()` とは独立して常に表示）
- `ChatApp` / `SuperChatApp` から `GemSelector` を完全撤去

## Alternatives Considered

- **GemSelector チップを維持してインプレース切替を提供:** チャット中に Gem を変えると同一スレッドにシステムプロンプトの異なるメッセージが混在するため却下。スレッド単位で Gem を固定するほうが整合性が高い。
- **MenuScreen に Gem 管理モーダルを置く:** CRUD 操作はモーダルより専用画面のほうが操作しやすく、将来の機能追加（説明・知識フィールドなど）にも対応しやすいため却下。
- **既存の ChatApp を Gem モード対応に拡張（`gemId` プロップ追加）:** ChatApp は ChatApp・SuperChat 共用の複雑な状態を持つため、Gem 専用の軽量コンポーネントとして分離するほうが保守性が高い。

## Consequences

**正の影響:**
- Gem チャットのスレッドが `gem-{gem_id}` スコープで分離され、通常チャットと混在しない
- Gem CRUD 管理が1画面に集約され、ユーザーが Gem を作成・編集・削除しやすくなった
- `GemSelector.tsx` を削除してコードベースが簡素化された

**注意点・落とし穴:**

1. **Header の `onBackToMenu` との競合（Pitfall 4）:** `gemchat` 画面では App.tsx の Header に `onBackToMenu` を渡さない。GemChatApp → GemsScreen への戻りは GemChatApp 内部の Back ボタン（`onBack` コールバック）で処理する。Header に `onBackToMenu` を渡すと MenuScreen に直接戻ってしまい GemsScreen をスキップする。

2. **MenuScreen の Gems カード配置（Pitfall 5）:** Gems カードは `apps.map()` ループの外側にレンダリングする。ループ内に置くと `apps.length === 0`（API ロード中・エラー時）にカードが表示されない。

3. **MessageArea の外側 div 保持（Pitfall 3）:** GemSelector のレンダリングブロックを削除する際、wrapper `<div style={{ flexDirection: 'column', flex: 1 }}>` は残す。この div は GemSelector とは独立したレイアウト用コンテナで、削除するとチャットエリアのレイアウトが崩れる。

4. **GemChatApp のチャット履歴は現状メモリのみ:** `useThreads('gem-{gem_id}')` でスレッドは作成・永続化されるが、画面を閉じて戻ると前回のスレッドを自動ロードする UI がない。Todo に積んだ将来対応項目。

5. **`useThreads` の `appId` 型を `string` に緩めた:** 元は `'chat' | 'superchat'` のリテラルユニオンだったが、Gem スコープの `'gem-{gem_id}'` を渡すために `string` に変更。既存の ChatApp / SuperChatApp の動作に影響なし。
