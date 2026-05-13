import json
from typing import Optional

from redis.asyncio import Redis


class JobStore:
    """Stores job results in Redis.

    SSE は Redis polling 経路に統一済 (Phase 39 / UIFIX-03)。in-memory queue
    経路 (旧 register / unregister API) は dead code として削除済。notify()
    のみ notifier.py 経由の呼び出し互換のため no-op stub で残置。
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def save_result(self, job_id: str, result: str) -> None:
        """Persist the job result to Redis with a 1-hour TTL."""
        await self.redis.set(
            f"job:{job_id}",
            json.dumps({"status": "done", "result": result}),
            ex=3600,
        )

    async def notify(self, job_id: str, status: str, **extra) -> None:
        """No-op stub (Phase 39 UIFIX-03 D-06).

        in-memory queue 経路は廃止済。notifier.py が表面 API 維持のため
        progress() / done() から呼び出しているが、production SSE は Redis
        polling (app/api/routes/chat.py:219-251) で完結している。
        """
        return None

    async def push_turn(self, job_id: str, name: str, content: str) -> None:
        """Append a debate turn to a Redis list (cross-process safe, polled by SSE)."""
        import json as _json
        await self.redis.rpush(f"job:{job_id}:turns", _json.dumps({"name": name, "content": content}))
        await self.redis.expire(f"job:{job_id}:turns", 3600)

    async def push_token(self, job_id: str, token: str) -> None:
        """Append a streaming token to a Redis list (cross-process safe, polled by SSE)."""
        await self.redis.rpush(f"job:{job_id}:tokens", token)
        await self.redis.expire(f"job:{job_id}:tokens", 3600)

    async def get_tokens(self, job_id: str, since: int = 0) -> list[str]:
        """Return streaming tokens from index `since` onward."""
        raws = await self.redis.lrange(f"job:{job_id}:tokens", since, -1)
        return [r.decode() if isinstance(r, bytes) else r for r in raws]

    async def get_turns(self, job_id: str, since: int = 0) -> list[dict]:
        """Return debate turns from index `since` onward."""
        raws = await self.redis.lrange(f"job:{job_id}:turns", since, -1)
        return [json.loads(r) for r in raws]

    async def push_tool_event(self, job_id: str, tool_name: str, query: str) -> None:
        """Store current tool execution status in Redis (polled by SSE generator)."""
        import time as _time
        payload = json.dumps({"tool": tool_name, "query": query, "ts": _time.time()})
        await self.redis.set(f"job:{job_id}:current_tool", payload, ex=60)

    async def clear_tool_event(self, job_id: str) -> None:
        """Clear the current tool status from Redis."""
        await self.redis.delete(f"job:{job_id}:current_tool")

    async def get_tool_event(self, job_id: str) -> Optional[dict]:
        """Return current tool event dict or None."""
        raw = await self.redis.get(f"job:{job_id}:current_tool")
        return json.loads(raw) if raw else None

    async def get(self, job_id: str) -> Optional[dict]:
        """Retrieve the stored job result from Redis, or None if not found."""
        raw = await self.redis.get(f"job:{job_id}")
        return json.loads(raw) if raw else None
