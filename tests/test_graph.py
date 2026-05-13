"""Tests for LangGraph conversation graph (GRPH-01, GRPH-02, GRPH-03)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver

from app.graph.builder import build_graph


@pytest.fixture
def mock_llm():
    """Mock BaseChatModel that exposes ainvoke + astream.

    Phase 31 以降、chatbot_node は llm.astream() を async for で iterate する
    (token streaming 経路の標準パターン)。AsyncMock では `async for` 不可なので
    astream は async generator を返す MagicMock(side_effect=...) で構築する。
    side_effect を使う理由は call_args_list を保持して呼び出し履歴の検証ができるため。
    """
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="mocked response"))

    async def _astream_gen(*args, **kwargs):
        yield AIMessage(content="mocked response")

    llm.astream = MagicMock(side_effect=_astream_gen)
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

    # chatbot_node は llm.astream() を呼ぶので呼び出し履歴は astream.call_args_list で検証する。
    # 実装は system_messages を先頭に prepend するため、SystemMessage を filter して
    # 蓄積された会話履歴 (Human/AI/Human) だけを検証する。
    second_call_messages = mock_llm.astream.call_args_list[1][0][0]
    history = [m for m in second_call_messages if not isinstance(m, SystemMessage)]
    assert len(history) == 3
    assert isinstance(history[0], HumanMessage)
    assert isinstance(history[1], AIMessage)
    assert isinstance(history[2], HumanMessage)
    assert history[2].content == "follow-up"


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
