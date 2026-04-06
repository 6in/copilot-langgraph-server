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
        """Publish a status event to Redis Pub/Sub (cross-process safe) and local queue."""
        event = {"status": status, **extra}
        # Redis Pub/Sub: worker と API が別プロセスでも届く
        await self.redis.publish(f"job:{job_id}:events", json.dumps(event))
        # 同一プロセスの queue にも投入（テスト・同期ユースケース用）
        if job_id in self.queues:
            await self.queues[job_id].put(event)

    async def get(self, job_id: str) -> Optional[dict]:
        """Retrieve the stored job result from Redis, or None if not found."""
        raw = await self.redis.get(f"job:{job_id}")
        return json.loads(raw) if raw else None
