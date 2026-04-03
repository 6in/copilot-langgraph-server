"""Abstract base class for pluggable worker task handlers."""
from abc import ABC, abstractmethod


class TaskHandler(ABC):
    """Interface every task handler must implement.

    The worker facade calls handle() after dispatching on task_type.
    Implementations are responsible for saving their result via job_store
    and signalling completion via notifier.
    """

    @abstractmethod
    async def handle(self, ctx: dict, job: dict) -> dict:
        """Execute the task.

        Args:
            ctx: arq worker context (redis_client, job_store, …).
            job: job payload dict (job_id, task_type, and handler-specific fields).

        Returns:
            dict with at minimum {"job_id": ..., "status": "done"}.
        """
