"""
app/orchestrator/debate_graph.py

DebateGraph — ターン制マルチエージェント会話グラフ

Exports:
    build_debate_graph: ファクトリ関数
    DebateState: TypedDict

Patterns:
    debate: A->B->A->B->... ラウンドロビン後 aggregator -> END
    chain:  A->B->C->... 1 回ずつ順に発言後 aggregator -> END
    panel:  A,B,C を max_turns 回繰り返し後 aggregator -> END

Security:
    T-17-01: participants リスト長 (2 <= N <= 10) と max_turns (1 <= N <= 20) を
             ファクトリ関数先頭でバリデーション
"""
from __future__ import annotations

import operator
import logging
from typing import Annotated, Any

from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


# ===========================================================================
# State
# ===========================================================================

class DebateState(TypedDict):
    """ターン制マルチエージェント会話グラフの状態 (D-03)"""
    turn: int
    max_turns: int
    pattern: str
    participants: list[str]
    messages: Annotated[list[BaseMessage], operator.add]
    current_agent_idx: int
    awaiting_extension: bool


# ===========================================================================
# Helpers
# ===========================================================================

def _extract_last_human_message(state: DebateState) -> str:
    """最後の HumanMessage の content を返す。なければ空文字列"""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def _make_pseudo_agent_state(state: DebateState) -> dict:
    """AgentState 互換 dict を返す（内部関数 T-17-02）

    agent.run(state) が期待するフィールドを持つ dict を構築する。
    外部入力を直接受けない内部ヘルパー。
    """
    return {
        "input": _extract_last_human_message(state),
        "messages": list(state["messages"]),
        "output": "",
        "next": "",
        "error": None,
        "context": None,
    }


# ===========================================================================
# Node factories
# ===========================================================================

def _make_dispatch_node(agents_map: dict, participants: list[str]):
    """debate/panel 用の単一ディスパッチャーノード

    state["current_agent_idx"] が指すエージェントを呼び出し、
    ターンカウンターと idx を進める。
    """
    async def dispatch_node(state: DebateState) -> dict:
        idx = state["current_agent_idx"]
        name = participants[idx % len(participants)]
        agent = agents_map[name]

        pseudo = _make_pseudo_agent_state(state)
        result = await agent.run(pseudo)

        output = result.get("output", "")
        new_messages = result.get("messages", [])
        if not new_messages:
            new_messages = [AIMessage(content=output)]

        next_idx = (idx + 1) % len(participants)
        new_turn = state["turn"] + 1

        return {
            "turn": new_turn,
            "current_agent_idx": next_idx,
            "messages": new_messages,
        }

    return dispatch_node


def _make_chain_node(name: str, agent):
    """chain パターン用の per-agent ノード"""
    async def chain_node(state: DebateState) -> dict:
        pseudo = _make_pseudo_agent_state(state)
        result = await agent.run(pseudo)

        output = result.get("output", "")
        new_messages = result.get("messages", [])
        if not new_messages:
            new_messages = [AIMessage(content=output)]

        return {
            "messages": new_messages,
        }

    chain_node.__name__ = f"chain_{name}"
    return chain_node


def _make_aggregator_node(llm: BaseChatModel):
    """統合ノード — 全発言を読んで要約を生成"""
    async def aggregator_node(state: DebateState) -> dict:
        # 直近の AI メッセージを収集して要約プロンプトを構築
        ai_contents = [
            m.content for m in state["messages"] if isinstance(m, AIMessage)
        ]
        summary_prompt = (
            "以下のエージェントたちの発言を読んで、議論の要点を日本語でまとめてください。\n\n"
            + "\n\n".join(ai_contents)
        )
        response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
        return {
            "messages": [AIMessage(content=response.content)],
        }

    return aggregator_node


# ===========================================================================
# Factory
# ===========================================================================

def build_debate_graph(
    participants: list[str],
    pattern: str,
    max_turns: int,
    agents: dict,
    llm: BaseChatModel,
    checkpointer=None,
) -> Any:
    """ターン制マルチエージェント会話グラフを構築して返す

    Args:
        participants: 参加エージェント名のリスト (2 <= N <= 10)
        pattern: "debate" | "chain" | "panel"
        max_turns: ターン数 (1 <= N <= 20)
        agents: エージェント名 -> エージェントインスタンスの dict
        llm: aggregator 用 LLM (BaseChatModel 互換)
        checkpointer: LangGraph checkpointer (省略可能)

    Returns:
        コンパイル済み LangGraph グラフ

    Raises:
        ValueError: participants 数または max_turns が範囲外

    Security:
        T-17-01: 入力値を先頭でバリデーション
    """
    # --- T-17-01: バリデーション ---
    if len(participants) < 2 or len(participants) > 10:
        raise ValueError(
            f"participants must be between 2 and 10, got {len(participants)}"
        )
    if max_turns < 1 or max_turns > 20:
        raise ValueError(
            f"max_turns must be between 1 and 20, got {max_turns}"
        )

    graph = StateGraph(DebateState)
    aggregator = _make_aggregator_node(llm)
    graph.add_node("aggregator", aggregator)

    if pattern == "chain":
        # chain パターン: A->B->C->...->aggregator->END
        for name in participants:
            node_name = f"agent_{name}"
            graph.add_node(node_name, _make_chain_node(name, agents[name]))

        # エントリポイント
        first_node = f"agent_{participants[0]}"
        graph.set_entry_point(first_node)

        # 線形チェーン
        for i in range(len(participants) - 1):
            src = f"agent_{participants[i]}"
            dst = f"agent_{participants[i + 1]}"
            graph.add_edge(src, dst)

        # 最後のエージェント -> aggregator -> END
        graph.add_edge(f"agent_{participants[-1]}", "aggregator")
        graph.add_edge("aggregator", END)

    else:
        # debate / panel パターン: ラウンドロビン dispatcher
        dispatch = _make_dispatch_node(agents, participants)
        graph.add_node("dispatcher", dispatch)
        graph.set_entry_point("dispatcher")

        def should_continue(state: DebateState) -> str:
            """ターン数に基づいてループ継続か集約かを判断

            - debate: max_turns 回の個別発言でループ終了
            - panel:  max_turns ラウンド × participants 数 = 総発言数でループ終了
            """
            n_participants = len(participants)
            if pattern == "panel":
                total_turns = state["max_turns"] * n_participants
            else:
                # debate: 1発言 = 1ターン
                total_turns = state["max_turns"]

            if state["turn"] >= total_turns:
                return "aggregator"
            return "dispatcher"

        graph.add_conditional_edges(
            "dispatcher",
            should_continue,
            {"dispatcher": "dispatcher", "aggregator": "aggregator"},
        )
        graph.add_edge("aggregator", END)

    return graph.compile(checkpointer=checkpointer)
