import asyncio
import json
from typing import Optional

from redis.asyncio import Redis


class JobStore:
    """Stores job results in Redis and manages asyncio.Queue signals for SSE."""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.queues: dict[str, asyncio.Queue] = {}

    def register_sse(self, job_id: str) -> asyncio.Queue:
        """Create and register an asyncio.Queue for SSE signalling. Returns the queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self.queues[job_id] = queue
        return queue

    def unregister_sse(self, job_id: str) -> None:
        """Remove the SSE queue for job_id (call in finally on disconnect)."""
        self.queues.pop(job_id, None)

    async def save_result(self, job_id: str, result: str) -> None:
        """Persist the job result to Redis with a 1-hour TTL."""
        await self.redis.set(
            f"job:{job_id}",
            json.dumps({"status": "done", "result": result}),
            ex=3600,
        )

    async def notify(self, job_id: str, status: str, **extra) -> None:
        """Put a status event onto the SSE queue if one is registered."""
        if job_id in self.queues:
            event = {"status": status, **extra}
            await self.queues[job_id].put(event)

    async def push_turn(self, job_id: str, name: str, content: str) -> None:
        """Append a debate turn to a Redis list (cross-process safe, polled by SSE)."""
        import json as _json
        await self.redis.rpush(f"job:{job_id}:turns", _json.dumps({"name": name, "content": content}))
        await self.redis.expire(f"job:{job_id}:turns", 3600)

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
