# フェーズ1実装仕様：オーケストレータ + サブエージェント 最小構成

> **スコープ**：「ルーターがエージェントを選んでそいつがLLMを呼ぶ」動作確認。
> RPCContext・Fallback・スコープ隔離・ライフサイクルフックは対象外。

---

## 1. ゴール

以下が動くことを確認する：

```
input: "このコードをレビューして"
  └─ OrchestratorGraph
       └─ RouterNode → "code-reviewer"
            └─ SubAgent(code-reviewer) → LLM呼び出し → output
```

---

## 2. ディレクトリ構成

```
project/
  agents/
    code-reviewer/
      AGENT.md
      rules.md
    sql-analyst/
      AGENT.md
  menus/
    super-chat.yaml
    simple-chat.yaml
  src/
    agent.py          # SubAgent, SubAgentRegistry
    graph.py          # OrchestratorGraph, RouterNode, SimpleGraph
    dispatcher.py     # MenuDispatcher
    state.py          # AgentState
    main.py           # エントリーポイント
  pyproject.toml
```

---

## 3. AGENT.md フォーマット（最小版）

フェーズ1で使うフィールドのみ：

```yaml
---
name: code-reviewer
description: |
  Python/JavaScript/TypeScript コードの静的解析・リント・フォーマットチェックを行う。
  入力: コードスニペットまたはファイルパス
  出力: 指摘リストと修正提案
  対象外: テスト実行 / デプロイ / DB操作
model: claude-opus-4-6
---

あなたは厳格なコードレビュアーです。
指摘は重大度（error/warning/info）付きで箇条書きにしてください。
```

- frontmatter（`---` 区切り）がメタデータ
- frontmatter 以降の本文が system prompt
- `files` / `tools` / `lifecycle` はフェーズ1では使わない

---

## 4. AgentState

```python
# src/state.py
from __future__ import annotations
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
```

---

## 5. SubAgent / SubAgentRegistry

```python
# src/agent.py
from __future__ import annotations
import frontmatter
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from state import AgentState


class SubAgent:
    def __init__(self, name: str, description: str, model: str, system_prompt: str):
        self.name = name
        self.description = description
        self._llm = ChatAnthropic(model=model)
        self._system_prompt = system_prompt

    @classmethod
    def from_dir(cls, agent_dir: Path) -> "SubAgent":
        post = frontmatter.load(agent_dir / "AGENT.md")
        meta = post.metadata
        return cls(
            name=meta["name"],
            description=meta["description"],
            model=meta.get("model", "claude-sonnet-4-6"),
            system_prompt=post.content,
        )

    def run(self, state: AgentState) -> AgentState:
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=state["input"]),
        ]
        response = self._llm.invoke(messages)
        return {
            "output": response.content,
            "messages": [AIMessage(content=response.content)],
        }


class SubAgentRegistry:
    def __init__(self, agent_dir: str):
        self.agents: dict[str, SubAgent] = {}
        for path in Path(agent_dir).glob("**/AGENT.md"):
            agent = SubAgent.from_dir(path.parent)
            self.agents[agent.name] = agent
            print(f"[registry] loaded: {agent.name}")

    def get(self, name: str) -> SubAgent:
        return self.agents[name]

    def all(self) -> list[SubAgent]:
        return list(self.agents.values())
```

---

## 6. RouterNode / OrchestratorGraph

```python
# src/graph.py
from __future__ import annotations
from langchain_anthropic import ChatAnthropic
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
        self._llm = ChatAnthropic(model="claude-haiku-4-5-20251001")  # ルーターは軽量モデル

    def __call__(self, state: AgentState) -> AgentState:
        agents = self._registry.all()
        descriptions = "\n\n".join(
            f"name: {a.name}\ndescription: {a.description}"
            for a in agents
        )
        messages = [
            SystemMessage(content=ROUTER_PROMPT.format(agent_descriptions=descriptions)),
            HumanMessage(content=state["input"]),
        ]
        response = self._llm.invoke(messages)
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


def build_orchestrator_graph(registry: SubAgentRegistry) -> any:
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


def build_simple_graph() -> any:
    """チャットモード用：LLM 1発"""
    from langchain_core.messages import HumanMessage

    def simple_node(state: AgentState) -> AgentState:
        llm = ChatAnthropic(model="claude-sonnet-4-6")
        response = llm.invoke([HumanMessage(content=state["input"])])
        return {"output": response.content, "messages": []}

    graph = StateGraph(AgentState)
    graph.add_node("llm", simple_node)
    graph.set_entry_point("llm")
    graph.add_edge("llm", END)
    return graph.compile()
```

---

## 7. MenuDispatcher

```python
# src/dispatcher.py
from __future__ import annotations
import yaml
from pathlib import Path
from state import AgentState


class MenuRegistry:
    def __init__(self, menu_dir: str):
        self.menus: dict[str, dict] = {}
        for path in Path(menu_dir).glob("*.yaml"):
            menu = yaml.safe_load(path.read_text())
            if menu.get("enabled", True):
                self.menus[menu["name"]] = menu

    def get_graph(self, name: str) -> str:
        return self.menus[name]["graph"]


class MenuDispatcher:
    def __init__(self, menu_registry: MenuRegistry, graphs: dict):
        self.menu_registry = menu_registry
        self.graphs = graphs

    def dispatch(self, user_input: str, mode: str) -> str:
        graph_name = self.menu_registry.get_graph(mode)
        graph = self.graphs[graph_name]
        initial: AgentState = {
            "input": user_input,
            "output": "",
            "messages": [],
            "next": "",
        }
        result = graph.invoke(initial)
        return result["output"]
```

---

## 8. メニュー定義ファイル

```yaml
# menus/super-chat.yaml
name: super-chat
label: "🚀 スーパーチャット"
description: "複数エージェントを使った高度なタスク処理"
graph: orchestrator
enabled: true
```

```yaml
# menus/simple-chat.yaml
name: simple-chat
label: "💬 チャット"
description: "シンプルな1対1の会話"
graph: simple
enabled: true
```

---

## 9. エントリーポイント

```python
# src/main.py
import os
from agent import SubAgentRegistry
from graph import build_orchestrator_graph, build_simple_graph
from dispatcher import MenuDispatcher, MenuRegistry


def main():
    registry = SubAgentRegistry("./agents")
    graphs = {
        "orchestrator": build_orchestrator_graph(registry),
        "simple":       build_simple_graph(),
    }
    dispatcher = MenuDispatcher(MenuRegistry("./menus"), graphs)

    # 動作確認
    cases = [
        ("simple-chat",  "Pythonのリスト内包表記を説明して"),
        ("super-chat",   "このコードをレビューして: def f(x): return x*x"),
        ("super-chat",   "SELECT * FROM usersのパフォーマンスを改善したい"),
        ("super-chat",   "今日の天気は？"),   # fallback を確認
    ]

    for mode, user_input in cases:
        print(f"\n{'='*60}")
        print(f"mode: {mode}")
        print(f"input: {user_input}")
        print(f"---")
        output = dispatcher.dispatch(user_input, mode)
        print(f"output: {output[:200]}...")


if __name__ == "__main__":
    main()
```

---

## 10. 依存パッケージ

```toml
# pyproject.toml（uv 前提）
[project]
name = "uaw-phase1"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "langchain-anthropic",
    "langgraph",
    "python-frontmatter",
    "pyyaml",
]
```

```bash
uv sync
ANTHROPIC_API_KEY=sk-... uv run python src/main.py
```

---

## 11. 確認ポイント

| 確認項目 | 期待動作 |
|---------|---------|
| ルーティングログ | `[router] 'このコードをレビューして' → code-reviewer` |
| サブエージェント実行 | code-reviewer の system prompt でLLMが応答する |
| fallback | 対応エージェントなしの入力で fallback_node が動く |
| simple-chat | ルーターを通らず直接LLMが応答する |

---

## 12. フェーズ2以降への移行パス

フェーズ1が動いたら以下を順番に追加する：

| フェーズ | 追加内容 | トリガー |
|---------|---------|---------|
| 2 | RPCContext + AgentState統合（ch17） | マルチユーザー対応が必要になったとき |
| 3 | エラーハンドリング強化（ch18） | エージェントが3つ以上になったとき |
| 4 | descriptionの規約lint + ルーティングログ（ch19） | ミスルーティングが気になり始めたとき |
| 5 | input_schema標準化（ch20） | ツールを実装し始めたとき |

---

*（フェーズ1：動かして確認する。設計の核心の検証が目的。）*
