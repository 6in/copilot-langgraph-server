"""Unit tests for MenuRegistry and MenuDispatcher (src/dispatcher.py)."""
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock
import pytest
from dispatcher import MenuRegistry, MenuDispatcher


def test_menu_registry_loads_enabled(tmp_menus_dir):
    """MenuRegistry loads enabled menus from the YAML directory."""
    registry = MenuRegistry(str(tmp_menus_dir))
    assert "super-chat" in registry.menus
    assert "simple-chat" in registry.menus


def test_menu_registry_get_graph(tmp_menus_dir):
    """MenuRegistry.get_graph() returns the correct graph name for a menu."""
    registry = MenuRegistry(str(tmp_menus_dir))
    assert registry.get_graph("super-chat") == "orchestrator"
    assert registry.get_graph("simple-chat") == "simple"


@pytest.mark.asyncio
async def test_dispatcher_invokes_correct_graph(tmp_menus_dir):
    """MenuDispatcher.dispatch() invokes the correct graph and returns its output."""
    registry = MenuRegistry(str(tmp_menus_dir))
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {"output": "test output", "messages": [], "input": "", "next": ""}
    graphs = {"orchestrator": mock_graph, "simple": AsyncMock()}
    dispatcher = MenuDispatcher(registry, graphs)
    result = await dispatcher.dispatch("review this code", "super-chat")
    assert result == "test output"
    mock_graph.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_dispatcher_routes_by_mode(tmp_menus_dir):
    """MenuDispatcher routes 'super-chat' to orchestrator graph and 'simple-chat' to simple graph."""
    registry = MenuRegistry(str(tmp_menus_dir))
    mock_orchestrator = AsyncMock()
    mock_orchestrator.ainvoke.return_value = {"output": "orchestrator result", "messages": [], "input": "", "next": ""}
    mock_simple = AsyncMock()
    mock_simple.ainvoke.return_value = {"output": "simple result", "messages": [], "input": "", "next": ""}
    graphs = {"orchestrator": mock_orchestrator, "simple": mock_simple}
    dispatcher = MenuDispatcher(registry, graphs)

    r1 = await dispatcher.dispatch("review code", "super-chat")
    assert r1 == "orchestrator result"
    mock_orchestrator.ainvoke.assert_called_once()
    mock_simple.ainvoke.assert_not_called()

    r2 = await dispatcher.dispatch("explain Python", "simple-chat")
    assert r2 == "simple result"
    mock_simple.ainvoke.assert_called_once()
