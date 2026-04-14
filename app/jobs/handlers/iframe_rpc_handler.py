"""IframeRpcHandler — handles iframe JSON-RPC requests from Canvas apps (Phase 18).

Supported methods:
  QUERY — executes a SELECT-only SQL query via MCP db_query tool (Phase 23+).
  AI    — invokes ChatCopilot for a one-shot response (no conversation history).

Security notes (T-18-01 through T-18-05):
  - SQL safety (SELECT-only guard, multi-statement prevention) is enforced by the
    MCP db_query tool (mcp_server/tools/db_query.py).
  - pool_name is validated by the MCP db_query tool against its configured pools.
  - github_token is forwarded from the JWT-authenticated HTTP request (T-18-03).
  - MCP server is internal-network only (mcp-server:8001) — no external access.
"""
import datetime
import decimal
import json
import logging

from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.providers.copilot import ChatCopilot
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def _json_default(obj):
    """非 JSON 型を文字列へ変換する（handle() の save_result 互換用）。"""
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class IframeRpcHandler(TaskHandler):
    """Handles task_type='iframe_app_api' dispatched by the arq worker."""

    async def handle(self, ctx: dict, job: dict) -> dict:
        job_id = job["job_id"]
        reply_to = job["reply_to"]
        method = job.get("rpc_method", "")
        params = job.get("rpc_params") or {}
        job_store = ctx["job_store"]
        notifier = build_notifier(reply_to, job_store)

        try:
            if method == "QUERY":
                result = await self._handle_query(ctx, params)
            elif method == "AI":
                result = await self._handle_ai(job, params)
            else:
                result = {"result": False, "error": f"Unknown method: {method}"}

            await job_store.save_result(job_id, json.dumps(result, default=_json_default))
            await notifier.done()
        except Exception as e:
            await job_store.save_result(job_id, json.dumps({"result": False, "error": str(e)}))
            await notifier.done()

        return {"job_id": job_id, "status": "done"}

    async def _handle_query(self, ctx: dict, params: dict) -> dict:
        """Execute a SELECT-only SQL query via MCP db_query tool.

        SQL safety (SELECT-only guard, pool validation) is delegated to the
        MCP db_query tool (mcp_server/tools/db_query.py).

        Args:
            ctx:    arq worker context; must contain ctx["mcp_tools"] list.
            params: {"pool_name": str, "sql": str, "user": str}

        Returns:
            {"result": true, "rows": [...]} on success
            {"result": false, "error": "..."} on any error
        """
        pool_name = params.get("pool_name", "")
        sql = params.get("sql", "")
        user = params.get("user", "")  # D-08: log for future RLS support
        logger.info("iframe-rpc QUERY user=%s pool=%s", user, pool_name)

        mcp_tools = ctx.get("mcp_tools") or []
        tool = next((t for t in mcp_tools if getattr(t, "name", None) == "db_query"), None)
        if tool is None:
            return {"result": False, "error": "db_query tool unavailable (MCP DEGRADED)"}

        try:
            out = await tool.ainvoke({"sql": sql, "pool_name": pool_name})
        except Exception as e:
            return {"result": False, "error": f"db_query invocation failed: {e}"}

        # langchain-mcp-adapters returns a list of content blocks:
        # [{"type": "text", "text": '{"rows":[...]}', "id": "..."}]
        if isinstance(out, list):
            text = next(
                (item["text"] for item in out if isinstance(item, dict) and item.get("type") == "text"),
                None,
            )
            if text is None:
                return {"result": False, "error": "db_query returned empty content list"}
            try:
                out = json.loads(text)
            except json.JSONDecodeError:
                return {"result": False, "error": f"db_query returned unparseable content: {text!r}"}

        if not isinstance(out, dict):
            return {"result": False, "error": f"db_query returned unexpected type: {type(out).__name__}"}
        if "error" in out:
            return {"result": False, "error": out["error"]}
        return {"result": True, "rows": out.get("rows", [])}

    async def _handle_ai(self, job: dict, params: dict) -> dict:
        """Invoke ChatCopilot for a one-shot AI response (D-14: no conversation history).

        Args:
            job:    arq job payload; must contain job["github_token"].
            params: {"model": str, "prompt": str}

        Returns:
            {"result": true, "responseText": "..."} on success
            {"result": false, "error": "..."} on exception
        """
        model = params.get("model", "claude-sonnet-4.5")
        prompt = params.get("prompt", "")
        github_token = job.get("github_token", "")

        llm = ChatCopilot(github_token=github_token, model=model)
        try:
            result = await llm.ainvoke([HumanMessage(content=prompt)])
            return {"result": True, "responseText": result.content}
        finally:
            await llm.close()
