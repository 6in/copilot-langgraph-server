"""Pydantic v2 request/response models for API endpoints.

Used by:
- app/api/routes/chat.py (Plan 02): ChatRequest, ChatResponse, ThreadInfo
- app/api/routes/auth.py (Plan 02): AuthStartResponse, AuthPollResponse, AuthStatusResponse
"""

from typing import Literal

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    model: str = "gpt-4.1"
    task_type: str = "langgraph"
    mode: Literal["simple", "super"] = "simple"


class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    error: str | None = None


class ThreadInfo(BaseModel):
    thread_id: str
    updated_at: str | None = None
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


class ChatAsyncResponse(BaseModel):
    """Response from POST /api/chat — returns job_id for async tracking."""
    job_id: str
    thread_id: str


class JobStatusResponse(BaseModel):
    """Response from GET /api/job/{job_id} — polling endpoint."""
    status: str  # "pending" | "done"
    result: str | None = None


class UserInfoResponse(BaseModel):
    login: str
    name: str | None = None
    avatar_url: str


class RenameThreadRequest(BaseModel):
    label: str
