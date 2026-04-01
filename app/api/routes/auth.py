"""Auth API routes — Device Flow start/poll/status (AUTH-03).

Endpoints:
- POST /api/auth/start  — begin Device Flow, return user_code + verification_uri + flow_id
- GET  /api/auth/poll   — single poll attempt using flow_id, set JWT cookie on success
- GET  /api/auth/status — JWT cookie auth state (authenticated/expired)
- POST /api/auth/logout — revoke JWT via blocklist, delete session cookie
"""
from uuid import uuid4

import jwt
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.api.models import AuthLogoutResponse, AuthPollResponse, AuthStartResponse, AuthStatusResponse
from app.auth.jwt_utils import add_to_blocklist, create_jwt, decode_jwt

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/start", response_model=AuthStartResponse)
async def start_auth(request: Request):
    """Start GitHub Device Flow. Returns user_code, verification_uri, and flow_id.

    Per D-01: Frontend displays the URL as a clickable link (no window.open).
    Per D-02: Frontend displays user_code with a Copy button.
    Per D-03: Frontend polls /api/auth/poll?flow_id=... every 5 seconds.

    flow_id is a unique key for this Device Flow session — supports multiple
    concurrent auth flows (multi-user capable).
    """
    auth_manager = request.app.state.auth_manager
    flow_data = await auth_manager.start_device_flow()

    # Generate a unique key for this flow session
    flow_id = uuid4().hex

    # Store device_code keyed by flow_id (replaces single "current" key)
    request.app.state.device_flows[flow_id] = flow_data["device_code"]

    return AuthStartResponse(
        user_code=flow_data["user_code"],
        verification_uri=flow_data["verification_uri"],
        device_code=flow_data["device_code"],
        flow_id=flow_id,
    )


@router.get("/poll")
async def poll_auth(request: Request, flow_id: str = Query(...)):
    """Single poll attempt for Device Flow completion.

    Called by frontend every 5 seconds (D-03) with the flow_id from /api/auth/start.
    On success: creates JWT, sets httpOnly session cookie, cleans up flow state.
    Returns {done: true} when authenticated, {done: false} while pending.
    """
    auth_manager = request.app.state.auth_manager
    device_code = request.app.state.device_flows.get(flow_id)

    if not device_code:
        return JSONResponse(
            content=AuthPollResponse(done=False, error="No active auth flow for this flow_id").model_dump()
        )

    try:
        token = await auth_manager.check_device_flow(device_code)
    except RuntimeError as e:
        # Terminal error (expired_token, access_denied)
        request.app.state.device_flows.pop(flow_id, None)
        return JSONResponse(
            content=AuthPollResponse(done=False, error=str(e)).model_dump()
        )

    if token is not None:
        # Auth succeeded — create JWT, set httpOnly cookie, clean up flow state
        jwt_token = create_jwt(token)
        request.app.state.device_flows.pop(flow_id, None)

        response = JSONResponse(content=AuthPollResponse(done=True).model_dump())
        response.set_cookie(
            key="session",
            value=jwt_token,
            httponly=True,
            samesite="lax",
            max_age=86400,  # 24 hours
            path="/",
        )
        return response

    return JSONResponse(content=AuthPollResponse(done=False).model_dump())


@router.post("/logout")
async def logout(request: Request):
    """Log out by revoking the JWT session cookie via in-memory blocklist.

    Reads JWT from session cookie, extracts JTI, adds to blocklist.
    Deletes the session cookie via Set-Cookie response header.

    Does NOT call auth_manager.logout() — token.enc is for CLI use only,
    not for web sessions. Web auth is fully JWT-cookie based.
    Does NOT call llm.close() — LLM token injection is per-request in Task 3.
    """
    session_cookie = request.cookies.get("session")

    if session_cookie:
        try:
            payload = decode_jwt(session_cookie)
            jti = payload.get("jti", "")
            if jti:
                add_to_blocklist(jti)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            # Token already invalid — blocklist not needed, proceed with cookie deletion
            pass

    response = JSONResponse(
        content=AuthLogoutResponse(success=True, message="Logged out successfully.").model_dump()
    )
    response.delete_cookie(key="session", path="/")
    return response


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(request: Request):
    """Return current authentication state based on JWT cookie.

    Per D-04: Frontend checks this to show "Session expired -- click to re-auth"
    in the header when expired=true.

    Auth state is derived entirely from the JWT cookie — no global app.state.auth_expired.
    """
    session_cookie = request.cookies.get("session")

    if not session_cookie:
        return AuthStatusResponse(authenticated=False, expired=False)

    try:
        decode_jwt(session_cookie)
        return AuthStatusResponse(authenticated=True, expired=False)
    except jwt.ExpiredSignatureError:
        return AuthStatusResponse(authenticated=False, expired=True)
    except jwt.InvalidTokenError:
        return AuthStatusResponse(authenticated=False, expired=False)
