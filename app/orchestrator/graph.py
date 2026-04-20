from __future__ import annotations

import logging
from typing import Any

from app.providers.copilot import ChatCopilot
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.observability.trace import trace_span
from app.orchestrator.state import AgentState
from app.orchestrator.agent import SubAgentRegistry

logger = logging.getLogger(__name__)


ROUTER_PROMPT = """\
あなたはエージェントルーターです。
ユーザーの入力を読み、最も適切なエージェントを1つ選んでください。

## 利用可能なエージェント

{agent_descriptions}

## ルール
- エージェント名（name の値）のみを返す
- 該当なしは "fallback" を返す
- 理由・説明は不要
"""


class RouterNode:
    def __init__(self, registry: SubAgentRegistry, github_token: str):
        self._registry = registry
        self._llm = ChatCopilot(model="claude-haiku-4-5-20251001", github_token=github_token)

    async def __call__(self, state: AgentState) -> AgentState:
        # Read context once — `context.correlation_id` becomes trace_id, and
        # user_id / app_id / thread_id populate span attributes (D-08, D-09).
        context = state.get("context")
        trace_id = context.correlation_id if context else ""
        agents = self._registry.all()

        # Common attributes for the routing span. D-13: user_input_prefix is
        # truncated to 200 chars (replaces the previous 80-char "input" field).
        common_attrs: dict[str, Any] = {
            "user_id": context.user_id if context else "unknown",
            "app_id": context.app_id if context else "",
            "thread_id": context.thread_id if context else "",
            "user_input_prefix": state["input"][:200],
            "candidates": [a.name for a in agents],
        }

        async with trace_span(
            "routing", trace_id=trace_id, attributes=common_attrs
        ) as span:
            # --- Stage 1: Keyword pre-filter ---
            user_input = state["input"].lower()
            keyword_matches = [
                a for a in agents
                if any(kw.lower() in user_input for kw in getattr(a, "keywords", []))
            ]
            if len(keyword_matches) == 1:
                chosen = keyword_matches[0].name
                span.set_attribute("stage", "keyword")
                span.set_attribute("chosen", chosen)
                span.set_attribute("agent_name", chosen)
                return {"next": chosen}

            # --- Stage 1.5: Single agent (no LLM needed) ---
            if len(agents) == 1:
                chosen = agents[0].name
                span.set_attribute("stage", "single")
                span.set_attribute("chosen", chosen)
                span.set_attribute("agent_name", chosen)
                return {"next": chosen}

            # --- Stage 2: LLM routing ---
            descriptions = "\n\n".join(
                f"name: {a.name}\ndescription: {a.description}"
                for a in agents
            )
            messages = [
                SystemMessage(content=ROUTER_PROMPT.format(agent_descriptions=descriptions)),
                HumanMessage(content=state["input"]),
            ]
            response = await self._llm.ainvoke(messages)
            chosen = response.content.strip()

            valid = {a.name for a in agents} | {"fallback"}
            if chosen not in valid:
                unknown = chosen
                chosen = "fallback"
                span.set_attribute("stage", "llm")
                span.set_attribute("chosen", chosen)
                span.set_attribute("agent_name", chosen)
                span.set_attribute("fallback", True)
                # status_message length cap per CONTEXT D-13 defensive truncation
                span.set_status("ERROR", f"unknown_agent={unknown}"[:200])
                return {"next": chosen}

            span.set_attribute("stage", "llm")
            span.set_attribute("chosen", chosen)
            span.set_attribute("agent_name", chosen)
            return {"next": chosen}


def fallback_node(state: AgentState) -> AgentState:
    return {
        "output": "対応できるエージェントが見つかりませんでした。",
        "messages": [],
    }


def _wrap_agent_run(agent):
    """Wrap agent.run to ensure AIMessage.name is set after SubAgent returns.

    LangGraph checkpoint serialization can lose AIMessage.name.
    DebateGraph works around this by force-setting name after each agent call.
    Apply the same pattern here so orchestrator threads preserve agent names on reload.
    """
    async def wrapped(state: AgentState) -> AgentState:
        result = await agent.run(state)
        raw_messages = result.get("messages", [])
        fixed = [
            AIMessage(content=m.content, name=agent.name)
            if isinstance(m, AIMessage) and not m.name else m
            for m in raw_messages
        ]
        return {**result, "messages": fixed}
    return wrapped


def build_orchestrator_graph(registry: SubAgentRegistry, github_token: str, checkpointer=None) -> Any:
    graph = StateGraph(AgentState)

    graph.add_node("router", RouterNode(registry, github_token))
    graph.add_node("fallback", fallback_node)
    for agent in registry.all():
        graph.add_node(agent.name, _wrap_agent_run(agent))

    graph.set_entry_point("router")

    routing_map = {a.name: a.name for a in registry.all()}
    routing_map["fallback"] = "fallback"
    graph.add_conditional_edges("router", lambda s: s["next"], routing_map)

    for agent in registry.all():
        graph.add_edge(agent.name, END)
    graph.add_edge("fallback", END)

    return graph.compile(checkpointer=checkpointer)
