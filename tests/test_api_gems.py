"""Test stubs for Gem CRUD API — GEM-01, GEM-02, GEM-03.

Wave 0: stubs only. Implementation will be added during task execution.
Tests run with: uv run pytest tests/test_api_gems.py -x -q
"""
import pytest


@pytest.mark.asyncio
async def test_create_gem():
    """GEM-01: POST /api/gems creates a gem for authenticated user."""
    pytest.skip("Wave 0 stub — implementation pending")


@pytest.mark.asyncio
async def test_list_gems():
    """GEM-02: GET /api/gems returns only the user's own gems."""
    pytest.skip("Wave 0 stub — implementation pending")


@pytest.mark.asyncio
async def test_delete_gem_ownership():
    """GEM-03: DELETE /api/gems/{id} returns 404 for another user's gem."""
    pytest.skip("Wave 0 stub — implementation pending")
