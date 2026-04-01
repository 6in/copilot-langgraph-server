"""Test stubs for job polling API endpoint (ASYNC-02).

These tests will be enabled in Plan 03 when the polling endpoint is created.
"""
import pytest


@pytest.mark.skip(reason="polling endpoint not yet created (Plan 03)")
async def test_get_job_pending():
    """GET /api/job/{id} returns {'status': 'pending'} before completion (ASYNC-02)."""
    pass


@pytest.mark.skip(reason="polling endpoint not yet created (Plan 03)")
async def test_get_job_done():
    """GET /api/job/{id} returns done result after save_result (ASYNC-02)."""
    pass
