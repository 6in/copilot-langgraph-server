# app/orchestrator/context.py
"""RPCContext frozen dataclass and _keep_first reducer for LangGraph AgentState."""
from dataclasses import dataclass, field
import uuid


def _keep_first(a, b):
    """Reducer for the context field: prefer fresh request context, fall back to existing.

    LangGraph calls this reducer as `_keep_first(checkpointed_value, new_value)` on
    every invocation where the handler passes an initial `context`. Internal graph
    nodes never return `context` in their state updates (verified 2026-04-20 during
    Phase 31 Wave 6 integration check), so the only callers are:

        (a) Initial invocation on a new thread:
            a = None (no checkpoint), b = fresh RPCContext -> returns b
        (b) Re-invocation on an existing thread:
            a = stale checkpointed RPCContext (old correlation_id),
            b = fresh RPCContext (new correlation_id for this request) -> returns b

    The previous semantics ("keep the first-set value") caused Phase 31's
    `correlation_id` / trace_id to stay frozen at the first request's UUID,
    breaking trace isolation across subsequent chats on the same thread_id.
    Child spans (routing / sub_agent / tool_call) read `state.context.correlation_id`
    and inherited the stale trace_id even though the handler's `request` span used
    the fresh correlation_id.

    The None guard preserves the original "don't let an accidental None wipe
    context" behavior from the previous implementation.
    """
    return b if b is not None else a


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
