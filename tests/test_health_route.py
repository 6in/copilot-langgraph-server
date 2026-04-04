"""Tests for GET /health/agents endpoint.

Tests verify:
- Returns a JSON list of agent health entries
- Each entry has required fields (name, agent_type, status, error)
- No JWT authentication required
- FAILED agents include a non-null error string in the response
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out the github-copilot-sdk (not installed in unit-test environment)
# ---------------------------------------------------------------------------
_copilot_stub = ModuleType("copilot")
_copilot_stub.CopilotClient = MagicMock  # type: ignore[attr-defined]
_copilot_stub.SubprocessConfig = MagicMock  # type: ignore[attr-defined]
_copilot_stub.PermissionHandler = MagicMock  # type: ignore[attr-defined]
sys.modules.setdefault("copilot", _copilot_stub)

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes.health import router
from app.orchestrator.agent import AgentHealth, AgentStatusEnum


@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(router)
    app.state.agent_health = [
        AgentHealth(name="good-agent", agent_type="folder", status=AgentStatusEnum.HEALTHY),
        AgentHealth(
            name="bad-agent",
            agent_type="code",
            status=AgentStatusEnum.FAILED,
            error="ImportError: no module named 'foo'",
        ),
    ]
    return app


@pytest.mark.asyncio
async def test_health_agents_returns_list(test_app):
    """GET /health/agents returns 200 with a JSON list of agent health entries."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.get("/health/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_health_entry_has_required_fields(test_app):
    """Each entry has name, agent_type, status fields; error is null for HEALTHY agents."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.get("/health/agents")
    assert resp.status_code == 200
    entries = resp.json()

    # Find the HEALTHY entry
    healthy = next(e for e in entries if e["status"] == "HEALTHY")
    assert healthy["name"] == "good-agent"
    assert healthy["agent_type"] == "folder"
    assert healthy["status"] == "HEALTHY"
    assert healthy["error"] is None


@pytest.mark.asyncio
async def test_health_no_auth_required(test_app):
    """GET /health/agents returns 200 without JWT cookie (no Depends(get_jwt_payload))."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # No cookies, no Authorization header — must still succeed
        resp = await client.get("/health/agents")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_failed_agent_shows_error(test_app):
    """When registry has a FAILED agent, response includes it with status='FAILED' and non-null error."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.get("/health/agents")
    assert resp.status_code == 200
    entries = resp.json()

    failed = next(e for e in entries if e["status"] == "FAILED")
    assert failed["name"] == "bad-agent"
    assert failed["agent_type"] == "code"
    assert failed["error"] is not None
    assert len(failed["error"]) > 0
