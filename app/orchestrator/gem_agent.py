from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from app.orchestrator.state import AgentState


class GemSubAgent:
    """Gem をプロンプトエージェントとして OrchestratorGraph に統合するラッパー。

    - SubAgent は継承しない（D-01）: SubAgent は from_dir() / ChatCopilot 生成ロジックを持つが
      GemSubAgent は DB から取得した system_prompt/knowledge を使うため不要。
    - keywords=[] 固定（D-03）: Stage-1 キーワードルーターをスキップし、
      常に Stage-2 LLM ルーターで評価される。
    - run() が返す AgentState は SubAgent と同一形式（D-05: graph.py 変更不要）。
    """

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        knowledge: str,
        llm: BaseChatModel,
    ) -> None:
        self.name = name
        self.description = description
        self.keywords: list[str] = []  # D-03: always empty → skips Stage-1
        self._llm = llm
        # D-02: system_prompt + knowledge を結合。knowledge が空なら system_prompt のみ
        self._full_prompt = (
            f"{system_prompt}\n\n{knowledge}" if knowledge else system_prompt
        )

    async def run(self, state: AgentState) -> AgentState:
        """D-04: BaseChatModel.ainvoke で応答を生成する。"""
        messages = [
            SystemMessage(content=self._full_prompt),
            HumanMessage(content=state["input"]),
        ]
        response = await self._llm.ainvoke(messages)
        return {
            "output": response.content,
            "messages": [AIMessage(content=response.content)],
        }

    async def close(self) -> None:
        """SubAgentRegistry.close() との互換のための no-op。
        llm の lifecycle は OrchestratorHandler が管理するため、ここでは何もしない。
        """
        pass
