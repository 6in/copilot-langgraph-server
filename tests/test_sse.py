"""Test stubs for SSE endpoint (ASYNC-04, ASYNC-06).

These tests will be enabled in Plan 03 when the SSE endpoint is created.
"""
import pytest


@pytest.mark.skip(reason="SSE endpoint not yet created (Plan 03)")
async def test_sse_done_signal():
    """SSE endpoint yields {'status': 'done'} when notifier.done() fires (ASYNC-04)."""
    pass


@pytest.mark.skip(reason="SSE endpoint not yet created (Plan 03)")
async def test_sse_already_done():
    """SSE endpoint returns immediate done if job already complete (ASYNC-06)."""
    pass
