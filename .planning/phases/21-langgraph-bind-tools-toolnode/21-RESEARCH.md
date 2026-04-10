# Phase 21: LangGraph bind_tools + ToolNode 統合 - Research

**Researched:** 2026-04-10
**Domain:** LangGraph ToolNode / langchain-core bind_tools / プロンプトエンジニアリング方式 tool_calls 生成
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: bind_tools の実装戦略: プロンプトエンジニアリング方式**
- `ChatCopilot.bind_tools(tools)` はツール定義を JSON スキーマとしてシステムプロンプトに埋め込む
- LLM レスポンスを JSON パースし、`AIMessage(tool_calls=[...])` を構築して返す
- `_agenerate()` の前処理でシステムプロンプトに注入:
  ```
  You have access to the following tools:
  {JSON schema list of tools}
  To call a tool, respond ONLY with valid JSON:
  {"tool": "<tool_name>", "args": {...}}
  If no tool is needed, respond normally.
  ```

**D-02: ReAct ループのアーキテクチャ: SubAgent 内部 mini ReAct グラフ**
- `ToolEnabledSubAgent` クラスを新規作成し、`run()` 内部に mini ReAct グラフを実装
- OrchestratorGraph は変更しない
- mini グラフ構造: `START → agent_node → (tool_calls あり?) → tool_node → agent_node → (なし) → END`
- ステップ制限: `recursion_limit` を活用（または `tool_step_count` State フィールド）

**D-03: ツール対応エージェントの識別: AGENT.md の `tools:` フラグ**
- AGENT.md frontmatter に `tools:` リストを追加
- SubAgentRegistry が tools あり → `ToolEnabledSubAgent`、なし → 従来の `SubAgent` を生成

**D-04: MCP クライアント接続管理: Worker 起動時 Singleton**
- arq worker `on_startup` で `MultiServerMCPClient` を初期化し、全タスクで共有
- `ctx["mcp_tools"]` を ToolEnabledSubAgent に渡す

### Claude's Discretion
- `bind_tools` の返り値型: `ChatCopilot` を mutate して返すか、`BoundChatCopilot(ChatCopilot)` サブクラスを返すか
- ステップ制限の実装方法: `recursion_limit` 設定 vs `step_count` State フィールド（Planner が LangGraph ドキュメントで確認して判断）
- mini ReAct グラフの checkpointer: SubAgent 内部の mini グラフにはチェックポインターを使わない（OrchestratorGraph が外側で PostgreSQL に保存する）

### Deferred Ideas (OUT OF SCOPE)
- Agent-Skills 統合（SKILL.md を LangGraph ツールとして登録）— Phase 24 以降
- ストリーミングツール応答 — Copilot SDK Technical Preview 未対応
- 並列ツール実行 — v5.1 以降
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TOOL-01 | OrchestratorGraph の SubAgent が `bind_tools` + `ToolNode` でツールを呼び出せる | ChatCopilot.bind_tools() 実装パターン、ToolNode + tools_condition API、mini ReAct グラフ構造を文書化 |
| TOOL-02 | tool_calls ループが最大 10 ステップで自動停止する | `recursion_limit` の設定方法（`config={"recursion_limit": 25}`）、GraphRecursionError ハンドリングを確認 |
| TOOL-03 | ツール呼び出し結果が `ToolMessage` として会話履歴に記録される | ToolMessage の構造・シリアライズ・AgentState messages への追加パターンを確認 |
</phase_requirements>

---

## Summary

Phase 21 は、プロンプトエンジニアリング方式でツール呼び出し機能を `ChatCopilot` に実装し、LangGraph の `ToolNode` を使った mini ReAct ループを `ToolEnabledSubAgent` に組み込む作業。Copilot SDK は OpenAI 互換の `function_calling` API を持たないため、LLM レスポンスを JSON パースして `AIMessage(tool_calls=[...])` を手動構築する方式を採用する（D-01 確定）。

現在インストールされているバージョン: `langgraph==1.1.6`、`langchain-core==1.2.26`。いずれも CLAUDE.md の要件（`langgraph>=1.1.4`、`langchain-core>=0.3.0`）を満たしている。`langchain-mcp-adapters>=0.2.2` は pyproject.toml に宣言済みだがローカル環境には未インストール（Docker 環境内でのみ利用可能）。

`ToolNode`、`tools_condition`、`GraphRecursionError` はすべて `langgraph.prebuilt` / `langgraph.errors` からインポート可能であることを確認。`ToolMessage` のシリアライズも `messages_to_dict` / `messages_from_dict` で完全に動作し、PostgreSQL チェックポインターで保存可能。

**Primary recommendation:** D-01 〜 D-04 の決定通りに実装する。`bind_tools` は `BoundChatCopilot` サブクラスを返す方式を採用し、mini ReAct グラフは `recursion_limit=25`（10 ループ × 2 ノード + バッファ）で上限を設定する。

---

## Standard Stack

### Core（確認済みバージョン）
| Library | Version (installed) | Purpose | Why Standard |
|---------|---------------------|---------|--------------|
| `langgraph` | 1.1.6 | mini ReAct グラフ、ToolNode、StateGraph | プロジェクト標準 AI オーケストレーター |
| `langchain-core` | 1.2.26 | BaseChatModel, ToolCall, ToolMessage, AIMessage | プロジェクト標準 LangChain 基盤 |
| `langchain-mcp-adapters` | >=0.2.2 (Docker) | MultiServerMCPClient.get_tools() | Phase 20 で採用済み |

### Key APIs（バージョン検証済み）
| API | Import Path | Verified |
|-----|-------------|---------|
| `ToolNode` | `from langgraph.prebuilt import ToolNode` | [VERIFIED: local install] |
| `tools_condition` | `from langgraph.prebuilt import tools_condition` | [VERIFIED: local install] |
| `GraphRecursionError` | `from langgraph.errors import GraphRecursionError` | [VERIFIED: local install] |
| `ToolCall` | `from langchain_core.messages.tool import ToolCall` | [VERIFIED: local install] |
| `InvalidToolCall` | `from langchain_core.messages.tool import InvalidToolCall` | [VERIFIED: local install] |
| `ToolMessage` | `from langchain_core.messages import ToolMessage` | [VERIFIED: local install] |

---

## Architecture Patterns

### Recommended Project Structure（変更ファイルのみ）
```
app/
├── providers/
│   └── copilot.py          # bind_tools() + BoundChatCopilot 追加
├── orchestrator/
│   ├── agent.py            # ToolEnabledSubAgent + SubAgentRegistry 拡張
│   └── tool_agent.py       # (オプション) ToolEnabledSubAgent 分離ファイル
├── jobs/
│   └── worker.py           # startup() に MCP Singleton 追加
agents/
└── general-assistant/
    └── AGENT.md            # tools: フラグ追加
```

### Pattern 1: BaseChatModel.bind_tools() の正しい実装

**What:** `BaseChatModel.bind_tools()` はデフォルトで `NotImplementedError` を raise する。`ChatCopilot` でオーバーライドし、`BoundChatCopilot` を返す。

**実装仕様（D-01 確定）:**

```python
# Source: langchain-core 1.2.26 BaseChatModel.bind_tools signature [VERIFIED: local install]
# from langchain_core.language_models.chat_models import BaseChatModel

import uuid
import json
from typing import Any, Callable, Sequence
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.messages.tool import ToolCall, InvalidToolCall
from langchain_core.runnables import Runnable

TOOL_SYSTEM_PROMPT_TEMPLATE = """\
You have access to the following tools:
{tool_schemas}

To call a tool, respond ONLY with valid JSON (no markdown, no explanation):
{{"tool": "<tool_name>", "args": {{...}}}}

If no tool is needed, respond normally in plain text.
"""

class BoundChatCopilot(ChatCopilot):
    """ChatCopilot with tool-calling via prompt engineering."""
    
    _bound_tools: list[BaseTool] = PrivateAttr(default_factory=list)
    
    def __init__(self, tools: list[BaseTool], **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_bound_tools', tools)
    
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        # Inject tool schemas into system prompt
        tool_schemas = json.dumps(
            [{"name": t.name, "description": t.description, 
              "parameters": t.get_input_jsonschema()} for t in self._bound_tools],
            ensure_ascii=False, indent=2
        )
        injected = SystemMessage(content=TOOL_SYSTEM_PROMPT_TEMPLATE.format(
            tool_schemas=tool_schemas
        ))
        augmented_messages = [injected] + list(messages)
        
        result = await super()._agenerate(augmented_messages, stop=stop, 
                                           run_manager=run_manager, **kwargs)
        
        # Parse response for tool call JSON
        content = result.generations[0].message.content
        try:
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict) and "tool" in parsed:
                tool_call = ToolCall(
                    name=parsed["tool"],
                    args=parsed.get("args", {}),
                    id=str(uuid.uuid4())[:8],
                )
                return ChatResult(generations=[
                    ChatGeneration(message=AIMessage(content="", tool_calls=[tool_call]))
                ])
        except (json.JSONDecodeError, KeyError):
            pass  # Normal text response
        return result


class ChatCopilot(BaseChatModel):
    # ... existing code ...
    
    def bind_tools(
        self,
        tools: Sequence[dict | type | Callable | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable:
        from langchain_core.tools import BaseTool as BT
        base_tools = [t for t in tools if isinstance(t, BT)]
        return BoundChatCopilot(
            tools=base_tools,
            model=self.model,
            github_token=self.github_token,
            auth_manager=self.auth_manager,
        )
```

**注意:** `BoundChatCopilot` は `ChatCopilot` のサブクラスとして `copilot.py` の末尾に追加する。`ChatCopilot` 自身に `_bound_tools` フィールドを持たせると Pydantic スキーマ汚染が起きるため、サブクラス分離が推奨 [ASSUMED: Pydantic v2 PrivateAttr の動作からの類推]。

### Pattern 2: mini ReAct グラフの構築

**What:** `ToolEnabledSubAgent.run()` 内部で LangGraph の mini StateGraph を構築し、`recursion_limit` で上限を設定する。

```python
# Source: langgraph 1.1.6 [VERIFIED: local install]
from typing import Annotated
import operator
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.errors import GraphRecursionError

class MiniReActState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


def build_react_graph(llm_with_tools, tool_node: ToolNode) -> Any:
    """mini ReAct グラフを構築して compile する（checkpointer なし）."""
    
    async def agent_node(state: MiniReActState) -> MiniReActState:
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}
    
    graph = StateGraph(MiniReActState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    
    return graph.compile()  # checkpointer なし（外側の OrchestratorGraph が担う）


class ToolEnabledSubAgent(SubAgent):
    def __init__(self, ..., tools: list[BaseTool]):
        super().__init__(...)
        self._tools = tools
        self._tool_node = ToolNode(tools)
        self._llm_with_tools = self._llm.bind_tools(tools)
    
    async def run(self, state: AgentState) -> AgentState:
        mini_graph = build_react_graph(self._llm_with_tools, self._tool_node)
        init_messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=state["input"]),
        ]
        try:
            result = await mini_graph.ainvoke(
                {"messages": init_messages},
                config={"recursion_limit": 25},  # 10 iterations × 2 nodes + buffer
            )
        except GraphRecursionError:
            # 上限超過: 最後の AIMessage を部分結果として返す
            result_messages = init_messages  # fallback
            # ... 最後の messages を取得して返す
        
        all_messages = result["messages"]
        last_ai = next(
            (m for m in reversed(all_messages) if isinstance(m, AIMessage)),
            AIMessage(content="(ツール呼び出しが上限に達しました)")
        )
        return {
            "output": last_ai.content,
            "messages": all_messages,  # ToolMessage を含む全履歴
            "agent_name": self.name,
        }
```

### Pattern 3: ToolNode の初期化と動作

**What:** `ToolNode` は `BaseTool` のリストを受け取り、`state["messages"][-1]` の `AIMessage.tool_calls` を見てツールを実行する。

```python
# Source: langgraph 1.1.6 ToolNode source [VERIFIED: local install]

from langgraph.prebuilt import ToolNode

tool_node = ToolNode(tools=[web_search_stub, ping])
# ToolNode は dict 入力 {"messages": [...]} を受け取り
# {"messages": [ToolMessage(...)]} を返す

# tools_condition は state["messages"][-1].tool_calls が空か否かを確認
# 空でなければ "tools"、空なら "__end__" を返す
```

**ToolNode の入出力:**
- 入力: `{"messages": [AIMessage(content="", tool_calls=[ToolCall(...)])]}` 
- 出力: `{"messages": [ToolMessage(content="result", tool_call_id="...", name="tool_name")]}`

### Pattern 4: Worker Singleton での MCP クライアント初期化

**What:** `worker.py` の `startup()` に `MultiServerMCPClient` 初期化を追加し、全タスクで `ctx["mcp_tools"]` を共有する。

```python
# Source: scripts/test_mcp_tools.py (Phase 20 実装済み) [VERIFIED: codebase grep]
# langchain-mcp-adapters>=0.2.2: async with パターン廃止、get_tools() を直接呼ぶ

from langchain_mcp_adapters.client import MultiServerMCPClient

async def startup(ctx: dict) -> None:
    # ... existing code ...
    
    # Phase 21: MCP client Singleton
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001") + "/mcp"
    mcp_client = MultiServerMCPClient({
        "copilot-tools": {
            "transport": "streamable_http",
            "url": mcp_url,
        }
    })
    ctx["mcp_tools"] = await mcp_client.get_tools()
    ctx["mcp_client"] = mcp_client
```

**注意:** MCP サーバーが起動していない場合に `startup()` が失敗するリスクがある。try/except でラップし、mcp_tools を空リストにして DEGRADED 状態で起動継続することを検討。

### Pattern 5: SubAgentRegistry の tools フラグ対応

**What:** `SubAgentRegistry` が AGENT.md の `tools:` フラグを読み取り、`ToolEnabledSubAgent` を生成する。

```python
# SubAgent.from_dir() の拡張
@classmethod
def from_dir(cls, agent_dir: Path, github_token: str, mcp_tools: list = None) -> "SubAgent":
    post = frontmatter.load(agent_dir / "AGENT.md")
    meta = post.metadata
    tools_list = meta.get("tools", [])
    
    if tools_list and mcp_tools:
        # ツール名でフィルタして BaseTool リストを組み立てる
        tool_map = {t.name: t for t in mcp_tools}
        selected_tools = [tool_map[name] for name in tools_list if name in tool_map]
        return ToolEnabledSubAgent(
            name=meta["name"],
            ...,
            tools=selected_tools,
        )
    return SubAgent(name=meta["name"], ...)
```

### Anti-Patterns to Avoid

- **`OrchestratorGraph` を変更する:** mini ReAct ループは `ToolEnabledSubAgent.run()` 内部に閉じ込める。外側グラフを変更しない（D-02 確定）
- **mini グラフに checkpointer を渡す:** mini グラフは `graph.compile()` のみで、`checkpointer` なし。OrchestratorGraph の外側 PostgreSQL チェックポインターが `messages` 全体を保存する
- **JSON パースの厳格化しすぎ:** LLM が `{"tool": "x", "args": {}}` 形式以外（マークダウンコードブロックで包む等）を返す可能性がある。`json.loads(content.strip().strip('` '))` 程度のクリーニングは必要

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ツール実行ループ | カスタム while ループ | `ToolNode` + `tools_condition` + `recursion_limit` | ToolNode は並列実行・エラーハンドリング・tool_call_id マッチングを内包 |
| ツール実行後のルーティング | 手動 if/else | `tools_condition` | `messages[-1].tool_calls` の有無を正しく確認する標準ルーター |
| ToolMessage シリアライズ | 手動 dict 変換 | LangGraph StateGraph の `operator.add` reducer | AgentState の `messages: Annotated[list[BaseMessage], operator.add]` が ToolMessage を自動蓄積 |
| 上限超過検知 | 手動カウンター | `GraphRecursionError` + `recursion_limit` config | LangGraph 組み込みの安全装置 |

**Key insight:** ToolNode は `AIMessage.tool_calls[*].id` と `ToolMessage.tool_call_id` の対応を自動管理する。手動で tool_call_id を追跡する必要はない。

---

## Common Pitfalls

### Pitfall 1: bind_tools がツールリストを渡さないまま ToolNode に渡す
**What goes wrong:** `ToolNode([])` は空ツールリストを受け入れるが、ツールが見つからない場合 `ToolMessage(content="Error: Tool 'xxx' not found", status="error")` を返してループが続く
**Why it happens:** MCP get_tools() の失敗やツール名フィルタのミスで空リストが渡る
**How to avoid:** `ToolEnabledSubAgent.__init__` でツールリストが空の場合は警告ログを出し、ツールなしの通常 SubAgent にフォールバックする

### Pitfall 2: JSON レスポンスのパース失敗で tool_calls を生成できない
**What goes wrong:** LLM が `{"tool": "web_search_stub", "args": {"query": "..."}}` ではなく `ここにツール呼び出し: {"tool": "..."}` のような混在テキストを返す
**Why it happens:** プロンプトエンジニアリング方式は LLM の遵守度に依存する
**How to avoid:** システムプロンプトに「JSON のみを返せ、他のテキストは含めるな」を強調。JSON 抽出を正規表現でフォールバック: `re.search(r'\{.*?\}', content, re.DOTALL)`
**Warning signs:** ToolNode が呼ばれず agent_node が繰り返し呼ばれる（tools_condition が常に `__end__` を返す）

### Pitfall 3: mini グラフに checkpointer を渡してしまう
**What goes wrong:** mini グラフが独自の checkpoint を作成し、OrchestratorGraph の thread_id との競合が起きる
**Why it happens:** `build_react_graph()` に checkpointer を渡し忘れ（渡してしまった場合）
**How to avoid:** `graph.compile()` のみ（checkpointer 引数なし）。`AgentState.messages` の `operator.add` reducer が ToolMessage を蓄積し、OrchestratorGraph の外側チェックポインターが保存する

### Pitfall 4: recursion_limit と実際のステップ数の計算ミス
**What goes wrong:** `recursion_limit=10` で 10 ループを期待すると、`agent_node` と `tool_node` で各 1 ステップ消費するため 5 ループしか回らない
**Why it happens:** recursion_limit はノード呼び出し回数（ステップ数）をカウント、ループ回数ではない
**How to avoid:** 10 ループ = 10 × (agent + tool) + 1 final_agent = 21 ステップ → `recursion_limit=25` が安全値

### Pitfall 5: worker.py startup での MCP クライアント初期化失敗
**What goes wrong:** MCP サーバーが未起動の状態で `get_tools()` を呼ぶとコネクションエラーが発生し、worker 全体が起動しない
**Why it happens:** Phase 20 のスモーク前提（mcp-server healthy 確認後）に依存している
**How to avoid:** `startup()` の MCP 初期化を try/except でラップ。失敗時は `ctx["mcp_tools"] = []` として DEGRADED 状態で継続。ToolEnabledSubAgent が tools=[] で初期化された場合は通常 SubAgent に降格

### Pitfall 6: ToolCall の `type` フィールドを省略する
**What goes wrong:** `ToolCall(name=..., args=..., id=...)` は `type` フィールドを自動補完するが、`dict` として手動構築する場合 `"type": "tool_call"` を忘れると ToolNode の parse で失敗する
**Why it happens:** `ToolCall` TypedDict には `type` フィールドがある（確認済み）
**How to avoid:** `ToolCall(name=..., args=..., id=...)` コンストラクタを使う（type は自動設定）。dict で構築する場合は `{"name": ..., "args": ..., "id": ..., "type": "tool_call"}` を明示

---

## Code Examples

### 完全な bind_tools → ToolNode → mini ReAct フロー

```python
# Source: langgraph 1.1.6 + langchain-core 1.2.26 [VERIFIED: local install]

# 1. ToolNode 初期化
from langgraph.prebuilt import ToolNode, tools_condition
tool_node = ToolNode(tools=[web_search_stub, ping])  # BaseTool リスト

# 2. LLM with tools
llm_with_tools = chat_copilot.bind_tools([web_search_stub, ping])
# → BoundChatCopilot を返す（プロンプト注入 + JSON パース内包）

# 3. mini ReAct グラフ
from langgraph.graph import StateGraph, END
from langgraph.errors import GraphRecursionError

graph = StateGraph(MiniReActState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")
compiled = graph.compile()  # checkpointer なし

# 4. 実行（recursion_limit で 10 ループ上限）
try:
    result = await compiled.ainvoke(
        {"messages": [SystemMessage(...), HumanMessage(...)]},
        config={"recursion_limit": 25},
    )
except GraphRecursionError:
    # 部分結果で返す
    pass
```

### AIMessage + ToolCall の手動構築

```python
# Source: langchain-core 1.2.26 [VERIFIED: local install]
import uuid
from langchain_core.messages import AIMessage
from langchain_core.messages.tool import ToolCall

tool_call = ToolCall(
    name="web_search_stub",
    args={"query": "LangGraph ToolNode"},
    id=str(uuid.uuid4())[:8],  # 短い ID で十分
)
msg = AIMessage(content="", tool_calls=[tool_call])
# msg.tool_calls は list[dict] として格納される（ToolNode が読む形式）
```

### ToolMessage のシリアライズ確認

```python
# Source: langchain-core 1.2.26 [VERIFIED: local install]
# ToolMessage は messages_to_dict / messages_from_dict でシリアライズ可能
# PostgreSQL チェックポインターが自動的に処理する

from langchain_core.messages import ToolMessage
tm = ToolMessage(
    content="search result",
    tool_call_id="call_abc123",
    name="web_search_stub",  # オプションだが推奨
)
# tm.type == "tool" → langgraph checkpoint serde が正しく識別する
```

### AGENT.md tools: フラグ例

```yaml
---
name: general-assistant
keywords: []
description: |
  汎用会話エージェント。...
  対象外: 専門エージェントが対応できる質問
model: claude-sonnet-4-6
tools:
  - web_search_stub
  - ping
---
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `async with MultiServerMCPClient(...) as client:` | `client = MultiServerMCPClient(...); tools = await client.get_tools()` | v0.2.2 | async context manager 廃止、直接 get_tools() 呼び出し |
| `MemorySaver` for mini graphs | checkpointer なし (外側グラフが担う) | 設計決定 (D-02) | mini グラフは stateless、OrchestratorGraph が PostgreSQL で永続化 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `BoundChatCopilot` を `ChatCopilot` のサブクラスとして実装することで Pydantic v2 の PrivateAttr が正しく機能する | Pattern 1 | ChatCopilot の `model_config = ConfigDict(arbitrary_types_allowed=True)` があるため低リスク。失敗した場合は `_bound_tools` を通常フィールドにする |
| A2 | MCP サーバーが worker startup 時に既に healthy である | Pattern 4 | Phase 20 の依存前提。失敗時の try/except で DEGRADED 運用は可能 |
| A3 | Copilot モデル（claude-sonnet-4-6）がシステムプロンプトの JSON 指示に従い `{"tool": "...", "args": {...}}` を返す確率が十分高い | Pattern 1 | D-01 で「スパイク検証必須」とされている。プロンプト設計の調整が必要な可能性あり |

---

## Open Questions

1. **`recursion_limit` 超過時の部分結果取得**
   - What we know: `GraphRecursionError` が raise される。`result["messages"]` は except 節では参照できない
   - What's unclear: except 節でそれまでの messages を取得する方法（`GraphRecursionError.state` フィールドがあるか？）
   - Recommendation: mini グラフの `astream()` を使い yield されたメッセージを蓄積する方式を検討。または try/except で `AIMessage(content="上限超過")` を返すシンプルフォールバック

2. **Copilot モデルの JSON 遵守率**
   - What we know: D-01 で「スパイク検証必須」とされている
   - What's unclear: `claude-sonnet-4-6` が JSON-only レスポンスをどの程度遵守するか
   - Recommendation: Plan 01 をスパイクタスクとし、最初に `general-assistant` + `web_search_stub` + `ping` で end-to-end 動作確認を行う

3. **`from_dir()` への `mcp_tools` 引数追加**
   - What we know: 現在の `from_dir(agent_dir, github_token)` に引数を追加する必要がある
   - What's unclear: `SubAgentRegistry` と `_load_code_agent()` の両方で引数シグネチャを変更する影響範囲
   - Recommendation: `mcp_tools: list = None` をオプション引数として追加し後方互換性を保つ

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `langgraph` | mini ReAct グラフ | ✓ | 1.1.6 | — |
| `langchain-core` | ToolCall, ToolMessage, bind_tools | ✓ | 1.2.26 | — |
| `langchain-mcp-adapters` | MultiServerMCPClient.get_tools() | ✗ (local) / ✓ (Docker) | >=0.2.2 | 空ツールリストで DEGRADED 動作 |
| MCP サーバー (mcp-server) | ツール取得 | ✓ (Phase 20 完了) | Phase 20 実装済み | startup() try/except で DEGRADED |
| PostgreSQL | ToolMessage 永続化 | ✓ | Phase 6 導入済み | — |

**Missing dependencies with no fallback:** なし

**Missing dependencies with fallback:**
- `langchain-mcp-adapters`: ローカル環境に未インストール。Docker 内では `pyproject.toml` の `langchain-mcp-adapters>=0.2.2` が解決される。テストはモックで対応

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]` asyncio_mode = "auto") |
| Quick run command | `uv run pytest tests/test_provider.py tests/test_orchestrator_graph.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-01 | `ChatCopilot.bind_tools([tools])` が `NotImplementedError` を raise しない | unit | `pytest tests/test_provider.py::test_bind_tools_returns_bound_model -x` | ❌ Wave 0 |
| TOOL-01 | `BoundChatCopilot._agenerate()` が JSON レスポンスを `AIMessage(tool_calls=[...])` に変換 | unit | `pytest tests/test_provider.py::test_bound_copilot_parses_tool_call_json -x` | ❌ Wave 0 |
| TOOL-01 | `ToolEnabledSubAgent.run()` が mini ReAct グラフを実行してツールを呼び出す | integration (mock) | `pytest tests/test_tool_agent.py::test_tool_enabled_subagent_runs_react_loop -x` | ❌ Wave 0 |
| TOOL-02 | `recursion_limit=25` で 10 ステップ超過時に `GraphRecursionError` が catch される | unit | `pytest tests/test_tool_agent.py::test_react_loop_stops_at_limit -x` | ❌ Wave 0 |
| TOOL-03 | `ToolMessage` が `AgentState.messages` に追加される | unit | `pytest tests/test_agent_state.py::test_tool_message_in_messages_state -x` | 既存ファイルに追加 |
| TOOL-03 | `ToolMessage` のシリアライズが `messages_to_dict` で正常動作 | unit | `pytest tests/test_agent_state.py::test_tool_message_serializable -x` | 既存ファイルに追加 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_provider.py tests/test_tool_agent.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_tool_agent.py` — ToolEnabledSubAgent, mini ReAct グラフ, recursion_limit テスト
- [ ] `tests/test_provider.py` への追加 — `test_bind_tools_returns_bound_model`, `test_bound_copilot_parses_tool_call_json`
- [ ] `tests/test_worker.py` への追加 — startup() MCP Singleton 初期化テスト（モック使用）

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | ToolNode の `_validate_tool_call()` が不明なツール名を `ToolMessage(status="error")` で処理 |
| V4 Access Control | yes | AGENT.md `tools:` フラグによるエージェント別ツール allowlist（完全制御は Phase 24） |

### Known Threat Patterns for ToolNode

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ツール名インジェクション（LLM が不正なツール名を生成） | Tampering | ToolNode の `_validate_tool_call()` が未登録ツール名をエラーとして処理 [VERIFIED: ToolNode source] |
| プロンプトインジェクション経由での任意ツール呼び出し | Tampering | Phase 21 のスタブツールは副作用なし。Phase 22/23 で実ツール導入時に慎重なプロンプト設計が必要 |
| args の未検証入力 | Tampering | `tool.get_input_jsonschema()` でスキーマ定義済み。ToolNode が pydantic バリデーションを通す |

---

## Sources

### Primary (HIGH confidence)
- `langgraph==1.1.6` ToolNode source (local inspect) — ToolNode 初期化, _parse_input, _validate_tool_call
- `langchain-core==1.2.26` BaseChatModel source (local inspect) — bind_tools シグネチャ
- `langchain-core==1.2.26` ToolCall, InvalidToolCall, ToolMessage (local import 確認)
- `langgraph.prebuilt.tools_condition` source (local inspect) — 完全なソースコード確認
- `langgraph.errors.GraphRecursionError` (local import 確認)
- `app/providers/copilot.py` (codebase read) — 現状の ChatCopilot 実装
- `app/orchestrator/agent.py` (codebase read) — SubAgent, SubAgentRegistry の現状
- `app/jobs/worker.py` (codebase read) — arq startup() の現状
- `scripts/test_mcp_tools.py` (codebase read) — MultiServerMCPClient.get_tools() パターン確認
- `tests/test_provider.py` (codebase read) — 既存テストパターン確認

### Secondary (MEDIUM confidence)
- `pyproject.toml` (codebase read) — 依存バージョン確認
- `mcp_server/tools/stubs.py` (codebase read) — スタブツール名・スキーマ確認

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ローカルインストールで全 API を直接確認
- Architecture: HIGH — ToolNode, tools_condition, AIMessage.tool_calls を実際のソースで確認
- Pitfalls: HIGH — ソースから直接導出（recursion_limit 計算、ToolNode validate ロジック）
- プロンプトエンジニアリング遵守率: LOW — スパイク未実施（D-01 で「スパイク検証必須」）

**Research date:** 2026-04-10
**Valid until:** 2026-05-10（langgraph は安定版 - 30日有効）
