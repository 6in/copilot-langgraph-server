# 0006. SuperChat Agent Selection UI and Mode Split

**Date:** 2026-04-04  
**Status:** Accepted

## Context

Phase 9 integrated the OrchestratorGraph into the main app as a mode toggle (Simple / Super buttons) inside the chat input bar. This had two problems:

1. **UX coupling** — Simple and Super chat shared one screen with a toggle button, making the distinction implicit. Users had no way to select *which* agents the Super mode should use; RouterNode chose automatically.
2. **No agent selectability** — The SuperChat mode always invoked all agents registered in `agents/`. There was no way for the user to narrow the routing to a specific subset.

The goal of this branch was to: (a) give SuperChat its own dedicated page at `/app/super`, (b) expose an agent-selection chip UI, and (c) wire the selection through the backend so OrchestratorHandler only instantiates the chosen agents.

Additionally, two UI regressions were caught and fixed post-implementation:
- The Simple/Super toggle remained visible on the `/app` (simple chat) page after the refactor — removed by stripping `mode`/`onModeChange` props from `MessageArea`.
- Removing the toggle div broke `MessageList` scroll because `cs-chat-container` lacked `min-height: 0`, preventing the flex item from shrinking below its natural content height.

## Decision

**Mode split via navigation, not in-page toggle:**
- `/app` renders `ChatApp` — always simple mode, no toggle.
- `/app/super` renders `SuperChatApp` — always super mode, agent chips at top of input area.
- Navigation between modes is done through `MenuScreen` cards, not an in-chat toggle.

**Agent list served by `GET /api/agents`:**
- Scans `AGENT_DIR` for `**/AGENT.md` frontmatter (name + description).
- Returns metadata only — no `github_token` or SDK instantiation needed at list time.
- JWT-protected.

**Agent selection passed as `agents: list[str] | None` through the job pipeline:**
- `ChatRequest` gains an `agents` field.
- `POST /api/chat` → `arq.enqueue_job` → `process_chat` → `OrchestratorHandler` — each layer forwards the field unchanged.
- `OrchestratorHandler` filters `registry.agents` dict to only the requested keys after `SubAgentRegistry` is built. `registry.close()` still covers all loaded agents.
- `None` (simple mode or omitted) means all agents — backward compatible.

**Frontend minimum-1 constraint:**
- `useAgents` enforces that at least one agent is always selected; deselecting the last chip is a no-op.

## Alternatives Considered

**Keep in-page mode toggle, add agent panel below it:**
Discarded — mixing Simple/Super in one screen without persistent state per thread would be confusing. Mode split via navigation makes each surface's purpose clear.

**Expose agent filter at `SubAgentRegistry` constructor level:**
The original `SubAgentRegistry(agent_dir, github_token)` loads all agents eagerly. Rather than adding a constructor parameter, the filter was applied post-construction by reassigning `registry.agents`. This is simpler and keeps `close()` correct (covers all loaded handles).

**Dynamic `GET /api/agents` backed by live SubAgent instantiation:**
Would require a `github_token` at list time. Rejected — listing agent metadata from AGENT.md frontmatter is stateless and cheaper.

## Consequences

**Positive:**
- SuperChat is a first-class UI surface with its own route and agent-selection controls.
- Agent list is dynamically discovered from `agents/` — adding a new AGENT.md file instantly makes it selectable without code changes.
- Simple chat is unaffected; no mode state in `ChatApp`.

**Negative / Gotchas:**
- **SuperChat history is not persisted.** `OrchestratorHandler` does not pass `thread_id` or a checkpointer to the graph. `checkpoints` table has no SuperChat rows → `GET /api/threads` (INNER JOIN checkpoints) never returns SuperChat threads. Tracked in todo: *SuperChat 履歴保存とモード別スレッド分離*.
- **No conversation continuity in Super mode.** Each message starts from `AgentState(input="", messages=[])` — there is no cross-turn memory in SuperChat threads.
- **`min-height: 0` is required on `cs-chat-container`** when used inside a flex column parent. Without it, the chatscope `MessageList` cannot scroll (the container grows unbounded instead). This applies any time `MessageArea` is nested inside a flex container that is not `MainContainer` directly.
- **Worktree isolation caveat:** The executor worktree did not have Phase 9 code (orchestrator_handler.py) because it branched before the feature branch commits. Any future executor running against this codebase must be launched from a branch that includes Phase 9, or the worktree merge step must be performed manually.
