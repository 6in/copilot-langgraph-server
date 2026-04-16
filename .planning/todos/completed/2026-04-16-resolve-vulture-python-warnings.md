---
created: 2026-04-16T00:00:00.000Z
title: vulture 80%+ Python 警告を解消
area: api
files:
  - app/api/routes/chat.py
  - app/providers/copilot.py
---

## Problem

`.planning/reports/2026-04-16-cleanup-inventory.md` §3 を参照。
`vulture --min-confidence 80`:

```
app/api/routes/chat.py:25: unused import 'ChatResponse' (90%)
app/providers/copilot.py:30: unused import 'Runnable' (90%)
app/providers/copilot.py:266: unused variable 'tool_choice' (100%)
mcp_server/server.py:25: unused variable 'server' (100%)   # ← FastMCP lifespan の false positive
```

## Solution

1. `ChatResponse` が本当に外部から import されていないか確認 → 削除 or `__all__` 整理
2. `Runnable` は型注釈で使っているだけなら `TYPE_CHECKING` ブロックへ
3. `tool_choice` は `bind_tools` の受け取りで捨てているだけなら、引数名を `_tool_choice` にリネームするか、実装を見直す
4. `mcp_server/server.py` の `server` は FastMCP lifespan のシグネチャ要件なので `# noqa: vulture` などで抑制するか、`_server` にリネーム
5. `vulture` CI を検討（追加は任意）

優先度: 低
