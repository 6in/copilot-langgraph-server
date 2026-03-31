"""Auth API routes — Device Flow start/poll/status (AUTH-03).

Endpoints:
- POST /api/auth/start — begin Device Flow, return user_code + verification_uri
- GET  /api/auth/poll  — single poll attempt, return done/pending
- GET  /api/auth/status — current auth state (authenticated/expired)
"""
from fastapi import APIRouter, Request

from app.api.models import AuthPollResponse, AuthStartResponse, AuthStatusResponse

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
