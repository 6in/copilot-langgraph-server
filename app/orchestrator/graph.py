from __future__ import annotations
import json
import logging
from typing import Any
from app.providers.copilot import ChatCopilot
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

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
        agents = self._registry.all()
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
            logger.warning(json.dumps({
                "event": "routing_fallback",
                "unknown": chosen,
                "fallback": "fallback",
            }))
            chosen = "fallback"

        context = state.get("context")
        logger.info(json.dumps({
            "event": "routing",
            "input": state["input"][:80],
            "chosen": chosen,
            "candidates": [a.name for a in agents],
            "thread_id": context.thread_id if context else "",
            "correlation_id": context.correlation_id if context else "",
        }))
        return {"next": chosen}


def fallback_node(state: AgentState) -> AgentState:
    return {
        "output": "対応できるエージェントが見つかりませんでした。",
        "messages": [],
    }


def build_orchestrator_graph(registry: SubAgentRegistry, github_token: str) -> Any:
    graph = StateGraph(AgentState)

    graph.add_node("router", RouterNode(registry, github_token))
    graph.add_node("fallback", fallback_node)
    for agent in registry.all():
        graph.add_node(agent.name, agent.run)

    graph.set_entry_point("router")

    routing_map = {a.name: a.name for a in registry.all()}
    routing_map["fallback"] = "fallback"
    graph.add_conditional_edges("router", lambda s: s["next"], routing_map)

    for agent in registry.all():
        graph.add_edge(agent.name, END)
    graph.add_edge("fallback", END)

    return graph.compile()
