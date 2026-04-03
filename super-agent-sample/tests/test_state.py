"""Unit tests for AgentState TypedDict (src/state.py)."""
from __future__ import annotations
from langchain_core.messages import HumanMessage
from state import AgentState


def test_agent_state_has_required_keys():
    """AgentState must declare all four required keys."""
    annotations = AgentState.__annotations__
    assert "input" in annotations
    assert "output" in annotations
    assert "messages" in annotations
    assert "next" in annotations


def test_agent_state_instantiation():
    """AgentState can be instantiated with valid values and all fields are accessible."""
    msg = HumanMessage(content="hello")
    state: AgentState = {
        "input": "hello",
        "output": "world",
        "messages": [msg],
        "next": "code-reviewer",
    }
    assert state["input"] == "hello"
    assert state["output"] == "world"
    assert state["messages"] == [msg]
    assert state["next"] == "code-reviewer"
