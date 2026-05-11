"""Pydantic v2 request/response models for API endpoints.

Used by:
- app/api/routes/chat.py (Plan 02): ChatRequest, ChatResponse, ThreadInfo
- app/api/routes/auth.py (Plan 02): AuthStartResponse, AuthPollResponse, AuthStatusResponse
"""

from typing import Literal

from pydantic import BaseModel


class AgentInfo(BaseModel):
    name: str
    description: str


class AppInfo(BaseModel):
    """Application package metadata returned by GET /api/apps (APP-02)."""

    slug: str
    name: str
    description: str
    icon: str
    agents: list[str]
    type: str = "superchat"


class ContextMessage(BaseModel):
    """Past conversation message for context injection (SuperChat)."""
    role: Literal["user", "ai"]
    content: str
    sender_name: str | None = None


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    model: str = "gpt-4.1"
    task_type: str = "langgraph"
    mode: Literal["simple", "super"] = "simple"
    agents: list[str] | None = None  # Optional list of agent names for super mode filtering
    app_id: str | None = None  # Application identifier (preferred over mode-derived mapping)
    gem_id: str | None = None  # Phase 15: Gem ID for thread association
    gem_ids: list[str] | None = None  # Phase 16: Gem IDs for SuperChat sub-agents
    context_messages: list[ContextMessage] | None = None  # 過去の会話コンテキスト（SuperChat用）
    # Phase 17: 討論チャット用フィールド
    participants: list[str] | None = None  # 討論参加者エージェント名リスト
    pattern: str = "debate"                # "debate" | "panel" | "chain"
    max_turns: int = 3                     # 討論ターン数
    current_turn: int = 0                  # 再エンキュー時に前回の終了ターンを渡す
    # Phase 36 (D-14): per-turn attachments — D-14 統一 dict スキーマのリスト
    # (kind / name / storage_name / path / size / mime_type / ext / modified_at)
    # pydantic 側で構造バリデーションはしない。worker 側で defensive `.get()` + `isinstance` で validate。
    attachments: list[dict] | None = None


class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    error: str | None = None


class ThreadInfo(BaseModel):
    thread_id: str
    updated_at: str | None = None
    label: str  # "Chat YYYY-MM-DD HH:mm" format
    app_id: str | None = None  # "chat" | "superchat" — application the thread belongs to


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


class AgentHealthEntry(BaseModel):
    name: str
    agent_type: str
    status: str  # "HEALTHY" | "DEGRADED" | "FAILED"
    error: str | None = None


class GemCreate(BaseModel):
    """Request body for POST /api/gems."""

    name: str
    system_prompt: str = ""
    description: str = ""    # Todo 6: Gem の説明文
    knowledge: str = ""      # Todo 7: ナレッジ（system_prompt に結合される）
    type: Literal["default", "canvas"] = "default"
    is_public: bool = False  # 公開共有フラグ


class GemUpdate(BaseModel):
    """Request body for PATCH /api/gems/{gem_id}."""

    name: str | None = None
    system_prompt: str | None = None
    description: str | None = None   # Todo 6
    knowledge: str | None = None     # Todo 7
    type: Literal["default", "canvas"] | None = None
    is_public: bool | None = None    # 公開共有フラグ


class GemInfo(BaseModel):
    """Response model for Gem endpoints."""

    gem_id: str
    name: str
    system_prompt: str
    description: str          # Todo 6: Gem カードに表示する説明文
    knowledge: str            # Todo 7: ナレッジ（フロントエンドの編集フォームに表示）
    type: str
    is_public: bool           # 公開共有フラグ
    is_owner: bool            # リクエストユーザーが所有者かどうか
    created_at: str
    updated_at: str


class CanvasAppInfo(BaseModel):
    """Response model for Canvas App endpoints."""

    app_id: str
    thread_id: str | None = None
    name: str
    thread_label: str | None = None
    html: str
    source: str
    deployed: bool
    deployed_at: str | None = None
    created_at: str


class CanvasDeployResponse(BaseModel):
    """Response model for POST /api/canvas/apps/{app_id}/deploy."""

    url: str
