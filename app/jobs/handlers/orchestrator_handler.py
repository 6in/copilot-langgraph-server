"""OrchestratorGraph task handler — routes user input through SubAgent routing."""
import os
import logging
from pathlib import Path

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.orchestrator.agent import SubAgentRegistry
from app.orchestrator.context import RPCContext
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
        # model_override: フロントで選択したモデル（未選択/空文字時は None → AGENT.md の model を使用）
        # Python の `or None` で空文字 ("") と None をまとめて None に正規化する
        model_override: str | None = job.get("model") or None
        reply_to: dict = job["reply_to"]

        job_store = ctx["job_store"]
        notifier = build_notifier(reply_to, job_store)

        # Read app_id from job payload; fall back to "superchat" for backward compat (D-08 REVISED)
        app_id: str = job.get("app_id", "superchat")
        # gem_ids (multi-select) takes precedence; fall back to singular gem_id for backward compat
        gem_ids: list[str] = job.get("gem_ids") or ([job["gem_id"]] if job.get("gem_id") else [])
        mcp_tools = ctx.get("mcp_tools", [])
        privileged_names = ctx.get("mcp_privileged_tool_names") or frozenset()
        registry = SubAgentRegistry(
            AGENT_DIR,
            github_token,
            mcp_tools=mcp_tools or None,
            privileged_tool_names=privileged_names,
            model_override=model_override,
        )
        agents_filter: list[str] | None = job.get("agents")
        try:
            await notifier.progress("thinking")

            if not registry.agents:
                raise RuntimeError(
                    f"No agents found in AGENT_DIR={AGENT_DIR}. "
                    "Check that agents/ directory exists and contains AGENT.md files."
                )

            # gem_ids がある場合は各 GemSubAgent を registry に追加してマルチエージェントに参加させる
            if gem_ids:
                try:
                    from app.orchestrator.gem_agent import GemSubAgent, DEFAULT_MODEL
                    import psycopg

                    github_login_for_gem: str = job.get("github_login", "unknown")
                    async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                """SELECT gem_id::text, name, system_prompt
                                   FROM gems
                                   WHERE gem_id = ANY(%s::uuid[])
                                     AND (is_public = true OR github_login = %s)""",
                                (gem_ids, github_login_for_gem),
                            )
                            rows = await cur.fetchall()

                    for row in rows:
                        _gid, gem_name, gem_system_prompt = row
                        gem_agent = GemSubAgent(
                            name=gem_name,
                            system_prompt=gem_system_prompt or "",
                            github_token=github_token,
                            model=model_override or DEFAULT_MODEL,
                        )
                        registry.agents[gem_name] = gem_agent
                        if agents_filter is None:
                            agents_filter = [gem_name]
                        elif gem_name not in agents_filter:
                            agents_filter = [*agents_filter, gem_name]
                        logger.info("OrchestratorHandler: injected GemSubAgent '%s'", gem_name)

                    not_found = len(gem_ids) - len(rows)
                    if not_found:
                        logger.warning("OrchestratorHandler: %d gem_id(s) not found or not accessible", not_found)
                except Exception as e:
                    logger.warning("OrchestratorHandler: gem fetch failed: %s", e)

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
                    "agent_name": None,
                    "context": context,
                    "context_messages": job.get("context_messages"),
                }
                from app.orchestrator.tool_context import tool_event_cb

                async def _tool_cb(tool_name: str, query: str) -> None:
                    await job_store.push_tool_event(job_id, tool_name, query)

                _token = tool_event_cb.set(_tool_cb)
                try:
                    # astream_events で on_chat_model_stream を捕捉してトークンを SSE に流す。
                    # Router (graph.py::Router) と ToolEnabledSubAgent は ainvoke のままなので
                    # これらの LLM 呼び出しは stream 発火しない（意図通り）。
                    # tool なし SubAgent / GemSubAgent のみ token が流れる。
                    result = None
                    async for event in graph.astream_events(initial, config=config, version="v2"):
                        kind = event.get("event")
                        if kind == "on_chat_model_stream":
                            chunk = event["data"].get("chunk")
                            token = getattr(chunk, "content", None) if chunk is not None else None
                            if token:
                                await notifier.send_token(token)
                        elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                            result = event["data"].get("output")
                    if result is None:
                        # astream_events completed but on_chain_end name didn't match
                        # (can happen with nested ReAct subgraphs like ToolEnabledSubAgent).
                        # Read final state from checkpoint instead of re-invoking the graph,
                        # which would process the user's message twice and duplicate messages.
                        final_state = await graph.aget_state(config)
                        if final_state and final_state.values:
                            result = final_state.values
                        else:
                            result = await graph.ainvoke(initial, config=config)
                finally:
                    tool_event_cb.reset(_token)
                    await job_store.clear_tool_event(job_id)
            final_text = result["output"]
            agent_name: str | None = result.get("agent_name")

            import json as _json
            if agent_name:
                saved = _json.dumps({"type": "orchestrator_result", "content": final_text, "agent_name": agent_name})
            else:
                saved = final_text

            await job_store.save_result(job_id, saved)
            await notifier.done()

        except Exception as e:
            logger.exception("OrchestratorHandler failed for job %s", job_id)
            await job_store.save_result(job_id, f"Error: {e}")
            await notifier.done()

        finally:
            await registry.close()

        return {"job_id": job_id, "status": "done"}
