---
phase: 22-web-search-tavily
plan: 02
status: complete
completed_at: 2026-04-13
---

## 実施内容

### Gap 1: TOOL_SYSTEM_PROMPT_TEMPLATE の強化
`app/providers/copilot.py` の `TOOL_SYSTEM_PROMPT_TEMPLATE` をシンプルな JSON 指示形式に整理。
"If no tool is needed, respond normally" の逃げ道フレーズを削除し、リアルタイム情報が必要な
ケースではツールを呼ぶよう指示を追加。

### Gap 2: モデル互換性の発見と解決
**根本原因:** GPT-4.1 (GitHub Copilot) はアーキテクチャ知識から JSON ベースのツール呼び出しを拒否する。
Claude Sonnet 4.6 は `TOOL_SYSTEM_PROMPT_TEMPLATE` の JSON 指示に正しく従い、web_search を実行する。
`agents/general-assistant/AGENT.md` の `model: claude-sonnet-4-6` が正しく機能していることを確認。

### Gap 3 (追加): ツール実行中 UI インジケーター
- `app/orchestrator/tool_context.py`: ContextVar (ToolEventCallback) 新規追加
- `app/jobs/job_store.py`: `push/clear/get_tool_event()` を Redis キーで実装
- `app/orchestrator/tool_agent.py`: agent_node でツール呼び出し検出時にコールバック実行
- `app/jobs/handlers/orchestrator_handler.py`: graph.ainvoke 前後で ContextVar セット/リセット
- `app/api/routes/chat.py`: SSE generator が `tool_executing` イベントを emit
- `frontend/src/hooks/useChat.ts`: `currentTool` 状態を追加
- `frontend/src/components/MessageArea.tsx` / `SuperChatApp.tsx`: 🔍 ツール実行中表示

### Gap 4 (追加): URL エビデンス付き検索結果
- `mcp_server/tools/web_search.py`: `formatted` + `source_urls` を返却形式に追加
- `TOOL_SYSTEM_PROMPT_TEMPLATE`: source_urls を回答に引用するよう指示

## UAT 結果

| テスト | 結果 |
|--------|------|
| test 3: リアルタイム情報への web_search 呼び出し | ✅ PASS |
| test 4: 検索結果サイズ制限・コンテキスト超過なし | ✅ PASS |

実機確認: 「明日の東京の目黒区の天気は？」で web_search が発火し、
Toshin.com の URL を含む回答が返ることを確認。

## 学習事項

- GPT-4.1 (Copilot API) は JSON ベース prompt engineering でのツール呼び出しに非対応
- Claude Sonnet 4.6 は TOOL_SYSTEM_PROMPT_TEMPLATE の指示に正しく従う
- 二重の system message（TOOL_SYSTEM_PROMPT_TEMPLATE + AGENT.md ツール指示）は混乱の原因になる
- `_try_parse_tool_call` に Attempt 3（テキスト混在 JSON 抽出）を追加済み
