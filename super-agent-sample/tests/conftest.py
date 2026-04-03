"""Shared pytest fixtures for super-agent-sample unit tests."""
from __future__ import annotations
import textwrap
import pytest


@pytest.fixture
def tmp_agents_dir(tmp_path):
    """Create a temporary agents/ directory with code-reviewer and sql-analyst AGENT.md files."""
    # code-reviewer
    code_reviewer_dir = tmp_path / "code-reviewer"
    code_reviewer_dir.mkdir()
    (code_reviewer_dir / "AGENT.md").write_text(
        textwrap.dedent("""\
            ---
            name: code-reviewer
            description: Code review agent
            model: claude-opus-4-6
            ---

            You are a code reviewer.
        """),
        encoding="utf-8",
    )

    # sql-analyst
    sql_analyst_dir = tmp_path / "sql-analyst"
    sql_analyst_dir.mkdir()
    (sql_analyst_dir / "AGENT.md").write_text(
        textwrap.dedent("""\
            ---
            name: sql-analyst
            description: SQL analysis agent
            model: claude-sonnet-4-6
            ---

            You are a SQL analyst.
        """),
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def tmp_menus_dir(tmp_path):
    """Create a temporary menus/ directory with super-chat.yaml and simple-chat.yaml."""
    (tmp_path / "super-chat.yaml").write_text(
        "name: super-chat\nlabel: Super Chat\ngraph: orchestrator\nenabled: true\n",
        encoding="utf-8",
    )
    (tmp_path / "simple-chat.yaml").write_text(
        "name: simple-chat\nlabel: Simple Chat\ngraph: simple\nenabled: true\n",
        encoding="utf-8",
    )
    return tmp_path
