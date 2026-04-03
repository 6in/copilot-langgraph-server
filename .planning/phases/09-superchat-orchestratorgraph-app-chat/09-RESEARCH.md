# Phase 9: SuperChat Integration - Research

**Researched:** 2026-04-04
**Domain:** OrchestratorGraph migration, arq handler pattern, React mode toggle
**Confidence:** HIGH (all findings based on direct source inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** orchestrator コードは `app/orchestrator/` に新設する
  - `agent.py` (SubAgent, SubAgentRegistry)
  - `graph.py` (RouterNode, OrchestratorGraph, build_orchestrator_graph, build_simple_graph)
  - `dispatcher.py` (MenuRegistry, MenuDispatcher)
  - `state.py` (AgentState)
- **D-02:** `super-agent-sample/src/` にあったスタンドアロンの `chat_copilot.py` / `auth_manager.py` コピーは削除し、`app/providers/copilot.py` と `app/auth/manager.py` を直接 import する形に修正する
- **D-03:** `super-agent-sample/` ディレクトリはサンプルとして維持（削除しない）
- **D-04:** 既存の `POST /api/chat` に `mode: Literal['simple', 'super'] = 'simple'` を追加する
- **D-05:** arq worker の `process_chat` 関数内で `mode` に応じてグラフを選択する
  - `simple` → 既存の `app.state.graph`（build_graph の結果）
  - `super` → OrchestratorGraph（起動時に初期化して `app.state.orchestrator_graph` に保存）
- **D-06:** ジョブ返却・SSE・ポーリングのパターンは変えない
- **D-07:** `agents/` と `menus/` ディレクトリはリポジトリルートに置く。環境変数 `AGENT_DIR`（デフォルト: `./agents`）と `MENU_DIR`（デフォルト: `./menus`）で設定可能にする
- **D-08:** React UI にモードトグル（`💬 Simple` / `🚀 Super`）を追加。デフォルト `simple`、ローカル state 管理

### Claude's Discretion

- `AgentState` と既存 `MessagesState` の相互変換の具体的実装
- lifespan での OrchestratorGraph 初期化の具体的コード
- モードトグルの UI 配置（送信ボタン横 or 入力欄上部）

### Deferred Ideas (OUT OF SCOPE)

- Vanilla JS UI 側のモード対応
- 新規エージェント定義の追加
- LangGraph checkpointer を OrchestratorGraph にも適用
- チャットのコンテキストにてユーザー情報も入れる
</user_constraints>

---

## Summary

Phase 9 migrates the `super-agent-sample/src/` prototype into `app/orchestrator/` and wires it into the existing job/SSE pipeline via a new `task_type="orchestrator"` handler. The main app already uses a pluggable `TASK_HANDLERS` dict in `worker.py` — adding the orchestrator is a clean extension, not a branch on `mode` inside `process_chat` itself.

The key insight from reading the actual code: the worker already abstracts task routing via `TaskHandler` subclasses. The cleanest path for D-05 is a new `OrchestratorHandler(TaskHandler)` registered as `task_type="orchestrator"`, mirroring `LangGraphHandler`. The `mode` field from the frontend maps to `task_type` in the POST body — the route handler translates `mode='super'` → `task_type='orchestrator'` before enqueuing.

`AgentState` and `MessagesState` are structurally incompatible (different keys). The OrchestratorGraph returns `result["output"]` (a string), which is the same shape `LangGraphHandler` extracts as `result["messages"][-1].content`. The handler just calls `result["output"]` instead — no shared state schema needed.

**Primary recommendation:** Implement as a new `OrchestratorHandler` in `app/jobs/handlers/orchestrator_handler.py`, register it in `TASK_HANDLERS`, and translate `mode` → `task_type` in the chat route.

---

## Migration Delta

### super-agent-sample/src/agent.py → app/orchestrator/agent.py

**Imports to change:**
```python
# REMOVE (standalone copies in super-agent-sample/src/)
from chat_copilot import ChatCopilot
from auth_manager import CopilotAuthManager
from state import AgentState

# REPLACE WITH
from app.providers.copilot import ChatCopilot
from app.auth.manager import CopilotAuthManager
from app.orchestrator.state import AgentState
```

**Classes to keep unchanged:**
- `SubAgent` — constructor, `from_dir()`, `run()` all unchanged
- `SubAgentRegistry` — unchanged

**Key observation:** `SubAgent.__init__` instantiates `CopilotAuthManager()` directly with no arguments. This is fine — `CopilotAuthManager` has no required constructor args. However, in the main app, `ChatCopilot` can receive a `github_token` directly (bypassing `auth_manager`). For the orchestrator context the `github_token` comes from the job payload — the handler must pass it to ChatCopilot. This means `SubAgent.__init__` needs a `github_token: str` parameter instead of creating its own `CopilotAuthManager`. See Risk Areas.

**frontmatter dependency:** `agent.py` uses `import frontmatter` (python-frontmatter). Verify this is in `pyproject.toml`. If not, `uv add python-frontmatter` is required.

**yaml dependency:** `dispatcher.py` uses `import yaml` (PyYAML). Verify it is in `pyproject.toml`.

---

### super-agent-sample/src/graph.py → app/orchestrator/graph.py

**Imports to change:**
```python
# REMOVE
from chat_copilot import ChatCopilot
from auth_manager import CopilotAuthManager
from state import AgentState
from agent import SubAgentRegistry

# REPLACE WITH
from app.providers.copilot import ChatCopilot
from app.auth.manager import CopilotAuthManager
from app.orchestrator.state import AgentState
from app.orchestrator.agent import SubAgentRegistry
```

**Classes/functions to keep:**
- `RouterNode` — keep as-is structurally, but same `github_token` threading concern applies (see Risk Areas)
- `fallback_node` — keep unchanged
- `build_orchestrator_graph(registry)` — keep signature, keep body
- `build_simple_graph()` — **DROP** this function. The main app already has `app/graph/builder.py:build_graph()` for the simple mode. `build_simple_graph` was only needed in the standalone sample.

**`ROUTER_PROMPT` constant:** Keep as-is.

---

### super-agent-sample/src/dispatcher.py → app/orchestrator/dispatcher.py

**Imports to change:**
```python
# REMOVE
from state import AgentState

# REPLACE WITH
from app.orchestrator.state import AgentState
```

**Classes to keep unchanged:**
- `MenuRegistry` — unchanged
- `MenuDispatcher` — unchanged

**Note:** `MenuDispatcher.dispatch()` takes a `mode: str` parameter that maps to a menu name (e.g., `"super-chat"`). In the main app integration, the orchestrator handler will not use `MenuDispatcher` — it calls `build_orchestrator_graph()` directly. `MenuDispatcher` is available for future extension but is not on the critical path for Phase 9.

---

### super-agent-sample/src/state.py → app/orchestrator/state.py

**No imports to change** — all imports are from stdlib and `langchain_core`.

```python
# File is fully portable as-is:
from __future__ import annotations
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
```

Keep verbatim.

---

## State Compatibility

`AgentState` and `MessagesState` are **structurally incompatible** by design:

| Property | `AgentState` | `MessagesState` |
|----------|-------------|-----------------|
| Input key | `input: str` | `messages: list[BaseMessage]` |
| Output key | `output: str` | `messages: list[BaseMessage]` (appended) |
| Routing key | `next: str` | — |
| Checkpointer | Not used | `AsyncPostgresSaver` |

**How result flows to SSE:**

The `LangGraphHandler` extracts the reply as:
```python
final_text = result["messages"][-1].content
await job_store.save_result(job_id, final_text)
```

The `OrchestratorHandler` extracts it as:
```python
final_text = result["output"]
await job_store.save_result(job_id, final_text)
```

Both call `job_store.save_result(job_id, str)` — the SSE/polling consumers (`/api/job/{id}`, `/api/chat/{job_id}/stream`) read from `job_store` and have no awareness of which graph produced the result. **No shared state schema is needed.**

**Thread history for super mode:** The OrchestratorGraph does not use a checkpointer (unlike the simple graph). This means super-mode conversations have **no persistent history** — each invocation is stateless from the graph's perspective. The CONTEXT.md deferred "LangGraph checkpointer for OrchestratorGraph" — this is consistent. The planner should note this limitation in task comments.

---

## Worker Integration Pattern

The existing worker uses a pluggable `TASK_HANDLERS` dict. The correct integration is:

**1. Add `OrchestratorHandler` to `app/jobs/handlers/orchestrator_handler.py`:**

```python
from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.providers.copilot import ChatCopilot
from app.orchestrator.agent import SubAgentRegistry
from app.orchestrator.graph import build_orchestrator_graph
from app.orchestrator.state import AgentState
import os

AGENT_DIR = os.getenv("AGENT_DIR", "./agents")

class OrchestratorHandler(TaskHandler):
    async def handle(self, ctx: dict, job: dict) -> dict:
        job_id = job["job_id"]
        prompt = job["prompt"]
        github_token = job["github_token"]
        model = job.get("model", "claude-sonnet-4.5")

        job_store = ctx["job_store"]
        notifier = build_notifier(job["reply_to"], job_store)

        try:
            await notifier.progress("thinking")
            registry = SubAgentRegistry(AGENT_DIR)
            graph = build_orchestrator_graph(registry)
            initial: AgentState = {
                "input": prompt,
                "output": "",
                "messages": [],
                "next": "",
            }
            result = await graph.ainvoke(initial)
            final_text = result["output"]

            await job_store.save_result(job_id, final_text)
            await notifier.done()
        except Exception as e:
            await job_store.save_result(job_id, f"Error: {e}")
            await notifier.done()

        return {"job_id": job_id, "status": "done"}
```

**2. Register in `worker.py`:**
```python
from app.jobs.handlers.orchestrator_handler import OrchestratorHandler

TASK_HANDLERS: dict[str, TaskHandler] = {
    "langgraph": LangGraphHandler(),
    "orchestrator": OrchestratorHandler(),
}
```

**3. Route `mode` → `task_type` in `chat.py`:**

```python
# In send_message route, before enqueuing:
task_type = "orchestrator" if body.mode == "super" else (body.task_type or "langgraph")

await arq_redis.enqueue_job(
    "process_chat",
    ...
    task_type=task_type,
)
```

**Alternative:** Map `mode='super'` directly to `task_type='orchestrator'` in the `ChatRequest` model via a validator, avoiding any route-layer logic. Either approach works; the route-layer translation is more explicit.

**Note on `app.state.orchestrator_graph` (D-05):** D-05 specified storing the compiled graph in `app.state`. However, `SubAgentRegistry` reads AGENT.md files from disk — it is fast and stateless. The `OrchestratorHandler` can reconstruct `registry` and `graph` per job without meaningful overhead (no DB connections, no external auth calls). This avoids adding orchestrator lifecycle to `lifespan`. If the planner prefers to follow D-05 literally (pre-compile at startup), the lifespan section below shows how.

---

## Lifespan Init Pattern

If the decision is to pre-initialize the orchestrator graph at startup (D-05 literal interpretation):

```python
# In app/api/main.py lifespan, INSIDE the AsyncPostgresSaver context block,
# after app.state.graph = build_graph(...):

from app.orchestrator.agent import SubAgentRegistry
from app.orchestrator.graph import build_orchestrator_graph

agent_dir = os.getenv("AGENT_DIR", "./agents")
menu_dir = os.getenv("MENU_DIR", "./menus")

registry = SubAgentRegistry(agent_dir)
orchestrator_graph = build_orchestrator_graph(registry)

app.state.orchestrator_graph = orchestrator_graph
app.state.agent_dir = agent_dir
app.state.menu_dir = menu_dir
```

**Caveat:** The arq worker runs in a **separate process** — it does not share `app.state` with the FastAPI process. `app.state.orchestrator_graph` is only accessible to the FastAPI routes, not to the worker. The worker must construct its own graph instance. This confirms that the per-job construction in `OrchestratorHandler` is the correct pattern for the worker, while `app.state.orchestrator_graph` would only be useful if the API process itself called `ainvoke` directly (which it does not — it delegates to arq).

**Recommendation (Claude's discretion):** Skip storing `orchestrator_graph` in `app.state` for Phase 9 since no API route calls it directly. The lifespan only needs to set `AGENT_DIR` / `MENU_DIR` env reading for documentation purposes. The worker reads env vars independently.

---

## Docker Changes

**Services requiring new env vars:** both `api` and `worker` (worker does the actual graph execution; api reads env vars for lifespan init if implemented).

**Volume mounts:** The repo root is already mounted as `.:/app` in both `api` and `worker`. Since `agents/` and `menus/` will live at the repo root, they are automatically available inside containers at `/app/agents` and `/app/menus` — no new volume declarations needed.

**docker-compose.yml changes:**

```yaml
api:
  environment:
    - REDIS_URL=redis://redis:6379
    - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable
    - AGENT_DIR=/app/agents          # add this
    - MENU_DIR=/app/menus            # add this

worker:
  environment:
    - REDIS_URL=redis://redis:6379
    - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable
    - AGENT_DIR=/app/agents          # add this
    - MENU_DIR=/app/menus            # add this
```

**Directory creation:** `agents/` and `menus/` must be created at the repo root. The contents from `super-agent-sample/agents/` and `super-agent-sample/menus/` should be copied (not moved — D-03 says keep the sample directory).

---

## Frontend Changes

### types.ts

Add `mode` to `ChatRequest`:

```typescript
export interface ChatRequest {
  message: string;
  thread_id: string;
  model: string;
  task_type?: string;
  mode?: 'simple' | 'super';   // add this
}
```

### useChat.ts

Add `selectedMode` to `UseChatOptions` and pass it in `postChat`:

```typescript
interface UseChatOptions {
  activeThreadId: string | null;
  selectedModel: string;
  selectedTaskType?: string;
  selectedMode?: 'simple' | 'super';   // add this
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  _onThreadCreated?: (threadId: string) => void;
  refreshThreads?: () => Promise<void>;
}
```

In `sendMessage`:
```typescript
const { job_id } = await postChat({
  message: text,
  thread_id: resolvedThreadId,
  model: selectedModel,
  task_type: selectedTaskType,
  mode: selectedMode ?? 'simple',   // add this
});
```

Add `selectedMode` to the `useCallback` dependency array.

### MessageArea.tsx

Add `mode` prop and toggle button. The toggle sits in the input bar, to the left of the textarea (recommended placement):

```typescript
interface MessageAreaProps {
  messages: ChatMessage[];
  isThinking: boolean;
  onSend: (text: string) => void;
  mode: 'simple' | 'super';         // add this
  onModeChange: (mode: 'simple' | 'super') => void;  // add this
}
```

Toggle button (inside the `chat-input-bar` div, above the textarea row):
```tsx
<div style={{ padding: '4px 8px 0', display: 'flex', gap: '4px' }}>
  <button
    onClick={() => onModeChange('simple')}
    style={{
      padding: '2px 8px',
      borderRadius: '4px',
      border: '1px solid #d1dbe3',
      background: mode === 'simple' ? '#0366d6' : 'none',
      color: mode === 'simple' ? '#fff' : '#666',
      fontSize: '0.8rem',
      cursor: 'pointer',
    }}
  >
    💬 Simple
  </button>
  <button
    onClick={() => onModeChange('super')}
    style={{
      padding: '2px 8px',
      borderRadius: '4px',
      border: '1px solid #d1dbe3',
      background: mode === 'super' ? '#0366d6' : 'none',
      color: mode === 'super' ? '#fff' : '#666',
      fontSize: '0.8rem',
      cursor: 'pointer',
    }}
  >
    🚀 Super
  </button>
</div>
```

### ChatApp.tsx

Add `mode` state and wire it through:

```typescript
const [chatMode, setChatMode] = useState<'simple' | 'super'>('simple');

const { isThinking, sendMessage } = useChat({
  activeThreadId,
  selectedModel,
  selectedMode: chatMode,   // add
  setMessages,
  refreshThreads,
});

// Pass to MessageArea:
<MessageArea
  messages={messages}
  isThinking={isThinking}
  onSend={handleSend}
  mode={chatMode}
  onModeChange={setChatMode}
/>
```

---

## Risk Areas

### 1. `github_token` threading into SubAgent / RouterNode

**Problem:** In `super-agent-sample`, `SubAgent.__init__` calls `CopilotAuthManager()` and `ChatCopilot(model=..., auth_manager=...)`. In the main app, each arq job carries a `github_token` from the authenticated user's JWT. `CopilotAuthManager()` reads a token from disk (`~/.copilot_sdk/token.enc`) — this works in single-user dev but is incorrect in multi-user production (all users would share one token).

**Fix:** Pass `github_token` through `SubAgent.__init__` and `SubAgentRegistry` so `ChatCopilot(github_token=token)` is used instead of `auth_manager`. `RouterNode` has the same issue — it also instantiates `ChatCopilot(auth_manager=CopilotAuthManager())` directly.

**Concretely:**
- `SubAgent.__init__(self, ..., github_token: str)` — store and pass to `ChatCopilot`
- `SubAgent.from_dir(cls, agent_dir, github_token: str)` — accept and forward
- `SubAgentRegistry.__init__(self, agent_dir, github_token: str)` — pass to all `SubAgent.from_dir` calls
- `RouterNode.__init__(self, registry, github_token: str)` — pass to `ChatCopilot`
- `build_orchestrator_graph(registry, github_token: str)` — pass to `RouterNode`
- `OrchestratorHandler.handle` — passes `job["github_token"]` through the chain

This is a **required change**, not optional. Without it the orchestrator uses the on-disk token for all users.

### 2. `python-frontmatter` dependency

`agent.py` imports `frontmatter` (package name: `python-frontmatter`). Check if it's already in `pyproject.toml`:

```bash
grep -i frontmatter /home/parallels/workspaces/copilot-langgraph/pyproject.toml
```

If absent, `uv add python-frontmatter` is required. Do not forget PyYAML (`pyyaml`) for `dispatcher.py`.

### 3. `SubAgentRegistry` constructed per job

Each `OrchestratorHandler.handle()` call constructs a new `SubAgentRegistry`, which reads AGENT.md files from disk. This is acceptable for Phase 9 (fast, no I/O bottleneck for chat latency). However, if `AGENT_DIR` does not exist or is empty, `SubAgentRegistry` will silently produce an empty registry, and `RouterNode` will always return `"fallback"`. The handler should guard against this:

```python
registry = SubAgentRegistry(AGENT_DIR)
if not registry.agents:
    raise RuntimeError(f"No agents found in AGENT_DIR={AGENT_DIR}. Check volume mount and directory contents.")
```

### 4. `build_simple_graph` in graph.py must be dropped

The prototype's `graph.py` contains `build_simple_graph()`. Do not migrate this function — the main app uses `app/graph/builder.py:build_graph()` for simple mode. Including it would create a dead code path and confuse future maintainers.

### 5. `task_type` vs `mode` field overlap

`ChatRequest` already has `task_type: str = "langgraph"`. Adding `mode: Literal['simple', 'super'] = 'simple'` creates two fields that partially overlap in meaning. The route handler must define a clear precedence rule: `mode` takes priority for routing; `task_type` is preserved for backwards compatibility with existing clients that set `task_type` directly. Specifically:
- If `mode == 'super'` → `task_type = 'orchestrator'` (override)
- If `mode == 'simple'` → use `task_type` as-is (default `'langgraph'`)

### 6. `async`/`await` in SubAgent.run

`SubAgent.run` is `async def` — this is correct. `RouterNode.__call__` is also `async def`. LangGraph's `StateGraph.compile()` supports async nodes when `ainvoke` is called. The arq worker calls `await graph.ainvoke(initial)` — fully async. No issues here.

### 7. `agents/` and `menus/` directory must exist before worker starts

If `agents/` does not exist at container start, `SubAgentRegistry` will raise `FileNotFoundError` (from `Path(agent_dir).glob(...)`). The worker startup does not call `SubAgentRegistry` — it is only constructed per job — so the startup itself won't fail. The first `mode='super'` job will fail at runtime. **Action:** Create `agents/` and `menus/` directories and populate them (copy from `super-agent-sample/`) as part of the implementation tasks, not deferred.

---

## Recommended Plan Structure

### Task 1: Create `app/orchestrator/` module
**Files:** `app/orchestrator/__init__.py`, `state.py`, `agent.py`, `dispatcher.py`, `graph.py`
**Actions:**
- Copy content from `super-agent-sample/src/` with import fixes
- Fix all relative imports to use `app.orchestrator.*`, `app.providers.copilot`, `app.auth.manager`
- Add `github_token` parameter threading through `SubAgent`, `SubAgentRegistry`, `RouterNode`, `build_orchestrator_graph`
- Drop `build_simple_graph` from `graph.py`
- Verify `python-frontmatter` and `pyyaml` are in `pyproject.toml`

### Task 2: Create `agents/` and `menus/` at repo root
**Files:** `agents/code-reviewer/AGENT.md`, `agents/code-reviewer/rules.md`, `agents/sql-analyst/AGENT.md`, `menus/super-chat.yaml`, `menus/simple-chat.yaml`
**Actions:**
- Copy content from `super-agent-sample/agents/` and `super-agent-sample/menus/`
- Do not delete `super-agent-sample/` (D-03)

### Task 3: Add `OrchestratorHandler` and wire into worker
**Files:** `app/jobs/handlers/orchestrator_handler.py`, `app/jobs/worker.py`
**Actions:**
- Create `OrchestratorHandler(TaskHandler)` per the pattern above
- Register `"orchestrator": OrchestratorHandler()` in `TASK_HANDLERS`
- Add `AGENT_DIR` env var read in handler

### Task 4: Extend API models and chat route
**Files:** `app/api/models.py`, `app/api/routes/chat.py`, `app/api/main.py`
**Actions:**
- Add `mode: Literal['simple', 'super'] = 'simple'` to `ChatRequest`
- Add `mode` → `task_type` translation in `send_message` route (before `enqueue_job`)
- Add `AGENT_DIR` / `MENU_DIR` env vars to lifespan (for documentation, even if worker builds its own registry)
- Update `docker-compose.yml` with `AGENT_DIR` / `MENU_DIR` env vars for `api` and `worker` services

### Task 5: Add mode toggle to React UI
**Files:** `frontend/src/types.ts`, `frontend/src/hooks/useChat.ts`, `frontend/src/components/MessageArea.tsx`, `frontend/src/components/ChatApp.tsx`
**Actions:**
- Add `mode` field to `ChatRequest` type
- Add `selectedMode` param to `useChat` options and pass in `postChat`
- Add `mode` / `onModeChange` props to `MessageArea` with toggle buttons
- Add `chatMode` state to `ChatApp` and wire through

---

## Environment Availability

The repo mounts `.:/app` for both `api` and `worker` — no new volume declarations needed. `agents/` and `menus/` will exist at repo root.

| Dependency | Required By | Available | Notes |
|------------|-------------|-----------|-------|
| `python-frontmatter` | `app/orchestrator/agent.py` | Unknown — check `pyproject.toml` | `uv add python-frontmatter` if absent |
| `pyyaml` | `app/orchestrator/dispatcher.py` | Unknown — check `pyproject.toml` | `uv add pyyaml` if absent |
| `agents/` dir at repo root | `SubAgentRegistry` | Not yet created | Task 2 creates it |
| `menus/` dir at repo root | `MenuRegistry` | Not yet created | Task 2 creates it |

---

## Sources

All findings are based on direct source code inspection (HIGH confidence). No external references required — the migration is fully characterised by reading the source files.

### Files Inspected
- `super-agent-sample/src/agent.py` — SubAgent, SubAgentRegistry
- `super-agent-sample/src/graph.py` — RouterNode, build_orchestrator_graph, build_simple_graph
- `super-agent-sample/src/dispatcher.py` — MenuRegistry, MenuDispatcher
- `super-agent-sample/src/state.py` — AgentState
- `super-agent-sample/agents/code-reviewer/AGENT.md`, `agents/sql-analyst/AGENT.md`
- `super-agent-sample/menus/super-chat.yaml`, `simple-chat.yaml`
- `app/api/main.py` — lifespan, app.state pattern
- `app/api/routes/chat.py` — POST /api/chat, enqueue_job call
- `app/jobs/worker.py` — TASK_HANDLERS, process_chat
- `app/jobs/handlers/base.py` — TaskHandler ABC
- `app/jobs/handlers/langgraph_handler.py` — canonical handler pattern
- `app/api/models.py` — ChatRequest, ChatAsyncResponse
- `app/providers/copilot.py` — ChatCopilot constructor signature
- `app/auth/manager.py` — CopilotAuthManager
- `app/graph/builder.py` — build_graph (simple mode, not to be replaced)
- `frontend/src/hooks/useChat.ts` — sendMessage, UseChatOptions
- `frontend/src/components/MessageArea.tsx` — input bar structure
- `frontend/src/components/ChatApp.tsx` — useChat call site
- `frontend/src/api/client.ts` — postChat, ChatRequest usage
- `frontend/src/types.ts` — ChatRequest interface
- `docker-compose.yml` — current env vars and volume mounts

---

## Metadata

**Confidence breakdown:**
- Migration delta: HIGH — based on direct file diff
- State compatibility: HIGH — based on reading both state schemas and handler code
- Worker integration: HIGH — existing TaskHandler pattern is clear
- Frontend changes: HIGH — hook and component structure fully inspected
- Risk areas: HIGH — all risks identified from code inspection, not speculation

**Research date:** 2026-04-04
**Valid until:** Stable — no external dependencies; valid until source files change
