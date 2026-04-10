"""Phase 20 MCP server tests (MCP-01, MCP-02).

Uses FastMCP's in-process Client to exercise the server without HTTP.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# mcp_server/ is a top-level sibling project (D-01); add to sys.path so tests
# can import `server` and `tools.stubs` without installing the package.
_MCP_SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
if str(_MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER_DIR))

pytest.importorskip("fastmcp", reason="fastmcp not installed in root env; run `cd mcp_server && uv sync` or add to root dev deps")

from fastmcp import Client  # noqa: E402
from server import mcp  # noqa: E402  (imports register_tools side-effect)

EXPECTED_TOOLS = {"ping", "web_search_stub", "db_query_stub", "claude_code_stub"}


@pytest.mark.asyncio
async def test_health_endpoint():
    """MCP-01: /health returns 200 with {"status": "ok"}."""
    # FastMCP custom routes are served by the ASGI app. Use the HTTP app
    # directly via httpx.AsyncClient with ASGITransport.
    import httpx

    app = mcp.http_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_stub_tools_registered():
    """MCP-02: all 4 Phase 20 stubs are registered with @mcp.tool."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS, f"unexpected tool set: {names}"


@pytest.mark.asyncio
async def test_ping_tool():
    """MCP-02: ping returns {status: ok, timestamp: <iso>}."""
    import datetime as _dt

    async with Client(mcp) as client:
        result = await client.call_tool("ping", {})

    # FastMCP 3.x Client.call_tool returns CallToolResult with .data dict
    payload = getattr(result, "data", None)
    if payload is None:
        payload = getattr(result, "structured_content", None)
    assert isinstance(payload, dict), f"ping returned non-dict: {payload!r}"
    assert payload.get("status") == "ok"
    ts = payload.get("timestamp")
    assert isinstance(ts, str) and ts, "ping timestamp missing"
    # must parse as ISO 8601
    _dt.datetime.fromisoformat(ts)


@pytest.mark.asyncio
async def test_stub_schemas_have_required_params():
    """MCP-02: stub tools expose their documented string parameters."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
    by_name = {t.name: t for t in tools}

    cases = {
        "web_search_stub": "query",
        "db_query_stub": "sql",
        "claude_code_stub": "command",
    }
    for tool_name, param_name in cases.items():
        tool = by_name[tool_name]
        schema = tool.inputSchema or {}
        props = schema.get("properties", {})
        assert param_name in props, f"{tool_name} missing param {param_name}: {props}"
        assert props[param_name].get("type") == "string"
