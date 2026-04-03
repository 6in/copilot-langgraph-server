# Phase 9: SuperChat メインアプリ統合 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 09-superchat-orchestratorgraph-app-chat
**Areas discussed:** Module placement, API surface, Agent/menu files location, Frontend coexistence

---

## Module Placement

| Option | Description | Selected |
|--------|-------------|----------|
| app/orchestrator/ 新モジュール | super-agent-sample/src/ の agent.py / graph.py / dispatcher.py / state.py を app/orchestrator/ に移植。ChatCopilot と CopilotAuthManager は本家 app/providers/ app/auth/ を import する形に修正。サンプルのスタンドアロンコピーは削除。 | ✓ |
| app/graph/ に吸収 | 既存の app/graph/builder.py に OrchestratorGraph を追加。ファイル数は減るが、builder.py が肥大化するリスクあり。 | |
| super-agent-sample/ はそのまま山存 | super-agent-sample/src/ を変えず、インポートパスで柔軟する。サンプルと本番の二重管理になるため追推しにくい。 | |

**User's choice:** app/orchestrator/ 新モジュール
**Notes:** サンプルのスタンドアロンコピー (chat_copilot.py / auth_manager.py) は削除し、本家を参照する。super-agent-sample/ 自体は維持。

---

## API Surface

| Option | Description | Selected |
|--------|-------------|----------|
| POST /api/super-chat 新エンドポイント | 既存の /api/chat に触れず、別ルートとして追加。ジョブ返却・SSE・ポーリングのパターンは /api/chat と同じ arq パターンを再利用。リグレッションリスクなし。 | |
| /api/chat に mode パラメータ | POST ボディに mode: 'simple' \| 'super' を追加。ルート内部で分岐。既存クライアントコードの修正とテスト変更が必要。 | ✓ |

**User's choice:** /api/chat に mode パラメータ
**Notes:** mode 省略時は 'simple' デフォルト（既存動作を維持）。mode='super' の場合のみ OrchestratorGraph を使用。

### API detail (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| mode 省略時は simple デフォルト | mode フィールドを追加しない既存クライアントは引き続き 'simple'（既存 LangGraph）で動作する。mode='super' を明示指定した場合のみ OrchestratorGraph を使う。arq worker の process_chat 関数内で mode に応じてグラフを選択する。 | ✓ |
| mode 省略時は super デフォルト | 新規リクエストはすべて OrchestratorGraph 経由。単純チャットは mode='simple' 指定が必要になる。 | |

**User's choice:** mode 省略時は simple デフォルト

---

## Agent/Menu Files Location

| Option | Description | Selected |
|--------|-------------|----------|
| リポジトリルートの agents/ menus/ を流用 | super-agent-sample/ の agents/ menus/ をそのままリポジトリルートに持ってくる。2箇所管理が不要。Docker では volume mount で参照する。 | ✓ |
| app/orchestrator/agents/ 配下に移動 | Python パッケージと同居。パス解決がやや複雑になるが app/ 内で完結する。 | |
| 現在の場所はまず考えない | Phase 9 のスコープ外として将来決める。今はハードコードパスの定数化のみ。 | |

**User's choice:** リポジトリルートの agents/ menus/ を流用
**Notes:** AGENT_DIR / MENU_DIR 環境変数でパスを設定可能にする。Docker Compose の api / worker サービスに追加。

---

## Frontend Coexistence

| Option | Description | Selected |
|--------|-------------|----------|
| モードトグルを React UI に追加 | メッセージ入力欄の近くにトグルボタン（💬 Simple / 🚀 Super）を配置。mode をローカル state で管理し、POST /api/chat に含める。最小限の UI 変更で動作確認できる。 | ✓ |
| 透過的（UI 変更なし） | API 側のみ実装。UI からは常に simple モード。動作確認は curl や直接 API コールに限定される。 | |
| 別ページ/ルート | React 内に /super-chat 等の新しいスクリーンを追加。実装規模が大きくなる。 | |

**User's choice:** モードトグルを React UI に追加

---

## Claude's Discretion

- AgentState と既存 MessagesState の相互変換の具体的実装
- lifespan での OrchestratorGraph 初期化の具体的コード
- モードトグルの UI 配置（送信ボタン横 or 入力欄上部）

## Deferred Ideas

- Vanilla JS UI 側のモード対応 — Phase 9 スコープ外
- 新規エージェント定義の追加
- LangGraph checkpointer を OrchestratorGraph にも適用（会話履歴永続化）— v2 候補
- 「チャットのコンテキストにてユーザー情報も入れるようにする」— 別フェーズで対応
