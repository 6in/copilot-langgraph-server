"""tests/test_gem_agent.py — GemSubAgent ユニットテスト (Phase 16)"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from app.orchestrator.gem_agent import GemSubAgent


def make_agent(system_prompt: str = "あなたはアシスタントです", knowledge: str = "") -> tuple[GemSubAgent, AsyncMock]:
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(content="テスト応答")
    agent = GemSubAgent(
        name="test-gem",
        description="テスト Gem",
        system_prompt=system_prompt,
        knowledge=knowledge,
        llm=mock_llm,
    )
    return agent, mock_llm


def make_state(input_text: str = "質問です") -> dict:
    """最小限の AgentState を作る。"""
    return {
        "input": input_text,
        "output": "",
        "messages": [],
        "next": "",
        "context": None,
        "error": None,
    }


def test_keywords_always_empty():
    agent, _ = make_agent()
    assert agent.keywords == []


def test_name_and_description():
    agent, _ = make_agent()
    assert agent.name == "test-gem"
    assert agent.description == "テスト Gem"


def test_full_prompt_with_knowledge():
    """knowledge あり → system_prompt + '\\n\\n' + knowledge"""
    agent, _ = make_agent(system_prompt="sys", knowledge="know")
    assert agent._full_prompt == "sys\n\nknow"


def test_full_prompt_without_knowledge():
    """knowledge が空文字 → system_prompt のみ"""
    agent, _ = make_agent(system_prompt="sys", knowledge="")
    assert agent._full_prompt == "sys"


@pytest.mark.asyncio
async def test_run_returns_correct_state():
    agent, mock_llm = make_agent(system_prompt="sys", knowledge="know")
    state = make_state("質問です")

    result = await agent.run(state)

    assert result["output"] == "テスト応答"
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == "テスト応答"


@pytest.mark.asyncio
async def test_run_uses_combined_system_prompt():
    """run() が system_prompt + knowledge を結合してシステムプロンプトに使うこと"""
    agent, mock_llm = make_agent(system_prompt="システム", knowledge="ナレッジ")
    state = make_state("入力テキスト")

    await agent.run(state)

    # ainvoke に渡された messages を確認
    call_args = mock_llm.ainvoke.call_args
    messages = call_args[0][0]
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == "システム\n\nナレッジ"
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "入力テキスト"


@pytest.mark.asyncio
async def test_run_uses_system_prompt_only_when_no_knowledge():
    """knowledge なし → system_prompt のみがシステムプロンプトに使われること"""
    agent, mock_llm = make_agent(system_prompt="システムのみ", knowledge="")
    state = make_state("入力")

    await agent.run(state)

    call_args = mock_llm.ainvoke.call_args
    messages = call_args[0][0]
    assert messages[0].content == "システムのみ"


@pytest.mark.asyncio
async def test_close_is_noop():
    """close() が例外を投げないこと"""
    agent, _ = make_agent()
    await agent.close()  # 例外が出なければ PASS
