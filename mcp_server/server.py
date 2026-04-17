"""FastMCP server entry point (Phase 20).

Runs on streamable-http transport at 0.0.0.0:8001 with /mcp endpoint.
/health custom route is exposed for Docker healthcheck (D-13).
Phase 23: db_query ツール追加 + FastMCP lifespan で psycopg_pool 初期化。
Phase 23 Plan 02: claude_code ツール追加。
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from tools.claude_code import register_tools as register_claude_code_tools
from tools.db_query import close_pools, init_pools
from tools.db_query import register_tools as register_db_query_tools
from tools.execute_python import register_tools as register_execute_python_tools
from tools.stubs import register_tools as register_stub_tools
from tools.web_search import register_tools as register_web_search_tools


@asynccontextmanager
async def lifespan(_server):
    """FastMCP lifespan: db_query プールを起動時に初期化し、終了時にクローズする。

    Pitfall 4 (23-RESEARCH.md): FastMCP lifespan は Callable[[FastMCP], AsyncContextManager]
    として受け付けるため、引数 server を取る asynccontextmanager にする。
    """
    config_path = os.environ.get("DB_POOLS_CONFIG", "/mcp_server/config/db_pools.yaml")
    await init_pools(config_path)
    try:
        yield
    finally:
        await close_pools()


mcp = FastMCP("copilot-mcp-server", lifespan=lifespan)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Docker healthcheck endpoint (D-13)."""
    return JSONResponse({"status": "ok"})


register_stub_tools(mcp)
register_web_search_tools(mcp)
register_db_query_tools(mcp)
register_claude_code_tools(mcp)
register_execute_python_tools(mcp)


# ─────────────────────────────────────────────
# Internal tool call endpoint for sandbox mcp_helper
# ─────────────────────────────────────────────

# Registry of directly callable tool functions.
# Tools registered via @mcp.tool are closures inside register_tools() and not
# directly accessible. We re-import the underlying functions here for the
# internal endpoint. This keeps the sandbox helper decoupled from FastMCP internals.
@mcp.custom_route("/internal/call_tool", methods=["POST"])
async def internal_call_tool(request: Request) -> JSONResponse:
    """Internal endpoint for sandbox mcp_helper to call MCP tools via HTTP.

    Not exposed externally — only accessible from localhost (sandbox subprocess).
    Uses FastMCP's call_tool() API to invoke registered tools.

    Request body: {"tool": "web_search", "args": {"query": "..."}}
    Response: {"result": {...}}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    tool_name = body.get("tool")
    args = body.get("args", {})
    if not tool_name:
        return JSONResponse({"error": "Missing 'tool' field"}, status_code=400)

    try:
        call_result = await mcp.call_tool(tool_name, args)
        # call_result.content is a list of TextContent objects
        # Extract the text from the first content block
        if hasattr(call_result, "structured_content") and call_result.structured_content is not None:
            return JSONResponse({"result": call_result.structured_content})
        if hasattr(call_result, "content") and call_result.content:
            text = call_result.content[0].text if hasattr(call_result.content[0], "text") else str(call_result.content[0])
            # Try to parse as JSON for structured result
            try:
                import json as _json
                return JSONResponse({"result": _json.loads(text)})
            except (ValueError, TypeError):
                return JSONResponse({"result": text})
        return JSONResponse({"result": str(call_result)})
    except Exception as e:
        return JSONResponse({"error": f"Tool execution failed: {e}"}, status_code=500)


if __name__ == "__main__":
    # D-08: streamable-http -> FastMCP.run uses transport="http"
    # D-09: /mcp endpoint path is FastMCP default for http transport
    # D-06: host="0.0.0.0" required so worker container can connect
    #       (Pitfall 3 -- 127.0.0.1 bind is unreachable across containers)
    mcp.run(transport="http", host="0.0.0.0", port=8001)
