"""Phase 24: MCP ツールカタログ + バリデーション (MCP-03).

D-03/D-04 per .planning/phases/24-config-yaml-tool-routing/24-CONTEXT.md.
config/mcp_tools.yaml で宣言したツール名と MCP サーバーが提供する実ツールリストの
完全一致を worker 起動時に検証する。不一致は RuntimeError で worker 起動を失敗させる。
"""
from __future__ import annotations

import yaml
from langchain_core.tools import BaseTool


class ToolRegistry:
    """MCP ツールカタログのバリデーションレジストリ。

    Usage:
        registry = ToolRegistry("config/mcp_tools.yaml")
        await registry.validate(mcp_tools)  # raises RuntimeError on mismatch
    """

    def __init__(self, yaml_path: str) -> None:
        with open(yaml_path) as f:
            cfg = yaml.safe_load(f) or {}
        entries = cfg.get("tools") or []
        self._expected: frozenset[str] = frozenset(
            entry["name"] for entry in entries
        )
        self._privileged: frozenset[str] = frozenset(
            entry["name"] for entry in entries if entry.get("privileged") is True
        )

    async def validate(self, mcp_tools: list[BaseTool]) -> None:
        """YAML カタログと MCP 実ツールリストを照合。不一致なら RuntimeError。

        D-03: 双方向チェック。
          - YAML にあるが MCP が提供しない → 起動失敗
          - MCP が提供するが YAML にない → 起動失敗
        """
        actual: frozenset[str] = frozenset(t.name for t in mcp_tools)
        missing = self._expected - actual
        extra = actual - self._expected
        if missing or extra:
            raise RuntimeError(
                "[ToolRegistry] mcp_tools.yaml と MCP サーバーのツールリストが不一致。"
                f" YAML のみ: {sorted(missing)}, MCP のみ: {sorted(extra)}"
            )

    def expected_tool_names(self) -> frozenset[str]:
        """YAML で宣言された期待ツール名集合を返す。"""
        return self._expected

    def privileged_tool_names(self) -> frozenset[str]:
        """`privileged: true` が付いたツール名集合を返す。

        privileged ツールは worker コンテナの FS 等への広範な権限を持つため、
        SubAgent が宣言した際は SubAgentRegistry が WARNING ログを出す。
        """
        return self._privileged
