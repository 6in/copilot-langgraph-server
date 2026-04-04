"""Agent health endpoint.

Endpoint:
- GET /health/agents -- list all discovered agents with health status (no auth required)

Reads from app.state.agent_health which is populated at startup by a metadata-only
SubAgentRegistry scan. This registry does NOT instantiate ChatCopilot -- it only parses
AGENT.md files and checks agent.py existence/importability.
"""
from fastapi import APIRouter, Request

from app.api.models import AgentHealthEntry
from app.orchestrator.agent import AgentHealth

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/agents", response_model=list[AgentHealthEntry])
async def list_agent_health(request: Request) -> list[AgentHealthEntry]:
    """Return health status for all discovered agents.

    No JWT required -- health endpoints are operational/infrastructure.
    Reads from app.state.agent_health populated at startup.
    """
    health_list: list[AgentHealth] = getattr(request.app.state, "agent_health", [])
    return [
        AgentHealthEntry(
            name=h.name,
            agent_type=h.agent_type,
            status=h.status.value,
            error=h.error,
        )
        for h in health_list
    ]
