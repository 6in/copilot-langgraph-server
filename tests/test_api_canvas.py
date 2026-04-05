"""Test stubs for Canvas Apps API — CANVAS-01, CANVAS-02, CANVAS-03.

Wave 0: stubs only. Implementation will be added during task execution.
Tests run with: uv run pytest tests/test_api_canvas.py -x -q
"""
import pytest


@pytest.mark.asyncio
async def test_upload_app():
    """CANVAS-01: POST /api/canvas/apps/upload saves HTML."""
    pytest.skip("Wave 0 stub — implementation pending")


@pytest.mark.asyncio
async def test_get_app():
    """CANVAS-02: GET /api/canvas/apps/{app_id} returns correct HTML."""
    pytest.skip("Wave 0 stub — implementation pending")


@pytest.mark.asyncio
async def test_deploy_app():
    """CANVAS-03: POST /api/canvas/apps/{app_id}/deploy writes HTML file."""
    pytest.skip("Wave 0 stub — implementation pending")
