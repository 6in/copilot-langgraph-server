---
created: 2026-04-18T00:00:00Z
title: ユーザー選択モデルをエージェントのデフォルトより優先する仕組み
area: api
files:
  - app/jobs/handlers/orchestrator_handler.py
  - app/orchestrator/agent.py
  - app/orchestrator/tool_agent.py
  - app/orchestrator/codeact_agent.py
  - app/api/routes/chat.py
  - frontend/src/hooks/useChat.ts
---

## Problem

現在 SuperChat モードではフロントエンドで選択したモデルが無視され、AGENT.md の `model` フィールドが使われる。
orchestrator_handler.py に `# model is intentionally unused in super mode` とコメントがある。

ユーザーが gpt-4.1 を選んでいても、AGENT.md に `model: claude-sonnet-4-6` と書いてあればそちらが使われる。
ユーザーの意図と実際の動作が乖離している。

## Solution

- AGENT.md の `model` フィールドはデフォルト値として扱う
- フロントエンドで選択されたモデルがある場合、それを優先する
- 実装案:
  1. POST /api/chat の `model` フィールドを orchestrator_handler に渡す
  2. SubAgentRegistry / ToolEnabledSubAgent / CodeActSubAgent の `__init__` で `model_override` パラメータを受け取る
  3. `model_override` が指定されていれば AGENT.md の model より優先する
  4. ChatCopilot(model=model_override or agent_default) で LLM を初期化
- 代替案: Cookie に model 名を格納して API で読み取る（リクエストごとに変えたくない場合）
