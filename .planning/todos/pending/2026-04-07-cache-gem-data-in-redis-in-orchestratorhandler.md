---
created: 2026-04-07T14:18:29.889Z
title: Cache GEM data in Redis in OrchestratorHandler
area: api
files:
  - app/jobs/handlers/orchestrator_handler.py:38-85
  - app/jobs/worker.py:54-107
---

## Problem

`OrchestratorHandler.handle()` はメッセージ送信ごとに PostgreSQL へ SELECT クエリを発行して GEM の `name` と `system_prompt` を取得している。現状の規模（200名・社内）では問題ないが、将来的に長大なテキストを持つペルソナ GEM を準備する場合、毎回 DB から引くコストが無視できなくなる。

## Solution

`ctx["redis_client"]`（arq worker の startup で既に生成済み）を使って GEM データをキャッシュする。

```python
# MGET でまとめて取得（gem_ids が複数でも1往復）
cache_keys = [f"gem:{gid}" for gid in gem_ids]
cached_values = await redis.mget(*cache_keys)

# キャッシュミス分だけ DB fetch → setex(TTL=600)
await redis.setex(f"gem:{gid}", 600, json.dumps([name, system_prompt]))
```

invalidation は `PATCH /api/gems/{gem_id}` と `DELETE /api/gems/{gem_id}` のハンドラで `DEL gem:{gem_id}` を呼ぶだけ。TTL は 10分程度が目安。
