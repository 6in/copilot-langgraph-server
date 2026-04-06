"""OrchestratorGraph task handler — routes user input through SubAgent routing."""
import os
import logging
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.orchestrator.agent import SubAgentRegistry
from app.orchestrator.context import RPCContext
from app.orchestrator.gem_agent import GemSubAgent
from app.orchestrator.graph import build_orchestrator_graph
from app.orchestrator.state import AgentState

logger = logging.getLogger(__name__)

AGENT_DIR = os.getenv("AGENT_DIR", "./agents")
APP_DIR = os.getenv("APP_DIR", "./apps")
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

        # Read app_id from job payload; fall back to "superchat" for backward compat (D-08 REVISED)
        app_id: str = job.get("app_id", "superchat")
        registry = SubAgentRegistry(AGENT_DIR, github_token)
        agents_filter: list[str] | None = job.get("agents")
        try:
            await notifier.progress("thinking")

            if not registry.agents:
                raise RuntimeError(
                    f"No agents found in AGENT_DIR={AGENT_DIR}. "
                    "Check that agents/ directory exists and contains AGENT.md files."
                )

            # If no explicit agents_filter from UI chips, derive from APP.md agents list (D-08 REVISED)
            # This allows app-scoped agent filtering without requiring the frontend to pass chips
            if not agents_filter and app_id:
                import frontmatter as fm
                app_md = Path(os.getenv("APP_DIR", APP_DIR)) / app_id / "APP.md"
                if app_md.exists():
                    try:
                        post = fm.load(str(app_md))
                        agents_filter = post.metadata.get("agents") or None
                    except Exception as e:
                        logger.warning(
                            "OrchestratorHandler: failed to load APP.md for app_id=%s: %s",
                            app_id, e,
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

            # D-06: gem_ids を job から読み取る
            gem_ids: list[str] = job.get("gem_ids") or []

            # D-07: DB から招待 Gem を一括取得（所有者または公開 Gem のみ）
            if gem_ids:
                from app.providers.copilot import ChatCopilot
                gem_llm = ChatCopilot(model="claude-haiku-4-5-20251001", github_token=github_token)
                try:
                    async with await psycopg.AsyncConnection.connect(
                        DB_URI, row_factory=dict_row
                    ) as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                """SELECT gem_id, name, description, system_prompt, knowledge
                                   FROM gems
                                   WHERE gem_id = ANY(%s::uuid[])
                                     AND (is_public = true OR github_login = %s)""",
                                (gem_ids, github_login),
                            )
                            gem_rows = await cur.fetchall()
                except Exception as e:
                    logger.warning("OrchestratorHandler: failed to fetch gems: %s", e)
                    gem_rows = []

                # D-08: GemSubAgent を生成し registry.agents に直接マージする
                for row in gem_rows:
                    gem_agent = GemSubAgent(
                        name=row["name"],
                        description=row["description"] or f"Gem: {row['name']}",
                        system_prompt=row["system_prompt"] or "",
                        knowledge=row["knowledge"] or "",
                        llm=gem_llm,
                    )
                    registry.agents[gem_agent.name] = gem_agent
                    logger.info("[registry] merged gem agent: %s", gem_agent.name)

            # Construct RPCContext at job intake — correlation_id generated here flows
            # through every node and log entry (CONTEXT-01, CONTEXT-04)
            context = RPCContext.from_http(
                user_id=github_login,
                app_id=app_id,
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
