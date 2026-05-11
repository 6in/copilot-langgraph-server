"""OrchestratorGraph task handler — routes user input through SubAgent routing."""
import os
import logging
from pathlib import Path

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.jobs.handlers.attachments_helper import (
    build_attachments_hint,
    scan_thread_attachments,
)
from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.observability.trace import trace_span
from app.orchestrator.agent import SubAgentRegistry
from app.orchestrator.context import RPCContext
from app.orchestrator.graph import build_orchestrator_graph
from app.orchestrator.state import AgentState

logger = logging.getLogger(__name__)

AGENT_DIR = os.getenv("AGENT_DIR", "./agents")
APP_DIR = os.getenv("APP_DIR", "./apps")
DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001")


class OrchestratorHandler(TaskHandler):
    """Handles task_type="orchestrator": builds OrchestratorGraph per job and routes input."""

    async def _prepare_new_attachments(
        self,
        job: dict,
        llm,
        model: str,
    ) -> list[dict]:
        """Phase 36 D-14/D-18: job.attachments を取り出し、vision 非対応モデルでは画像を drop する.

        LangGraphHandler._prepare_messages_input と同じロジックだが、SuperChat 経路では
        SubAgent 側で HumanMessage を作るため messages_input ではなく state['new_attachments']
        を経由して伝搬する. SystemMessage 警告は SubAgent 側 system_prompt 注入は v6.1 検討
        (Plan 07 Open Issues). 本 plan では D-18 の画像 drop のみを defense-in-depth で適用する.

        Args:
            job: arq job dict (job.get('attachments') を参照)
            llm: ChatCopilot 互換 (await llm.is_vision_model(model) を呼ぶ)
            model: vision 判定対象のモデル ID

        Returns:
            text/code は全て残し、vision 非対応時は ext in {png,jpg,jpeg,webp} を除外したリスト.
            空 / None / SDK 例外時は [] を返す (fail-safe).
        """
        new_attachments: list[dict] = job.get("attachments") or []
        if not new_attachments:
            return []
        vision_ok = await llm.is_vision_model(model)
        if vision_ok:
            return new_attachments
        image_exts = {"png", "jpg", "jpeg", "webp"}
        return [
            a for a in new_attachments
            if isinstance(a, dict)
            and (a.get("ext") or "").lower().lstrip(".") not in image_exts
        ]

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
        # Extract github_login early so the request span sees the real user_id even on
        # failure paths (instead of "unknown"). Legacy jobs without github_login still
        # get the defensive "unknown" fallback below.
        github_login: str = job.get("github_login", "unknown")

        # Phase 31 Plan 04: build RPCContext at handler entry and wrap the whole
        # job lifecycle in a `request` span. correlation_id becomes trace_id for
        # every routing / sub_agent / tool_call span emitted downstream (D-08).
        context = RPCContext.from_http(
            user_id=github_login,
            app_id=app_id,
            thread_id=thread_id,
        )
        async with trace_span(
            "request",
            trace_id=context.correlation_id,
            attributes={
                "user_id": context.user_id,
                "app_id": context.app_id,
                "thread_id": context.thread_id,
                "handler": "orchestrator",
            },
        ):
            return await self._handle_inner(
                ctx, job, job_store, notifier, context,
                job_id=job_id,
                thread_id=thread_id,
                prompt=prompt,
                github_token=github_token,
                model_override=model_override,
                app_id=app_id,
                github_login=github_login,
            )

    async def _handle_inner(
        self,
        ctx: dict,
        job: dict,
        job_store,
        notifier,
        context: RPCContext,
        *,
        job_id: str,
        thread_id: str,
        prompt: str,
        github_token: str,
        model_override: str | None,
        app_id: str,
        github_login: str,
    ) -> dict:
        """Original handler body, unchanged except that RPCContext is passed in."""
        # gem_ids (multi-select) takes precedence; fall back to singular gem_id for backward compat
        gem_ids: list[str] = job.get("gem_ids") or ([job["gem_id"]] if job.get("gem_id") else [])

        # Phase 37.1: per-job MCP client with x-thread-id / x-github-login headers (Route A).
        # Worker startup の mcp_tools は headers を持たないため、attachments_list/extract が
        # 常に空 thread_id でスキャンしてしまう。job 単位で client を作り直し、
        # その client から取得したツールを agent に bind することで RPCContext を伝播する。
        mcp_tools = ctx.get("mcp_tools", [])  # fallback (startup tools, no headers)
        per_job_mcp_client = None
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient  # noqa: PLC0415

            per_job_mcp_client = MultiServerMCPClient({
                "copilot-tools": {
                    "transport": "streamable_http",
                    "url": MCP_SERVER_URL + "/mcp",
                    "headers": {
                        "x-thread-id": context.thread_id,
                        "x-github-login": context.user_id,
                    },
                }
            })
            mcp_tools = await per_job_mcp_client.get_tools()
        except Exception as e:
            logger.warning(
                "OrchestratorHandler: per-job MCP client failed (%s); falling back to startup tools without headers",
                e,
            )

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

            # RPCContext and github_login are already built above (handler entry).
            # correlation_id propagates via state["context"] to every node and log entry.

            # Phase 37.1: thread フォルダ scan + LLM 向け hint prepend (D-11)
            attachments_meta = scan_thread_attachments(thread_id, github_login)
            attachments_hint = build_attachments_hint(attachments_meta)
            effective_prompt = (
                "## 添付ファイル情報\n" + attachments_hint
                + "\n\n## ユーザー入力\n" + prompt
            ) if attachments_hint else prompt

            # Phase 36 D-14/D-18: per-turn 新規添付 + vision 非対応モデル時の画像 drop
            # (defense-in-depth — UI pre-validate / handler 側 / provider 側で多段防御).
            # aggregator 用 LLM インスタンスを生成して is_vision_model だけ参照する.
            # SubAgent 側の HumanMessage 注入は v6.1 検討 (Plan 07 Open Issues).
            from app.providers.copilot import ChatCopilot  # noqa: PLC0415

            aggregator_model = job.get("model") or "claude-sonnet-4.5"
            _vision_llm = ChatCopilot(github_token=github_token, model=aggregator_model)
            try:
                new_attachments = await self._prepare_new_attachments(
                    job, _vision_llm, aggregator_model,
                )
            finally:
                await _vision_llm.close()

            async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
                await checkpointer.setup()
                graph = build_orchestrator_graph(registry, github_token, checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}

                # Per AgentState reducer: do NOT pass messages — checkpointer accumulates
                # via operator.add. Pass only input/output/next/context/error each turn.
                # context and error must always be present — no NotRequired on AgentState.
                initial: AgentState = {
                    "input": effective_prompt,
                    "output": "",
                    "next": "",
                    "error": None,
                    "agent_name": None,
                    "context": context,
                    "context_messages": job.get("context_messages"),
                    "attachments": attachments_meta or None,
                    # Phase 36 D-14/D-20: per-turn 新規添付 (SubAgent 側で HumanMessage に展開).
                    "new_attachments": new_attachments or None,
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
            # MEDIUM-02 (Phase 37 Code Review): per-job MCP client cleanup。
            # langchain-mcp-adapters 0.1.0+ の MultiServerMCPClient は stateless で、
            # get_tools() 内部で各サーバーごとに新規セッションを生成→即クローズする。
            # 現バージョン (0.1.x) では context manager 利用は NotImplementedError。
            # ただしコードの意図を明確にし、将来のバージョンで stateful な cleanup が
            # 必要になった場合に対応できるよう、明示的な close 試行を入れる。
            # None チェック: 生成時に例外で落ちた場合を考慮。
            if per_job_mcp_client is not None:
                # 優先: aclose / close メソッドがあれば呼ぶ。
                # フォールバック: 何もしない（0.1.x では NotImplementedError な __aexit__ は呼ばない）。
                closer = (
                    getattr(per_job_mcp_client, "aclose", None)
                    or getattr(per_job_mcp_client, "close", None)
                )
                if closer is not None:
                    try:
                        result = closer()
                        if hasattr(result, "__await__"):
                            await result
                    except Exception as e:
                        logger.warning(
                            "OrchestratorHandler: per-job MCP client close failed: %s", e
                        )

        return {"job_id": job_id, "status": "done"}
