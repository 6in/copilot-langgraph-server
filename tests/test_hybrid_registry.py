# tests/test_hybrid_registry.py
"""Unit tests for hybrid SubAgentRegistry with per-agent health tracking.

Tests cover:
- Folder-type agent loading (AGENT.md only)
- Code-type agent loading (agent.py takes precedence)
- FAILED isolation (ImportError in agent.py)
- DEGRADED isolation (ConnectionError in agent.py)
- Health dict population
- registry.all() returns only HEALTHY agents
- Empty directory edge case
"""
import sys
import textwrap
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import frontmatter
import pytest

# ---------------------------------------------------------------------------
# Stub out the github-copilot-sdk (not installed in unit-test environment)
# ---------------------------------------------------------------------------
_copilot_stub = ModuleType("copilot")
_copilot_stub.CopilotClient = MagicMock  # type: ignore[attr-defined]
_copilot_stub.SubprocessConfig = MagicMock  # type: ignore[attr-defined]
_copilot_stub.PermissionHandler = MagicMock  # type: ignore[attr-defined]
sys.modules.setdefault("copilot", _copilot_stub)

from app.orchestrator.agent import (  # noqa: E402  (import after stub)
    AgentHealth,
    AgentStatusEnum,
    SubAgentRegistry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_agent_md(agent_dir: Path, name: str, description: str = "A test agent", model: str = "gpt-4.1") -> None:
    """Write a minimal AGENT.md with required frontmatter into agent_dir."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(
        content="You are a test agent.",
        **{"name": name, "description": description, "model": model},
    )
    (agent_dir / "AGENT.md").write_text(frontmatter.dumps(post))


def _make_registry(agent_base_dir: Path) -> SubAgentRegistry:
    """Create a SubAgentRegistry with mocked ChatCopilot."""
    with patch("app.orchestrator.agent.ChatCopilot") as mock_cls:
        mock_cls.return_value = MagicMock()
        registry = SubAgentRegistry(str(agent_base_dir), github_token="ghu_test")
    return registry


# ---------------------------------------------------------------------------
# Test: folder-type agent loading
# ---------------------------------------------------------------------------

def test_folder_type_agent_loads(tmp_path: Path) -> None:
    """Folder-type agent (AGENT.md only, no agent.py) loads as HEALTHY.

    registry.all() must include it with correct name and description.
    """
    agent_dir = tmp_path / "test-agent"
    _write_agent_md(agent_dir, name="test-agent", description="A folder-type test agent")

    registry = _make_registry(tmp_path)

    assert "test-agent" in registry.agents
    agent = registry.agents["test-agent"]
    assert agent.name == "test-agent"
    assert agent.description == "A folder-type test agent"

    assert "test-agent" in registry.health
    health = registry.health["test-agent"]
    assert health.status == AgentStatusEnum.HEALTHY
    assert health.agent_type == "folder"
    assert health.error is None

    assert any(a.name == "test-agent" for a in registry.all())


# ---------------------------------------------------------------------------
# Test: code-type agent takes precedence
# ---------------------------------------------------------------------------

def test_code_type_takes_precedence(tmp_path: Path) -> None:
    """Code-type agent (AGENT.md + agent.py) is loaded via agent.py.

    Health entry shows agent_type='code'.
    """
    agent_dir = tmp_path / "code-agent"
    _write_agent_md(agent_dir, name="code-agent", description="A code-type agent")

    # Write a minimal agent.py that exposes a SubAgent class
    agent_py_content = textwrap.dedent("""\
        from unittest.mock import MagicMock

        class SubAgent:
            def __init__(self, name, description, model, system_prompt, github_token):
                self.name = name
                self.description = description
                self._llm = MagicMock()
                self._system_prompt = system_prompt

            @classmethod
            def from_dir(cls, agent_dir, github_token):
                return cls(
                    name="code-agent",
                    description="Loaded from agent.py",
                    model="gpt-4.1",
                    system_prompt="You are code-agent.",
                    github_token=github_token,
                )

            async def run(self, state):
                return {"output": "ok", "messages": []}

            async def close(self):
                pass
    """)
    (agent_dir / "agent.py").write_text(agent_py_content)

    registry = _make_registry(tmp_path)

    assert "code-agent" in registry.agents
    assert registry.agents["code-agent"].name == "code-agent"

    health = registry.health["code-agent"]
    assert health.status == AgentStatusEnum.HEALTHY
    assert health.agent_type == "code"


# ---------------------------------------------------------------------------
# Test: FAILED agent is isolated (ImportError)
# ---------------------------------------------------------------------------

def test_failed_agent_isolated(tmp_path: Path) -> None:
    """An agent.py that raises ImportError is recorded as FAILED.

    Other healthy agents remain HEALTHY and appear in registry.all().
    """
    # Good agent (folder-type)
    good_dir = tmp_path / "good-agent"
    _write_agent_md(good_dir, name="good-agent")

    # Broken agent (code-type that raises ImportError)
    broken_dir = tmp_path / "broken-agent"
    _write_agent_md(broken_dir, name="broken-agent")
    (broken_dir / "agent.py").write_text("raise ImportError('missing-dep')\n")

    registry = _make_registry(tmp_path)

    assert "good-agent" in registry.agents
    assert registry.health["good-agent"].status == AgentStatusEnum.HEALTHY

    # broken-agent should be recorded as FAILED but NOT in agents dict
    assert "broken-agent" not in registry.agents
    assert "broken-agent" in registry.health
    assert registry.health["broken-agent"].status == AgentStatusEnum.FAILED
    assert "missing-dep" in registry.health["broken-agent"].error

    # Only the good agent is in all()
    all_names = [a.name for a in registry.all()]
    assert "good-agent" in all_names
    assert "broken-agent" not in all_names


# ---------------------------------------------------------------------------
# Test: DEGRADED agent is isolated (ConnectionError)
# ---------------------------------------------------------------------------

def test_degraded_agent_isolated(tmp_path: Path) -> None:
    """An agent.py that raises ConnectionError is recorded as DEGRADED.

    registry.all() excludes DEGRADED agents.
    registry.health[name].status == AgentStatusEnum.DEGRADED.
    """
    degraded_dir = tmp_path / "degraded-agent"
    _write_agent_md(degraded_dir, name="degraded-agent")
    (degraded_dir / "agent.py").write_text(
        "raise ConnectionError('copilot api unreachable')\n"
    )

    registry = _make_registry(tmp_path)

    assert "degraded-agent" not in registry.agents
    assert "degraded-agent" in registry.health
    health = registry.health["degraded-agent"]
    assert health.status == AgentStatusEnum.DEGRADED
    assert "copilot api unreachable" in health.error

    assert not any(a.name == "degraded-agent" for a in registry.all())


# ---------------------------------------------------------------------------
# Test: health dict populated for all agents
# ---------------------------------------------------------------------------

def test_health_dict_populated(tmp_path: Path) -> None:
    """After loading 3 agents (healthy/failed/degraded), health has 3 entries."""
    # Healthy folder-type
    healthy_dir = tmp_path / "healthy-agent"
    _write_agent_md(healthy_dir, name="healthy-agent")

    # FAILED (ImportError)
    failed_dir = tmp_path / "failed-agent"
    _write_agent_md(failed_dir, name="failed-agent")
    (failed_dir / "agent.py").write_text("raise ImportError('bad module')\n")

    # DEGRADED (ConnectionError)
    degraded_dir = tmp_path / "degraded-agent"
    _write_agent_md(degraded_dir, name="degraded-agent")
    (degraded_dir / "agent.py").write_text("raise ConnectionError('no server')\n")

    registry = _make_registry(tmp_path)

    assert len(registry.health) == 3

    assert registry.health["healthy-agent"].status == AgentStatusEnum.HEALTHY
    assert registry.health["healthy-agent"].error is None

    assert registry.health["failed-agent"].status == AgentStatusEnum.FAILED
    assert registry.health["failed-agent"].error is not None

    assert registry.health["degraded-agent"].status == AgentStatusEnum.DEGRADED
    assert registry.health["degraded-agent"].error is not None


# ---------------------------------------------------------------------------
# Test: registry.all() returns only HEALTHY; get() raises for failed agents
# ---------------------------------------------------------------------------

def test_all_returns_only_healthy(tmp_path: Path) -> None:
    """registry.all() excludes FAILED and DEGRADED agents.

    registry.get() for a failed agent raises KeyError.
    """
    good_dir = tmp_path / "good-agent"
    _write_agent_md(good_dir, name="good-agent")

    failed_dir = tmp_path / "failed-agent"
    _write_agent_md(failed_dir, name="failed-agent")
    (failed_dir / "agent.py").write_text("raise ImportError('boom')\n")

    degraded_dir = tmp_path / "degraded-agent"
    _write_agent_md(degraded_dir, name="degraded-agent")
    (degraded_dir / "agent.py").write_text("raise ConnectionError('timeout')\n")

    registry = _make_registry(tmp_path)

    healthy_names = [a.name for a in registry.all()]
    assert healthy_names == ["good-agent"]

    with pytest.raises(KeyError):
        registry.get("failed-agent")

    with pytest.raises(KeyError):
        registry.get("degraded-agent")


# ---------------------------------------------------------------------------
# Test: empty directory produces no crash
# ---------------------------------------------------------------------------

def test_empty_dir_no_crash(tmp_path: Path) -> None:
    """SubAgentRegistry with an empty directory produces empty dicts, no exception."""
    registry = _make_registry(tmp_path)

    assert registry.agents == {}
    assert registry.health == {}
    assert registry.all() == []
