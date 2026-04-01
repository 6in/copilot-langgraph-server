from app.jobs.job_store import JobStore


class BaseNotifier:
    """Abstract base for all notification strategies."""

    async def progress(self, status: str) -> None:
        ...

    async def done(self) -> None:
        ...


class WebNotifier(BaseNotifier):
    """Notifier that signals the SSE queue via JobStore."""

    def __init__(self, job_id: str, job_store: JobStore):
        self.job_id = job_id
        self.job_store = job_store

    async def progress(self, status: str) -> None:
        await self.job_store.notify(self.job_id, status)

    async def done(self) -> None:
        await self.job_store.notify(self.job_id, "done")


def build_notifier(reply_to: dict, job_store: JobStore) -> BaseNotifier:
    """Factory that returns the correct Notifier for the reply_to channel type."""
    if reply_to["type"] == "web":
        return WebNotifier(reply_to["job_id"], job_store)
    raise ValueError(f"Unknown reply_to type: {reply_to['type']}")
