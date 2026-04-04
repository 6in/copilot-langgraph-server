---
phase: quick
plan: 260404-eoj
type: execute
wave: 1
depends_on: []
files_modified:
  - app/api/routes/agents.py
  - app/api/routes/chat.py
  - app/api/models.py
  - app/api/main.py
  - app/jobs/worker.py
  - app/jobs/handlers/orchestrator_handler.py
  - frontend/src/types.ts
  - frontend/src/api/client.ts
  - frontend/src/hooks/useAgents.ts
  - frontend/src/hooks/useChat.ts
  - frontend/src/components/SuperChatApp.tsx
  - frontend/src/components/MessageArea.tsx
  - frontend/src/components/MenuScreen.tsx
  - frontend/src/App.tsx
autonomous: true
must_haves:
  truths:
    - "GET /api/agents returns list of available agents with name and description"
    - "POST /api/chat accepts optional agents[] field and passes it through to worker"
    - "OrchestratorHandler filters SubAgentRegistry to only requested agents when agents[] is provided"
    - "Menu screen shows SuperChat card that navigates to super chat view"
    - "SuperChat view displays agent toggle chips fetched from GET /api/agents"
    - "SuperChat view sends selected agent names in POST /api/chat agents[] field"
  artifacts:
    - path: "app/api/routes/agents.py"
      provides: "GET /api/agents endpoint"
    - path: "frontend/src/components/SuperChatApp.tsx"
      provides: "SuperChat page with agent selection UI"
    - path: "frontend/src/hooks/useAgents.ts"
      provides: "Hook to fetch and manage agent selection state"
  key_links:
    - from: "frontend/src/hooks/useAgents.ts"
      to: "/api/agents"
      via: "fetch on mount"
      pattern: "getAgents"
    - from: "frontend/src/components/SuperChatApp.tsx"
      to: "useChat"
      via: "agents prop in sendMessage"
      pattern: "agents.*postChat"
    - from: "app/api/routes/chat.py"
      to: "app/jobs/worker.py"
      via: "arq enqueue_job agents kwarg"
      pattern: "agents.*enqueue_job"
    - from: "app/jobs/handlers/orchestrator_handler.py"
      to: "SubAgentRegistry"
      via: "filter registry.agents by job agents list"
      pattern: "agents.*registry"
---

<objective>
Add GET /api/agents endpoint, POST /api/chat agents[] field, dynamic agent filtering in OrchestratorHandler, and a SuperChat dedicated page with agent selection toggle UI.

Purpose: Let users choose which agents participate in super mode, enabling targeted multi-agent orchestration instead of always using all agents.
Output: Working SuperChat page at /app screen='superchat' with agent selection and backend plumbing.
</objective>

<execution_context>
@.planning/quick/260404-eoj-superchat-ui/260404-eoj-PLAN.md
</execution_context>

<context>
@app/api/routes/chat.py
@app/api/models.py
@app/jobs/handlers/orchestrator_handler.py
@app/orchestrator/agent.py
@app/jobs/worker.py
@frontend/src/App.tsx
@frontend/src/components/ChatApp.tsx
@frontend/src/components/MenuScreen.tsx
@frontend/src/components/MessageArea.tsx
@frontend/src/hooks/useChat.ts
@frontend/src/api/client.ts
@frontend/src/types.ts

<interfaces>
<!-- Key types and contracts the executor needs -->

From app/api/models.py:
```python
class ChatRequest(BaseModel):
    message: str
    thread_id: str
    model: str = "gpt-4.1"
    task_type: str = "langgraph"
    mode: Literal["simple", "super"] = "simple"
```

From app/orchestrator/agent.py:
```python
class SubAgent:
    def __init__(self, name: str, description: str, model: str, system_prompt: str, github_token: str): ...
    @classmethod
    def from_dir(cls, agent_dir: Path, github_token: str) -> "SubAgent": ...

class SubAgentRegistry:
    def __init__(self, agent_dir: str, github_token: str): ...
    agents: dict[str, SubAgent]
    def get(self, name: str) -> SubAgent: ...
    def all(self) -> list[SubAgent]: ...
```

From app/jobs/worker.py:
```python
async def process_chat(ctx, *, job_id, thread_id, prompt, model, github_token, reply_to, task_type="langgraph") -> dict:
```

From frontend/src/types.ts:
```typescript
export interface ChatRequest {
  message: string; thread_id: string; model: string;
  task_type?: string; mode?: 'simple' | 'super';
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — GET /api/agents endpoint + POST /api/chat agents[] pass-through + OrchestratorHandler filtering</name>
  <files>
    app/api/routes/agents.py
    app/api/models.py
    app/api/routes/chat.py
    app/api/main.py
    app/jobs/worker.py
    app/jobs/handlers/orchestrator_handler.py
  </files>
  <action>
1. **Create `app/api/routes/agents.py`:**
   - New router `APIRouter(prefix="/api", tags=["agents"])`
   - `GET /api/agents` endpoint (JWT protected via `get_jwt_payload` dependency from chat.py)
   - Scans `AGENT_DIR` (env var, default `./agents`) using `pathlib.Path.glob("**/AGENT.md")`
   - For each AGENT.md, parse frontmatter with `python-frontmatter` to extract `name` and `description`
   - Return `list[AgentInfo]` — see model below
   - Do NOT instantiate SubAgent or ChatCopilot — this is metadata-only, no github_token needed

2. **Add to `app/api/models.py`:**
   ```python
   class AgentInfo(BaseModel):
       name: str
       description: str
   ```
   - Add `agents: list[str] | None = None` field to `ChatRequest` — optional list of agent names for super mode

3. **Update `app/api/routes/chat.py` `send_message()`:**
   - Pass `body.agents` through to `arq_redis.enqueue_job()` as `agents=body.agents` kwarg

4. **Update `app/jobs/worker.py` `process_chat()`:**
   - Add `agents: list[str] | None = None` parameter
   - Include `"agents": agents` in the `job` dict passed to handler

5. **Update `app/jobs/handlers/orchestrator_handler.py` `handle()`:**
   - Read `agents_filter: list[str] | None = job.get("agents")` from job dict
   - After building `registry = SubAgentRegistry(AGENT_DIR, github_token)`:
     - If `agents_filter` is not None and not empty, filter `registry.agents` to only keep keys in `agents_filter`:
       ```python
       if agents_filter:
           registry.agents = {k: v for k, v in registry.agents.items() if k in agents_filter}
       ```
     - If filtering results in empty agents dict, raise RuntimeError with helpful message
   - This preserves backward compatibility: when agents[] is None (simple mode or old clients), all agents are used

6. **Register router in `app/api/main.py`:**
   - Import and include `agents.router` alongside existing routers
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && python -c "
import frontmatter, os
from pathlib import Path
# Verify agent scanning works
agent_dir = './agents'
agents = []
for p in Path(agent_dir).glob('**/AGENT.md'):
    post = frontmatter.load(p)
    agents.append({'name': post.metadata['name'], 'description': post.metadata['description']})
assert len(agents) == 2, f'Expected 2 agents, got {len(agents)}'
print('Agent scan OK:', [a['name'] for a in agents])

# Verify models import
from app.api.models import AgentInfo, ChatRequest
req = ChatRequest(message='hi', thread_id='t1', agents=['code-reviewer'])
assert req.agents == ['code-reviewer']
req2 = ChatRequest(message='hi', thread_id='t1')
assert req2.agents is None
print('Models OK')
"</automated>
  </verify>
  <done>
    - GET /api/agents returns 2 agents (code-reviewer, sql-analyst) with name and description
    - ChatRequest accepts optional agents[] field
    - OrchestratorHandler filters registry when agents[] provided, uses all when None
    - Worker passes agents through to handler
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — SuperChat page with agent selection toggle UI</name>
  <files>
    frontend/src/types.ts
    frontend/src/api/client.ts
    frontend/src/hooks/useAgents.ts
    frontend/src/hooks/useChat.ts
    frontend/src/components/SuperChatApp.tsx
    frontend/src/components/MessageArea.tsx
    frontend/src/components/MenuScreen.tsx
    frontend/src/App.tsx
  </files>
  <action>
1. **Add to `frontend/src/types.ts`:**
   ```typescript
   export interface AgentInfo {
     name: string;
     description: string;
   }
   ```
   - Add `agents?: string[]` to `ChatRequest` interface

2. **Add to `frontend/src/api/client.ts`:**
   ```typescript
   export const getAgents = () =>
     apiFetch<AgentInfo[]>(`${API_BASE}/api/agents`);
   ```
   - Import `AgentInfo` from types

3. **Create `frontend/src/hooks/useAgents.ts`:**
   - `useAgents()` hook that:
     - Fetches agents from `getAgents()` on mount
     - Maintains `selectedAgents: Set<string>` state (all selected by default after fetch)
     - Exposes: `agents: AgentInfo[]`, `selectedAgents: string[]` (as array), `toggleAgent(name: string)`, `isLoading: boolean`
     - `toggleAgent`: if agent is selected, remove it; if not, add it. Minimum 1 agent must remain selected (do not allow deselecting the last one)

4. **Update `frontend/src/hooks/useChat.ts`:**
   - Add `agents?: string[]` to `UseChatOptions` interface
   - Pass `agents` through to `postChat()` call: `agents: selectedMode === 'super' ? agents : undefined`
   - Add `agents` to `useCallback` dependency array

5. **Create `frontend/src/components/SuperChatApp.tsx`:**
   - Similar structure to `ChatApp.tsx` but with agent selection panel
   - Uses `useThreads()`, `useChat()`, `useAgents()` hooks
   - Mode is always 'super' (no toggle needed — this is the SuperChat page)
   - Agent selection UI: horizontal row of toggle chips/buttons above the message input area
     - Each chip shows agent name, highlighted with #0366d6 background when selected, transparent when not
     - Clicking toggles selection (useAgents.toggleAgent)
     - Show agent description as `title` attribute (tooltip on hover)
   - Layout: same sidebar + chat area as ChatApp, but with agent chips row between message list and input
   - Pass `selectedAgents` array to `useChat` as `agents` option
   - No Simple/Super toggle buttons (remove mode toggle from this view — it is always super)

6. **Update `frontend/src/components/MenuScreen.tsx`:**
   - Add a second FeatureCard for SuperChat:
     ```
     icon: lightning bolt unicode character (U+26A1)
     title: "SuperChat"
     description: "Multi-agent orchestration with selectable agents"
     onClick: () => onNavigate('superchat')
     ```

7. **Update `frontend/src/App.tsx`:**
   - Import `SuperChatApp`
   - Add `'superchat'` to `currentScreen` state type: `'menu' | 'chat' | 'superchat'`
   - Add screen branch: when `currentScreen === 'superchat'`, render `<SuperChatApp selectedModel={selectedModel} />` with Header (including onBackToMenu)
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>
    - MenuScreen shows SuperChat card alongside Chat card
    - Clicking SuperChat navigates to superchat screen with agent chips
    - Agent chips are fetched from GET /api/agents and displayed as toggleable buttons
    - Selected agents are passed to POST /api/chat as agents[] field
    - TypeScript compiles without errors
  </done>
</task>

</tasks>

<verification>
1. Backend: `python -c "from app.api.models import AgentInfo, ChatRequest; print('OK')"` succeeds
2. Backend: GET /api/agents returns JSON array with code-reviewer and sql-analyst
3. Frontend: `npx tsc --noEmit` passes
4. E2E: Navigate to Menu -> SuperChat -> see agent chips -> toggle agents -> send message with selected agents
</verification>

<success_criteria>
- GET /api/agents returns agent metadata from agents/ directory
- POST /api/chat accepts agents[] and passes through to OrchestratorHandler
- OrchestratorHandler filters registry to selected agents only
- SuperChat page renders with agent selection toggle chips
- All selected agents visible as highlighted chips, deselected agents dimmed
- Message sent from SuperChat includes agents[] in request body
</success_criteria>

<output>
After completion, create `.planning/quick/260404-eoj-superchat-ui/260404-eoj-SUMMARY.md`
</output>
