"""Unit tests for AgentState context field and _keep_first reducer via LangGraph StateGraph.

Tests verify:
1. CONTEXT-01: A node can read state["context"].correlation_id and use it.
2. CONTEXT-02: A node returning a new context value does not overwrite the original.
"""
import pytest
from langgraph.graph import StateGraph, END
from app.orchestrator.state import AgentState
from app.orchestrator.context import RPCContext


async def test_context_accessible_in_node():
    """CONTEXT-01: Node can read state['context'].correlation_id.

    Build a minimal StateGraph with one node that reads state["context"].correlation_id
    and writes it to output. Invoke with initial RPCContext. Assert output equals
    the original correlation_id.
    """
    def read_context_node(state: AgentState) -> dict:
        ctx = state["context"]
        return {"output": ctx.correlation_id}

    graph = StateGraph(AgentState)
    graph.add_node("reader", read_context_node)
    graph.set_entry_point("reader")
    graph.add_edge("reader", END)
    compiled = graph.compile()

    initial_ctx = RPCContext(user_id="alice", app_id="chat", thread_id="t-001")

    result = await compiled.ainvoke({
        "input": "hello",
        "output": "",
        "messages": [],
        "next": "",
        "context": initial_ctx,
        "error": None,
    })

    assert result["output"] == initial_ctx.correlation_id


async def test_context_fresh_value_wins_over_stale():
    """CONTEXT-02: `_keep_first` reducer prefers the newer context when one is provided.

    Fix 2026-04-20 (Phase 31 Wave 6): the reducer previously kept the first value
    written. That froze ``correlation_id`` / trace_id across subsequent requests on
    the same thread (LangGraph checkpointer kept restoring the original context),
    which broke per-request trace isolation. Real graph nodes never return
    ``context`` in their state updates, so preferring the freshest caller-provided
    value is both safe and necessary.

    This graph passes a fresh context from a node and verifies that downstream
    nodes observe the new value.
    """
    def update_context_node(state: AgentState) -> dict:
        new_ctx = RPCContext(user_id="bob", app_id="chat", thread_id="t-002")
        return {"context": new_ctx}

    def verify_context_node(state: AgentState) -> dict:
        ctx = state["context"]
        return {"output": ctx.user_id}

    graph = StateGraph(AgentState)
    graph.add_node("updater", update_context_node)
    graph.add_node("verifier", verify_context_node)
    graph.set_entry_point("updater")
    graph.add_edge("updater", "verifier")
    graph.add_edge("verifier", END)
    compiled = graph.compile()

    original_ctx = RPCContext(user_id="alice", app_id="chat", thread_id="t-001")

    result = await compiled.ainvoke({
        "input": "hello",
        "output": "",
        "messages": [],
        "next": "",
        "context": original_ctx,
        "error": None,
    })

    # Fresh context from the `updater` node must win over the initial "alice".
    assert result["output"] == "bob"
    assert result["context"].user_id == "bob"
