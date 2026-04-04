# Debug: SuperChat Agent Routing Failure

**Phase:** 10
**Severity:** blocker
**Status:** resolved
**updated:** 2026-04-04T05:00:00Z

## Symptom

SuperChatで任意のメッセージ（例:「私の名前は田中です」）を送信すると、AIが「対応できるエージェントが見つかりませんでした。」と返答し、会話が成立しない。

## Root Cause

`SubAgentRegistry` にはドメイン特化エージェント（`sql-analyst`, `code-reviewer`）のみが登録されており、汎用会話エージェントが存在しない。`RouterNode` の LLM ディスパッチャーは一般的な会話メッセージをどのエージェントにもマッチさせられず `"fallback"` を返す。`fallback_node()` はその受け皿として固定の「エージェントが見つかりません」文字列を返す実装になっている。

## Evidence

- `app/orchestrator/graph.py` line 55: `fallback_node()` がエラー文字列の発生源
- `agents/` ディレクトリ: `sql-analyst/` と `code-reviewer/` のみ存在、汎用エージェントなし
- `ROUTER_PROMPT` (graph.py lines 11-23): 「該当なしは 'fallback' を返す」と明示的に指示

## Fix Direction

`agents/general-assistant/AGENT.md` など汎用会話エージェントを追加し、ルーターが一般メッセージをハンドルできるようにする。または `fallback_node` を LLM 呼び出しに変更して汎用応答を生成するようにする。
