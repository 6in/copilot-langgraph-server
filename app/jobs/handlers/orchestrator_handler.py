"""OrchestratorGraph task handler — routes user input through SubAgent routing."""
import os
import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.orchestrator.agent import SubAgentRegistry
from app.orchestrator.context import RPCContext
from app.orchestrator.graph import build_orchestrator_graph
from app.orchestrator.state import AgentState

logger = logging.getLogger(__name__)

AGENT_DIR = os.getenv("AGENT_DIR", "./agents")
DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")


class OrchestratorHandler(TaskHandler):
    """Handles task_type="orchestrator": builds OrchestratorGraph per job and routes input."""

    async def handle(self, ctx: dict, job: dict) -> dict:
        job_id: str = job["job_id"]
        thread_id: str = job["thread_id"]
        prompt: str = job["prompt"]
        github_token: str = job["github_token"]
        # model is intentionally unused in super mode; each agent's AGENT.md defines its own model
        reply_to: dict = job["reply_to"]

        job_store = ctx["job_store"]
        notifier = build_notifier(reply_to, job_store)

        registry = SubAgentRegistry(AGENT_DIR, github_token)
        agents_filter: list[str] | None = job.get("agents")
        try:
            await notifier.progress("thinking")

            if not registry.agents:
                raise RuntimeError(
                    f"No agents found in AGENT_DIR={AGENT_DIR}. "
                    "Check that agents/ directory exists and contains AGENT.md files."
                )

            # Filter registry to only requested agents (when agents[] provided)
            # None means "all agents" (simple mode or legacy clients)
            if agents_filter:
                registry.agents = {
                    k: v for k, v in registry.agents.items() if k in agents_filter
                }
                if not registry.agents:
                    raise RuntimeError(
                        f"No matching agents after filtering: requested={agents_filter}, "
                        f"available={list(SubAgentRegistry(AGENT_DIR, github_token).agents.keys())}"
                    )

            # Extract github_login from job payload; default to "unknown" for legacy jobs
            github_login: str = job.get("github_login", "unknown")

            # Construct RPCContext at job intake — correlation_id generated here flows
            # through every node and log entry (CONTEXT-01, CONTEXT-04)
            context = RPCContext.from_http(
                user_id=github_login,
                app_id="superchat",
                thread_id=thread_id,
            )

            async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
                await checkpointer.setup()
                graph = build_orchestrator_graph(registry, github_token, checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}

                # Per AgentState reducer: do NOT pass messages — checkpointer accumulates
                # via operator.add. Pass only input/output/next/context/error each turn.
                # context and error must always be present — no NotRequired on AgentState.
                initial: AgentState = {
                    "input": prompt,
                    "output": "",
                    "next": "",
                    "error": None,
                    "context": context,
                }
                result = await graph.ainvoke(initial, config=config)
            final_text = result["output"]

            await job_store.save_result(job_id, final_text)
            await notifier.done()

        except Exception as e:
            logger.exception("OrchestratorHandler failed for job %s", job_id)
            await job_store.save_result(job_id, f"Error: {e}")
            await notifier.done()

        finally:
            await registry.close()

        return {"job_id": job_id, "status": "done"}
