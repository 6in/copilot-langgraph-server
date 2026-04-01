"""Test stubs for the arq worker (ASYNC-07).

These tests will be enabled in Plan 02 when the process_chat worker function is created.
"""
import pytest


@pytest.mark.skip(reason="worker not yet created (Plan 02)")
async def test_process_chat_saves_result():
    """process_chat calls job_store.save_result then notifier.done (ASYNC-07)."""
    pass
