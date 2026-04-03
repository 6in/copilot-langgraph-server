---
created: 2026-04-02T04:11:13.254Z
title: Extend worker to support pluggable async task types via routing facade
area: api
files:
  - worker.py
---

## Problem

現在の Worker は LangGraph チャット処理専用になっている。将来的に ClaudeCode の実行・OpenCode の実行・一般的なサーバー処理など、多様な非同期タスクを同じワーカー基盤で動かしたいが、処理タイプを区別する仕組みがない。

## Solution

Redis へのリクエストパラメータに `task_type`（例: `"langgraph"`, `"claude_code"`, `"opencode"`, `"generic"` 等）を追加し、Worker 側にファサード（ルーター）を設ける。

```
POST /chat → Redis キュー { task_type: "langgraph", ... }
                            ↓
                     Worker Facade (worker.py)
                      ├─ "langgraph" → 既存の LangGraph 処理
                      ├─ "claude_code" → ClaudeCode 実行ハンドラー
                      ├─ "opencode" → OpenCode 実行ハンドラー
                      └─ "generic" → 汎用サーバー処理ハンドラー
```

各ハンドラーは共通インターフェース（`async def handle(job: dict) -> result`）に準拠させ、ファサードが `task_type` を見てディスパッチする。既存の LangGraph フローは後方互換を保ちつつ `task_type` デフォルト値で動作継続できるようにする。
