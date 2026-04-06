# 0011. マルチエージェント討論チャット — ターン制会話プラットフォーム

**Date:** 2026-04-06  
**Status:** Accepted

## Context

複数の Gem / SubAgent をターン制で会話させる新アプリ「討論チャット（DebateChatApp）」を Phase 17 で実装した。ユーザーがパターン（debate/panel/chain）と参加エージェントを選択し、お題を投稿すると、指定ターン数でエージェント同士が順番に発言する。

既存の OrchestratorGraph / SuperChatApp はオーケストレーターが1つのタスクを複数のサブエージェントに振り分ける構造だが、討論チャットは「各エージェントが同じトピックについて順番に主張を述べる」という別トポロジーを必要とした。

## Decision

### グラフ設計
- `DebateGraph` を OrchestratorGraph とは独立した新しい `StateGraph` として実装（`app/graph/debate_builder.py`）
- `DebateState` を独自 TypedDict で定義（`AgentState` から継承しない）。`turns: list[dict]`、`current_agent_idx`、`awaiting_extension` を含む
- 3パターン（debate/panel/chain）は同一の `build_debate_graph()` ファクトリ関数でエッジ分岐により対応

### ハンドラー
- `task_type="debate"` を新規登録し `DebateHandler` を実装（`app/jobs/debate_handler.py`）
- `astream` ループで各ターンを直接蓄積し、ターンごとに Redis リスト経由で SSE へ push
- `aget_state` による事後チェックポイント読み出しは採用しない（後述）

### ターン延長
- ターン終了後の延長承認は **再エンキュー方式** で実装（`interrupt_before` は不採用）
- フロントエンドがターン終了を検知したら「延長しますか？」UIを表示し、追加ターン数を付けて同一 `thread_id` で再度 `POST /api/chat` を送る

### フロントエンド
- `DebateChatApp.tsx` を新規作成。パターン選択・参加エージェント/Gem チェックリスト・ターン数入力の設定パネルを実装
- `App.tsx` の `Screen` 型に `'debate'` を追加し `MenuScreen` からナビゲート
- 各エージェントの発言は `[エージェント名]:` プレフィックス形式で既存 `MessageArea` に積み上げ（`ChatMessage` 型変更なし）

## Alternatives Considered

### aget_state によるターン蓄積
実装当初、各ターン後に `aget_state()` で LangGraph チェックポインタから `turns` を読み出す設計を採用した。しかし PostgreSQL チェックポインタからの逆シリアライズで `AIMessage` 型情報が失われ、ターンが正しく再構成できなかった。`astream` のチャンクは in-memory のため型が保持される。→ **廃止、astream 直接蓄積に変更**

### Redis Pub/Sub によるクロスプロセス SSE
Worker プロセスから API プロセスへターンをリアルタイム転送するために Redis Pub/Sub を最初に採用したが、SSE クライアントの再接続時にメッセージが消える問題が発生した。→ **Redis リストへの RPUSH + BLPOP ポーリング方式に変更**

### interrupt_before によるターン延長
LangGraph の `interrupt_before` でターン途中に停止してユーザー確認を挟む案を検討したが、arq バックグラウンド worker との相性が悪く、worker タイムアウト管理が複雑になる。→ **再エンキュー方式を採用**

## Consequences

### 正の影響
- OrchestratorGraph を一切変更せず、新しいグラフトポロジーをゼロから追加できた
- `task_type` によるハンドラー切り替えパターンが3種類（langgraph/orchestrator/debate）に拡張され、今後の新パターン追加も同じ手順で可能

### 注意点・落とし穴

**1. `applications` テーブルへのシード漏れがサイレント障害になる**  
`threads` テーブルは `app_id REFERENCES applications(app_id)` の外部キー制約を持つ。シードに `'debate'` レコードを追加し忘れると、スレッド INSERT が FK 制約違反で失敗する。エラーは `except Exception: pass` で握り潰されるためログに何も出ず、フロントエンドはスレッドが表示されないまま（今回修正済み: `e43ec1e`）。  
→ 新しいアプリ（`app_id`）を追加する際は必ず `app/api/main.py` の applications シード INSERT に追加すること。

**2. DebateState と MessagesState の非互換**  
`get_thread_messages()` は通常チャット用の `MessagesState` グラフでチェックポインタを読むため、`DebateState` チェックポイントを解釈できない。`task_type="debate"` の thread には最小限の `StateGraph(DebateState)` を使って同チェックポインタから再読み出すフォールバックが必要（実装済み: `chat.py`）。

**3. astream ループでの型保持**  
チェックポインタ経由（`aget_state`）では LangGraph が `AIMessage` を dict に変換して保存するため型が失われる。`astream` のチャンクは Python プロセス内 in-memory なので型が保持される。ターンを再構成する処理は常に `astream` のストリームから行うこと。
