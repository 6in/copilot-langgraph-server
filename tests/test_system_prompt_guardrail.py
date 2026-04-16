"""Regression tests for the SubAgent security guardrail (#6).

Ensures:
1. build_system_prompt_prefix() always injects the FS / hallucination ban.
2. The guardrail mentions the key concepts so reviewers can grep for them.
3. SubAgentRegistry logs a SECURITY warning when an agent declares a
   privileged MCP tool (e.g. claude_code).
"""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import frontmatter
import pytest

from app.utils.system_prompt import SECURITY_GUARDRAIL, build_system_prompt_prefix
from app.orchestrator.agent import SubAgentRegistry


# ---------------------------------------------------------------------------
# build_system_prompt_prefix
# ---------------------------------------------------------------------------

def test_guardrail_contains_key_phrases() -> None:
    """The guardrail must mention FS access ban AND the anti-hallucination rule."""
    assert "ファイルシステム" in SECURITY_GUARDRAIL
    assert "推測" in SECURITY_GUARDRAIL or "幻覚" in SECURITY_GUARDRAIL
    assert "作話" in SECURITY_GUARDRAIL or "幻覚" in SECURITY_GUARDRAIL


def test_prefix_includes_guardrail_without_user_id() -> None:
    prefix = build_system_prompt_prefix(None)
    assert SECURITY_GUARDRAIL in prefix
    assert "現在時刻" in prefix
    assert "ログイン中のユーザー" not in prefix


def test_prefix_includes_guardrail_with_user_id() -> None:
    prefix = build_system_prompt_prefix("alice")
    assert SECURITY_GUARDRAIL in prefix
    assert "ログイン中のユーザー: alice" in prefix


# ---------------------------------------------------------------------------
# SubAgentRegistry privileged-tool warning
# ---------------------------------------------------------------------------

def _write_agent_md(agent_dir: Path, *, name: str, tools: list[str]) -> None:
    agent_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(
        content="You are a test agent.",
        name=name,
        description=f"Test agent.\n対象外: none",
        model="gpt-4.1",
        tools=tools,
    )
    (agent_dir / "AGENT.md").write_text(frontmatter.dumps(post))


def _make_registry(
    agent_base_dir: Path,
    mcp_tools: list,
    privileged: frozenset[str] | None = None,
) -> SubAgentRegistry:
    with patch("app.orchestrator.agent.ChatCopilot") as mock_cls:
        mock_cls.return_value = MagicMock()
        return SubAgentRegistry(
            str(agent_base_dir),
            github_token="ghu_test",
            mcp_tools=mcp_tools,
            privileged_tool_names=privileged or frozenset(),
        )


def _fake_tool(name: str):
    tool = MagicMock()
    tool.name = name
    return tool


def test_privileged_tool_declaration_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Agent declaring 'claude_code' triggers a SECURITY warning."""
    agent_dir = tmp_path / "risky-agent"
    _write_agent_md(agent_dir, name="risky-agent", tools=["claude_code", "ping"])

    mcp_tools = [_fake_tool("claude_code"), _fake_tool("ping")]
    with caplog.at_level(logging.WARNING, logger="app.orchestrator.agent"):
        _make_registry(tmp_path, mcp_tools, privileged=frozenset({"claude_code"}))

    msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        "SECURITY" in m and "risky-agent" in m and "claude_code" in m for m in msgs
    ), f"Expected SECURITY warning listing claude_code; got: {msgs}"


def test_non_privileged_tool_does_not_warn(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Agent declaring only non-privileged tools does not trigger the SECURITY warning."""
    agent_dir = tmp_path / "safe-agent"
    _write_agent_md(agent_dir, name="safe-agent", tools=["ping", "web_search"])

    mcp_tools = [_fake_tool("ping"), _fake_tool("web_search"), _fake_tool("claude_code")]
    with caplog.at_level(logging.WARNING, logger="app.orchestrator.agent"):
        _make_registry(tmp_path, mcp_tools, privileged=frozenset({"claude_code"}))

    security_msgs = [
        r.message
        for r in caplog.records
        if r.levelno == logging.WARNING and "SECURITY" in r.message
    ]
    assert security_msgs == [], f"Unexpected SECURITY warnings: {security_msgs}"


# ---------------------------------------------------------------------------
# ToolRegistry privileged set loading
# ---------------------------------------------------------------------------

def test_tool_registry_loads_privileged_names(tmp_path: Path) -> None:
    """ToolRegistry exposes privileged_tool_names() from YAML."""
    from app.orchestrator.tool_registry import ToolRegistry

    yaml_path = tmp_path / "mcp_tools.yaml"
    yaml_path.write_text(
        "tools:\n"
        "  - name: ping\n"
        "    description: hc\n"
        "  - name: claude_code\n"
        "    description: cli\n"
        "    privileged: true\n"
    )
    registry = ToolRegistry(str(yaml_path))
    assert registry.privileged_tool_names() == frozenset({"claude_code"})
    assert registry.expected_tool_names() == frozenset({"ping", "claude_code"})
