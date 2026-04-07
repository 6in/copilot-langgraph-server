"""Application packages metadata endpoint — APP-02, T-14-01.

Endpoint:
- GET /api/apps — list available applications with slug/name/description/icon/agents (JWT protected)

Scans APP_DIR for APP.md files, reads frontmatter to extract metadata.
Does NOT instantiate ChatCopilot — metadata-only scan (D-07 REVISED).

JWT protection enforced via Depends(get_jwt_payload) — T-14-01: unauthenticated users get 401.
"""
import os
from pathlib import Path

import frontmatter
from fastapi import APIRouter, Depends

from app.api.models import AppInfo
from app.api.routes.chat import get_jwt_payload

APP_DIR = os.getenv("APP_DIR", "./apps")

router = APIRouter(prefix="/api", tags=["apps"])


@router.get("/apps", response_model=list[AppInfo])
async def list_apps(_payload: dict = Depends(get_jwt_payload)) -> list[AppInfo]:
    """Return available applications by scanning APP_DIR for APP.md files.

    Reads frontmatter fields: name, description, icon, agents.
    JWT-protected — requires valid session cookie (T-14-01).
    Malformed APP.md files are skipped without crashing (T-14-05).
    """
    apps: list[AppInfo] = []
    # Re-read APP_DIR at request time so tests can patch via env var
    app_dir_path = Path(os.getenv("APP_DIR", APP_DIR))
    if not app_dir_path.exists():
        return apps

    for app_md in sorted(app_dir_path.glob("*/APP.md")):
        slug = app_md.parent.name
        try:
            post = frontmatter.load(str(app_md))
            name = post.metadata.get("name", "")
            if not name:
                continue  # Skip malformed entries without a name
            description = post.metadata.get("description", "")
            icon = post.metadata.get("icon", "")
            agents: list[str] = post.metadata.get("agents") or []
            app_type: str = str(post.metadata.get("type", "superchat"))
            apps.append(AppInfo(
                slug=slug,
                name=str(name),
                description=str(description).strip(),
                icon=str(icon),
                agents=list(agents),
                type=app_type,
            ))
        except Exception:
            # Skip malformed APP.md files — do not crash the endpoint
            continue

    return apps
