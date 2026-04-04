# Phase 11: RPCContext Integration - Research

**Researched:** 2026-04-04
**Domain:** LangGraph AgentState reducer patterns, Python frozen dataclasses, structured logging with correlation_id
**Confidence:** HIGH

## Summary

Phase 11 adds `RPCContext` as an immutable field to `AgentState` using LangGraph's `Annotated[T, reducer]` pattern. The mechanism relies on a `_keep_first` reducer that silently discards any subsequent writes to `state["context"]` after the initial value is set at request intake. This is the canonical pattern for immutable fields in LangGraph TypedDict state.

The codebase already has a well-defined spec: `docs/pre/agent_architecture_additions.md` section 17 contains the exact `RPCContext` dataclass definition, `_keep_first` reducer, updated `AgentState`, factory methods (`from_http`, `from_slack`), and the expected correlation_id log format. The design doc is authoritative — implementation should follow it verbatim.

The integration points are narrow: `app/orchestrator/state.py` (AgentState extension), `app/orchestrator/graph.py` (RouterNode logging), and `app/jobs/handlers/orchestrator_handler.py` (RPCContext construction from job payload). The simple LangGraph chat path (`app/graph/builder.py`) does not use AgentState and does not need changes in Phase 11.

**Primary recommendation:** Implement RPCContext as a `frozen=True` dataclass in a new `app/orchestrator/context.py` module, extend `AgentState` with `context: Annotated[RPCContext, _keep_first]`, add `from_http` and `from_slack` classmethods, inject at OrchestratorHandler call site, and add structured logging to RouterNode.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONTEXT-01 | RPCContext（user_id / app_id / thread_id / correlation_id）が AgentState のフィールドとして統合され、全ノードから state["context"] で参照できる | LangGraph TypedDict + Annotated reducer pattern — HIGH confidence |
| CONTEXT-02 | RPCContext が frozen=True データクラス + _keep_first reducer により、グラフ実行中にノードが上書きできない | Python dataclasses(frozen=True) + LangGraph Annotated pattern — HIGH confidence |
| CONTEXT-03 | HTTP リクエスト（from_http）と Slack イベント（from_slack）から RPCContext を構築するファクトリメソッドが利用できる | Standard @classmethod factory pattern — HIGH confidence |
| CONTEXT-04 | ルーティングログ・監査ログに correlation_id が含まれ、1リクエストの処理を横断追跡できる | Structured logging via Python `logging` module, format already specified in design doc — HIGH confidence |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` (stdlib) | 3.12 | RPCContext definition | `frozen=True` provides immutability enforcement at assignment level; `field(default_factory=lambda: str(uuid.uuid4()))` for auto-generated correlation_id |
| `langgraph` | 1.1.4 (locked) | AgentState with `Annotated[T, reducer]` | `Annotated` metadata in TypedDict fields is how LangGraph merges state across parallel nodes and between turns |
| `typing` / `typing_extensions` | stdlib | `Annotated`, `TypedDict` | Already used in `app/orchestrator/state.py` — no new dependency |
| `logging` (stdlib) | 3.12 | Structured routing + audit logs | Project already uses `logging.getLogger(__name__)` in `orchestrator_handler.py` |
| `uuid` (stdlib) | 3.12 | Auto-generate correlation_id | Standard, already imported in routes/chat.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `operator` (stdlib) | 3.12 | `operator.add` reducer for messages | Already used; keep for `messages` field; `_keep_first` is a custom function, not operator-based |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `frozen=True` dataclass | Pydantic `model_config = ConfigDict(frozen=True)` | Pydantic adds a dependency not currently needed for this type; dataclass is simpler and sufficient |
| `frozen=True` dataclass | Plain TypedDict subkey | No immutability guarantee — any node can overwrite; contradicts CONTEXT-02 |
| Python `logging` | `structlog` library | structlog would require adding a new dependency; plain `logging` with JSON-formatted messages is sufficient for Phase 11 scope |

**Installation:** No new packages needed. All libraries are stdlib or already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

New file:
```
app/
  orchestrator/
    context.py        — RPCContext dataclass + _keep_first reducer
    state.py          — AgentState TypedDict (updated to add context field)
    graph.py          — RouterNode (updated to log correlation_id)
```

No structural changes to handlers, routes, or graph builder.

### Pattern 1: Immutable State Field via _keep_first Reducer

**What:** LangGraph merges node return dicts into state using per-field reducers. For `Annotated[T, reducer_fn]`, the reducer is called as `reducer_fn(current_value, new_value)`. Returning `current_value` unconditionally means the first-written value is preserved even if a node attempts to overwrite it.

**When to use:** Any state field that must be set once at intake and remain unchanged through all graph nodes.

**Example (from docs/pre/agent_architecture_additions.md section 17):**
```python
# app/orchestrator/context.py
from dataclasses import dataclass, field
import uuid


def _keep_first(a, b):
    """context は最初にセットされた値を維持（ノードが上書き不可）"""
    return a


@dataclass(frozen=True)
class RPCContext:
    user_id: str
    app_id: str = ""
    thread_id: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def from_http(cls, request_data: dict) -> "RPCContext":
        """Construct from HTTP request fields (user_id, app_id, thread_id)."""
        return cls(
            user_id=request_data.get("user_id", ""),
            app_id=request_data.get("app_id", ""),
            thread_id=request_data.get("thread_id", ""),
            # correlation_id auto-generated if not provided
        )

    @classmethod
    def from_slack(cls, event: dict) -> "RPCContext":
        """Construct from Slack event payload."""
        return cls(
            user_id=event["user"],
            thread_id=event.get("thread_ts", event["ts"]),
        )
```

```python
# app/orchestrator/state.py  (updated)
from __future__ import annotations
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from app.orchestrator.context import RPCContext, _keep_first


class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
    context: Annotated[RPCContext, _keep_first]
    error: str | None
```

### Pattern 2: RPCContext Injection at OrchestratorHandler

**What:** The OrchestratorHandler is the single point where an HTTP job becomes a graph invocation. This is where RPCContext must be constructed and placed in the initial AgentState dict.

**When to use:** Every invocation of `graph.ainvoke(initial, config=...)` in `OrchestratorHandler.handle()`.

**Example:**
```python
# app/jobs/handlers/orchestrator_handler.py (updated section)
from app.orchestrator.context import RPCContext

# Inside handle():
github_login = job.get("github_login", job.get("user_id", "unknown"))
context = RPCContext(
    user_id=github_login,
    app_id="superchat",
    thread_id=thread_id,
)

initial: AgentState = {
    "input": prompt,
    "output": "",
    "next": "",
    "error": None,
    "context": context,
}
```

### Pattern 3: Structured Routing Log with correlation_id

**What:** RouterNode emits a structured log entry after every routing decision. The log contains `input`, `chosen`, `candidates`, `thread_id`, and `correlation_id`.

**When to use:** Inside `RouterNode.__call__` after `chosen` is determined.

**Example (from docs/pre/agent_architecture_additions.md section 19):**
```python
import json, logging
logger = logging.getLogger(__name__)

# Inside RouterNode.__call__ after routing decision:
context = state.get("context")
logger.info(json.dumps({
    "event": "routing",
    "input": state["input"][:80],
    "chosen": chosen,
    "candidates": [a.name for a in agents],
    "thread_id": context.thread_id if context else "",
    "correlation_id": context.correlation_id if context else "",
}))
```

### Anti-Patterns to Avoid

- **Putting RPCContext in LangGraph config instead of state:** `config["configurable"]` is for checkpointer thread_id and run metadata — it does not flow through node return dicts. Nodes cannot read config. Use state only.
- **Using a mutable dataclass:** Without `frozen=True`, nodes can mutate the context object in-place, bypassing the `_keep_first` reducer.
- **Constructing RPCContext inside a node:** Breaks the immutability contract — the context must be constructed before `ainvoke` and placed in the initial state dict.
- **Adding `context` to the simple chat graph (app/graph/builder.py):** The simple chat graph uses `MessagesState` (a LangGraph built-in), not `AgentState`. Phase 11 scopes to the orchestrator graph only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Immutable field in TypedDict state | Custom state class with `__setattr__` override | `Annotated[RPCContext, _keep_first]` | LangGraph's reducer system is the sanctioned way; custom overrides break graph serialization and checkpointing |
| Correlation ID generation | Random string from `secrets` or timestamp | `uuid.uuid4()` via `field(default_factory=...)` | UUID4 is universally unique, standard, already used in the codebase for job_id/thread_id |
| Structured logging format | Custom log handler | `json.dumps({...})` in `logger.info()` | Minimal, zero-dependency, and sufficient for Phase 11 requirements |

**Key insight:** LangGraph's `Annotated[T, fn]` reducer mechanism is designed exactly for this pattern — custom reducers are a first-class feature, not a workaround.

---

## Common Pitfalls

### Pitfall 1: TypedDict Does Not Enforce Frozen at Runtime

**What goes wrong:** `AgentState` is a TypedDict, so `state["context"] = new_value` compiles and runs without error — the TypedDict itself provides no immutability. The `_keep_first` reducer is only invoked by LangGraph's state merge machinery when a node **returns** a new value for the field.

**Why it happens:** TypedDict is a type hint, not a runtime enforcer. The frozen protection comes from `frozen=True` on the dataclass (mutation of the object) plus `_keep_first` (discards re-assignments via return dict).

**How to avoid:** Never pass `{"context": new_ctx}` from a node that should not update it — simply omit the `context` key from the return dict. Only include fields that the node actually changes.

**Warning signs:** A node returns `{**state, "context": modified}` — this pattern overrides the reducer by flattening all state fields and is a bug.

### Pitfall 2: Initial State Must Include All Required TypedDict Keys

**What goes wrong:** `AgentState` after Phase 11 will have a `context` field with no default. If `OrchestratorHandler` calls `graph.ainvoke` without `"context"` in the initial dict, LangGraph may raise a `KeyError` or silently omit the field.

**Why it happens:** TypedDict fields are required by default (no `NotRequired` annotation). LangGraph validates the initial state dict against the schema.

**How to avoid:** Always include `"context": RPCContext(...)` in the `initial` dict passed to `ainvoke`. Add `error: str | None` with `None` default as well (already in design doc).

**Warning signs:** `KeyError: 'context'` in any node, or the field being `None` when accessed.

### Pitfall 3: `_keep_first` Must Handle the Unset (None) Case

**What goes wrong:** On the first call, LangGraph calls `_keep_first(None, initial_value)` or `_keep_first(initial_value, None)` depending on whether the field was previously unset in the checkpoint.

**Why it happens:** When a new thread starts, there is no prior checkpoint value. LangGraph may pass `None` as the first argument.

**How to avoid:** Implement `_keep_first` to handle `None`:
```python
def _keep_first(a, b):
    return a if a is not None else b
```

**Warning signs:** `context` is `None` in a node even though it was set in the initial state.

### Pitfall 4: frozen=True Dataclass in LangGraph Checkpoint Serialization

**What goes wrong:** LangGraph checkpointers (PostgreSQL) serialize state to JSON/pickle. A `frozen=True` dataclass is not JSON-serializable by default, and `dataclasses.asdict()` is needed for the serializer to work.

**Why it happens:** LangGraph's PostgreSQL checkpointer uses pickle-based serialization (not pure JSON), so Python dataclasses are typically safe. However, if a custom serializer is added later, `frozen=True` breaks field mutation during deserialization.

**How to avoid:** Verify pickle round-trip works. For Phase 11 scope (PostgreSQL checkpointer via `AsyncPostgresSaver`), pickle serialization of dataclasses is safe. No action needed unless switching to a JSON-only checkpointer.

**Warning signs:** `TypeError: cannot assign to field 'x'` during checkpoint restore.

### Pitfall 5: RouterNode Receives State Without context on First Turn (Legacy Threads)

**What goes wrong:** Existing threads in PostgreSQL have checkpoints without a `context` key. When a second message is sent to an old thread, LangGraph loads the checkpoint and the merged state may be missing `context`.

**Why it happens:** Old checkpoints predate Phase 11 and were saved without the `context` field.

**How to avoid:** Use `.get("context")` in nodes rather than direct `state["context"]` access. `RouterNode` and logging code must guard against `None`.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'correlation_id'`.

---

## Code Examples

### RPCContext Definition (from design doc, section 17-6)

```python
# app/orchestrator/context.py
from dataclasses import dataclass, field
import uuid


def _keep_first(a, b):
    """Keeps the first-set context value; discards node overwrites."""
    return a if a is not None else b


@dataclass(frozen=True)
class RPCContext:
    user_id: str
    app_id: str = ""
    thread_id: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def from_http(cls, user_id: str, app_id: str, thread_id: str) -> "RPCContext":
        return cls(user_id=user_id, app_id=app_id, thread_id=thread_id)

    @classmethod
    def from_slack(cls, event: dict) -> "RPCContext":
        return cls(
            user_id=event["user"],
            thread_id=event.get("thread_ts", event["ts"]),
        )
```

### AgentState Update (from design doc, section 17-2)

```python
# app/orchestrator/state.py
from __future__ import annotations
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from app.orchestrator.context import RPCContext, _keep_first


class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
    context: Annotated[RPCContext, _keep_first]
    error: str | None
```

### OrchestratorHandler Initial State (from design doc, section 17-3)

```python
# OrchestratorHandler.handle() — construct RPCContext from job fields
context = RPCContext.from_http(
    user_id=job.get("github_login", "unknown"),
    app_id="superchat",
    thread_id=thread_id,
)
initial: AgentState = {
    "input": prompt,
    "output": "",
    "next": "",
    "error": None,
    "context": context,
}
result = await graph.ainvoke(initial, config=config)
```

### Routing Log with correlation_id (from design doc, section 19-5)

```python
# RouterNode.__call__() — after chosen is determined
import json, logging
logger = logging.getLogger(__name__)

context = state.get("context")
logger.info(json.dumps({
    "event": "routing",
    "input": state["input"][:80],
    "chosen": chosen,
    "candidates": [a.name for a in agents],
    "thread_id": context.thread_id if context else "",
    "correlation_id": context.correlation_id if context else "",
}))
```

---

## Current State Analysis

### What Exists Today

| Component | Location | Current State | Phase 11 Change |
|-----------|----------|---------------|-----------------|
| `AgentState` | `app/orchestrator/state.py` | `input`, `output`, `messages`, `next` — no context | Add `context` + `error` fields |
| `RouterNode` | `app/orchestrator/graph.py` | `print()` statements only, no correlation_id | Replace with `logger.info(json.dumps(...))` including `correlation_id` |
| `OrchestratorHandler` | `app/jobs/handlers/orchestrator_handler.py` | Constructs `initial` dict without context | Add `context = RPCContext.from_http(...)` before `ainvoke` |
| `SubAgent.run()` | `app/orchestrator/agent.py` | Does not access `context` | No change needed for Phase 11 — context available if needed |
| `app/graph/builder.py` | simple chat path | Uses `MessagesState` (LangGraph built-in) | No change — out of scope |

### Where user_id / app_id / thread_id Come From Today

In `app/api/routes/chat.py`:
- `github_login` from `payload.get("github_login", "unknown")` (JWT claim)
- `app_id = "superchat" if body.mode == "super" else "chat"`
- `thread_id = body.thread_id`

These are currently NOT passed to the arq worker job payload (only `github_token` is passed). For Phase 11, `github_login` must be added to the job payload so `OrchestratorHandler` can construct `RPCContext.from_http(user_id=github_login, ...)`.

**Current job payload fields in `process_chat`:**
```
job_id, thread_id, prompt, model, github_token, reply_to, task_type, agents
```

**Required addition for Phase 11:**
```
github_login (from JWT payload in chat.py)
```

This means `POST /api/chat` must pass `github_login` to `arq_redis.enqueue_job()`, and `process_chat` worker function signature must accept it.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `print()` for routing debug | `logger.info()` with structured JSON | Phase 11 | Enables log aggregation, grep by correlation_id |
| No context field in AgentState | `context: Annotated[RPCContext, _keep_first]` | Phase 11 | Immutable tracing context in every node |

---

## Open Questions

1. **Should `from_http` use HTTP headers or job payload fields?**
   - What we know: The design doc's `from_http` reads HTTP headers (`X-User-Id` etc.). The actual app passes these values via arq job payload (no direct HTTP headers in the worker context).
   - What's unclear: Whether to follow the design doc signature literally or adapt it to read from the job dict.
   - Recommendation: Implement `from_http` as a classmethod that takes explicit kwargs (`user_id`, `app_id`, `thread_id`) rather than raw HTTP headers, since the worker never has the raw request. The name `from_http` still signals the semantic intent.

2. **Should `github_login` be renamed to `user_id` at the job payload boundary?**
   - What we know: The project uses `github_login` throughout. `RPCContext` uses `user_id` (generic).
   - What's unclear: Whether Phase 11 introduces a naming conversion or passes `github_login` value as `user_id`.
   - Recommendation: Pass `github_login` value as `user_id` in `RPCContext`. No renaming needed at DB or JWT level.

3. **Should CONTEXT-04 audit log entries go to the `audit_log` DB table (already created in `main.py`) or to application logs only?**
   - What we know: `audit_log` table exists with `correlation_id`-friendly `metadata JSONB` column. REQUIREMENTS.md has CONTEXT-05 (DB audit) as a v3.1 future requirement, explicitly deferred.
   - What's unclear: Whether CONTEXT-04 means "application log entries" or "DB writes."
   - Recommendation: CONTEXT-04 = structured application log entries only (not DB writes). CONTEXT-05 (DB audit) is explicitly v3.1 out of scope. The planner should confirm this boundary.

---

## Environment Availability

Step 2.6: Environment availability audit for Phase 11 dependencies.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | See pyproject.toml | 3.12.3 (from uv.lock) | — |
| `dataclasses` stdlib | RPCContext | Built-in | 3.12 | — |
| `uuid` stdlib | correlation_id | Built-in | 3.12 | — |
| `logging` stdlib | Structured logs | Built-in | 3.12 | — |
| `langgraph` | AgentState | Locked 1.1.4 | 1.1.4 | — |
| PostgreSQL | Checkpointer | Docker service | 17 (pgvector image) | — |
| Redis | arq worker | Docker service | current | — |

All dependencies available. No blocking gaps.

---

## Validation Architecture

nyquist_validation is enabled (config.json has `"nyquist_validation": true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0 + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| Quick run command | `pytest tests/test_worker.py tests/test_graph.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONTEXT-01 | state["context"] accessible from RouterNode after ainvoke | unit | `pytest tests/test_rpccontext.py::test_context_accessible_in_node -x` | Wave 0 |
| CONTEXT-02 | Node returning new context value has no effect — original survives | unit | `pytest tests/test_rpccontext.py::test_context_immutable_via_reducer -x` | Wave 0 |
| CONTEXT-02 | frozen=True dataclass raises FrozenInstanceError on mutation | unit | `pytest tests/test_rpccontext.py::test_rpccontext_frozen -x` | Wave 0 |
| CONTEXT-03 | RPCContext.from_http() produces correct field values | unit | `pytest tests/test_rpccontext.py::test_from_http_factory -x` | Wave 0 |
| CONTEXT-03 | RPCContext.from_slack() produces correct field values | unit | `pytest tests/test_rpccontext.py::test_from_slack_factory -x` | Wave 0 |
| CONTEXT-04 | RouterNode log output contains correlation_id | unit | `pytest tests/test_rpccontext.py::test_router_log_contains_correlation_id -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_rpccontext.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_rpccontext.py` — covers CONTEXT-01 through CONTEXT-04; new file needed

*(Existing test infrastructure covers all other requirements; only one new test file needed)*

---

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md are binding on this phase:

| Directive | Impact on Phase 11 |
|-----------|-------------------|
| Tech stack: Python only | RPCContext is a Python dataclass; no TypeScript changes needed |
| `langchain-core` only (not full `langchain`) | AgentState uses `langchain_core.messages.BaseMessage` only — already compliant |
| SDK pinned `github-copilot-sdk==0.2.0` | Not touched in Phase 11 |
| `pyproject.toml` for dependencies | No new packages needed — all stdlib |
| Async-first: all routes are `async def` | `OrchestratorHandler.handle()` is already async; RPCContext construction is sync (dataclass) |
| Backend architecture: `app/orchestrator/` for orchestrator code | New `context.py` module goes in `app/orchestrator/` |
| Primary startup method: `docker compose up` | Integration testing via docker compose |
| No direct repo edits outside GSD workflow | Planner must structure tasks within GSD execution |
| Branch required: never commit directly to main | Phase work on dedicated branch |

---

## Sources

### Primary (HIGH confidence)
- `docs/pre/agent_architecture_additions.md` (sections 17–19) — definitive RPCContext design, AgentState spec, reducer pattern, and routing log format
- `app/orchestrator/state.py` — current AgentState definition (confirmed by direct read)
- `app/orchestrator/graph.py` — current RouterNode implementation (confirmed by direct read)
- `app/jobs/handlers/orchestrator_handler.py` — current job handler (confirmed by direct read)
- `app/api/routes/chat.py` — current HTTP-to-job-payload flow (confirmed by direct read)
- Python `dataclasses` stdlib documentation — `frozen=True` behavior
- LangGraph TypedDict `Annotated` reducer pattern — confirmed by existing `operator.add` usage in `state.py`

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — CONTEXT-01 through CONTEXT-04 requirements
- `.planning/ROADMAP.md` — Phase 11 success criteria

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed in lock file, all stdlib
- Architecture: HIGH — design doc in repo defines exact implementation; current code confirmed by direct read
- Pitfalls: HIGH — based on confirmed LangGraph behavior and codebase-specific patterns

**Research date:** 2026-04-04
**Valid until:** 2026-07-04 (LangGraph 1.1.4 locked; stable for 90 days)
