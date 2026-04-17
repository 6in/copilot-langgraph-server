# 0039. AskUserQuestion — AI-UI 対話的質問プロトコル

**Date:** 2026-04-18  
**Status:** Accepted

## Context

AI エージェントがユーザーに選択肢や確認を提示したい場合、プレーンテキストで質問を書くしかなかった。ユーザーは自由入力で回答する必要があり、構造化データとして回答を受け取れないため、AI 側の解釈ミスが起きやすかった。

LangGraph のグラフ構造上、`interrupt()` のようなネイティブな対話機構はフロントエンドの SSE + ジョブキューアーキテクチャと相性が悪く、バックエンド側で会話をブロックする方式は採用できなかった。

## Decision

**システムプロンプト注入 + フロントエンド検出方式**を採用した。

1. **バックエンド**: `AUQ_PROTOCOL` をシステムプロンプトに注入し、AI に `<ask_user_question>` XML タグで構造化質問（single/multi/text）を出力させる
2. **フロントエンド**: ジョブ結果受信時に `<ask_user_question>` タグを検出し、`QuestionPanel` コンポーネントで選択肢 UI を表示。回答はテキスト化して既存チャットフローで送信
3. **AskMe ボタン**: Send ボタンの隣に配置し、ユーザーが明示的に AUQ フォーマットでの回答を AI に要求できる

### 重要な実装詳細

- **`orchestrator_result` アンラップが必須**: SuperChat 経由の応答は `{"type": "orchestrator_result", "content": "..."}` で JSON ラップされる。`<ask_user_question>` タグはエスケープされた `content` フィールド内にあるため、外側の JSON を先にパースして `content` を取り出してから AUQ 検出を行う必要がある。これを怠ると `parseAUQ` の `JSON.parse` がエスケープ済みクォート（`\"`）で失敗する
- **検出は 4 箇所で統一**: SSE `done` ハンドラ、即座完了チェック、polling フォールバック、`parseJobResult` 関数の全てで `orchestrator_result` アンラップ → AUQ 検出の順序を守る
- **履歴ロード時のタグ除去**: `loadThreadMessages`（`client.ts`）で DB から読み込んだメッセージの `<ask_user_question>` タグをストリップし、「質問パネルが表示されました」に置換する。ライブレスポンスでは除去しない（`MarkdownMessage` ではなく `client.ts` で処理する）

## Alternatives Considered

### LangGraph `interrupt()` ベース
グラフ実行を中断してユーザー入力を待つネイティブ方式。SSE + arq ジョブキューでは worker がブロックされ、スケーラビリティに影響するため不採用。

### WebSocket 双方向通信
リアルタイム対話には最適だが、既存アーキテクチャが SSE 前提で構築されており、移行コストが大きすぎるため不採用。

### バックエンド側で AUQ を検出して専用レスポンス型を返す
`job_store` に保存する前に AI 出力をパースし、`{"type": "auq", "questions": [...]}` として保存する方式。バックエンド変更が大きく、既存の Canvas/Debate 結果型との整合性確保が必要になるため、フロントエンド検出の方がシンプルだった。

## Consequences

### Positive
- バックエンド変更が最小限（システムプロンプト追加のみ）
- 全 5 アプリ（Chat/SuperChat/GemChat/CanvasChat/DebateChat）で統一的に動作
- AI がプロトコルに従わない場合でもフォールバックでプレーンテキスト表示される（graceful degradation）

### Negative
- AI モデル（Copilot）が `<ask_user_question>` フォーマットに常に従うとは限らない — AskMe ボタンで明示的に要求する回避策を用意
- `orchestrator_result` ラッパーの存在を忘れると AUQ 検出が壊れる — SuperChat 経由のテストを必ず含めること
- 履歴ロード時の AUQ タグ処理を `MarkdownMessage`（レンダリング層）で行うとライブレスポンスも影響を受ける — 必ず `client.ts`（データ取得層）で行うこと
- react-markdown v10 で `code` コンポーネントへの `className` 渡しが不安定 — `pre` コンポーネントで hast ノードから直接言語を取得する方式に変更済み
