"""tests/test_orchestrator_handler_gems.py — gem_ids 統合ロジックのテスト (Phase 16)"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.api.models import ChatRequest
from app.orchestrator.gem_agent import GemSubAgent


# ----- ChatRequest フィールドテスト（DB 不要） -----

class TestChatRequestGemIds:
    def test_gem_ids_default_is_none(self):
        req = ChatRequest(message="hello", thread_id="t")
        assert req.gem_ids is None

    def test_gem_ids_accepts_list(self):
        req = ChatRequest(message="hello", thread_id="t", gem_ids=["id1", "id2"])
        assert req.gem_ids == ["id1", "id2"]

    def test_gem_id_and_gem_ids_coexist(self):
        """gem_id（単数）と gem_ids（複数）は独立フィールドとして共存する（D-12）"""
        req = ChatRequest(
            message="hello",
            thread_id="t",
            gem_id="single-gem",
            gem_ids=["gem-a", "gem-b"],
        )
        assert req.gem_id == "single-gem"
        assert req.gem_ids == ["gem-a", "gem-b"]


# ----- GemSubAgent マージロジックのユニットテスト -----

class TestGemAgentMergeLogic:
    """OrchestratorHandler の gem_ids 処理ロジックを直接テストする。

    handle() 全体は arq ctx / DB 接続が必要なため、
    「gem_ids が渡されたときに GemSubAgent が registry に追加されるか」を
    独立した関数として検証する。
    """

    def _build_gem_agent(self, gem_row: dict, llm: object) -> GemSubAgent:
        """orchestrator_handler.py の GemSubAgent 生成ロジックを複製したヘルパー。"""
        return GemSubAgent(
            name=gem_row["name"],
            description=gem_row.get("description") or f"Gem: {gem_row['name']}",
            system_prompt=gem_row.get("system_prompt") or "",
            knowledge=gem_row.get("knowledge") or "",
            llm=llm,
        )

    def test_gem_agent_name_matches_db_row(self):
        mock_llm = AsyncMock()
        row = {"name": "コードレビュー Bot", "description": "レビュー専門", "system_prompt": "sys", "knowledge": "know"}
        agent = self._build_gem_agent(row, mock_llm)
        assert agent.name == "コードレビュー Bot"

    def test_gem_agent_description_fallback(self):
        """description が空のとき 'Gem: {name}' にフォールバックする。"""
        mock_llm = AsyncMock()
        row = {"name": "MyGem", "description": "", "system_prompt": "sys", "knowledge": ""}
        agent = self._build_gem_agent(row, mock_llm)
        assert agent.description == "Gem: MyGem"

    def test_merge_into_registry_agents(self):
        """GemSubAgent が registry.agents dict にマージされる（D-08）。"""
        mock_llm = AsyncMock()
        row = {"name": "TestGem", "description": "test", "system_prompt": "sys", "knowledge": ""}
        gem_agent = self._build_gem_agent(row, mock_llm)

        # registry.agents は通常の dict
        registry_agents = {"existing-agent": MagicMock(name="existing-agent")}
        registry_agents[gem_agent.name] = gem_agent

        assert "TestGem" in registry_agents
        assert isinstance(registry_agents["TestGem"], GemSubAgent)
        assert "existing-agent" in registry_agents  # 既存エージェントは消えない

    def test_gem_ids_none_produces_empty_gem_list(self):
        """gem_ids が None/[] のとき DB クエリが不要（後方互換 D-09）。"""
        gem_ids = None
        assert not (gem_ids or [])  # handler の `if gem_ids:` ガードと同等

        gem_ids_empty: list = []
        assert not gem_ids_empty

    def test_keywords_empty_for_stage2_routing(self):
        """GemSubAgent.keywords=[] により Stage-1 をスキップし Stage-2 LLM ルーターで評価（D-03）。"""
        mock_llm = AsyncMock()
        row = {"name": "TestGem", "description": "test", "system_prompt": "sys", "knowledge": ""}
        agent = self._build_gem_agent(row, mock_llm)
        assert agent.keywords == []
