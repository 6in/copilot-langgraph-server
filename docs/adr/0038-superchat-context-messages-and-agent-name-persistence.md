# 0038. SuperChat 過去メッセージコンテキスト注入とエージェント名永続化

**Date:** 2026-04-16  
**Status:** Accepted

## Context

SuperChat で過去の会話を LLM に文脈として渡す手段がなかった。各ターンの SubAgent は `state["input"]`（現在のプロンプト）しか受け取らず、「さっきの続き」等の文脈依存リクエストに対応できない状態だった。

加えて、SuperChat スレッドをリロードすると AI メッセージのエージェント名（バッジ・色）が消える問題が判明した。OrchestratorGraph の `SubAgent.run()` が返す `AIMessage(name=agent_name)` の `name` 属性が、LangGraph checkpoint のシリアライズ/デシリアライズ過程で失われていた。DebateGraph では同じ問題を `dispatch_node` 内での `AIMessage.name` 強制付与で回避していたが、OrchestratorGraph には同等の処理がなかった。

## Decision

### 1. context_messages によるシステム的コンテキスト注入

フロントエンドのメッセージテキストに過去会話を埋め込む方式（`<details>` HTML 等）を**廃止**し、API リクエストの `context_messages` フィールドとしてバックエンドに渡す方式を採用した。

- `ChatRequest.context_messages: list[ContextMessage]` を追加
- `SubAgent.run()` / `ToolEnabledSubAgent.run()` が `state["context_messages"]` を `HumanMessage` / `AIMessage` として LLM メッセージリストに注入（system prompt の後、現在の入力の前）
- フロントエンドは各メッセージにチェックボックス（デフォルト ON）を表示し、チェック済みメッセージを `ContextMessage[]` として送信

### 2. _wrap_agent_run による AIMessage.name 強制付与

DebateGraph と同じパターンを OrchestratorGraph に適用:

- `graph.py` に `_wrap_agent_run()` ラッパーを追加
- `SubAgent.run()` の戻り値の `AIMessage` に対し、`name` が未設定なら `agent.name` を強制付与
- checkpoint に `name` 付きで保存されるため、リロード時もエージェント名が復元される

### 3. get_thread_messages のスキーマ分岐

スレッド種別ごとに正しい state schema で checkpoint を読み込むよう `get_thread_messages` を再構成:

- `thread_app_id not in ("chat", "debate")` → `AgentState` スキーマ
- `"chat"` → `MessagesState`（デフォルト graph）
- `"debate"` → `DebateState`（既存）

## Alternatives Considered

1. **メッセージテキストに過去会話を `<details>` HTML で埋め込む** — 最初に実装したが、MarkdownMessage のレンダリングに副作用（`rehype-raw` のスペーシング崩壊）が発生。根本的にプレゼンテーション層とデータ層の責務が混在する設計のため廃止。

2. **rehype-raw プラグインで `<details>` をレンダリング** — 全体の Markdown レンダリングに副作用（20行分の間延び表示）。`splitDetailsBlocks()` で React コンポーネント化も試みたが、そもそもテキスト埋め込み自体が不要だった。

3. **Resend ボタン + 再送信モード UI** — 初期実装。操作が分かりにくく（Resend クリック → 含めるチェックボックス ON/OFF）、常時チェックボックス方式に簡素化。

4. **agent_name を別テーブルに保存** — 確実だがスキーマ変更が大きい。`_wrap_agent_run` で `AIMessage.name` を強制付与する方が既存パターン（DebateGraph）と整合し、変更が最小限。

## Consequences

### Positive

- SuperChat で過去の会話コンテキストを LLM に渡せるようになり、文脈依存の応答が可能に
- ユーザーがチェックボックスで含めるメッセージを選択可能（デフォルト全選択）
- SuperChat リロード時にエージェント名・色が正しく復元される
- `enableResend` フラグで SuperChat のみ有効化 — 他アプリに影響なし

### Negative

- `context_messages` はフロントエンドの session state に依存 — ページリロード後は再選択が必要
- `_wrap_agent_run` は LangGraph の checkpoint シリアライズの問題のワークアラウンド — LangGraph 側の修正で不要になる可能性がある
- `get_thread_messages` のスキーマ分岐が 3 パターンに増加 — 新しいアプリ種別追加時に考慮が必要
