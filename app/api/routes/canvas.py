"""Canvas Apps API routes — HTML app storage, editing, and deployment (Phase 15).

Endpoints:
- POST   /api/canvas/apps/upload           — Upload HTML app
- GET    /api/canvas/apps/{app_id}         — Get app (for editor)
- GET    /api/canvas/apps                  — Get latest app for a thread (?thread_id=)
- PATCH  /api/canvas/apps/{app_id}         — Edit HTML
- POST   /api/canvas/apps/{app_id}/deploy  — Deploy app to static files
- GET    /api/canvas/apps/{app_id}/source  — Get source thread_id for deployed app

All endpoints are JWT-protected via Depends(get_jwt_payload).
Ownership is enforced by filtering on github_login from JWT payload.
404 is returned instead of 403 to avoid leaking app existence (T-15-06).
"""
import os
from pathlib import Path

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.rows import dict_row
from pydantic import BaseModel

from app.api.models import CanvasAppInfo, CanvasDeployResponse
from app.api.routes.chat import get_jwt_payload

router = APIRouter(prefix="/api/canvas", tags=["canvas"])


class CanvasUploadRequest(BaseModel):
    """Request body for POST /api/canvas/apps/upload."""

    name: str
    html: str


class CanvasUpdateRequest(BaseModel):
    """Request body for PATCH /api/canvas/apps/{app_id}."""

    html: str
    name: str | None = None


def _row_to_canvas_app(row: dict) -> CanvasAppInfo:
    """Convert a psycopg dict_row result to a CanvasAppInfo response model."""
    return CanvasAppInfo(
        app_id=str(row["app_id"]),
        thread_id=row["thread_id"],
        name=row["name"],
        thread_label=row.get("thread_label"),
        html=row["html"],
        source=row["source"],
        deployed=row["deployed"],
        deployed_at=row["deployed_at"].isoformat() if row["deployed_at"] else None,
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
    )


@router.post("/apps/upload", response_model=CanvasAppInfo, status_code=201)
async def upload_app(
    body: CanvasUploadRequest,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> CanvasAppInfo:
    """Upload a new HTML app (CANVAS-02).

    Stores the HTML in canvas_apps with source='upload'.
    thread_id is NULL for uploads — they are not associated with a chat thread.
    github_login is taken from the JWT payload.
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO canvas_apps (github_login, name, html, source)
                   VALUES (%s, %s, %s, 'upload')
                   RETURNING app_id, thread_id, name, html, source, deployed, deployed_at, created_at""",
                (github_login, body.name, body.html),
            )
            row = await cur.fetchone()
        await conn.commit()

    return _row_to_canvas_app(row)


@router.get("/gem", response_model=dict)
async def get_canvas_gem_id(
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> dict:
    """Canvas 専用 Gem の gem_id を返す (Phase 16).

    gem_id は UUID — 秘密情報ではないが JWT 保護で一貫性を保つ (T-16-01)。
    """
    return {"gem_id": str(request.app.state.canvas_gem_id)}


@router.get("/apps", response_model=list[CanvasAppInfo])
async def list_or_get_by_thread(
    request: Request,
    thread_id: str | None = None,
    deployed: bool | None = None,
    payload: dict = Depends(get_jwt_payload),
) -> list[CanvasAppInfo]:
    """Get canvas apps for the authenticated user (CANVAS-02).

    If thread_id is provided: returns the most recent app for that thread.
    Otherwise: returns up to 20 most recent apps for the user.
    Optional deployed filter: ?deployed=true returns only deployed apps (Phase 16).
    Ownership is enforced by github_login from JWT.
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            if thread_id is not None:
                await cur.execute(
                    """SELECT ca.app_id, ca.thread_id, ca.name, t.label AS thread_label,
                              ca.html, ca.source, ca.deployed, ca.deployed_at, ca.created_at
                       FROM canvas_apps ca
                       LEFT JOIN threads t ON ca.thread_id = t.thread_id
                       WHERE ca.thread_id = %s AND ca.github_login = %s
                       ORDER BY ca.created_at DESC
                       LIMIT 1""",
                    (thread_id, github_login),
                )
            else:
                query = """SELECT ca.app_id, ca.thread_id, ca.name, t.label AS thread_label,
                                  ca.html, ca.source, ca.deployed, ca.deployed_at, ca.created_at
                           FROM canvas_apps ca
                           LEFT JOIN threads t ON ca.thread_id = t.thread_id
                           WHERE ca.github_login = %s"""
                params: list = [github_login]
                if deployed is not None:
                    query += " AND ca.deployed = %s"
                    params.append(deployed)
                query += " ORDER BY ca.created_at DESC LIMIT 20"
                await cur.execute(query, params)
            rows = await cur.fetchall()

    return [_row_to_canvas_app(row) for row in rows]


@router.get("/apps/{app_id}", response_model=CanvasAppInfo)
async def get_app(
    app_id: str,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> CanvasAppInfo:
    """Get a specific canvas app by ID (for editor) (CANVAS-03).

    Returns 404 if app does not exist or belongs to a different user (T-15-06).
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT app_id, thread_id, name, html, source, deployed, deployed_at, created_at
                   FROM canvas_apps
                   WHERE app_id = %s::uuid AND github_login = %s""",
                (app_id, github_login),
            )
            row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Canvas app not found")

    return _row_to_canvas_app(row)


@router.patch("/apps/{app_id}", response_model=CanvasAppInfo)
async def update_app(
    app_id: str,
    body: CanvasUpdateRequest,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> CanvasAppInfo:
    """Edit an existing canvas app's HTML (and optionally name) (CANVAS-03).

    Returns 404 if app does not exist or belongs to a different user (T-15-06).
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            if body.name is not None:
                await cur.execute(
                    """UPDATE canvas_apps
                       SET html = %s, name = %s
                       WHERE app_id = %s::uuid AND github_login = %s
                       RETURNING app_id, thread_id, name, html, source, deployed, deployed_at, created_at""",
                    (body.html, body.name, app_id, github_login),
                )
            else:
                await cur.execute(
                    """UPDATE canvas_apps
                       SET html = %s
                       WHERE app_id = %s::uuid AND github_login = %s
                       RETURNING app_id, thread_id, name, html, source, deployed, deployed_at, created_at""",
                    (body.html, app_id, github_login),
                )
            row = await cur.fetchone()
        await conn.commit()

    if row is None:
        raise HTTPException(status_code=404, detail="Canvas app not found")

    return _row_to_canvas_app(row)


@router.post("/apps/{app_id}/deploy", response_model=CanvasDeployResponse)
async def deploy_app(
    app_id: str,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> CanvasDeployResponse:
    """Deploy a canvas app to static files (CANVAS-04).

    Writes HTML to ./static/apps/{app_id}/index.html and updates deployed=TRUE.
    app_id is a UUID from the DB — not from user input — so path traversal is not possible (T-15-05).
    Returns the public URL for the deployed app.
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT app_id, html FROM canvas_apps
                   WHERE app_id = %s::uuid AND github_login = %s""",
                (app_id, github_login),
            )
            row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Canvas app not found")

    # Deploy: write to ./static/apps/{app_id}/index.html
    # app_id comes from DB (UUID) — not user input — so path traversal is impossible (T-15-05)
    deploy_dir = Path("./static/apps") / str(row["app_id"])
    deploy_dir.mkdir(parents=True, exist_ok=True)
    app_prefix = os.getenv("APP_PREFIX", "")
    html = row["html"].replace("$URL_PREFIX", app_prefix)
    (deploy_dir / "index.html").write_text(html, encoding="utf-8")

    # Update deployed status
    async with await psycopg.AsyncConnection.connect(db_uri) as conn:
        await conn.execute(
            "UPDATE canvas_apps SET deployed = TRUE, deployed_at = now() WHERE app_id = %s::uuid",
            (app_id,),
        )
        await conn.commit()

    return CanvasDeployResponse(url=f"/apps/{row['app_id']}/")


@router.get("/apps/{app_id}/source")
async def get_source(
    app_id: str,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> dict:
    """Get the source thread_id for a deployed canvas app.

    Returns {"thread_id": str | null} so the frontend can navigate back to the source thread.
    Returns 404 if app does not exist or belongs to a different user (T-15-06).
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT thread_id FROM canvas_apps
                   WHERE app_id = %s::uuid AND github_login = %s""",
                (app_id, github_login),
            )
            row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Canvas app not found")

    return {"thread_id": row["thread_id"]}
