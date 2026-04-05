"""Unit tests for AppRegistry — APP-01, APP-04, T-14-05.

Tests run with: uv run pytest tests/test_app_registry.py -x -q
"""
import logging
from pathlib import Path

import pytest

from app.orchestrator.apps import AppDefinition, AppRegistry


def _write_app_md(directory: Path, content: str) -> Path:
    """Helper to write an APP.md file in the given directory."""
    directory.mkdir(parents=True, exist_ok=True)
    md_path = directory / "APP.md"
    md_path.write_text(content, encoding="utf-8")
    return md_path


# ---------------------------------------------------------------------------
# Test 1: Happy path — 2 APP.md files scanned, correct AppDefinition returned
# ---------------------------------------------------------------------------

def test_registry_scans_two_apps(tmp_path):
    """AppRegistry returns 2 AppDefinition objects with correct fields."""
    _write_app_md(
        tmp_path / "chat",
        "---\nname: Chat\ndescription: AI chat\nicon: \U0001f4ac\nagents:\n  - general-assistant\n---\n",
    )
    _write_app_md(
        tmp_path / "superchat",
        "---\nname: SuperChat\ndescription: Multi-agent\nicon: \u26a1\nagents:\n  - code-reviewer\n  - sql-analyst\n---\n",
    )

    registry = AppRegistry(str(tmp_path))
    apps = registry.all()

    assert len(apps) == 2
    slugs = {a.slug for a in apps}
    assert slugs == {"chat", "superchat"}

    chat = registry.get("chat")
    assert chat is not None
    assert chat.name == "Chat"
    assert chat.description == "AI chat"
    assert chat.icon == "\U0001f4ac"
    assert chat.agents == ["general-assistant"]

    superchat = registry.get("superchat")
    assert superchat is not None
    assert superchat.name == "SuperChat"
    assert "code-reviewer" in superchat.agents
    assert "sql-analyst" in superchat.agents


# ---------------------------------------------------------------------------
# Test 2: APP.md references non-existent agent — warns but does not crash
# ---------------------------------------------------------------------------

def test_registry_nonexistent_agent_logs_warning(tmp_path, caplog):
    """APP.md referencing a missing agent folder logs warning, still creates AppDefinition."""
    _write_app_md(
        tmp_path / "chat",
        "---\nname: Chat\ndescription: AI chat\nicon: \U0001f4ac\nagents:\n  - ghost-agent\n---\n",
    )

    with caplog.at_level(logging.WARNING, logger="app.orchestrator.apps"):
        registry = AppRegistry(str(tmp_path))

    assert len(registry.all()) == 1
    app = registry.get("chat")
    assert app is not None
    assert app.agents == ["ghost-agent"]
    # Warning should be present in logs
    assert any("ghost-agent" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Test 3: Same agent in two APP.md files — both AppDefinitions include it (APP-04)
# ---------------------------------------------------------------------------

def test_shared_agent_in_two_apps(tmp_path):
    """Same agent name in two APP.md files — both AppDefinition objects include it."""
    _write_app_md(
        tmp_path / "chat",
        "---\nname: Chat\ndescription: d1\nicon: A\nagents:\n  - general-assistant\n---\n",
    )
    _write_app_md(
        tmp_path / "superchat",
        "---\nname: SuperChat\ndescription: d2\nicon: B\nagents:\n  - general-assistant\n  - code-reviewer\n---\n",
    )

    registry = AppRegistry(str(tmp_path))
    chat = registry.get("chat")
    superchat = registry.get("superchat")

    assert "general-assistant" in chat.agents
    assert "general-assistant" in superchat.agents
    assert "code-reviewer" in superchat.agents


# ---------------------------------------------------------------------------
# Test 4: Empty apps/ directory — returns empty list
# ---------------------------------------------------------------------------

def test_empty_apps_dir(tmp_path):
    """Empty apps/ directory returns empty list."""
    registry = AppRegistry(str(tmp_path))
    assert registry.all() == []


# ---------------------------------------------------------------------------
# Test 5: Malformed APP.md (missing name) is skipped with warning (T-14-05)
# ---------------------------------------------------------------------------

def test_malformed_app_md_skipped(tmp_path, caplog):
    """Malformed APP.md (missing name) is logged and skipped; does not crash."""
    # Bad app: no name
    _write_app_md(
        tmp_path / "bad-app",
        "---\ndescription: no name here\nicon: X\nagents: []\n---\n",
    )
    # Good app alongside bad one
    _write_app_md(
        tmp_path / "chat",
        "---\nname: Chat\ndescription: ok\nicon: C\nagents:\n  - general-assistant\n---\n",
    )

    with caplog.at_level(logging.WARNING, logger="app.orchestrator.apps"):
        registry = AppRegistry(str(tmp_path))

    # Only the valid app is returned
    apps = registry.all()
    assert len(apps) == 1
    assert apps[0].slug == "chat"
    # Warning should mention the bad app
    assert any("bad-app" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Test: get_agent_names convenience method
# ---------------------------------------------------------------------------

def test_get_agent_names(tmp_path):
    """get_agent_names returns correct list or empty list for unknown slug."""
    _write_app_md(
        tmp_path / "chat",
        "---\nname: Chat\ndescription: d\nicon: C\nagents:\n  - general-assistant\n---\n",
    )
    registry = AppRegistry(str(tmp_path))
    assert registry.get_agent_names("chat") == ["general-assistant"]
    assert registry.get_agent_names("unknown") == []
