"""CodeActSubAgent — Python コード生成→直接実行エージェント。

LLM にコードを書かせ、execute_python MCP ツールで直接実行する。
MCP ツール（web_search, db_query 等）は Python コード内から mcp_helper
モジュール経由で呼び出す。

フロー:
1. LLM がユーザー要求に応える Python コードを生成（```python ブロック）
2. agent が execute_python を直接呼び出し
3. エラーなら LLM にフィードバックしてリトライ
4. 成功なら LLM がコード＋結果をまとめて最終回答

AGENT.md に `agent_type: codeact` を指定すると SubAgentRegistry がこのクラスを使う。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.utils.system_prompt import build_system_prompt_prefix
from app.providers.copilot import ChatCopilot
from app.orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _normalize_tool_result(result: Any) -> str:
    """MCP ツールの戻り値を文字列に正規化する。"""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and "text" in item:
                return item["text"]
            text = getattr(item, "text", None)
            if text:
                return text
        return str(result)
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)
    text = getattr(result, "text", None)
    if text:
        return text
    return str(result)


def _extract_code(text: str) -> str | None:
    """テキストから Python コードブロックを抽出する。"""
    matches = re.findall(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if matches:
        return "\n\n".join(m.strip() for m in matches if m.strip())
    matches = re.findall(r"```\s*\n(.*?)```", text, re.DOTALL)
    for m in matches:
        code = m.strip()
        if code and any(kw in code for kw in ("import ", "def ", "print(", "for ", "class ")):
            return code
    return None


def _looks_like_markdown(text: str) -> bool:
    """stdout が Markdown フォーマット（テーブル・見出し等）を含むか判定する。"""
    lines = text.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        # Markdown テーブル行: | col1 | col2 |
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 3:
            return True
        # Markdown 見出し: # Heading
        if re.match(r"^#{1,6}\s+\S", stripped):
            return True
    return False


def _parse_execute_result(raw: str) -> tuple[str, str, int]:
    """execute_python の結果をパースして (stdout, stderr, exit_code) を返す。"""
    try:
        data = json.loads(raw)
        return (data.get("stdout", ""), data.get("stderr", ""), data.get("exit_code", 0))
    except (json.JSONDecodeError, TypeError):
        return (raw, "", 0)


SUMMARY_PROMPT = """\
上記の実行結果をもとに、ユーザーの質問に分かりやすく回答してください。

ルール:
- 実行結果の生データをそのまま貼り付けない。必要な情報を抽出・整理して回答する
- データが複数項目ある場合は Markdown の表（| col1 | col2 |）を使う
- コードは既に表示済みなので繰り返さない
- 簡潔に、ユーザーが知りたいことに直接答える
"""


class CodeActSubAgent:
    """Python コード生成→直接実行エージェント。

    SubAgent / ToolEnabledSubAgent と同じインターフェース（name, description, run, close）を実装。
    """

    def __init__(
        self,
        name: str,
        description: str,
        model: str,
        system_prompt: str,
        github_token: str,
        tools: list[BaseTool],
        keywords: list[str] | None = None,
        max_iterations: int = 5,
    ):
        self.name = name
        self.description = description
        self.keywords: list[str] = keywords or []
        self.meta: dict[str, Any] = {}
        self._llm = ChatCopilot(model=model, github_token=github_token)
        self._system_prompt = system_prompt
        self._tools = {t.name: t for t in tools}
        self._max_iterations = max_iterations

    @classmethod
    def from_dir(
        cls,
        agent_dir: Path | str,
        github_token: str,
        tools: list[BaseTool] | None = None,
    ) -> "CodeActSubAgent":
        import frontmatter

        agent_dir = Path(agent_dir)
        post = frontmatter.load(agent_dir / "AGENT.md")
        meta = post.metadata
        instance = cls(
            name=meta["name"],
            description=meta["description"],
            model=meta.get("model", "gpt-4.1"),
            system_prompt=post.content,
            github_token=github_token,
            tools=tools or [],
            keywords=meta.get("keywords", []),
            max_iterations=meta.get("max_iterations", 5),
        )
        instance.meta = meta
        return instance

    async def run(self, state: AgentState) -> AgentState:
        """コード生成→実行→まとめのループを実行する。"""
        context = state.get("context")
        user_id = context.user_id if context and getattr(context, "user_id", None) not in (None, "unknown") else None
        base_system = build_system_prompt_prefix(user_id) + "\n\n" + self._system_prompt
        user_input = state["input"]

        execute_python = self._tools.get("execute_python")
        if not execute_python:
            # execute_python がない場合は通常の LLM 応答
            response = await self._llm.ainvoke([
                SystemMessage(content=base_system),
                HumanMessage(content=user_input),
            ])
            return {
                "output": response.content,
                "messages": [HumanMessage(content=user_input), AIMessage(content=response.content, name=self.name)],
                "agent_name": self.name,
            }

        messages: list[BaseMessage] = [
            SystemMessage(content=base_system),
            HumanMessage(content=user_input),
        ]

        # ツール実行のトレースを記録（最終出力に含める）
        trace_parts: list[str] = []

        for iteration in range(self._max_iterations):
            logger.info("[codeact] %s: iteration %d", self.name, iteration + 1)
            response = await self._llm.ainvoke(messages)
            content = response.content

            # Python コードブロックを検出 → execute_python
            code = _extract_code(content)
            if code:
                logger.info("[codeact] %s: executing python (%d chars)", self.name, len(code))

                # UI にツール実行中を通知
                from app.orchestrator.tool_context import tool_event_cb
                cb = tool_event_cb.get()
                if cb:
                    try:
                        await cb("execute_python", "")
                    except Exception:
                        pass

                try:
                    result = await execute_python.ainvoke({"code": code})
                    raw_result = _normalize_tool_result(result)
                except Exception as e:
                    raw_result = json.dumps({"stdout": "", "stderr": str(e), "exit_code": -1})

                stdout, stderr, exit_code = _parse_execute_result(raw_result)

                # トレースにコードのみ追加（stdout はまとめ LLM に渡すだけ、ユーザーには見せない）
                trace_parts.append(f"```python\n{code}\n```")
                if stderr:
                    trace_parts.append(f"**stderr:**\n```\n{stderr}\n```")

                # エラーの場合はリトライ用にフィードバック
                if exit_code != 0 and iteration < self._max_iterations - 1:
                    error_msg = stderr or stdout
                    messages.append(AIMessage(content=content, name=self.name))
                    messages.append(HumanMessage(
                        content=f"実行エラー (exit_code={exit_code}):\n```\n{error_msg}\n```\nエラーを修正したコードを書いてください。```python ブロックだけ返してください。"
                    ))
                    continue

                # 成功 → まとめを生成
                messages.append(AIMessage(content=content, name=self.name))
                messages.append(HumanMessage(
                    content=f"実行結果:\n```\n{stdout}\n```\n\n{SUMMARY_PROMPT}"
                ))
                summary = await self._llm.ainvoke(messages)
                trace_parts.append("---")
                trace_parts.append(summary.content)
                break

            # コードブロックなし → テキスト応答
            # 初回でコードなしの場合、コード生成を促す
            if iteration == 0 and not trace_parts:
                messages.append(AIMessage(content=content, name=self.name))
                messages.append(HumanMessage(
                    content="コードを書いて実行してください。```python ブロックでコードだけを返してください。説明は不要です。"
                ))
                continue

            # 2回目以降でコードなし → テキスト応答として終了
            trace_parts.append(content)
            break
        else:
            # max_iterations 到達
            trace_parts.append("(最大イテレーション数に到達しました)")

        output = "\n\n".join(trace_parts)

        return {
            "output": output,
            "messages": [
                HumanMessage(content=user_input),
                AIMessage(content=output, name=self.name),
            ],
            "agent_name": self.name,
        }

    async def close(self) -> None:
        await self._llm.close()
