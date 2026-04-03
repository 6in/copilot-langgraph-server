"""Unit tests for SubAgent and SubAgentRegistry (src/agent.py)."""
from __future__ import annotations
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock
from agent import SubAgent, SubAgentRegistry


def test_subagent_from_dir_loads_metadata(tmp_agents_dir):
    """SubAgent.from_dir() loads name, description, model from AGENT.md frontmatter."""
    with patch("agent.ChatAnthropic"):
        agent = SubAgent.from_dir(tmp_agents_dir / "code-reviewer")
    assert agent.name == "code-reviewer"
    assert agent.description == "Code review agent"
    assert agent.description != ""


def test_subagent_from_dir_default_model(tmp_path):
    """SubAgent.from_dir() defaults model to 'claude-sonnet-4-6' when model field is missing."""
    agent_dir = tmp_path / "no-model-agent"
    agent_dir.mkdir()
    (agent_dir / "AGENT.md").write_text(
        textwrap.dedent("""\
            ---
            name: no-model-agent
            description: Agent without model field
            ---

            You have no model specified.
        """),
        encoding="utf-8",
    )
    with patch("agent.ChatAnthropic") as MockLLM:
        agent = SubAgent.from_dir(agent_dir)
        MockLLM.assert_called_once_with(model="claude-sonnet-4-6")
    assert agent.name == "no-model-agent"


def test_subagent_from_dir_loads_system_prompt(tmp_agents_dir):
    """SubAgent.from_dir() loads the AGENT.md body as the system prompt."""
    with patch("agent.ChatAnthropic"):
        agent = SubAgent.from_dir(tmp_agents_dir / "code-reviewer")
    assert isinstance(agent._system_prompt, str)
    assert len(agent._system_prompt.strip()) > 0


def test_registry_discovers_agents(tmp_agents_dir):
    """SubAgentRegistry discovers all AGENT.md files in the directory."""
    with patch("agent.ChatAnthropic"):
        registry = SubAgentRegistry(str(tmp_agents_dir))
    assert len(registry.all()) == 2


def test_registry_get_by_name(tmp_agents_dir):
    """SubAgentRegistry.get() returns the correct agent by name."""
    with patch("agent.ChatAnthropic"):
        registry = SubAgentRegistry(str(tmp_agents_dir))
    agent = registry.get("code-reviewer")
    assert agent.name == "code-reviewer"
