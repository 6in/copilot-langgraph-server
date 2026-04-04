# app/orchestrator/context.py
"""RPCContext frozen dataclass and _keep_first reducer for LangGraph AgentState."""
from dataclasses import dataclass, field
import uuid


def _keep_first(a, b):
    """Keeps the first-set context value; discards node overwrites.

    LangGraph calls this reducer as _keep_first(current_value, new_value) when
    a node returns a new value for the context field. Returning the existing value
    unconditionally preserves the context set at request intake.

    Handles the unset checkpoint case: when a new thread starts, LangGraph may
    pass None as the first argument (no prior checkpoint). In that case, return b.
    """
    return a if a is not None else b


@dataclass(frozen=True)
class RPCContext:
    """Immutable request context threaded through all LangGraph nodes.

    Fields:
        user_id: GitHub login or Slack user ID of the requestor.
        app_id: Application identifier (e.g. "superchat", "chat").
        thread_id: Conversation thread identifier.
        correlation_id: Auto-generated UUID4 for cross-log tracing.
    """

    user_id: str
    app_id: str = ""
    thread_id: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def from_http(cls, user_id: str, app_id: str, thread_id: str) -> "RPCContext":
        """Construct RPCContext from HTTP request fields.

        Takes explicit kwargs rather than raw HTTP headers because the arq worker
        never has the raw HTTP request — the fields are passed via job payload.
        """
        return cls(user_id=user_id, app_id=app_id, thread_id=thread_id)

    @classmethod
    def from_slack(cls, event: dict) -> "RPCContext":
        """Construct RPCContext from a Slack event payload.

        thread_id uses thread_ts if present (reply in a thread), otherwise ts
        (top-level message).
        """
        return cls(
            user_id=event["user"],
            thread_id=event.get("thread_ts", event["ts"]),
        )
