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


def test_tool_registry_real_yaml_contract():
    """Phase 30: 実 config/mcp_tools.yaml を ToolRegistry が読み込めることを確認する。

    拡張スキーマ (python_wrapper / sandbox_exposed) は ToolRegistry から参照されないため、
    既存の name / privileged 契約のみを検証する。
    """
    from pathlib import Path

    real_yaml = Path(__file__).resolve().parent.parent / "config" / "mcp_tools.yaml"
    assert real_yaml.exists(), f"config/mcp_tools.yaml not found: {real_yaml}"

    registry = ToolRegistry(str(real_yaml))

    expected = {"ping", "web_search", "db_query", "claude_code", "execute_python", "get_current_datetime"}
    assert registry.expected_tool_names() == frozenset(expected)

    # ADR 0023/0024: privileged は claude_code と execute_python のみ
    assert registry.privileged_tool_names() == frozenset({"claude_code", "execute_python"})


def test_tool_registry_extended_schema_ignored(tmp_path):
    """Phase 30: python_wrapper / sandbox_exposed フィールドがあっても ToolRegistry は無視して壊れない。"""
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text(
        "tools:\n"
        "  - name: ping\n"
        "    sandbox_exposed: true\n"
        "    python_wrapper:\n"
        "      function_name: ping\n"
        "      args: []\n"
        "      return_type: dict\n"
        "  - name: claude_code\n"
        "    privileged: true\n"
        "    sandbox_exposed: false\n"
    )

    registry = ToolRegistry(str(yaml_file))
    assert registry.expected_tool_names() == frozenset({"ping", "claude_code"})
    assert registry.privileged_tool_names() == frozenset({"claude_code"})
