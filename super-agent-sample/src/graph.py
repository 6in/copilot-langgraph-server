from __future__ import annotations
import os
from typing import Any
from copilot import ChatCopilot
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from state import AgentState
from agent import SubAgentRegistry


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
    def __init__(self, registry: SubAgentRegistry):
        self._registry = registry
        self._llm = ChatCopilot(model="claude-haiku-4-5-20251001", github_token=os.environ.get("GITHUB_TOKEN", ""))  # ルーターは軽量モデル

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
            print(f"[router] unknown '{chosen}' → fallback")
            chosen = "fallback"

        print(f"[router] '{state['input'][:40]}' → {chosen}")
        return {"next": chosen}


def fallback_node(state: AgentState) -> AgentState:
    return {
        "output": "対応できるエージェントが見つかりませんでした。",
        "messages": [],
    }


def build_orchestrator_graph(registry: SubAgentRegistry) -> Any:
    graph = StateGraph(AgentState)

    graph.add_node("router", RouterNode(registry))
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


def build_simple_graph() -> Any:
    """チャットモード用：LLM 1発"""

    async def simple_node(state: AgentState) -> AgentState:
        llm = ChatCopilot(model="claude-sonnet-4-6", github_token=os.environ.get("GITHUB_TOKEN", ""))
        response = await llm.ainvoke([HumanMessage(content=state["input"])])
        return {"output": response.content, "messages": []}

    graph = StateGraph(AgentState)
    graph.add_node("llm", simple_node)
    graph.set_entry_point("llm")
    graph.add_edge("llm", END)
    return graph.compile()
