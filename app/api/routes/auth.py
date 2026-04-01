"""Auth API routes — Device Flow start/poll/status (AUTH-03).

Endpoints:
- POST /api/auth/start — begin Device Flow, return user_code + verification_uri
- GET  /api/auth/poll  — single poll attempt, return done/pending
- GET  /api/auth/status — current auth state (authenticated/expired)
"""
from fastapi import APIRouter, Request

from app.api.models import AuthLogoutResponse, AuthPollResponse, AuthStartResponse, AuthStatusResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/start", response_model=AuthStartResponse)
async def start_auth(request: Request):
    """Start GitHub Device Flow. Returns user_code and verification_uri.

    Per D-01: Frontend displays the URL as a clickable link (no window.open).
    Per D-02: Frontend displays user_code with a Copy button.
    Per D-03: Frontend polls /api/auth/poll every 5 seconds.
    """
    auth_manager = request.app.state.auth_manager
    flow_data = await auth_manager.start_device_flow()

    # Store device_code for subsequent poll calls
    request.app.state.device_flows["current"] = flow_data["device_code"]

    return AuthStartResponse(
        user_code=flow_data["user_code"],
        verification_uri=flow_data["verification_uri"],
        device_code=flow_data["device_code"],
    )


@router.get("/poll", response_model=AuthPollResponse)
async def poll_auth(request: Request):
    """Single poll attempt for Device Flow completion.

    Called by frontend every 5 seconds (D-03). Returns {done: true} when
    token is obtained, {done: false} while pending.
    """
    auth_manager = request.app.state.auth_manager
    device_code = request.app.state.device_flows.get("current")

    if not device_code:
        return AuthPollResponse(done=False, error="No active auth flow")

    try:
        token = await auth_manager.check_device_flow(device_code)
    except RuntimeError as e:
        # Terminal error (expired_token, access_denied)
        request.app.state.device_flows.pop("current", None)
        return AuthPollResponse(done=False, error=str(e))

    if token is not None:
        # Auth succeeded — clean up flow state, reset expired flag
        request.app.state.device_flows.pop("current", None)
        request.app.state.auth_expired = False
        return AuthPollResponse(done=True)

    return AuthPollResponse(done=False)


@router.post("/logout", response_model=AuthLogoutResponse)
async def logout(request: Request):
    """Log out by deleting the stored token and resetting in-memory auth state.

    After logout the user can re-authenticate via Device Flow in-browser without
    restarting the server. llm.close() resets ChatCopilot._client so the next
    chat request will re-initialize with the new token.
    """
    auth_manager = request.app.state.auth_manager
    deleted = auth_manager.logout()

    # Reset all in-memory auth state
    request.app.state.auth_expired = False
    request.app.state.device_flows.clear()

    # Reset ChatCopilot client so _ensure_client() re-initializes on next chat
    await request.app.state.llm.close()

    return AuthLogoutResponse(
        success=True,
        message=(
            "Logged out successfully."
            if deleted
            else "No active session found."
        ),
    )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(request: Request):
    """Return current authentication state.

    Per D-04: Frontend checks this to show "Session expired -- click to re-auth"
    in the header when expired=true.
    """
    auth_manager = request.app.state.auth_manager
    token = auth_manager.load_token()

    if token is None:
        return AuthStatusResponse(authenticated=False, expired=False)

    # If chat route detected auth expiry, surface it
    if request.app.state.auth_expired:
        return AuthStatusResponse(authenticated=False, expired=True)

    return AuthStatusResponse(authenticated=True, expired=False)
