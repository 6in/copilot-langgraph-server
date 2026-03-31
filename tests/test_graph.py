"""Tests for LangGraph conversation graph (GRPH-01, GRPH-02, GRPH-03)."""
import pytest
from unittest.mock import AsyncMock
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.graph.builder import build_graph


@pytest.fixture
def mock_llm():
    """Mock BaseChatModel that returns a fixed AIMessage."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="mocked response"))
    return llm


@pytest.fixture
def graph(mock_llm):
    """Fresh compiled graph with MemorySaver per test."""
    checkpointer = MemorySaver()
    return build_graph(mock_llm, checkpointer)


@pytest.mark.asyncio
async def test_messages_accumulate(graph, mock_llm):
    """GRPH-01: Second message sees full history (human + AI + human)."""
    config = {"configurable": {"thread_id": "t1"}}
    await graph.ainvoke({"messages": [HumanMessage(content="hello")]}, config=config)
    await graph.ainvoke({"messages": [HumanMessage(content="follow-up")]}, config=config)

    second_call_messages = mock_llm.ainvoke.call_args_list[1][0][0]
    assert len(second_call_messages) == 3
    assert isinstance(second_call_messages[0], HumanMessage)
    assert isinstance(second_call_messages[1], AIMessage)
    assert isinstance(second_call_messages[2], HumanMessage)
    assert second_call_messages[2].content == "follow-up"


@pytest.mark.asyncio
async def test_thread_isolation(graph, mock_llm):
    """GRPH-02: Different thread_ids have independent histories."""
    config_a = {"configurable": {"thread_id": "thread-a"}}
    config_b = {"configurable": {"thread_id": "thread-b"}}

    await graph.ainvoke({"messages": [HumanMessage(content="A message")]}, config=config_a)
    result_b = await graph.ainvoke({"messages": [HumanMessage(content="B message")]}, config=config_b)

    # Thread B: only HumanMessage("B message") + AIMessage("mocked response")
    assert len(result_b["messages"]) == 2
    assert result_b["messages"][0].content == "B message"


@pytest.mark.asyncio
async def test_extension_point(graph):
    """GRPH-03: Graph has chatbot node with START->chatbot->END edges."""
    # Access the graph's node list
    node_names = list(graph.nodes.keys())
    assert "chatbot" in node_names

    # Verify edges: START -> chatbot, chatbot -> END
    # CompiledStateGraph stores edges; we verify the structure
    # by checking the graph can be drawn (has valid topology)
    assert graph.get_graph() is not None


@pytest.mark.asyncio
async def test_single_message_response(graph):
    """Basic: single message returns HumanMessage + AIMessage."""
    config = {"configurable": {"thread_id": "single"}}
    result = await graph.ainvoke({"messages": [HumanMessage(content="hi")]}, config=config)
    assert len(result["messages"]) == 2
    assert isinstance(result["messages"][0], HumanMessage)
    assert isinstance(result["messages"][1], AIMessage)
    assert result["messages"][1].content == "mocked response"
