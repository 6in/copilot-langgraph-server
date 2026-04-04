"""Tests for ScriptBackend: INPUT_SCHEMA validation before run() call."""
import sys
from pathlib import Path

import pytest

from app.orchestrator.script_backend import ScriptBackend


def _write_tool(tmp_path: Path, name: str, content: str) -> Path:
    """Write a tool script to tmp_path and return its path."""
    path = tmp_path / f"{name}.py"
    path.write_text(content)
    return path


# --- test_valid_input_passes ---


def test_valid_input_passes(tmp_path: Path) -> None:
    """ScriptBackend.call() with valid kwargs matching INPUT_SCHEMA returns result."""
    tool = _write_tool(
        tmp_path,
        "good_tool",
        """
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "x": {"type": "string"},
    },
    "required": ["x"],
    "additionalProperties": False,
}

def run(x: str) -> dict:
    return {"result": x}
""",
    )
    backend = ScriptBackend()
    result = backend.call(tool, {"x": "hello"})
    assert result == {"result": "hello"}


# --- test_invalid_input_raises_valueerror ---


def test_invalid_input_raises_valueerror(tmp_path: Path) -> None:
    """ScriptBackend.call() with wrong type raises ValueError containing 'validation failed'."""
    tool = _write_tool(
        tmp_path,
        "typed_tool",
        """
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "x": {"type": "string"},
    },
    "required": ["x"],
}

def run(x) -> dict:
    return {"result": x}
""",
    )
    backend = ScriptBackend()
    with pytest.raises(ValueError, match="validation failed"):
        backend.call(tool, {"x": 123})  # int instead of string


# --- test_extra_field_rejected ---


def test_extra_field_rejected(tmp_path: Path) -> None:
    """ScriptBackend.call() with additionalProperties=False and extra field raises ValueError."""
    tool = _write_tool(
        tmp_path,
        "strict_tool",
        """
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "x": {"type": "string"},
    },
    "required": ["x"],
    "additionalProperties": False,
}

def run(x: str, **kw) -> dict:
    return {"result": x}
""",
    )
    backend = ScriptBackend()
    with pytest.raises(ValueError, match="validation failed"):
        backend.call(tool, {"x": "hello", "extra": "bad"})


# --- test_no_schema_skips_validation ---


def test_no_schema_skips_validation(tmp_path: Path) -> None:
    """ScriptBackend.call() on a tool without INPUT_SCHEMA succeeds (permissive)."""
    tool = _write_tool(
        tmp_path,
        "legacy_tool",
        """
def run(**kw) -> dict:
    return dict(kw)
""",
    )
    backend = ScriptBackend()
    result = backend.call(tool, {"anything": "goes"})
    assert result == {"anything": "goes"}


# --- test_missing_run_raises ---


def test_missing_run_raises(tmp_path: Path) -> None:
    """ScriptBackend.call() on a script without run() raises AttributeError."""
    tool = _write_tool(
        tmp_path,
        "no_run_tool",
        """
INPUT_SCHEMA = {"type": "object"}

# run() is intentionally missing
""",
    )
    backend = ScriptBackend()
    with pytest.raises(AttributeError, match="no run\\(\\) function"):
        backend.call(tool, {})


# --- test_missing_required_field_raises ---


def test_missing_required_field_raises(tmp_path: Path) -> None:
    """ScriptBackend.call() with missing required field raises ValueError."""
    tool = _write_tool(
        tmp_path,
        "required_tool",
        """
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {"type": "string"},
    },
    "required": ["file_path"],
}

def run(file_path: str) -> dict:
    return {"path": file_path}
""",
    )
    backend = ScriptBackend()
    with pytest.raises(ValueError, match="validation failed"):
        backend.call(tool, {})  # missing file_path


# --- test_example_tool_with_valid_input ---


def test_example_tool_with_valid_input() -> None:
    """Integration: lint_file.py example tool works end-to-end via ScriptBackend."""
    tool_path = Path(__file__).parent.parent / "agents" / "code-reviewer" / "tools" / "lint_file.py"
    assert tool_path.exists(), f"Example tool not found at {tool_path}"
    backend = ScriptBackend()
    result = backend.call(tool_path, {"file_path": "example.py"})
    assert result["status"] == "clean"
    assert result["file_path"] == "example.py"


# --- test_example_tool_extra_field_rejected ---


def test_example_tool_extra_field_rejected() -> None:
    """Integration: lint_file.py rejects extra fields (additionalProperties=False)."""
    tool_path = Path(__file__).parent.parent / "agents" / "code-reviewer" / "tools" / "lint_file.py"
    backend = ScriptBackend()
    with pytest.raises(ValueError, match="validation failed"):
        backend.call(tool_path, {"file_path": "example.py", "unknown": "field"})
