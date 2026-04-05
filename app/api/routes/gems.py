"""Gem CRUD API routes — AI persona management (Phase 15).

Endpoints:
- POST   /api/gems              — Create a new Gem
- GET    /api/gems              — List user's Gems
- GET    /api/gems/{gem_id}     — Get a specific Gem
- PATCH  /api/gems/{gem_id}     — Update a Gem
- DELETE /api/gems/{gem_id}     — Delete a Gem

All endpoints are JWT-protected via Depends(get_jwt_payload).
Ownership is enforced by filtering on github_login from JWT payload.
404 is returned instead of 403 to avoid leaking gem existence.
"""
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.rows import dict_row

from app.api.models import GemCreate, GemInfo, GemUpdate
from app.api.routes.chat import get_jwt_payload

router = APIRouter(prefix="/api", tags=["gems"])


def _row_to_gem(row: dict) -> GemInfo:
    """Convert a psycopg dict_row result to a GemInfo response model."""
    return GemInfo(
        gem_id=str(row["gem_id"]),
        name=row["name"],
        system_prompt=row["system_prompt"],
        type=row["type"],
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
    )


@router.post("/gems", response_model=GemInfo, status_code=201)
async def create_gem(
    body: GemCreate,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> GemInfo:
    """Create a new Gem (AI persona) for the authenticated user (GEM-01).

    Inserts a row into the gems table and returns the created gem.
    github_login is taken from the JWT payload — users can only create gems for themselves.
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO gems (github_login, name, system_prompt, type)
                   VALUES (%s, %s, %s, %s)
                   RETURNING gem_id, name, system_prompt, type, created_at, updated_at""",
                (github_login, body.name, body.system_prompt, body.type),
            )
            row = await cur.fetchone()
        await conn.commit()

    return _row_to_gem(row)


@router.get("/gems", response_model=list[GemInfo])
async def list_gems(
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> list[GemInfo]:
    """List all Gems owned by the authenticated user (GEM-02).

    Returns gems sorted by created_at DESC (most recent first).
    Only returns gems belonging to the JWT user — no cross-user access.
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT gem_id, name, system_prompt, type, created_at, updated_at
                   FROM gems
                   WHERE github_login = %s
                   ORDER BY created_at DESC""",
                (github_login,),
            )
            rows = await cur.fetchall()

    return [_row_to_gem(row) for row in rows]


@router.get("/gems/{gem_id}", response_model=GemInfo)
async def get_gem(
    gem_id: str,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> GemInfo:
    """Get a specific Gem by ID (ownership enforced).

    Returns 404 if gem does not exist or belongs to a different user.
    404 is used instead of 403 to avoid leaking gem existence (T-15-01).
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT gem_id, name, system_prompt, type, created_at, updated_at
                   FROM gems
                   WHERE gem_id = %s::uuid AND github_login = %s""",
                (gem_id, github_login),
            )
            row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Gem not found")

    return _row_to_gem(row)


@router.patch("/gems/{gem_id}", response_model=GemInfo)
async def update_gem(
    gem_id: str,
    body: GemUpdate,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> GemInfo:
    """Update a Gem's fields (partial update, ownership enforced).

    Only provided fields are updated (model_dump exclude_unset).
    Returns 422 if no fields are provided.
    Returns 404 if gem does not exist or belongs to a different user (T-15-01).
    Column names are hardcoded — only values are parameterized (T-15-02).
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=422, detail="No fields to update")

    # Build SET clause with hardcoded column names — values are parameterized (T-15-02)
    allowed_columns = {"name", "system_prompt", "type"}
    set_clause = ", ".join(f"{k} = %s" for k in fields if k in allowed_columns)
    values = [v for k, v in fields.items() if k in allowed_columns]

    if not set_clause:
        raise HTTPException(status_code=422, detail="No valid fields to update")

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""UPDATE gems
                    SET {set_clause}, updated_at = now()
                    WHERE gem_id = %s::uuid AND github_login = %s
                    RETURNING gem_id, name, system_prompt, type, created_at, updated_at""",
                (*values, gem_id, github_login),
            )
            row = await cur.fetchone()
        await conn.commit()

    if row is None:
        raise HTTPException(status_code=404, detail="Gem not found")

    return _row_to_gem(row)


@router.delete("/gems/{gem_id}", status_code=204)
async def delete_gem(
    gem_id: str,
    request: Request,
    payload: dict = Depends(get_jwt_payload),
) -> None:
    """Delete a Gem (ownership enforced) (GEM-03).

    Returns 404 if gem does not exist or belongs to a different user (T-15-01).
    Affected threads will have gem_id set to NULL (ON DELETE SET NULL).
    """
    github_login = payload.get("github_login", "unknown")
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri) as conn:
        result = await conn.execute(
            "DELETE FROM gems WHERE gem_id = %s::uuid AND github_login = %s",
            (gem_id, github_login),
        )
        await conn.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Gem not found")
