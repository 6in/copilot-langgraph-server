"""ToolEnabledSubAgent — SubAgent with LangGraph mini ReAct loop.

Implements TOOL-01 (ReAct loop via ToolNode), TOOL-02 (recursion limit),
and TOOL-03 (ToolMessage accumulation in AgentState.messages).

Architecture:
    ToolEnabledSubAgent.run()
        -> build_react_graph(llm_with_tools, tool_node)
        -> mini ReAct: agent_node -> tools_condition -> ToolNode -> agent_node -> ...
        -> END when no tool_calls in AIMessage
        -> GraphRecursionError caught after DEFAULT_RECURSION_LIMIT steps

Circular import avoidance:
    tool_agent.py does NOT import from agent.py at module level.
    ToolEnabledSubAgent duplicates the minimal SubAgent interface
    (name, description, keywords, _llm, _system_prompt, run, close)
    to break the agent.py <-> tool_agent.py cycle.
    agent.py imports ToolEnabledSubAgent; tool_agent.py does NOT import agent.py.
"""

from __future__ import annotations

import logging
import operator
from pathlib import Path
from typing import Annotated, Any

from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.errors import GraphRecursionError

from app.observability.trace import attach_usage_attributes, trace_span
from app.observability.traced_tool import TracedTool
from app.utils.system_prompt import build_system_prompt_prefix
from app.providers.copilot import ChatCopilot
from app.orchestrator.state import AgentState

logger = logging.getLogger(__name__)


class MiniReActState(TypedDict):
    """Minimal state for the mini ReAct subgraph.

    Only messages are needed — the full AgentState is managed by the caller.
    Using Annotated[list, operator.add] allows nodes to return message lists
    that are automatically appended by LangGraph's message reducer.
    """

    messages: Annotated[list[BaseMessage], operator.add]


def _extract_python_code(text: str) -> str | None:
    """Extract Python code from LLM text response.

    Looks for ```python code blocks first, then falls back to
    detecting code-like content (import statements, function definitions).
    Returns the extracted code string, or None if no code found.
    """
    import re

    # Try ```python blocks
    matches = re.findall(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if matches:
        # Concatenate all python blocks (LLM may split code across blocks)
        return "\n\n".join(m.strip() for m in matches if m.strip())

    # Try generic ``` blocks that look like Python
    matches = re.findall(r"```\s*\n(.*?)```", text, re.DOTALL)
    for m in matches:
        code = m.strip()
        if code and any(kw in code for kw in ("import ", "def ", "print(", "for ", "class ")):
            return code

    return None


def build_react_graph(llm_with_tools: Any, tool_node: ToolNode, tool_names: list[str] | None = None):
    """Build a minimal ReAct StateGraph (agent -> ToolNode -> agent -> ... -> END).

    Design decision D-02: no checkpointer — this mini graph is stateless.
    The outer AgentState (with SQLite checkpointer) owns persistence.

    Args:
        llm_with_tools: A bound LLM (result of llm.bind_tools(tools)).
        tool_node: A pre-constructed ToolNode wrapping the same tools.
        tool_names: List of tool names (used for code extraction fallback).

    Returns:
        CompiledGraph ready for ainvoke().
    """
    _tool_names = tool_names or []
    _has_execute_python = "execute_python" in _tool_names

    async def agent_node(state: MiniReActState) -> dict:
        """Call the LLM and return the response as a new message."""
        response = await llm_with_tools.ainvoke(state["messages"])

        # Fallback: if LLM returned text without tool_calls and execute_python is available,
        # extract Python code from the response and create a synthetic tool call.
        # Copilot SDK models often ignore JSON tool call format entirely.
        if not getattr(response, "tool_calls", None) and _has_execute_python:
            has_prior_tool_interaction = any(
                not isinstance(m, (SystemMessage, HumanMessage))
                for m in state["messages"]
            )
            if not has_prior_tool_interaction:
                code = _extract_python_code(response.content)

                # If no code blocks found, ask LLM to write code only (no explanation)
                if not code:
                    logger.info("[agent_node] No code in LLM response — requesting code-only output")
                    code_request = HumanMessage(content=(
                        "上記の説明ではなく、実行可能な Python コードだけを書いてください。\n"
                        "```python で始めて ``` で終わるコードブロック1つだけを返してください。\n"
                        "説明やコメントは不要です。コードだけ。"
                    ))
                    code_response = await llm_with_tools.ainvoke(
                        state["messages"] + [response, code_request]
                    )
                    # If Phase 2 returned a proper tool call, use it directly
                    if getattr(code_response, "tool_calls", None):
                        logger.info("[agent_node] Code-only request returned tool_calls — using directly")
                        response = code_response
                    else:
                        code = _extract_python_code(code_response.content)

                if code:
                    logger.info("[agent_node] Creating synthetic execute_python tool call (%d chars)", len(code))
                    import uuid
                    from langchain_core.messages.tool import ToolCall
                    tc = ToolCall(name="execute_python", args={"code": code}, id=str(uuid.uuid4())[:8])
                    response = AIMessage(content="", tool_calls=[tc])

        # Emit tool execution event for UI progress indicator
        if getattr(response, "tool_calls", None):
            from app.orchestrator.tool_context import tool_event_cb
            cb = tool_event_cb.get()
            if cb:
                for tc in response.tool_calls:
                    name = tc.get("name", "tool") if isinstance(tc, dict) else getattr(tc, "name", "tool")
                    args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                    query = args.get("query", "") if isinstance(args, dict) else ""
                    try:
                        await cb(name, query)
                    except Exception:
                        pass  # never block tool execution on notification failure
        return {"messages": [response]}

    graph = StateGraph(MiniReActState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    # D-02: no checkpointer for the mini graph
    return graph.compile()


def _build_rich_output(all_messages: list[BaseMessage], last_ai: AIMessage) -> str:
    """Build output that includes tool call code and results before the final summary.

    For agents like CodeAct, this shows the Python code executed and its output,
    making the full execution trace visible in the chat UI.
    """
    from langchain_core.messages import ToolMessage

    sections: list[str] = []
    for msg in all_messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                code = args.get("code", "")
                logger.debug("[rich-output] AIMessage tool_call: name=%s args_keys=%s code_len=%d", name, list(args.keys()) if isinstance(args, dict) else "?", len(code))
                if code:
                    sections.append(f"```python\n{code}\n```")
        elif isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            # Parse execute_python JSON result to show stdout/stderr cleanly
            try:
                import json
                result = json.loads(content)
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                exit_code = result.get("exit_code")
                parts = []
                if stdout:
                    parts.append(f"```\n{stdout}\n```")
                if stderr:
                    parts.append(f"**stderr:**\n```\n{stderr}\n```")
                if exit_code is not None and exit_code != 0:
                    parts.append(f"exit code: {exit_code}")
                if parts:
                    sections.append("\n".join(parts))
            except (json.JSONDecodeError, TypeError):
                if content.strip():
                    sections.append(f"```\n{content}\n```")

    if sections:
        # Tool trace + final summary
        return "\n\n".join(sections) + "\n\n---\n\n" + last_ai.content
    return last_ai.content


class ToolEnabledSubAgent:
    """SubAgent that executes a mini ReAct loop to call tools.

    Intentionally does NOT inherit from SubAgent (agent.py) to avoid circular
    import. Implements the same interface: name, description, keywords,
    _llm, _system_prompt, run(), close().

    Wraps the LLM with bind_tools(), builds a ToolNode, and runs a
    LangGraph mini ReAct graph on each request.

    Safety (TOOL-02, T-21-04):
        DEFAULT_RECURSION_LIMIT = 25 caps the loop at ~10 tool calls.
        GraphRecursionError is caught and a partial result is returned.
        AGENT.md の `recursion_limit` フィールドで per-agent カスタマイズ可能（例: CodeAct は 12）。

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
        recursion_limit: int | None = None,
        privileged_tool_names: frozenset[str] = frozenset(),
    ):
        self.name = name
        self.description = description
        self.keywords: list[str] = keywords or []
        self.recursion_limit = recursion_limit or self.DEFAULT_RECURSION_LIMIT
        self._llm = ChatCopilot(model=model, github_token=github_token)
        self._system_prompt = system_prompt
        self._tools = tools
        # Phase 31 Plan 04: privileged set lets TracedTool flag sandbox_exposed=false
        # tools in tool_call spans (D-12). Defaults to empty frozenset for legacy
        # construction paths that don't supply it (eg tests, canvas).
        self._privileged_names: frozenset[str] = frozenset(privileged_tool_names)
        if not tools:
            logger.warning(
                "[tool-agent] '%s' initialized with empty tools list",
                name,
            )
        # Wrap every tool with TracedTool so ToolNode invocations emit tool_call
        # spans. The LLM still sees the original tool schemas via bind_tools.
        wrapped_tools: list[BaseTool] = [
            TracedTool(t, privileged_tool_names=self._privileged_names) for t in tools
        ]
        self._tool_node = ToolNode(wrapped_tools)
        self._llm_with_tools = self._llm.bind_tools(tools)

    @classmethod
    def from_dir(
        cls,
        agent_dir: Path | str,
        github_token: str,
        tools: list[BaseTool] | None = None,
        privileged_tool_names: frozenset[str] = frozenset(),
    ) -> "ToolEnabledSubAgent":
        """Load from AGENT.md frontmatter, accepting tools as an explicit argument.

        Args:
            agent_dir: Path to the agent directory containing AGENT.md.
            github_token: GitHub OAuth token for the Copilot SDK.
            tools: List of BaseTool instances to bind. Defaults to [].
            privileged_tool_names: Tool names requiring ``privileged=True`` in
                tool_call spans (Phase 31 D-12). Passed through to TracedTool.
        """
        import frontmatter

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
            recursion_limit=meta.get("recursion_limit"),
            privileged_tool_names=privileged_tool_names,
        )

    async def run(self, state: AgentState) -> AgentState:
        """Execute the mini ReAct loop and return the final output.

        Builds a fresh mini graph per invocation (stateless D-02).
        Catches GraphRecursionError to return a partial result instead
        of propagating the exception to the caller (TOOL-02).

        Phase 31 Plan 04: wrapped in ``trace_span("sub_agent", ...)`` so ToolNode
        calls made inside ``mini_graph.ainvoke`` see the common 4 attributes and
        parent span_id via ContextVar (the TracedTool wrapper on each tool emits
        its own child ``tool_call`` span).

        Returns:
            Partial AgentState dict with output, messages, and agent_name.
        """
        mini_graph = build_react_graph(
            self._llm_with_tools, self._tool_node,
            tool_names=[t.name for t in self._tools],
        )
        context = state.get("context")
        trace_id = context.correlation_id if context else ""
        common_attrs: dict = {
            "user_id": context.user_id if context else "unknown",
            "app_id": context.app_id if context else "",
            "thread_id": context.thread_id if context else "",
            "agent_name": self.name,
            "model_name": getattr(self._llm, "model", "unknown"),
        }
        async with trace_span(
            "sub_agent", trace_id=trace_id, attributes=common_attrs
        ) as span:
            user_id = context.user_id if context and getattr(context, "user_id", None) not in (None, "unknown") else None
            system_prompt = build_system_prompt_prefix(user_id) + "\n\n" + self._system_prompt
            init_messages: list[BaseMessage] = [
                SystemMessage(content=system_prompt),
            ]
            # Inject past conversation context if provided
            ctx_msgs = state.get("context_messages")
            if ctx_msgs:
                for cm in ctx_msgs:
                    if cm["role"] == "user":
                        init_messages.append(HumanMessage(content=cm["content"]))
                    else:
                        init_messages.append(AIMessage(content=cm["content"], name=cm.get("sender_name")))
            init_messages.append(HumanMessage(content=state["input"]))
            try:
                result = await mini_graph.ainvoke(
                    {"messages": init_messages},
                    config={"recursion_limit": self.recursion_limit},
                )
                all_messages: list[BaseMessage] = result["messages"]
            except GraphRecursionError:
                logger.warning(
                    "[tool-agent] %s: recursion limit reached (%d), returning partial result",
                    self.name,
                    self.recursion_limit,
                )
                all_messages = init_messages  # fallback to initial messages
                # Record the recursion stop reason on the sub_agent span so dashboards
                # can surface it without grepping logger.warning lines (D-06).
                span.set_attribute("recursion_limit_reached", True)
                span.set_attribute("recursion_limit", self.recursion_limit)
                span.set_status("ERROR", "recursion_limit_reached")

            last_ai = next(
                (m for m in reversed(all_messages) if isinstance(m, AIMessage) and m.content),
                AIMessage(content="(ツール呼び出しが上限に達しました)"),
            )
            # Build rich output: include tool calls (code) and results before the final summary.
            # This allows the frontend to display the full execution trace.
            output = _build_rich_output(all_messages, last_ai)
            # Attach Copilot SDK ASSISTANT_USAGE event payload (Plan 01 confirmed 4 fields).
            attach_usage_attributes(span, self._llm)
            span.set_attribute("message_count", len(all_messages))
            return {
                "output": output,
                "messages": all_messages,
                "agent_name": self.name,
            }

    async def close(self) -> None:
        """Release the underlying ChatCopilot client."""
        await self._llm.close()
