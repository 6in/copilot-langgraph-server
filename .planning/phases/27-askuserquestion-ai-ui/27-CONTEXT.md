# Phase 27: AskUserQuestion の実装 - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

AI エージェントがユーザーに選択肢・確認を提示する対話的インタラクションパターンをチャット UI + バックエンドに組み込む。`work/uaw/` の参考実装（AskUserQuestion.jsx, Chat.jsx, system_prompt_auq.md）をベースに、本プロジェクトのアーキテクチャ（chatscope + useChat + SSE ジョブキュー）に統合する。

</domain>

<decisions>
## Implementation Decisions

### 質問パネルの表示位置
- **D-01:** 入力エリア置換パターンを採用する。質問パネル表示時はテキスト入力欄を QuestionPanel に置き換え、高さは自動調整される（work/uaw/Chat.jsx のパターン踏襲）
- **D-02:** 質問パネルが未回答の間、テキスト入力欄は無効化する。「質問に回答してください」等のヒントを表示し、回答後に入力欄を復帰させる

### バックエンド統合方式
- **D-03:** system prompt 駆動方式を採用する。AI レスポンスに `<ask_user_question>` タグで JSON を埋め込む方式（work/uaw/system_prompt_auq.md のプロトコル踏襲）。専用 API エンドポイントは追加しない
- **D-04:** ユーザーの回答はテキスト化して通常の POST /api/chat に送信する。「質問：回答」形式のテキストに変換し、既存のチャットフローをそのまま使う（work/uaw/Chat.jsx の handleQuestionSubmit パターン）

### 対応アプリ範囲
- **D-05:** 全アプリ一律で有効化する（Chat / SuperChat / GemChat / CanvasChat / DebateChat）。useChat の共通ロジック（parseJobResult 拡張）で対応し、アプリ別の個別実装は行わない
- **D-06:** 質問プロトコルは共通ベースレベルで注入する。LangGraphHandler / OrchestratorHandler の共通システムプロンプトに追加し、全エージェントが質問可能な状態にする

### 回答後の履歴表示
- **D-07:** 回答済みの質問パネルはスレッド履歴に残さない。回答はテキスト化されて通常のユーザーメッセージとして送信されるため、履歴には通常メッセージバブルとして表示される。ロック済みパネルの特別表示は不要
- **D-08:** スレッド再開時の復元はテキストメッセージとして行う。追加実装不要（既存の履歴読み込みフローがそのまま動く）

### Claude's Discretion
- QuestionPanel の TypeScript 化・スタイリング詳細（ダークテーマ適合）
- parseJobResult での `ask_user_question` 検出ロジックの具体的実装
- system prompt への質問プロトコル追記の文言調整

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 参考実装
- `work/uaw/AskUserQuestion.jsx` — QuestionPanel コンポーネント（single/multi/text 質問タイプ、ロック済み表示、その他自由入力）
- `work/uaw/Chat.jsx` — チャット統合デモ（parseAUQ → QuestionPanel 表示 → handleQuestionSubmit でテキスト化送信）
- `work/uaw/system_prompt_auq.md` — AI に `<ask_user_question>` タグを使わせるためのシステムプロンプト仕様

### 既存コードベース（統合先）
- `frontend/src/hooks/useChat.ts` — sendMessage / parseJobResult（ここに ask_user_question 検出を追加）
- `frontend/src/components/MessageArea.tsx` — メッセージリスト + 入力欄（入力エリア置換の実装先）
- `frontend/src/types.ts` — ChatMessage 型定義
- `app/jobs/handlers/langgraph_handler.py` — LangGraph ハンドラー（system prompt 注入先）
- `app/jobs/handlers/orchestrator_handler.py` — Orchestrator ハンドラー（system prompt 注入先）

### ADR・パターン
- `.planning/patterns.md` — ADR 由来パターンカタログ
- `docs/adr/INDEX.md` — ADR カテゴリ別索引

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parseJobResult()` in useChat.ts — canvas/debate_result/orchestrator_result の JSON ペイロード検出パターンが確立済み。`ask_user_question` タイプを追加すれば自然に統合できる
- `MarkdownMessage` コンポーネント — AI バブル内のリッチ表示に利用中
- `work/uaw/AskUserQuestion.jsx` — QuestionPanel の完成度の高い参考実装（TypeScript 変換が必要）

### Established Patterns
- AI レスポンスの特殊ペイロード検出: `parseJobResult()` で JSON を try-parse → type フィールドで分岐（Phase 15/17 で確立）
- chatscope `Message.CustomContent` で任意の React コンポーネントを AI バブル内に表示
- ダークテーマのインラインスタイル（work/uaw のスタイルがそのまま使える）

### Integration Points
- `useChat.ts` の `parseJobResult()` — ask_user_question タイプ分岐を追加
- `MessageArea.tsx` の入力エリア — QuestionPanel による条件付き置換
- `LangGraphHandler` / `OrchestratorHandler` — 共通システムプロンプトへの質問プロトコル追加
- 各 ChatApp コンポーネント（ChatApp, SuperChatApp, etc.）— useChat からの質問状態を受け取り MessageArea に渡す

</code_context>

<specifics>
## Specific Ideas

- work/uaw の参考実装を TypeScript に変換して frontend/src/components/ に配置
- `<ask_user_question>` タグのパース結果を useChat の状態として管理し、MessageArea に渡す
- 回答送信は work/uaw の handleQuestionSubmit パターン（回答を「質問：回答」テキストに変換して sendMessage 呼び出し）を踏襲

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-askuserquestion-ai-ui*
*Context gathered: 2026-04-17*
