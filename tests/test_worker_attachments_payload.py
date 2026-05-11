"""Phase 36 D-14: worker.process_chat に attachments が流れることを検証.

Plan 36-04 Task 1 (RED): process_chat の signature に `attachments` kwarg を追加し、
job dict に詰めて handler に渡せることを TDD で確認する.

意図:
- arq REST 入口 (chat.py の enqueue_job(attachments=...)) → worker.process_chat → handler
  の payload bridge を test で固定する.
- handler 本体 (LangGraphHandler / OrchestratorHandler) は本テストでは触らない (Task 2/3 で別途).
- TASK_HANDLERS dict に AsyncMock handler を monkeypatch して `job` dict を capture する方針.
"""
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_process_chat_passes_attachments_to_handler(monkeypatch):
    """attachments=[dict] を渡すと handler 受け取る job dict に attachments が含まれる."""
    from app.jobs import worker

    captured_job: dict = {}

    async def fake_handle(ctx, job):
        captured_job.update(job)
        return {"job_id": job["job_id"], "status": "done"}

    fake_handler = AsyncMock()
    fake_handler.handle = fake_handle
    monkeypatch.setitem(worker.TASK_HANDLERS, "langgraph", fake_handler)

    atts = [
        {
            "kind": "file",
            "name": "a.txt",
            "storage_name": "20260423T120000_a.txt",
            "path": "/shared/thread-files/u/t/20260423T120000_a.txt",
            "size": 5,
            "mime_type": "text/plain",
            "ext": "txt",
            "modified_at": "2026-04-23T12:00:00Z",
        }
    ]

    await worker.process_chat(
        {},  # ctx
        job_id="j-1",
        thread_id="t-1",
        prompt="hi",
        model="gpt-4.1",
        github_token="ghu_x",
        reply_to={"type": "web", "job_id": "j-1"},
        task_type="langgraph",
        attachments=atts,
    )

    assert captured_job["attachments"] == atts


@pytest.mark.asyncio
async def test_process_chat_without_attachments_default_none(monkeypatch):
    """attachments を渡さない場合 job["attachments"] is None (後方互換)."""
    from app.jobs import worker

    captured_job: dict = {}

    async def fake_handle(ctx, job):
        captured_job.update(job)
        return {"job_id": job["job_id"], "status": "done"}

    fake_handler = AsyncMock()
    fake_handler.handle = fake_handle
    monkeypatch.setitem(worker.TASK_HANDLERS, "langgraph", fake_handler)

    await worker.process_chat(
        {},
        job_id="j-2",
        thread_id="t-2",
        prompt="hi",
        model="gpt-4.1",
        github_token="ghu_x",
        reply_to={"type": "web", "job_id": "j-2"},
        task_type="langgraph",
    )
    assert captured_job["attachments"] is None


@pytest.mark.asyncio
async def test_process_chat_unknown_task_type_early_return():
    """未知 task_type は handler dispatch する前に early return するため
    attachments が指定されていても regression なし (job_store.save_result が呼ばれる).
    """
    from app.jobs import worker

    class _FakeJobStore:
        def __init__(self) -> None:
            self.saved: tuple | None = None

        async def save_result(self, job_id, result):
            self.saved = (job_id, result)

    js = _FakeJobStore()
    result = await worker.process_chat(
        {"job_store": js},
        job_id="j-3",
        thread_id="t-3",
        prompt="hi",
        model="gpt-4.1",
        github_token="ghu_x",
        reply_to={"type": "web", "job_id": "j-3"},
        task_type="unknown_type",
        attachments=[{"kind": "file"}],
    )
    assert result["status"] == "error"
    assert js.saved is not None
    assert "unknown task_type" in js.saved[1]
