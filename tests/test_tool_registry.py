"""Phase 24: ToolRegistry ユニットテスト (MCP-03)。"""
from __future__ import annotations

import pytest
from langchain_core.tools import tool

from app.orchestrator.tool_registry import ToolRegistry


@tool
def ping(message: str = "") -> str:
    """Ping tool."""
    return "pong"


@tool
def web_search(query: str) -> str:
    """Web search tool."""
    return ""


def test_tool_registry_expected_names(tmp_path):
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text("tools:\n  - name: ping\n  - name: web_search\n")

    registry = ToolRegistry(str(yaml_file))
    assert registry.expected_tool_names() == frozenset({"ping", "web_search"})


def test_tool_registry_empty_yaml_section(tmp_path):
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text("# no tools key\n")

    registry = ToolRegistry(str(yaml_file))
    assert registry.expected_tool_names() == frozenset()


@pytest.mark.asyncio
async def test_tool_registry_validate_pass(tmp_path):
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text("tools:\n  - name: ping\n")

    registry = ToolRegistry(str(yaml_file))
    await registry.validate([ping])  # must not raise


@pytest.mark.asyncio
async def test_tool_registry_validate_fail_missing(tmp_path):
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text("tools:\n  - name: ping\n  - name: web_search\n")

    registry = ToolRegistry(str(yaml_file))
    with pytest.raises(RuntimeError, match="web_search"):
        await registry.validate([ping])  # web_search missing from MCP


@pytest.mark.asyncio
async def test_tool_registry_validate_fail_extra(tmp_path):
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text("tools:\n  - name: ping\n")

    registry = ToolRegistry(str(yaml_file))
    with pytest.raises(RuntimeError, match="MCP のみ"):
        await registry.validate([ping, web_search])  # web_search extra


@pytest.mark.asyncio
async def test_tool_registry_file_not_found(tmp_path):
    missing_path = tmp_path / "nonexistent.yaml"
    with pytest.raises((FileNotFoundError, RuntimeError)):
        ToolRegistry(str(missing_path))
