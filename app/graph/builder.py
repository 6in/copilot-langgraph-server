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
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph


def _trim_html_history(messages: list) -> list:
    """Keep all messages but replace older HTML AI responses with a placeholder.

    Canvas chat accumulates large HTML payloads in history. We only need the
    most recent HTML for context; older ones waste tokens without adding value.
    An AI message is treated as HTML when its content is long and contains HTML tags.
    """
    def _is_html(msg) -> bool:
        if not isinstance(msg, AIMessage):
            return False
        content = msg.content if isinstance(msg.content, str) else ""
        return len(content) > 300 and any(
            tag in content.lower() for tag in ("<html", "<!doctype", "<body", "<div", "<head")
        )

    html_indices = [i for i, m in enumerate(messages) if _is_html(m)]
    if len(html_indices) <= 1:
        return messages  # 0 or 1 HTML message — nothing to trim

    # Replace all but the most recent HTML AI message with a short placeholder
    last_html_idx = html_indices[-1]
    trimmed = []
    for i, msg in enumerate(messages):
        if i in html_indices and i != last_html_idx:
            trimmed.append(AIMessage(content="[previous HTML response omitted]"))
        else:
            trimmed.append(msg)
    return trimmed


SYSTEM_PROMPT = SystemMessage(content=(
    "You are a helpful assistant. "
    "When outputting code blocks, always specify the language identifier "
    "(e.g. ```python, ```typescript, ```bash). "
    "Never use a plain ``` without a language."
))


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

    async def chatbot_node(state: MessagesState, config: RunnableConfig) -> dict:
        configurable = (config or {}).get("configurable", {})
        gem_system_prompt = configurable.get("system_prompt", "")
        github_login = configurable.get("github_login", "")

        system_messages = [SYSTEM_PROMPT]
        if github_login and github_login != "unknown":
            system_messages.append(SystemMessage(content=(
                f"The authenticated user's GitHub login is: {github_login}. "
                f"When the user asks about their name, identity, or who they are, "
                f"answer with this GitHub username."
            )))
        if gem_system_prompt:
            system_messages.append(SystemMessage(content=gem_system_prompt))

        # llm.astream() で iterate することで LangGraph の on_chat_model_stream が
        # 発火し、langgraph_handler が notifier.send_token 経由で SSE にトークンを
        # 流せるようになる。chunk を accumulate して最終 AIMessage を返す。
        response: AIMessage | None = None
        async for chunk in llm.astream(system_messages + state["messages"]):
            response = chunk if response is None else response + chunk
        if response is None:
            response = AIMessage(content="")
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("chatbot", chatbot_node)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)

    return builder.compile(checkpointer=checkpointer)


def build_canvas_graph(llm: BaseChatModel, checkpointer: BaseCheckpointSaver):
    """Build and compile the Canvas-specific conversation graph.

    Identical to build_graph except the chatbot node applies _trim_html_history
    before invoking the LLM — older HTML AI responses are replaced with a
    placeholder so only the most recent HTML is sent as context.
    """

    async def chatbot_node(state: MessagesState, config: RunnableConfig) -> dict:
        configurable = (config or {}).get("configurable", {})
        gem_system_prompt = configurable.get("system_prompt", "")
        github_login = configurable.get("github_login", "")

        system_messages = [SYSTEM_PROMPT]
        if github_login and github_login != "unknown":
            system_messages.append(SystemMessage(content=(
                f"The authenticated user's GitHub login is: {github_login}. "
                f"When the user asks about their name, identity, or who they are, "
                f"answer with this GitHub username."
            )))
        if gem_system_prompt:
            system_messages.append(SystemMessage(content=gem_system_prompt))

        response: AIMessage | None = None
        async for chunk in llm.astream(system_messages + _trim_html_history(state["messages"])):
            response = chunk if response is None else response + chunk
        if response is None:
            response = AIMessage(content="")
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("chatbot", chatbot_node)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)

    return builder.compile(checkpointer=checkpointer)
