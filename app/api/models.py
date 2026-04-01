"""Pydantic v2 request/response models for API endpoints.

Used by:
- app/api/routes/chat.py (Plan 02): ChatRequest, ChatResponse, ThreadInfo
- app/api/routes/auth.py (Plan 02): AuthStartResponse, AuthPollResponse, AuthStatusResponse
"""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    model: str = "gpt-4.1"


class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    error: str | None = None


class ThreadInfo(BaseModel):
    thread_id: str
    updated_at: str
    label: str  # "Chat YYYY-MM-DD HH:mm" format


class AuthStartResponse(BaseModel):
    user_code: str
    verification_uri: str
    device_code: str
    flow_id: str  # Unique identifier for this Device Flow session


class AuthPollResponse(BaseModel):
    done: bool
    error: str | None = None
    retry_after: int | None = None  # seconds to wait before next poll (slow_down)


class AuthStatusResponse(BaseModel):
    authenticated: bool
    expired: bool
    username: str | None = None  # Reserved for future multi-user display


class AuthLogoutResponse(BaseModel):
    success: bool
    message: str
