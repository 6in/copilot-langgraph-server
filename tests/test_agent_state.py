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


async def test_context_immutable_via_reducer():
    """CONTEXT-02: _keep_first reducer prevents node from overwriting context.

    Build a StateGraph with two sequential nodes. First node returns a new RPCContext
    with user_id="overwriter". Second node reads state["context"]. After full graph
    invocation, state["context"].user_id must remain the ORIGINAL value ("alice"),
    not "overwriter".
    """
    def overwrite_attempt_node(state: AgentState) -> dict:
        # This node tries to replace context — _keep_first should discard this
        new_ctx = RPCContext(user_id="overwriter", app_id="evil", thread_id="x")
        return {"context": new_ctx}

    def verify_context_node(state: AgentState) -> dict:
        ctx = state["context"]
        return {"output": ctx.user_id}

    graph = StateGraph(AgentState)
    graph.add_node("overwriter", overwrite_attempt_node)
    graph.add_node("verifier", verify_context_node)
    graph.set_entry_point("overwriter")
    graph.add_edge("overwriter", "verifier")
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

    # _keep_first should have preserved "alice", not "overwriter"
    assert result["output"] == "alice"
    assert result["context"].user_id == "alice"
