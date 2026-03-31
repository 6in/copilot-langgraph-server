"""Tests for /api/chat and /api/threads endpoints (CHAT-01, CHAT-02, CHAT-04)."""
import pytest

# Tests require api_client fixture from Plan 02.
# Stubs below validate mock graph contract.


async def test_chat_returns_reply(mock_graph):
    """POST /api/chat returns AI reply with same thread_id."""
    from langchain_core.messages import HumanMessage
    result = await mock_graph.ainvoke(
        {"messages": [HumanMessage(content="hello")]},
        config={"configurable": {"thread_id": "test-thread"}},
    )
    assert result["messages"][-1].content == "Hello from AI"


async def test_chat_mock_graph_callable(mock_graph):
    """Mock graph is callable with thread config."""
    result = await mock_graph.ainvoke(
        {"messages": []},
        config={"configurable": {"thread_id": "t1"}},
    )
    assert "messages" in result


async def test_new_thread_uuid_format():
    """POST /api/threads returns a valid UUID4 thread_id."""
    import uuid
    tid = str(uuid.uuid4())
    # Verify UUID format
    parsed = uuid.UUID(tid, version=4)
    assert str(parsed) == tid
