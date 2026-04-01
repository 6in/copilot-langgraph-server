"""GET /api/me — GitHub user profile for the authenticated session."""

import jwt as pyjwt
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.auth.jwt_utils import decode_jwt, decrypt_github_token
from app.api.models import UserInfoResponse

router = APIRouter(prefix="/api", tags=["me"])


@router.get("/me", response_model=UserInfoResponse)
async def get_me(request: Request):
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    try:
        payload = decode_jwt(session_cookie)
    except pyjwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Session expired"})
    except pyjwt.InvalidTokenError:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    github_token = decrypt_github_token(payload["github_token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    if resp.status_code != 200:
        return JSONResponse(status_code=502, content={"detail": "GitHub API error"})

    data = resp.json()
    return UserInfoResponse(
        login=data["login"],
        name=data.get("name"),
        avatar_url=data["avatar_url"],
    )
