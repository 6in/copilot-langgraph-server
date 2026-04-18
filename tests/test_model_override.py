"""Tests for model_override propagation in SubAgentRegistry / SubAgent.from_dir.

Phase 29-01: SuperChat のユーザー選択モデルが AGENT.md のデフォルトモデルより優先されることを検証する。

Covered:
- Test 1: SubAgentRegistry(model_override="gpt-4o") → folder-type SubAgent の _llm.model が "gpt-4o"
- Test 2: SubAgentRegistry(model_override=None) → AGENT.md の model ("gpt-4.1") が使われる
- Test 3: SubAgentRegistry(model_override="") → 空文字は None 扱いで AGENT.md の model が使われる
- Test 4: ToolEnabledSubAgent に model_override が伝播される
- Test 5: CodeActSubAgent に model_override が伝播される
- Test 6: SubAgent.from_dir に model_override を渡すと AGENT.md の model より優先される
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.tools import tool


def write_agent_md(
    agent_dir: Path,
    *,
    model: str = "gpt-4.1",
    with_tools: bool = False,
    agent_type: str | None = None,
) -> None:
    """Write a minimal AGENT.md with optional tools / agent_type flags.

    Builds the frontmatter line-by-line (no textwrap.dedent) so optional
    ``tools:`` / ``agent_type:`` blocks do not break YAML indentation when
    absent or present.
    """
    agent_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "---",
        f"name: {agent_dir.name}",
        "keywords: []",
        "description: |",
        "  テスト用エージェント。",
        "  対象外: なし",
        f"model: {model}",
    ]
    if with_tools:
        lines += ["tools:", "  - ping", "  - web_search_stub"]
    if agent_type:
        lines.append(f"agent_type: {agent_type}")
    lines += ["---", "", "テスト用プロンプト。", ""]
    (agent_dir / "AGENT.md").write_text("\n".join(lines))


@pytest.fixture
def mock_copilot_cls():
    """Patch Copilot SDK internals so ChatCopilot can be instantiated without a real client."""
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


# ---------------------------------------------------------------------------
# Test 1: SubAgentRegistry に model_override を渡すと folder-type SubAgent に反映される
# ---------------------------------------------------------------------------
def test_registry_model_override_applies_to_subagent(tmp_path, mock_copilot_cls):
    """Test 1: model_override="gpt-4o" → folder-type SubAgent._llm.model == "gpt-4o"."""
    from app.orchestrator.agent import SubAgent, SubAgentRegistry

    write_agent_md(tmp_path / "folder-agent")  # AGENT.md model: gpt-4.1

    registry = SubAgentRegistry(str(tmp_path), "ghu_test", model_override="gpt-4o")

    assert "folder-agent" in registry.agents
    agent = registry.agents["folder-agent"]
    assert isinstance(agent, SubAgent)
    assert agent._llm.model == "gpt-4o", (
        f"Expected _llm.model='gpt-4o', got {agent._llm.model!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: model_override=None → AGENT.md の model がフォールバック
# ---------------------------------------------------------------------------
def test_registry_no_model_override_uses_agent_md(tmp_path, mock_copilot_cls):
    """Test 2: model_override=None → AGENT.md の model が使われる。"""
    from app.orchestrator.agent import SubAgent, SubAgentRegistry

    write_agent_md(tmp_path / "folder-agent", model="gpt-4.1")

    registry = SubAgentRegistry(str(tmp_path), "ghu_test", model_override=None)

    agent = registry.agents["folder-agent"]
    assert isinstance(agent, SubAgent)
    assert agent._llm.model == "gpt-4.1", (
        f"Expected AGENT.md fallback model='gpt-4.1', got {agent._llm.model!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: model_override="" → 空文字は None 扱い、AGENT.md の model がフォールバック
# ---------------------------------------------------------------------------
def test_registry_empty_string_model_override_falls_back(tmp_path, mock_copilot_cls):
    """Test 3: model_override="" → AGENT.md の model がフォールバック（空文字は falsy）。"""
    from app.orchestrator.agent import SubAgent, SubAgentRegistry

    write_agent_md(tmp_path / "folder-agent", model="gpt-4.1")

    registry = SubAgentRegistry(str(tmp_path), "ghu_test", model_override="")

    agent = registry.agents["folder-agent"]
    assert isinstance(agent, SubAgent)
    assert agent._llm.model == "gpt-4.1", (
        f"Empty-string model_override should fall back to AGENT.md model, got {agent._llm.model!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: ToolEnabledSubAgent に model_override が反映される
# ---------------------------------------------------------------------------
def test_registry_model_override_applies_to_tool_enabled_subagent(tmp_path, mock_copilot_cls):
    """Test 4: tools 付き AGENT.md + model_override → ToolEnabledSubAgent._llm.model が override 値。"""
    from app.orchestrator.agent import SubAgentRegistry
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    write_agent_md(tmp_path / "tool-agent", model="gpt-4.1", with_tools=True)
    mock_mcp_tools = make_mock_tools()

    registry = SubAgentRegistry(
        str(tmp_path),
        "ghu_test",
        mcp_tools=mock_mcp_tools,
        model_override="claude-sonnet-4-6",
    )

    agent = registry.agents["tool-agent"]
    assert isinstance(agent, ToolEnabledSubAgent)
    assert agent._llm.model == "claude-sonnet-4-6", (
        f"Expected ToolEnabledSubAgent._llm.model='claude-sonnet-4-6', got {agent._llm.model!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: CodeActSubAgent に model_override が反映される
# ---------------------------------------------------------------------------
def test_registry_model_override_applies_to_codeact_subagent(tmp_path, mock_copilot_cls):
    """Test 5: agent_type=codeact AGENT.md + model_override → CodeActSubAgent._llm.model が override 値。"""
    from app.orchestrator.agent import SubAgentRegistry
    from app.orchestrator.codeact_agent import CodeActSubAgent

    write_agent_md(
        tmp_path / "codeact-agent",
        model="gpt-4.1",
        with_tools=True,
        agent_type="codeact",
    )
    mock_mcp_tools = make_mock_tools()

    registry = SubAgentRegistry(
        str(tmp_path),
        "ghu_test",
        mcp_tools=mock_mcp_tools,
        model_override="claude-sonnet-4-6",
    )

    agent = registry.agents["codeact-agent"]
    assert isinstance(agent, CodeActSubAgent)
    assert agent._llm.model == "claude-sonnet-4-6", (
        f"Expected CodeActSubAgent._llm.model='claude-sonnet-4-6', got {agent._llm.model!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: SubAgent.from_dir に model_override を渡すと AGENT.md の model より優先される
# ---------------------------------------------------------------------------
def test_subagent_from_dir_respects_model_override(tmp_path, mock_copilot_cls):
    """Test 6: SubAgent.from_dir(model_override=...) は AGENT.md の model より優先される。"""
    from app.orchestrator.agent import SubAgent

    write_agent_md(tmp_path / "folder-agent", model="gpt-4.1")

    agent = SubAgent.from_dir(
        tmp_path / "folder-agent",
        github_token="ghu_test",
        model_override="gpt-4o",
    )

    assert isinstance(agent, SubAgent)
    assert agent._llm.model == "gpt-4o", (
        f"Expected from_dir(model_override='gpt-4o') to produce _llm.model='gpt-4o', "
        f"got {agent._llm.model!r}"
    )

    # Sanity: model_override=None に戻すと AGENT.md の値が使われる
    agent2 = SubAgent.from_dir(
        tmp_path / "folder-agent",
        github_token="ghu_test",
        model_override=None,
    )
    assert agent2._llm.model == "gpt-4.1"
