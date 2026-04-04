"""Tests for scripts/lint_tools.py: INPUT_SCHEMA enforcement CI script."""
import sys
from pathlib import Path

import pytest

# Import lint_tools function directly from scripts directory
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lint_tools import lint_tools  # noqa: E402


def _make_tool(agents_path: Path, agent: str, name: str, content: str) -> Path:
    """Create a tool script under agents_path/<agent>/tools/<name>.py."""
    tools_dir = agents_path / agent / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    path = tools_dir / f"{name}.py"
    path.write_text(content)
    return path


# --- test_lint_all_good ---


def test_lint_all_good(tmp_path: Path) -> None:
    """lint_tools() with all tools having INPUT_SCHEMA returns empty error list."""
    _make_tool(
        tmp_path,
        "agent1",
        "good",
        """
INPUT_SCHEMA = {"type": "object"}

def run(**kw):
    return kw
""",
    )
    errors = lint_tools(str(tmp_path))
    assert errors == []


# --- test_lint_missing_schema ---


def test_lint_missing_schema(tmp_path: Path) -> None:
    """lint_tools() with a tool missing INPUT_SCHEMA returns non-empty error list."""
    _make_tool(
        tmp_path,
        "agent1",
        "bad",
        """
def run(**kw):
    return kw
""",
    )
    errors = lint_tools(str(tmp_path))
    assert len(errors) == 1
    assert "missing INPUT_SCHEMA" in errors[0]
    assert "bad.py" in errors[0]


# --- test_lint_excludes_init ---


def test_lint_excludes_init(tmp_path: Path) -> None:
    """lint_tools() ignores __init__.py (and other _-prefixed files) in tools/."""
    tools_dir = tmp_path / "agent1" / "tools"
    tools_dir.mkdir(parents=True)
    # Create __init__.py without INPUT_SCHEMA — should be ignored
    (tools_dir / "__init__.py").write_text("# empty init\n")
    # Also create _private.py without INPUT_SCHEMA — should also be ignored
    (tools_dir / "_private.py").write_text("def helper(): pass\n")

    errors = lint_tools(str(tmp_path))
    assert errors == [], f"Expected no errors but got: {errors}"


# --- test_lint_nonexistent_dir ---


def test_lint_nonexistent_dir() -> None:
    """lint_tools('nonexistent') returns empty list without crashing."""
    errors = lint_tools("nonexistent_path_that_does_not_exist")
    assert errors == []


# --- test_lint_multiple_agents ---


def test_lint_multiple_agents(tmp_path: Path) -> None:
    """lint_tools() checks all agents, reports missing schemas across multiple agents."""
    # agent1 has INPUT_SCHEMA
    _make_tool(
        tmp_path,
        "agent1",
        "good",
        "INPUT_SCHEMA = {'type': 'object'}\ndef run(**kw): return kw\n",
    )
    # agent2 is missing INPUT_SCHEMA
    _make_tool(
        tmp_path,
        "agent2",
        "missing",
        "def run(**kw): return kw\n",
    )
    errors = lint_tools(str(tmp_path))
    assert len(errors) == 1
    assert "agent2" in errors[0]
    assert "missing INPUT_SCHEMA" in errors[0]


# --- test_lint_real_agents_dir ---


def test_lint_real_agents_dir() -> None:
    """Integration: lint_tools() on actual agents/ dir passes (all tools have INPUT_SCHEMA)."""
    agents_dir = Path(__file__).parent.parent / "agents"
    if not agents_dir.exists():
        pytest.skip("No agents/ directory in repo")
    errors = lint_tools(str(agents_dir))
    assert errors == [], f"Tool scripts missing INPUT_SCHEMA: {errors}"
