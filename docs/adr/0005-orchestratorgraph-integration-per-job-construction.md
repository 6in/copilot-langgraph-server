# 0005. OrchestratorGraph Integration — Per-Job Construction over Shared State

**Date:** 2026-04-04  
**Status:** Accepted

## Context

Phase 8 produced a standalone `super-agent-sample/` demonstrating the OrchestratorGraph + SubAgent + RouterNode architecture. Phase 9 integrated this into the main app as a selectable `mode='super'` on `POST /api/chat`.

Two design questions arose during integration:

**1. Where should the orchestrator graph live at runtime?**

The initial design (D-05 in CONTEXT.md) proposed storing a compiled `OrchestratorGraph` in `app.state` at lifespan startup, mirroring how the LangGraph `build_graph()` result is stored. However, the arq worker runs in a **separate process** — it does not share `app.state` with the FastAPI process. Any graph compiled in `lifespan` is inaccessible to the worker that actually runs the job.

**2. How should `github_token` be scoped?**

Each user authenticates via Device Flow and receives a unique `github_token`. `SubAgent` instances each hold a `ChatCopilot` instance that spawns a Copilot SDK subprocess tied to that token. A shared registry would either use a single token (wrong for multi-user) or require complex per-request swap logic.

## Decision

Construct `SubAgentRegistry` and compile the `OrchestratorGraph` **per job** inside `OrchestratorHandler.handle()`, not at startup.

```python
class OrchestratorHandler(TaskHandler):
    async def handle(self, ctx: dict, job: dict) -> dict:
        registry = SubAgentRegistry(AGENT_DIR, github_token)
        try:
            graph = build_orchestrator_graph(registry, github_token)
            result = await graph.ainvoke(initial)
            ...
        finally:
            await registry.close()
```

`SubAgent.close()` and `SubAgentRegistry.close()` were added to terminate Copilot SDK subprocesses in the `finally` block, preventing process leaks.

`github_token` is threaded through `SubAgent.__init__`, `SubAgent.from_dir`, `SubAgentRegistry.__init__`, `RouterNode.__init__`, and `build_orchestrator_graph` so each job runs fully isolated with the requesting user's token.

## Alternatives Considered

**Store compiled graph in `app.state` at lifespan (D-05 original)**  
Rejected because the arq worker is a separate process and cannot access `app.state`. Even if it could, a shared graph would require a shared token, breaking per-user isolation.

**Store registry in worker's global scope (startup hook)**  
arq supports `on_startup` hooks. A shared registry could be created there. Rejected because it would still use a single token (the first user's), and SDK subprocess lifecycle becomes entangled with worker process lifetime rather than request lifetime.

**Cache registry per token**  
Build a dict keyed by `github_token` and reuse across jobs. Not implemented — adds complexity (invalidation, memory growth) for a latency win that is not yet needed. AGENT.md files are small and disk reads are fast.

## Consequences

**Positive:**
- Multi-user token isolation is guaranteed by construction — no shared state between requests
- Worker startup cannot fail due to missing `agents/` directory (failure is deferred to the first `mode='super'` job, where it produces a clear error message)
- No orchestrator lifecycle code needed in FastAPI `lifespan`
- Clean separation: each job owns its registry and cleans up after itself

**Negative / Gotchas:**
- Each `mode='super'` request pays the cost of reading AGENT.md files from disk and spawning Copilot SDK subprocesses. For Phase 9's latency profile (LLM calls dominate), this is negligible. If AGENT.md count grows large or SDK startup becomes slow, a per-worker cache keyed by `github_token` would be the next step.
- `agents/` directory must exist and be populated before any `mode='super'` job runs. The directory is at repo root, mounted as `/app/agents` in Docker via the existing `.:/app` volume. If the directory is missing, the first super-mode request will fail with a `FileNotFoundError` or empty-registry RuntimeError — not a startup failure.
- Super-mode conversations have no checkpointer (no persistent thread history). Each request is stateless. This is explicitly deferred and documented.
- The `finally: await registry.close()` pattern is critical. Without it, each request leaks one Copilot SDK subprocess per SubAgent. The `close()` methods must be called even when `graph.ainvoke` raises.
