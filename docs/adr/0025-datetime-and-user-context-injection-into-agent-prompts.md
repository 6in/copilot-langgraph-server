# 0025. 全エージェントへの現在日時・ログインユーザー自動注入

**Date:** 2026-04-13  
**Status:** Accepted

## Context

エージェント（SubAgent / ToolEnabledSubAgent）が現在の日時を知る手段がなかった。日付・時刻に関する質問に対して不正確な回答をするほか、スケジュール計算や期限判定などの時刻依存タスクを正しく処理できない状態だった。

同様に、ログイン中のユーザー名をエージェントが把握できておらず、「私の名前は？」に対して「わかりません」と返答していた。

問題の調査で、注入箇所がチャットモード（LangGraph）と SuperChat モード（Orchestrator）で分断されていることが判明した。`builder.py` では `github_login` をシステムプロンプトに注入しているが、`SubAgent.run()` / `DebateChat` ではその仕組みが存在しなかった。

## Decision

以下の 2 つのアプローチを組み合わせて実装した。

**1. システムプロンプトへの自動注入**

`app/utils/datetime_utils.py` に `get_datetime_context()` ヘルパーを新設（JST・曜日付き）。すべての SubAgent 実装（`SubAgent.run()`、`ToolEnabledSubAgent.run()`）でシステムプロンプトの先頭にこれを付加する。`github_login` は `state["context"].user_id` から取得して同じく先頭に付加。

`LangGraphHandler`（Chat / GemChat / Canvas）では `effective_system_prompt` を構築する際に datetime を注入し、`builder.py` 既存の `github_login` 注入と共存させた。

**2. MCP ツール `get_current_datetime` の追加**

ツール経由でも日時を取得できるよう `mcp_server/tools/stubs.py` に `get_current_datetime` MCP ツールを追加。ISO 8601 形式・日本語フォーマット・曜日を返す。`config/mcp_tools.yaml` のカタログにも登録。

DebateChat は `_make_pseudo_agent_state()` が `context: None` を渡していたため、`RPCContext(user_id=github_login, ...)` を生成して渡すよう修正した。

## Alternatives Considered

**プロンプトインジェクションを LangGraph の config のみで行う**  
`builder.py` の既存パターン（`config["configurable"]` 経由）は Chat モードにしか効かない。Orchestrator / Debate のグラフ構造はこの config を参照しないため、全パスを統一できない。

**エージェントごとの AGENT.md に日時を書かせる**  
静的な記述では実行時の日時を反映できない。

**現在時刻ツールのみで対応（注入なし）**  
ツールを呼ばなければ日時を得られないため、モデルが自発的にツールを呼ぶ必要がある。エージェントが常にツールを使うとは限らないため、プロンプト注入との併用とした。

## Consequences

**ポジティブ:**
- すべてのチャットパス（Chat / SuperChat / GemChat / Canvas / DebateChat）で現在日時とユーザー名が利用可能になった
- `get_datetime_context()` が `app/utils/datetime_utils.py` に独立しているため将来の変更が容易

**ネガティブ / 注意点:**
- `app/utils/datetime_utils.py` を `app/orchestrator/agent.py` から import すると、`handlers/__init__.py` → `orchestrator_handler.py` → `agent.py` の循環インポートが発生する。当初 `handlers/base.py` に配置したため循環が起きた。解決策として `app/utils/` という循環に巻き込まれない独立モジュールを新設した。
- MCP ツールを追加した場合は `config/mcp_tools.yaml` への登録も必須。`ToolRegistry` が起動時に完全一致チェックを行うため、登録漏れで worker が起動失敗する。
- `DebateChat` の `_make_pseudo_agent_state()` は `AgentState` 互換の dict を手動で構築するため、`SubAgent.run()` が `state["context"]` に依存する変更を加えた際は必ずここも更新が必要。
