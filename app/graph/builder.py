"""LangGraph conversation graph builder.

Compiles a StateGraph with a single chatbot node that calls the LLM
with the full message history. The compiled graph is reused across
all thread invocations (compile once at startup).

Extension point (v2): To add tool-calling, insert a ToolNode and
replace the chatbot->END edge with add_conditional_edges(tools_condition).
See: langgraph.prebuilt.ToolNode, langgraph.prebuilt.tools_condition
"""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph


def build_graph(llm: BaseChatModel, checkpointer: BaseCheckpointSaver):
    """Build and compile the conversation graph once at startup.

    Parameters
    ----------
    llm:
        Any BaseChatModel -- in production this is ChatCopilot.
    checkpointer:
        MemorySaver (tests) or AsyncPostgresSaver (production).
        The caller owns the checkpointer lifecycle.

    Returns
    -------
    CompiledStateGraph
        Thread-safe compiled graph. Call ``await graph.ainvoke(...)``
        with ``config={"configurable": {"thread_id": "<id>"}}``
        to scope conversation state per thread.

    Extension point
    ---------------
    To add tool-calling in v2, insert a ToolNode and replace
    the chatbot->END edge with add_conditional_edges(tools_condition):

        from langgraph.prebuilt import ToolNode, tools_condition
        builder.add_node("tools", ToolNode(tools))
        builder.add_conditional_edges("chatbot", tools_condition)
        builder.add_edge("tools", "chatbot")
    """

    async def chatbot_node(state: MessagesState) -> dict:
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("chatbot", chatbot_node)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)

    return builder.compile(checkpointer=checkpointer)
