"""Agents metadata endpoint.

Endpoint:
- GET /api/agents — list available agents with name and description (JWT protected)

Scans AGENT_DIR for AGENT.md files, reads frontmatter to extract name and description.
Does NOT instantiate SubAgent or ChatCopilot — metadata-only, no github_token needed.
"""
import os
from pathlib import Path

import frontmatter
from fastapi import APIRouter, Depends

from app.api.models import AgentInfo
from app.api.routes.chat import get_jwt_payload

AGENT_DIR = os.getenv("AGENT_DIR", "./agents")

router = APIRouter(prefix="/api", tags=["agents"])


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents(_payload: dict = Depends(get_jwt_payload)) -> list[AgentInfo]:
    """Return available agents by scanning AGENT_DIR for AGENT.md files.

    Reads frontmatter fields: name, description.
    JWT-protected — requires valid session cookie.
    """
    agents: list[AgentInfo] = []
    agent_path = Path(AGENT_DIR)
    if not agent_path.exists():
        return agents

    for agent_md in sorted(agent_path.glob("**/AGENT.md")):
        try:
            post = frontmatter.load(str(agent_md))
            name = post.metadata.get("name", "")
            description = post.metadata.get("description", "")
            if name:
                agents.append(AgentInfo(name=name, description=description.strip()))
        except Exception:
            # Skip malformed AGENT.md files
            continue

    return agents
