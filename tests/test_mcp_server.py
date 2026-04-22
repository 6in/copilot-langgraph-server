"""MCP server tests (MCP-01, MCP-02, SEARCH-01, SEARCH-02, DB-01, DB-02).

Uses FastMCP's in-process Client to exercise the server without HTTP.
Phase 22: web_search_stub replaced by real Tavily web_search tool.
Phase 23: db_query_stub replaced by real db_query tool.
Phase 23 Plan 02: claude_code_stub replaced by real claude_code tool.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# mcp_server/ is a top-level sibling project (D-01); add to sys.path so tests
# can import `server` and `tools.stubs` without installing the package.
_MCP_SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
if str(_MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER_DIR))

pytest.importorskip("fastmcp", reason="fastmcp not installed in root env; run `cd mcp_server && uv sync` or add to root dev deps")

from fastmcp import Client  # noqa: E402
from server import mcp  # noqa: E402  (imports register_tools side-effect)

# Phase 28: execute_python 追加 + get_current_datetime 漏れ修正
EXPECTED_TOOLS = {"ping", "web_search", "db_query", "claude_code", "execute_python", "get_current_datetime",
                  "attachments_list", "attachments_extract"}  # Phase 37


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
    """MCP-02: expected tool set is registered (Phase 23: db_query replaces db_query_stub)."""
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
    """MCP-02: tools expose their documented string parameters."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
    by_name = {t.name: t for t in tools}

    cases = {
        "web_search": "query",
        "db_query": "sql",
        "claude_code": "prompt",
        "execute_python": "code",
    }
    for tool_name, param_name in cases.items():
        tool = by_name[tool_name]
        schema = tool.inputSchema or {}
        props = schema.get("properties", {})
        assert param_name in props, f"{tool_name} missing param {param_name}: {props}"
        assert props[param_name].get("type") == "string"


@pytest.mark.asyncio
async def test_web_search_normal():
    """SEARCH-01: web_search が Tavily 検索結果を返す。"""
    pytest.importorskip("langchain_community", reason="langchain_community not installed in root env")
    mock_results = [
        {"url": "https://example.com/1", "content": "Result 1"},
        {"url": "https://example.com/2", "content": "Result 2"},
    ]
    with patch(
        "langchain_community.tools.tavily_search.TavilySearchResults",
    ) as MockTavily:
        MockTavily.return_value.invoke.return_value = mock_results
        async with Client(mcp) as client:
            result = await client.call_tool("web_search", {"query": "test query"})
    payload = result.data if hasattr(result, "data") else result.structured_content
    assert "results" in payload
    assert len(payload["results"]) == 2
    assert payload["results"][0]["url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_web_search_truncates_content():
    """SEARCH-02: 500 文字超の content が切り捨てられる（SEARCH-02 REVISED: Copilot SDK タイムアウト対策で 500 文字）。"""
    pytest.importorskip("langchain_community", reason="langchain_community not installed in root env")
    long_content = "x" * 2000
    mock_results = [{"url": "https://example.com", "content": long_content}]
    with patch(
        "langchain_community.tools.tavily_search.TavilySearchResults",
    ) as MockTavily:
        MockTavily.return_value.invoke.return_value = mock_results
        async with Client(mcp) as client:
            result = await client.call_tool("web_search", {"query": "test"})
    payload = result.data if hasattr(result, "data") else result.structured_content
    assert len(payload["results"][0]["content"]) == 500


@pytest.mark.asyncio
async def test_web_search_error_handling():
    """web_search エラー時に {"error": ...} を返す。"""
    pytest.importorskip("langchain_community", reason="langchain_community not installed in root env")
    with patch(
        "langchain_community.tools.tavily_search.TavilySearchResults",
    ) as MockTavily:
        MockTavily.return_value.invoke.side_effect = Exception("API key invalid")
        async with Client(mcp) as client:
            result = await client.call_tool("web_search", {"query": "test"})
    payload = result.data if hasattr(result, "data") else result.structured_content
    assert "error" in payload
    assert "web_search failed" in payload["error"]


# ─────────────────────────────────────────────
# Phase 23 DB-01 / DB-02: is_select_only ユニットテスト
# ─────────────────────────────────────────────

def test_is_select_only_select():
    """DB-02: SELECT 1 は許可される。"""
    from tools.db_query import is_select_only
    assert is_select_only("SELECT 1") is True


def test_is_select_only_with_cte():
    """DB-02: WITH ... SELECT は許可される。"""
    from tools.db_query import is_select_only
    assert is_select_only("WITH cte AS (SELECT 1) SELECT * FROM cte") is True


def test_is_select_only_insert_blocked():
    """DB-02: INSERT はブロックされる。"""
    from tools.db_query import is_select_only
    assert is_select_only("INSERT INTO t VALUES (1)") is False


def test_is_select_only_update_blocked():
    """DB-02: UPDATE はブロックされる。"""
    from tools.db_query import is_select_only
    assert is_select_only("UPDATE t SET x=1") is False


def test_is_select_only_delete_blocked():
    """DB-02: DELETE はブロックされる。"""
    from tools.db_query import is_select_only
    assert is_select_only("DELETE FROM t") is False


def test_is_select_only_multistatement_blocked():
    """DB-02: 複文（SELECT 1; DELETE FROM t）はブロックされる。"""
    from tools.db_query import is_select_only
    assert is_select_only("SELECT 1; DELETE FROM t") is False


def test_is_select_only_comment_stripped_line():
    """DB-02: ラインコメント付き SQL はコメントストリップ後に判定される。"""
    from tools.db_query import is_select_only
    assert is_select_only("-- DELETE\nSELECT 1") is True


def test_is_select_only_comment_stripped_block():
    """DB-02: ブロックコメント付き SQL はコメントストリップ後に判定される。"""
    from tools.db_query import is_select_only
    assert is_select_only("/* DELETE */ SELECT 1") is True


def test_is_select_only_empty_blocked():
    """DB-02: 空文字列はブロックされる。"""
    from tools.db_query import is_select_only
    assert is_select_only("") is False


# ─────────────────────────────────────────────
# Phase 23: db_query ツール ユニットテスト（pool 未初期化 / blocked cases）
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_db_query_blocks_insert():
    """DB-02: INSERT はブロックされ error が返る。"""
    async with Client(mcp) as client:
        result = await client.call_tool("db_query", {"sql": "INSERT INTO foo VALUES (1)"})
    payload = result.data if hasattr(result, "data") else result.structured_content
    assert payload == {"error": "Only SELECT queries are allowed"}


@pytest.mark.asyncio
async def test_db_query_blocks_delete():
    """DB-02: DELETE はブロックされ error が返る。"""
    async with Client(mcp) as client:
        result = await client.call_tool("db_query", {"sql": "DELETE FROM foo"})
    payload = result.data if hasattr(result, "data") else result.structured_content
    assert payload == {"error": "Only SELECT queries are allowed"}


@pytest.mark.asyncio
async def test_db_query_blocks_multistatement():
    """DB-02: 複文はブロックされ error が返る。"""
    async with Client(mcp) as client:
        result = await client.call_tool("db_query", {"sql": "SELECT 1; DELETE FROM foo"})
    payload = result.data if hasattr(result, "data") else result.structured_content
    assert payload == {"error": "Only SELECT queries are allowed"}


@pytest.mark.asyncio
async def test_db_query_unknown_pool():
    """DB-01: 未知のプール名を指定すると error が返る。"""
    async with Client(mcp) as client:
        result = await client.call_tool("db_query", {"sql": "SELECT 1", "pool_name": "nonexistent"})
    payload = result.data if hasattr(result, "data") else result.structured_content
    assert "error" in payload
    assert "Unknown pool" in payload["error"]


# ─────────────────────────────────────────────
# Phase 23: integration テスト（実 PostgreSQL 接続が必要）
# ─────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_db_query_select_returns_rows():
    """DB-01: SELECT 1 AS one が {"rows": [{"one": 1}]} を返す（実 PostgreSQL 接続）。"""
    from tools.db_query import init_pools, close_pools

    await init_pools("/app/config/db_pools.yaml")
    try:
        async with Client(mcp) as client:
            result = await client.call_tool("db_query", {"sql": "SELECT 1 AS one"})
        payload = result.data if hasattr(result, "data") else result.structured_content
        assert "rows" in payload, f"Expected rows, got: {payload}"
        assert payload["rows"] == [{"one": 1}]
    finally:
        await close_pools()


# ─────────────────────────────────────────────
# Phase 23 Plan 02: claude_code ツール ユニットテスト
# CODE-01, CODE-02, CODE-03, D-06
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_claude_code_env_sanitized():
    """CODE-02: CLAUDECODE=1 等の禁止 env が claude サブプロセスに渡らない。"""
    import os
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.claude_code import claude_code

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"hello", b""))
    mock_proc.returncode = 0

    with patch.dict(os.environ, {
        "CLAUDECODE": "1",
        "ANTHROPIC_API_KEY": "secret",
        "DATABASE_URL": "postgresql://localhost/db",
        "PATH": "/usr/bin",
        "HOME": "/root",
    }):
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await claude_code(prompt="test", cwd="/tmp")

    _args, kwargs = mock_exec.call_args
    env = kwargs.get("env", {})
    assert set(env.keys()).issubset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"}), \
        f"Unexpected env keys: {set(env.keys())}"
    assert "CLAUDECODE" not in env, "CLAUDECODE must not be passed to subprocess"
    assert "ANTHROPIC_API_KEY" not in env, "ANTHROPIC_API_KEY must not be passed to subprocess"
    assert "DATABASE_URL" not in env, "DATABASE_URL must not be passed to subprocess"


@pytest.mark.asyncio
async def test_claude_code_returns_output():
    """CODE-01: claude_code が正常出力を {"output": str, "exit_code": int, ...} 形式で返す。"""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.claude_code import claude_code

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"hello world", b""))
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await claude_code(prompt="test", cwd="/tmp")

    assert result == {
        "output": "hello world",
        "exit_code": 0,
        "truncated": False,
        "file_path": None,
    }


@pytest.mark.asyncio
async def test_claude_code_timeout_terminate():
    """CODE-03: communicate() が TimeoutError → proc.terminate() が呼ばれ proc.kill() は呼ばれない。"""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.claude_code import claude_code

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
    mock_proc.wait = AsyncMock(return_value=None)  # wait() 成功 → kill 不要
    mock_proc.terminate = MagicMock()
    mock_proc.kill = MagicMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await claude_code(prompt="test", cwd="/tmp")

    mock_proc.terminate.assert_called_once()
    mock_proc.kill.assert_not_called()
    assert "Timeout after 60s" in result.get("error", "")


@pytest.mark.asyncio
async def test_claude_code_timeout_kill_escalation():
    """CODE-03: communicate() も wait() も TimeoutError → proc.kill() が呼ばれ zombie 回収。"""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.claude_code import claude_code

    wait_call_count = 0

    async def wait_side_effect():
        nonlocal wait_call_count
        wait_call_count += 1
        if wait_call_count == 1:
            raise asyncio.TimeoutError()
        return None  # 2回目（kill後）は成功

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
    mock_proc.wait = AsyncMock(side_effect=wait_side_effect)
    mock_proc.terminate = MagicMock()
    mock_proc.kill = MagicMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await claude_code(prompt="test", cwd="/tmp")

    mock_proc.kill.assert_called_once()
    assert "Timeout after 60s" in result.get("error", "")
    assert result["exit_code"] == -1


@pytest.mark.asyncio
async def test_claude_code_truncation():
    """D-06: stdout が 4000 文字超のとき output が切り捨てられ file_path が返る。"""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.claude_code import claude_code

    long_output = "x" * 5000
    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(long_output.encode(), b""))
    mock_proc.returncode = 0

    fake_file_path = "/shared/claude-code-outputs/20260413_abcdef12.txt"
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("tools.claude_code._save_overflow_output", return_value=fake_file_path) as mock_save:
            result = await claude_code(prompt="test", cwd="/tmp")

    assert result["truncated"] is True
    assert len(result["output"]) == 4000
    assert result["file_path"] == fake_file_path
    mock_save.assert_called_once_with(long_output)


@pytest.mark.asyncio
async def test_claude_code_cli_missing():
    """CODE-01: claude CLI が見つからない場合に error が返る。"""
    from unittest.mock import patch

    from tools.claude_code import claude_code

    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("claude not found")):
        result = await claude_code(prompt="test", cwd="/tmp")

    assert "claude CLI not found in PATH" in result.get("error", "")
    assert result["exit_code"] == -1
    assert result["output"] == ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_claude_code_e2e_smoke():
    """CODE-01 e2e: claude_code ツールが構造化レスポンスを返す（claude CLI 無し環境はスキップ）。"""
    async with Client(mcp) as client:
        try:
            result = await client.call_tool("claude_code", {"prompt": "print('hello')", "cwd": "/tmp"})
        except Exception:
            pytest.skip("claude_code e2e failed — likely no claude CLI in container")

    payload = result.data if hasattr(result, "data") else result.structured_content
    assert isinstance(payload.get("exit_code"), int), f"exit_code must be int: {payload}"
    assert isinstance(payload.get("output"), str), f"output must be str: {payload}"


# ─────────────────────────────────────────────
# Phase 28: execute_python ツール ユニットテスト
# EXEC-01〜06
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_python_returns_stdout():
    """EXEC-01: execute_python が正常出力を返す。"""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.execute_python import execute_python, _load_allowlist

    # allowlist キャッシュをリセットして math を許可
    import tools.execute_python as ep_mod
    ep_mod._cached_allowlist = frozenset(["math", "json"])

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"hello\n", b""))
    mock_proc.returncode = 0

    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute_python(code="print('hello')")
    finally:
        ep_mod._cached_allowlist = None

    assert result["stdout"] == "hello\n"
    assert result["exit_code"] == 0
    assert result["truncated"] is False
    assert result["stderr"] == ""


@pytest.mark.asyncio
async def test_execute_python_env_sanitized():
    """EXEC-02: DATABASE_URL 等がサブプロセスに渡らない。"""
    import os
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.execute_python import execute_python
    import tools.execute_python as ep_mod
    ep_mod._cached_allowlist = frozenset()

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))
    mock_proc.returncode = 0

    try:
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://localhost/db",
            "SECRET_KEY": "secret123",
            "PATH": "/usr/bin",
            "HOME": "/root",
        }):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
                await execute_python(code="print('ok')")

        _args, kwargs = mock_exec.call_args
        env = kwargs.get("env", {})
        assert set(env.keys()).issubset({"PATH", "HOME", "LANG", "LC_ALL", "TERM", "PYTHONPATH"}), \
            f"Unexpected env keys: {set(env.keys())}"
        assert "DATABASE_URL" not in env
        assert "SECRET_KEY" not in env
    finally:
        ep_mod._cached_allowlist = None


@pytest.mark.asyncio
async def test_execute_python_timeout():
    """EXEC-03: タイムアウト時に error を返しプロセスを terminate する。"""
    import asyncio as _asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.execute_python import execute_python
    import tools.execute_python as ep_mod
    ep_mod._cached_allowlist = frozenset()

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(side_effect=_asyncio.TimeoutError())
    mock_proc.wait = AsyncMock(return_value=None)
    mock_proc.terminate = MagicMock()
    mock_proc.kill = MagicMock()

    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute_python(code="print('slow')", timeout=1)
    finally:
        ep_mod._cached_allowlist = None

    mock_proc.terminate.assert_called_once()
    assert "Timeout" in result.get("error", "")
    assert result["exit_code"] == -1


@pytest.mark.asyncio
async def test_execute_python_blocks_disallowed_import():
    """EXEC-04: ホワイトリスト外 import がブロックされる。"""
    from tools.execute_python import execute_python
    import tools.execute_python as ep_mod
    ep_mod._cached_allowlist = frozenset(["math", "json"])

    try:
        result = await execute_python(code="import subprocess\nprint('hi')")
    finally:
        ep_mod._cached_allowlist = None

    assert result["exit_code"] == 1
    assert "Blocked imports" in result.get("error", "")
    assert "subprocess" in result.get("error", "")


@pytest.mark.asyncio
async def test_execute_python_allows_whitelisted_import():
    """EXEC-05: 許可モジュールの import は通過する。"""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tools.execute_python import execute_python
    import tools.execute_python as ep_mod
    ep_mod._cached_allowlist = frozenset(["math", "json"])

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"3.14\n", b""))
    mock_proc.returncode = 0

    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute_python(code="import math\nprint(math.pi)")
    finally:
        ep_mod._cached_allowlist = None

    assert result["exit_code"] == 0
    assert result["stdout"] == "3.14\n"
    assert "error" not in result
