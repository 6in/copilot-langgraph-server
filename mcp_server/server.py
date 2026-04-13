"""FastMCP server entry point (Phase 20).

Runs on streamable-http transport at 0.0.0.0:8001 with /mcp endpoint.
/health custom route is exposed for Docker healthcheck (D-13).
"""
from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from tools.stubs import register_tools as register_stub_tools
from tools.web_search import register_tools as register_web_search_tools

mcp = FastMCP("copilot-mcp-server")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Docker healthcheck endpoint (D-13)."""
    return JSONResponse({"status": "ok"})


register_stub_tools(mcp)
register_web_search_tools(mcp)


if __name__ == "__main__":
    # D-08: streamable-http -> FastMCP.run uses transport="http"
    # D-09: /mcp endpoint path is FastMCP default for http transport
    # D-06: host="0.0.0.0" required so worker container can connect
    #       (Pitfall 3 -- 127.0.0.1 bind is unreachable across containers)
    mcp.run(transport="http", host="0.0.0.0", port=8001)
