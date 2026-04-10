"""ToolEnabledSubAgent — SubAgent with LangGraph mini ReAct loop.

Implements TOOL-01 (ReAct loop via ToolNode), TOOL-02 (recursion limit),
and TOOL-03 (ToolMessage accumulation in AgentState.messages).

Architecture:
    ToolEnabledSubAgent.run()
        -> build_react_graph(llm_with_tools, tool_node)
        -> mini ReAct: agent_node -> tools_condition -> ToolNode -> agent_node -> ...
        -> END when no tool_calls in AIMessage
        -> GraphRecursionError caught after DEFAULT_RECURSION_LIMIT steps
"""

from __future__ import annotations

import logging
import operator
from typing import Annotated, Any

from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.errors import GraphRecursionError

from app.orchestrator.agent import SubAgent
from app.orchestrator.state import AgentState

logger = logging.getLogger(__name__)


class MiniReActState(TypedDict):
    """Minimal state for the mini ReAct subgraph.

    Only messages are needed — the full AgentState is managed by the caller.
    Using Annotated[list, operator.add] allows nodes to return message lists
    that are automatically appended by LangGraph's message reducer.
    """

    messages: Annotated[list[BaseMessage], operator.add]


def build_react_graph(llm_with_tools: Any, tool_node: ToolNode):
    """Build a minimal ReAct StateGraph (agent -> ToolNode -> agent -> ... -> END).

    Design decision D-02: no checkpointer — this mini graph is stateless.
    The outer AgentState (with SQLite checkpointer) owns persistence.

    Args:
        llm_with_tools: A bound LLM (result of llm.bind_tools(tools)).
        tool_node: A pre-constructed ToolNode wrapping the same tools.

    Returns:
        CompiledGraph ready for ainvoke().
    """

    async def agent_node(state: MiniReActState) -> dict:
        """Call the LLM and return the response as a new message."""
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MiniReActState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    # D-02: no checkpointer for the mini graph
    return graph.compile()


class ToolEnabledSubAgent(SubAgent):
    """SubAgent that executes a mini ReAct loop to call tools.

    Wraps the LLM with bind_tools(), builds a ToolNode, and runs a
    LangGraph mini ReAct graph on each request.

    Safety (TOOL-02, T-21-04):
        DEFAULT_RECURSION_LIMIT = 25 caps the loop at ~10 tool calls.
        GraphRecursionError is caught and a partial result is returned.

    Pitfall 1 mitigation:
        If tools list is empty, logs a warning but still instantiates.
        SubAgentRegistry is responsible for the tools/no-tools decision.
    """

    DEFAULT_RECURSION_LIMIT = 25  # 10 loops x 2 nodes + buffer (TOOL-02, Pitfall 4)

    def __init__(
        self,
        name: str,
        description: str,
        model: str,
        system_prompt: str,
        github_token: str,
        tools: list[BaseTool],
        keywords: list[str] | None = None,
    ):
        super().__init__(name, description, model, system_prompt, github_token, keywords)
        self._tools = tools
        if not tools:
            logger.warning(
                "[tool-agent] '%s' initialized with empty tools list",
                name,
            )
        self._tool_node = ToolNode(tools)
        self._llm_with_tools = self._llm.bind_tools(tools)

    @classmethod
    def from_dir(cls, agent_dir, github_token: str, tools: list[BaseTool] | None = None) -> "ToolEnabledSubAgent":
        """Load from AGENT.md frontmatter, accepting tools as an explicit argument.

        Args:
            agent_dir: Path to the agent directory containing AGENT.md.
            github_token: GitHub OAuth token for the Copilot SDK.
            tools: List of BaseTool instances to bind. Defaults to [].
        """
        import frontmatter
        from pathlib import Path

        agent_dir = Path(agent_dir)
        post = frontmatter.load(agent_dir / "AGENT.md")
        meta = post.metadata
        return cls(
            name=meta["name"],
            description=meta["description"],
            model=meta.get("model", "claude-sonnet-4-6"),
            system_prompt=post.content,
            github_token=github_token,
            tools=tools or [],
            keywords=meta.get("keywords", []),
        )

    async def run(self, state: AgentState) -> AgentState:
        """Execute the mini ReAct loop and return the final output.

        Builds a fresh mini graph per invocation (stateless D-02).
        Catches GraphRecursionError to return a partial result instead
        of propagating the exception to the caller (TOOL-02).

        Returns:
            Partial AgentState dict with output, messages, and agent_name.
        """
        mini_graph = build_react_graph(self._llm_with_tools, self._tool_node)
        init_messages: list[BaseMessage] = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=state["input"]),
        ]
        try:
            result = await mini_graph.ainvoke(
                {"messages": init_messages},
                config={"recursion_limit": self.DEFAULT_RECURSION_LIMIT},
            )
            all_messages: list[BaseMessage] = result["messages"]
        except GraphRecursionError:
            logger.warning(
                "[tool-agent] %s: recursion limit reached (%d), returning partial result",
                self.name,
                self.DEFAULT_RECURSION_LIMIT,
            )
            all_messages = init_messages  # fallback to initial messages

        last_ai = next(
            (m for m in reversed(all_messages) if isinstance(m, AIMessage) and m.content),
            AIMessage(content="(ツール呼び出しが上限に達しました)"),
        )
        return {
            "output": last_ai.content,
            "messages": all_messages,
            "agent_name": self.name,
        }
