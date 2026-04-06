"""
tests/test_debate_graph.py

DebateGraph のユニットテスト (TDD)
- debate/chain/panel 3 パターン
- 再エンキュー（同一 thread_id への 2 回目 ainvoke）
- participants バリデーション
- _make_pseudo_agent_state 構造確認
"""
from __future__ import annotations

import operator
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Annotated

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver


# ===========================================================================
# Mock helpers
# ===========================================================================

def make_mock_agent(name: str) -> MagicMock:
    """固定文字列を返すモックエージェント"""
    agent = MagicMock()
    agent.name = name

    async def fake_run(state: dict) -> dict:
        return {"output": f"[{name}] response", "messages": [AIMessage(content=f"[{name}] response")]}

    agent.run = fake_run
    return agent


def make_mock_llm(response_text: str = "aggregated summary") -> MagicMock:
    """固定文字列を返すモック LLM (BaseChatModel 互換)"""
    llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = response_text
    llm.ainvoke = AsyncMock(return_value=mock_response)
    return llm


# ===========================================================================
# Import under test (will fail until implementation exists)
# ===========================================================================

from app.orchestrator.debate_graph import build_debate_graph, DebateState, _make_pseudo_agent_state


# ===========================================================================
# Validation tests
# ===========================================================================

class TestValidation:
    def test_participants_less_than_2_raises_value_error(self):
        """1名以下の場合 ValueError を raise"""
        with pytest.raises(ValueError, match="participants"):
            build_debate_graph(
                participants=["A"],
                pattern="debate",
                max_turns=2,
                agents={"A": make_mock_agent("A")},
                llm=make_mock_llm(),
            )

    def test_zero_participants_raises_value_error(self):
        """0名の場合 ValueError を raise"""
        with pytest.raises(ValueError, match="participants"):
            build_debate_graph(
                participants=[],
                pattern="debate",
                max_turns=2,
                agents={},
                llm=make_mock_llm(),
            )

    def test_max_turns_zero_raises_value_error(self):
        """max_turns=0 の場合 ValueError を raise (T-17-01)"""
        with pytest.raises(ValueError, match="max_turns"):
            build_debate_graph(
                participants=["A", "B"],
                pattern="debate",
                max_turns=0,
                agents={"A": make_mock_agent("A"), "B": make_mock_agent("B")},
                llm=make_mock_llm(),
            )

    def test_max_turns_over_20_raises_value_error(self):
        """max_turns>20 の場合 ValueError を raise (T-17-01)"""
        with pytest.raises(ValueError, match="max_turns"):
            build_debate_graph(
                participants=["A", "B"],
                pattern="debate",
                max_turns=21,
                agents={"A": make_mock_agent("A"), "B": make_mock_agent("B")},
                llm=make_mock_llm(),
            )

    def test_participants_over_10_raises_value_error(self):
        """participants > 10 の場合 ValueError を raise (T-17-01)"""
        names = [f"Agent{i}" for i in range(11)]
        agents = {n: make_mock_agent(n) for n in names}
        with pytest.raises(ValueError, match="participants"):
            build_debate_graph(
                participants=names,
                pattern="debate",
                max_turns=2,
                agents=agents,
                llm=make_mock_llm(),
            )


# ===========================================================================
# _make_pseudo_agent_state tests
# ===========================================================================

class TestMakePseudoAgentState:
    def test_returns_dict_with_required_fields(self):
        """AgentState 互換フィールドを持つ dict を返す"""
        state: DebateState = {
            "turn": 1,
            "max_turns": 4,
            "pattern": "debate",
            "participants": ["A", "B"],
            "messages": [HumanMessage(content="hello")],
            "current_agent_idx": 0,
            "awaiting_extension": False,
        }
        result = _make_pseudo_agent_state(state)

        assert "input" in result
        assert "messages" in result
        assert "output" in result
        assert "next" in result
        assert "error" in result
        assert "context" in result

    def test_input_is_last_human_message_content(self):
        """input は最後の HumanMessage の content"""
        state: DebateState = {
            "turn": 0,
            "max_turns": 4,
            "pattern": "debate",
            "participants": ["A", "B"],
            "messages": [HumanMessage(content="topic question")],
            "current_agent_idx": 0,
            "awaiting_extension": False,
        }
        result = _make_pseudo_agent_state(state)
        assert result["input"] == "topic question"

    def test_input_falls_back_to_empty_string_when_no_human_message(self):
        """HumanMessage がない場合 input は空文字列"""
        state: DebateState = {
            "turn": 1,
            "max_turns": 4,
            "pattern": "debate",
            "participants": ["A", "B"],
            "messages": [AIMessage(content="something")],
            "current_agent_idx": 0,
            "awaiting_extension": False,
        }
        result = _make_pseudo_agent_state(state)
        assert result["input"] == ""


# ===========================================================================
# debate pattern tests
# ===========================================================================

class TestDebatePattern:
    @pytest.mark.asyncio
    async def test_debate_2_participants_max_turns_4_produces_correct_messages(self):
        """
        2 participants ["A", "B"], max_turns=4 =>
        A,B,A,B の順に 4 回発言後 aggregator が 1 回発言。
        messages 内の AIMessage 数 = 5
        """
        agent_a = make_mock_agent("A")
        agent_b = make_mock_agent("B")
        llm = make_mock_llm("final summary")

        graph = build_debate_graph(
            participants=["A", "B"],
            pattern="debate",
            max_turns=4,
            agents={"A": agent_a, "B": agent_b},
            llm=llm,
        )

        config = {"configurable": {"thread_id": "test-debate-4"}}
        result = await graph.ainvoke(
            {
                "turn": 0,
                "max_turns": 4,
                "pattern": "debate",
                "participants": ["A", "B"],
                "messages": [HumanMessage(content="Should AI be regulated?")],
                "current_agent_idx": 0,
                "awaiting_extension": False,
            },
            config=config,
        )

        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        # 4 turns (A,B,A,B) + 1 aggregator = 5
        assert len(ai_messages) == 5, f"Expected 5 AI messages, got {len(ai_messages)}: {ai_messages}"

    @pytest.mark.asyncio
    async def test_debate_max_turns_2_stops_at_2_then_aggregates(self):
        """
        max_turns=2 => 2 回の発言後 aggregator が呼ばれて END
        AIMessage 数 = 3 (A, B, aggregator)
        """
        agent_a = make_mock_agent("A")
        agent_b = make_mock_agent("B")
        llm = make_mock_llm("summary of 2 turns")

        graph = build_debate_graph(
            participants=["A", "B"],
            pattern="debate",
            max_turns=2,
            agents={"A": agent_a, "B": agent_b},
            llm=llm,
        )

        config = {"configurable": {"thread_id": "test-debate-2"}}
        result = await graph.ainvoke(
            {
                "turn": 0,
                "max_turns": 2,
                "pattern": "debate",
                "participants": ["A", "B"],
                "messages": [HumanMessage(content="topic")],
                "current_agent_idx": 0,
                "awaiting_extension": False,
            },
            config=config,
        )

        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        # 2 turns (A, B) + 1 aggregator = 3
        assert len(ai_messages) == 3, f"Expected 3 AI messages, got {len(ai_messages)}"


# ===========================================================================
# chain pattern tests
# ===========================================================================

class TestChainPattern:
    @pytest.mark.asyncio
    async def test_chain_3_participants_produces_4_ai_messages(self):
        """
        3 participants ["A","B","C"], pattern="chain" =>
        A->B->C の順に 1 回ずつ発言後 aggregator。計 4 AI メッセージ
        """
        agents = {name: make_mock_agent(name) for name in ["A", "B", "C"]}
        llm = make_mock_llm("chain summary")

        graph = build_debate_graph(
            participants=["A", "B", "C"],
            pattern="chain",
            max_turns=1,
            agents=agents,
            llm=llm,
        )

        config = {"configurable": {"thread_id": "test-chain-3"}}
        result = await graph.ainvoke(
            {
                "turn": 0,
                "max_turns": 1,
                "pattern": "chain",
                "participants": ["A", "B", "C"],
                "messages": [HumanMessage(content="chain topic")],
                "current_agent_idx": 0,
                "awaiting_extension": False,
            },
            config=config,
        )

        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        # A, B, C + aggregator = 4
        assert len(ai_messages) == 4, f"Expected 4 AI messages, got {len(ai_messages)}"


# ===========================================================================
# panel pattern tests
# ===========================================================================

class TestPanelPattern:
    @pytest.mark.asyncio
    async def test_panel_3_participants_max_turns_3_produces_10_ai_messages(self):
        """
        3 participants, pattern="panel", max_turns=3 =>
        A,B,C,A,B,C,A,B,C の順に 9 回発言後 aggregator。計 10 AI メッセージ
        """
        agents = {name: make_mock_agent(name) for name in ["A", "B", "C"]}
        llm = make_mock_llm("panel summary")

        graph = build_debate_graph(
            participants=["A", "B", "C"],
            pattern="panel",
            max_turns=3,
            agents=agents,
            llm=llm,
        )

        config = {"configurable": {"thread_id": "test-panel-3"}}
        result = await graph.ainvoke(
            {
                "turn": 0,
                "max_turns": 3,
                "pattern": "panel",
                "participants": ["A", "B", "C"],
                "messages": [HumanMessage(content="panel topic")],
                "current_agent_idx": 0,
                "awaiting_extension": False,
            },
            config=config,
        )

        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        # 3 turns * 3 participants = 9 + 1 aggregator = 10
        assert len(ai_messages) == 10, f"Expected 10 AI messages, got {len(ai_messages)}"


# ===========================================================================
# Re-enqueue (continuation) tests
# ===========================================================================

class TestReEnqueue:
    @pytest.mark.asyncio
    async def test_same_thread_id_continues_from_previous_state(self):
        """
        debate max_turns=2 実行後、同一 thread_id で max_turns=4 を渡すと
        ターン 2 から再開して total AIMessage 数が増える
        """
        agents = {name: make_mock_agent(name) for name in ["A", "B"]}
        llm = make_mock_llm("extended summary")
        checkpointer = MemorySaver()

        graph = build_debate_graph(
            participants=["A", "B"],
            pattern="debate",
            max_turns=2,
            agents=agents,
            llm=llm,
            checkpointer=checkpointer,
        )

        thread_id = "test-reenqueue-same"
        config = {"configurable": {"thread_id": thread_id}}

        # 1st invoke: max_turns=2
        result1 = await graph.ainvoke(
            {
                "turn": 0,
                "max_turns": 2,
                "pattern": "debate",
                "participants": ["A", "B"],
                "messages": [HumanMessage(content="initial topic")],
                "current_agent_idx": 0,
                "awaiting_extension": False,
            },
            config=config,
        )

        ai_after_first = [m for m in result1["messages"] if isinstance(m, AIMessage)]

        # 2nd invoke: max_turns=4, turn=2 (continuation)
        result2 = await graph.ainvoke(
            {
                "turn": 2,
                "max_turns": 4,
                "pattern": "debate",
                "participants": ["A", "B"],
                "messages": [],
                "current_agent_idx": 0,
                "awaiting_extension": False,
            },
            config=config,
        )

        ai_after_second = [m for m in result2["messages"] if isinstance(m, AIMessage)]

        # 2nd invoke should produce more AI messages than 1st
        assert len(ai_after_second) > len(ai_after_first), (
            f"Re-enqueue should produce more messages. "
            f"1st: {len(ai_after_first)}, 2nd: {len(ai_after_second)}"
        )
