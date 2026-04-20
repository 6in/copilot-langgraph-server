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

Phase 31 observability (D-08 .. D-12):
  - handle() is wrapped in a "request" span (trace_id = job["correlation_id"]).
  - _handle_query invokes the db_query MCP tool inside a "tool_call" span
    (privileged=False because db_query has sandbox_exposed=true in config/mcp_tools.yaml).
  - _handle_ai invokes ChatCopilot inside a "tool_call" span with tool_name="ai".
  - The old free-text log ``iframe-rpc QUERY user=... pool=...`` is removed; user_id
    and pool_name are surfaced as span attributes instead.
"""
import datetime
import decimal
import json
import logging

from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.observability.config import get_args_max_chars, get_result_max_chars
from app.observability.trace import trace_span
from app.orchestrator.context import RPCContext
from app.providers.copilot import ChatCopilot
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


# AI モデルエイリアス → Copilot SDK の実モデル ID へのマッピング。
# 将来 config.yaml に移行する余地を残すためクラス外の定数として定義する。
MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "gpt-4.1": "gpt-4.1",
}
# 許可済み実モデル ID（エイリアスを使わず直接指定された場合のホワイトリスト）
ALLOWED_MODEL_IDS: frozenset[str] = frozenset(MODEL_ALIASES.values())
DEFAULT_MODEL_ALIAS: str = "haiku"


def resolve_model(value: str | None) -> str:
    """モデル値をエイリアス解決する。

    - None → 既定 (haiku)
    - エイリアス ('haiku'/'sonnet'/'gpt-4.1') → 対応する実 ID
    - 実 ID 直指定 (ALLOWED_MODEL_IDS 内) → 素通り
    - 空文字列・未知のエイリアス・ALLOWED 外の実 ID → ValueError

    silent fallback は行わない。呼び出し側は ValueError を捕捉して
    {"result": False, "error": str(e)} を返すこと。
    """
    if value is None:
        return MODEL_ALIASES[DEFAULT_MODEL_ALIAS]
    if value == "":
        raise ValueError(
            f"model must not be empty. Allowed aliases: {sorted(MODEL_ALIASES.keys())}, "
            f"or one of the real IDs: {sorted(ALLOWED_MODEL_IDS)}"
        )
    if value in MODEL_ALIASES:
        return MODEL_ALIASES[value]
    if value in ALLOWED_MODEL_IDS:
        return value
    raise ValueError(
        f"Unknown model '{value}'. Allowed aliases: {sorted(MODEL_ALIASES.keys())}, "
        f"or one of the real IDs: {sorted(ALLOWED_MODEL_IDS)}"
    )


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
        github_login = job.get("github_login", "unknown")
        # Phase 31 D-08: route (Task 2) populates correlation_id + app_id; fallback for
        # legacy payloads keeps handler runnable in isolation (tests, replay).
        correlation_id = job.get("correlation_id") or ""
        app_id = job.get("app_id") or "canvas"
        job_store = ctx["job_store"]
        notifier = build_notifier(reply_to, job_store)

        # Phase 31 D-08: RPCContext は他 handler と I/F を揃えるため構築するが、
        # iframe_rpc は thread_id を使わない (LangGraph checkpointer 非対応経路)。
        rpc_ctx = RPCContext.from_http(user_id=github_login, app_id=app_id, thread_id="")
        trace_id = correlation_id or rpc_ctx.correlation_id

        async with trace_span(
            "request",
            trace_id=trace_id,
            attributes={
                "user_id": github_login,
                "app_id": app_id,
                "thread_id": "",
                "handler": "iframe_rpc",
                "rpc_method": method,
            },
        ) as req_span:
            try:
                if method == "QUERY":
                    result = await self._handle_query(ctx, params, trace_id, github_login)
                elif method == "AI":
                    result = await self._handle_ai(job, params, trace_id, github_login)
                else:
                    result = {"result": False, "error": f"Unknown method: {method}"}
                    req_span.set_status("ERROR", f"unknown_method={method}"[:200])
                    req_span.set_attribute("success", False)

                await job_store.save_result(job_id, json.dumps(result, default=_json_default))
                await notifier.done()
            except Exception as e:  # pragma: no cover - defensive catch-all
                req_span.set_status("ERROR", str(e)[:200])
                req_span.set_attribute("success", False)
                await job_store.save_result(job_id, json.dumps({"result": False, "error": str(e)}))
                await notifier.done()

            return {"job_id": job_id, "status": "done"}

    async def _handle_query(self, ctx: dict, params: dict, trace_id: str = "", user_id: str = "unknown") -> dict:
        """Execute a SELECT-only SQL query via MCP db_query tool.

        SQL safety (SELECT-only guard, pool validation) is delegated to the
        MCP db_query tool (mcp_server/tools/db_query.py).

        Args:
            ctx:      arq worker context; must contain ctx["mcp_tools"] list.
            params:   {"pool_name": str, "sql": str, "user": str}
            trace_id: correlation_id carried from handle() (span trace_id)
            user_id:  github_login (span common attribute)

        Returns:
            {"result": true, "rows": [...]} on success
            {"result": false, "error": "..."} on any error
        """
        pool_name = params.get("pool_name", "")
        sql = params.get("sql", "")
        # Note: params.get("user") is no longer logged as free text; user_id
        # (github_login) is recorded as a span attribute instead (D-08 .. D-12).

        mcp_tools = ctx.get("mcp_tools") or []
        tool = next((t for t in mcp_tools if getattr(t, "name", None) == "db_query"), None)
        if tool is None:
            return {"result": False, "error": "db_query tool unavailable (MCP DEGRADED)"}

        args_json = json.dumps({"sql": sql, "pool_name": pool_name}, ensure_ascii=False)
        args_max = get_args_max_chars()
        result_max = get_result_max_chars()

        async with trace_span(
            "tool_call",
            trace_id=trace_id,
            attributes={
                "user_id": user_id,
                "app_id": "canvas",
                "thread_id": "",
                "agent_name": "iframe_rpc",
                "model_name": "",
                "tool_name": "db_query",
                "args_bytes": len(args_json.encode("utf-8")),
                "args_prefix": args_json[:args_max],
                # db_query has sandbox_exposed=true → not privileged (D-12)
                "privileged": False,
                # iframe_rpc-specific operational attribute — useful for per-pool
                # aggregation in Plan 06 recipes.
                "pool_name": pool_name,
            },
        ) as span:
            try:
                out = await tool.ainvoke({"sql": sql, "pool_name": pool_name})
            except Exception as e:
                span.set_status("ERROR", str(e)[:200])
                span.set_attribute("success", False)
                return {"result": False, "error": f"db_query invocation failed: {e}"}

            # langchain-mcp-adapters returns a list of content blocks:
            # [{"type": "text", "text": '{"rows":[...]}', "id": "..."}]
            if isinstance(out, list):
                text = next(
                    (item["text"] for item in out if isinstance(item, dict) and item.get("type") == "text"),
                    None,
                )
                if text is None:
                    span.set_status("ERROR", "empty_content_list")
                    span.set_attribute("success", False)
                    return {"result": False, "error": "db_query returned empty content list"}
                try:
                    out = json.loads(text)
                except json.JSONDecodeError:
                    span.set_status("ERROR", "unparseable_content")
                    span.set_attribute("success", False)
                    return {"result": False, "error": f"db_query returned unparseable content: {text!r}"}

            # Record result size / prefix after content-block normalisation.
            out_json = json.dumps(out, ensure_ascii=False, default=str)
            span.set_attribute("result_bytes", len(out_json.encode("utf-8")))
            span.set_attribute("result_prefix", out_json[:result_max])

            if not isinstance(out, dict):
                span.set_status("ERROR", f"unexpected_type={type(out).__name__}")
                span.set_attribute("success", False)
                return {"result": False, "error": f"db_query returned unexpected type: {type(out).__name__}"}
            if "error" in out:
                span.set_status("ERROR", str(out["error"])[:200])
                span.set_attribute("success", False)
                return {"result": False, "error": out["error"]}

            span.set_attribute("success", True)
            span.set_attribute("row_count", len(out.get("rows", [])))
            return {"result": True, "rows": out.get("rows", [])}

    async def _handle_ai(self, job: dict, params: dict, trace_id: str = "", user_id: str = "unknown") -> dict:
        """Invoke ChatCopilot for a one-shot AI response (D-14: no conversation history).

        Args:
            job:      arq job payload; must contain job["github_token"].
            params:   {"model": str, "prompt": str}
            trace_id: correlation_id carried from handle() (span trace_id)
            user_id:  github_login (span common attribute)

        Returns:
            {"result": true, "responseText": "..."} on success
            {"result": false, "error": "..."} on exception
        """
        raw_model = params.get("model")  # None と未指定は同一扱い(default=haiku)、
        # 空文字列 "" は明示的な無効値として拒否する
        prompt = params.get("prompt", "")
        github_token = job.get("github_token", "")

        try:
            model = resolve_model(raw_model)
        except ValueError as e:
            return {"result": False, "error": str(e)}

        args_json = json.dumps({"model": model, "prompt": prompt}, ensure_ascii=False)
        args_max = get_args_max_chars()
        result_max = get_result_max_chars()

        async with trace_span(
            "tool_call",
            trace_id=trace_id,
            attributes={
                "user_id": user_id,
                "app_id": "canvas",
                "thread_id": "",
                "agent_name": "iframe_rpc",
                "model_name": model,
                "tool_name": "ai",
                "args_bytes": len(args_json.encode("utf-8")),
                "args_prefix": args_json[:args_max],
                # AI (LLM one-shot) has no MCP catalog entry; treat as non-privileged
                # because it runs inside the same trust zone as db_query here.
                "privileged": False,
            },
        ) as span:
            llm = ChatCopilot(github_token=github_token, model=model)
            try:
                result = await llm.ainvoke([HumanMessage(content=prompt)])
                content = result.content
                content_str = str(content)
                span.set_attribute("result_bytes", len(content_str.encode("utf-8")))
                span.set_attribute("result_prefix", content_str[:result_max])
                span.set_attribute("success", True)
                return {"result": True, "responseText": content}
            except Exception as e:
                span.set_status("ERROR", str(e)[:200])
                span.set_attribute("success", False)
                return {"result": False, "error": str(e)}
            finally:
                await llm.close()
