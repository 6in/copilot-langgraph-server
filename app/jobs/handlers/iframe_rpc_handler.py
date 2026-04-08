"""IframeRpcHandler — handles iframe JSON-RPC requests from Canvas apps (Phase 18).

Supported methods:
  QUERY — executes a SELECT-only SQL query against a named DB pool.
  AI    — invokes ChatCopilot for a one-shot response (no conversation history).

Security notes (T-18-01 through T-18-05):
  - is_select_only strips SQL comments and rejects multi-statement input before
    allowing any query to reach the database.
  - pool_name is validated against ctx["db_pools"] keys — unknown pools rejected.
  - github_token is forwarded from the JWT-authenticated HTTP request (T-18-03).
"""
import json
import logging
import re

from psycopg.rows import dict_row

from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.providers.copilot import ChatCopilot
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

# Matches block comments (/* ... */) and line comments (-- ...)
_COMMENT_RE = re.compile(r'/\*.*?\*/|--[^\n]*', re.DOTALL)
_ALLOWED_PREFIXES = frozenset(["SELECT", "WITH"])


def is_select_only(sql: str) -> bool:
    """Return True only if the SQL is a single SELECT or WITH statement.

    Defense layers (T-18-01):
      1. Strip block and line comments before checking.
      2. Strip trailing semicolon, then reject any remaining semicolons
         (multi-statement prevention).
      3. Verify that the first token is SELECT or WITH.
    """
    cleaned = _COMMENT_RE.sub('', sql).strip()
    body = cleaned.rstrip(';')
    if ';' in body:
        return False
    tokens = body.split()
    return bool(tokens) and tokens[0].upper() in _ALLOWED_PREFIXES


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

            await job_store.save_result(job_id, json.dumps(result))
            await notifier.done()
        except Exception as e:
            await job_store.save_result(job_id, json.dumps({"result": False, "error": str(e)}))
            await notifier.done()

        return {"job_id": job_id, "status": "done"}

    async def _handle_query(self, ctx: dict, params: dict) -> dict:
        """Execute a SELECT-only SQL query against a named psycopg_pool pool.

        Args:
            ctx:    arq worker context; must contain ctx["db_pools"] dict.
            params: {"pool_name": str, "sql": str, "user": str}

        Returns:
            {"result": true, "rows": [...]} on success
            {"result": false, "error": "..."} on any error
        """
        pool_name = params.get("pool_name", "")
        sql = params.get("sql", "")
        user = params.get("user", "")  # D-08: log for future RLS support

        if not is_select_only(sql):
            return {"result": False, "error": "Only SELECT queries are allowed"}

        db_pools = ctx.get("db_pools", {})
        logger.info("iframe-rpc QUERY user=%s pool=%s", user, pool_name)

        if pool_name not in db_pools:
            return {"result": False, "error": f"Unknown pool: {pool_name}"}

        pool = db_pools[pool_name]
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()

        return {"result": True, "rows": [dict(r) for r in rows]}

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
