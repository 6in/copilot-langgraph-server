"""Tests for SubAgentRegistry tools-flag support.

Verifies that SubAgentRegistry creates ToolEnabledSubAgent when tools: is declared
in AGENT.md and mcp_tools are provided, and falls back to SubAgent otherwise.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.tools import tool


def write_agent_md(agent_dir: Path, *, with_tools: bool = True) -> None:
    """Write a minimal AGENT.md frontmatter file for testing."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    if with_tools:
        content = textwrap.dedent("""\
            ---
            name: test-agent
            keywords: []
            description: |
              テスト用エージェント。
              対象外: なし
            model: gpt-4.1
            tools:
              - ping
              - web_search_stub
            ---

            テスト用プロンプト。
        """)
    else:
        content = textwrap.dedent("""\
            ---
            name: normal-agent
            keywords: []
            description: |
              通常エージェント。
              対象外: なし
            model: gpt-4.1
            ---

            通常プロンプト。
        """)
    (agent_dir / "AGENT.md").write_text(content)


@pytest.fixture
def mock_copilot_cls():
    """Patch ChatCopilot so no Copilot SDK is instantiated."""
    with patch("app.providers.copilot.CopilotClient"), \
         patch("app.providers.copilot.SubprocessConfig"), \
         patch("app.providers.copilot.PermissionHandler"):
        yield


@tool
def ping(message: str) -> str:
    """A ping tool."""
    return f"pong: {message}"


@tool
def web_search_stub(query: str) -> str:
    """A web search stub tool."""
    return f"results for: {query}"


def make_mock_tools() -> list:
    """Return real @tool-decorated tools (ToolNode requires actual BaseTool instances)."""
    return [ping, web_search_stub]


def test_registry_creates_tool_enabled_agent(tmp_path, mock_copilot_cls):
    """SubAgentRegistry creates ToolEnabledSubAgent when tools: is set and mcp_tools provided."""
    from app.orchestrator.agent import SubAgentRegistry
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    write_agent_md(tmp_path / "test-agent", with_tools=True)
    mock_mcp_tools = make_mock_tools()

    registry = SubAgentRegistry(str(tmp_path), "ghu_test", mcp_tools=mock_mcp_tools)

    assert "test-agent" in registry.agents, f"Expected 'test-agent' in {list(registry.agents)}"
    agent = registry.agents["test-agent"]
    assert isinstance(agent, ToolEnabledSubAgent), (
        f"Expected ToolEnabledSubAgent, got {type(agent).__name__}"
    )


def test_registry_creates_normal_agent_without_tools(tmp_path, mock_copilot_cls):
    """SubAgentRegistry creates SubAgent (not ToolEnabledSubAgent) when tools: not in AGENT.md."""
    from app.orchestrator.agent import SubAgent, SubAgentRegistry
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    write_agent_md(tmp_path / "normal-agent", with_tools=False)

    registry = SubAgentRegistry(str(tmp_path), "ghu_test")

    assert "normal-agent" in registry.agents
    agent = registry.agents["normal-agent"]
    assert isinstance(agent, SubAgent), f"Expected SubAgent, got {type(agent).__name__}"
    assert not isinstance(agent, ToolEnabledSubAgent), "Should NOT be ToolEnabledSubAgent"


def test_registry_creates_normal_agent_when_no_mcp_tools(tmp_path, mock_copilot_cls):
    """SubAgentRegistry falls back to SubAgent when tools: is set but mcp_tools=None."""
    from app.orchestrator.agent import SubAgent, SubAgentRegistry
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    write_agent_md(tmp_path / "test-agent", with_tools=True)

    registry = SubAgentRegistry(str(tmp_path), "ghu_test", mcp_tools=None)

    assert "test-agent" in registry.agents
    agent = registry.agents["test-agent"]
    assert isinstance(agent, SubAgent), f"Expected SubAgent fallback, got {type(agent).__name__}"
    assert not isinstance(agent, ToolEnabledSubAgent), "Should NOT be ToolEnabledSubAgent"


def write_codeact_agent_md(agent_dir: Path) -> None:
    """Write a CodeAct AGENT.md with recursion_limit for testing."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent("""\
        ---
        name: codeact
        keywords:
          - コード実行
          - Python実行
        description: |
          CodeAct テストエージェント。
          対象外: なし
        model: gpt-4.1
        tools:
          - ping
        recursion_limit: 12
        ---

        テスト用 CodeAct プロンプト。
    """)
    (agent_dir / "AGENT.md").write_text(content)


def test_tool_enabled_agent_reads_recursion_limit(tmp_path, mock_copilot_cls):
    """EXEC-07: ToolEnabledSubAgent が AGENT.md の recursion_limit を読み込む。"""
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    write_codeact_agent_md(tmp_path / "codeact")
    mock_tools = make_mock_tools()

    agent = ToolEnabledSubAgent.from_dir(
        tmp_path / "codeact",
        github_token="ghu_test",
        tools=mock_tools,
    )

    assert agent.recursion_limit == 12, \
        f"Expected recursion_limit=12, got {agent.recursion_limit}"
    assert agent.name == "codeact"


def test_tool_enabled_agent_default_recursion_limit(tmp_path, mock_copilot_cls):
    """recursion_limit 未指定時はデフォルト値 25 を使用する。"""
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    write_agent_md(tmp_path / "test-agent", with_tools=True)
    mock_tools = make_mock_tools()

    agent = ToolEnabledSubAgent.from_dir(
        tmp_path / "test-agent",
        github_token="ghu_test",
        tools=mock_tools,
    )

    assert agent.recursion_limit == 25, \
        f"Expected default recursion_limit=25, got {agent.recursion_limit}"
