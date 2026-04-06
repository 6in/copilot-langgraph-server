# 0009. Gem UX 強化 — 専用ナビゲーション・スレッド分離・description/knowledge フィールド

**Date:** 2026-04-06  
**Status:** Accepted

## Context

Phase 15 で Gem（カスタム AI アシスタント）の基本 CRUD と Canvas 機能を実装したが、以下の UX 問題が残っていた：

1. **GemSelector が ChatApp/SuperChatApp に混在** — Gem を選んでチャットする UI が汎用チャット画面に埋め込まれており、Gem の使い方として直感的でなかった。
2. **Gem 専用チャット画面がない** — 選択した Gem を起動する独立した画面がなく、スレッド管理も Gem 単位で分離されていなかった。
3. **Gem の説明情報が欠如** — Gem カードには system_prompt の先頭しか表示できず、用途を一目で把握できなかった。また、ドメイン知識を静的コンテキストとして付与する `knowledge` フィールドも存在しなかった。
4. **スレッド分離の実装上の落とし穴** — `useChat` の `appId` に `gem-{id}` を渡すと、DB の applications テーブルに FK 制約で弾かれるという問題があった。

## Decision

### ナビゲーション設計

`App.tsx` に `type Screen = 'menu' | 'superchat' | 'gems' | 'gemchat'` の enum を導入し、4画面ナビゲーションを実装した。

- **MenuScreen** に「💎 Gems」固定カードを `apps.map()` の外側に独立配置（動的アプリ一覧と混在させない）
- **GemsScreen** で Gem の CRUD 管理ハブとして機能し、「チャット開始」ボタンから GemChatApp へ遷移
- **GemChatApp** を新規作成（ChatApp と同パターン）— Back ボタンで必ず GemsScreen に戻る

### スレッド分離

`useThreads('gem-${gem.gem_id}')` で Gem 単位のスレッドフィルタリングを実現。ただし `useChat` の `appId` に `gem-xxx` を渡すと applications FK 制約に弾かれるため、`useChat` からは `appId` を渡さず、バックエンドの `GET /api/threads` に `gem_id` クエリパラメータを追加してフィルタリングする方式に切り替えた。

### description / knowledge フィールド

- `description`（VARCHAR 200）: Gem の用途説明。カード表示に使用（system_prompt の代替）
- `knowledge`（TEXT）: ドメイン知識をシステムプロンプトに `## 知識\n{knowledge}` セクションとして結合して渡す

バックエンド: `ADD COLUMN IF NOT EXISTS` で冪等なスキーマ変更（Alembic 不使用）  
フロントエンド: GemsScreen に Description（単行 input, maxLength=200）と Knowledge（textarea rows=3）を追加

## Alternatives Considered

- **GemSelector を ChatApp に残す** — Gem 選択を既存チャット画面に組み込む方式。実装は少ないが、Gem ごとのスレッド管理が複雑になり、UX の文脈が不明確になるため棄却。
- **useChat の appId に gem-xxx を渡す** — 当初の実装。applications FK 制約で INSERT が失敗した。appId はスレッド作成時の applications テーブル FK に使われるため、任意文字列を渡せない。バックエンドフィルタ方式に変更。
- **GemChatApp の Back ボタンを App.tsx Header で処理** — Header の `onBackToMenu` を流用する案。gemchat 画面では「GemsScreen へ戻る」が正しい遷移先であり、「MenuScreen へ戻る」とは異なる。GemChatApp 内部に `onBack` コールバックを持たせることで、遷移先を明示的に制御した。

## Consequences

**正の影響:**
- Gem の使い方が明確な画面フローで表現され、直感的なナビゲーションが実現した
- Gem 単位でスレッドが分離されるため、異なる Gem の会話が混在しない
- `knowledge` フィールドにより、ドメイン知識を持つ専門 AI として Gem を構成できる

**注意点・落とし穴:**
- `useChat` の `appId` に `gem-xxx` 形式の任意文字列を渡してはいけない。applications テーブルの FK 制約で弾かれる。Gem スレッドのフィルタは `GET /api/threads?gem_id=xxx` で行う。
- GemChatApp の Back ボタン遷移先は GemsScreen（`setCurrentScreen('gems')`）。MenuScreen まで戻すと、どの Gem からチャットしていたかコンテキストが失われる。
- Gems 固定カードは `apps.map()` の外側の独立グリッドに置くこと。動的アプリ一覧の中に混ぜると、アプリ追加/削除時にカードが消える。
- スレッドラベルのタイムスタンプは JST で生成する（UTC のまま表示すると UI 上で9時間ずれる）。
