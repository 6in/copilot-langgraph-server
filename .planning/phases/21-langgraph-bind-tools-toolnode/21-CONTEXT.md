# Phase 21 Context: LangGraph bind_tools + ToolNode 統合

**Phase:** 21
**Name:** LangGraph bind_tools + ToolNode 統合
**Date:** 2026-04-10
**Status:** Ready for planning

---

## Phase Goal

SubAgent が bind_tools + ToolNode の ReAct ループでツールを呼び出し、結果が会話履歴に残る。

**Success Criteria:**
1. `llm.bind_tools([...])` を呼んでも NotImplementedError が発生しない
2. tool-enabled SubAgent が Web 検索プロンプトに対してツール呼び出しを発火させ、end-to-end で結果を返す
3. ToolMessage が PostgreSQL チェックポイントに会話履歴として記録され、スレッド再開後も参照できる
4. tool_calls ループが 10 ステップを超えると自動停止し、部分結果を返す

---

## Canonical Refs

- `.planning/ROADMAP.md` — Phase 21 詳細定義（Goal, Success Criteria, Requirements）
- `.planning/REQUIREMENTS.md` — TOOL-01, TOOL-02, TOOL-03
- `app/providers/copilot.py` — ChatCopilot (bind_tools 実装対象)
- `app/orchestrator/agent.py` — SubAgent, SubAgentRegistry (ToolEnabledSubAgent 追加対象)
- `app/orchestrator/graph.py` — OrchestratorGraph (変更なし)
- `app/orchestrator/state.py` — AgentState (messages フィールドに ToolMessage が追加される)
- `mcp_server/tools/stubs.py` — Phase 20 スタブツール定義
- `scripts/test_mcp_tools.py` — MultiServerMCPClient の使用例

---

## Decisions

### 1. bind_tools の実装戦略: プロンプトエンジニアリング方式

**決定:** `ChatCopilot.bind_tools(tools)` はツール定義を JSON スキーマとしてシステムプロンプトに埋め込む。LLM レスポンスを JSON パースし、`AIMessage(tool_calls=[...])` を構築して返す。

**理由:**
- Copilot SDK は Technical Preview のため、OpenAI 互換の tool_calls をネイティブでサポートするか不明
- プロンプトエンジニアリング方式は SDK 非依存で確実に動作する
- SDK が将来ネイティブサポートした場合も、このレイヤーで切り替え可能

**実装仕様:**
- `bind_tools(tools)` は `BoundChatCopilot`（または `ChatCopilot` のサブクラス）を返す
- `_agenerate()` の前処理でシステムプロンプトに以下を注入:
  ```
  You have access to the following tools:
  {JSON schema list of tools}
  
  To call a tool, respond ONLY with valid JSON:
  {"tool": "<tool_name>", "args": {...}}
  
  If no tool is needed, respond normally.
  ```
- レスポンスが JSON なら `AIMessage(tool_calls=[ToolCall(name=..., args=..., id=...)])` に変換
- JSON でなければ通常の `AIMessage(content=...)` を返す（最終回答）

### 2. ReAct ループのアーキテクチャ: SubAgent 内部 mini ReAct グラフ

**決定:** `ToolEnabledSubAgent` クラスを新規作成し、`run()` 内部に LangGraph の mini ReAct グラフ（agent ↔ ToolNode ループ）を実装する。OrchestratorGraph は変更しない。

**理由:**
- 既存の OrchestratorGraph（Router → SubAgent → END）への影響を最小化
- tool-enabled でないエージェントに影響しない
- SubAgent 単位で ReAct ループの挙動（ステップ数制限など）を独立制御できる

**実装仕様:**
```
ToolEnabledSubAgent.run(state: AgentState):
  mini_graph = build_react_graph(llm_with_tools, tool_node, max_steps=10)
  result = await mini_graph.ainvoke({"messages": [SystemMessage, HumanMessage]})
  return AgentState(
      output=last_ai_message.content,
      messages=result["messages"],  # ToolMessage を含む全履歴
      agent_name=self.name,
  )
```

**mini ReAct グラフ構造:**
```
START → agent_node → (tool_calls あり?) → tool_node → agent_node
                   → (tool_calls なし) → END
```

**ステップ制限（TOOL-02）:** AgentState に `tool_step_count: int` を追加し、10 を超えたら tool_node を経由せず END へ遷移する条件エッジ、または LangGraph の `recursion_limit` を活用する。

### 3. ツール対応エージェントの識別: AGENT.md の `tools:` フラグ

**決定:** AGENT.md frontmatter に `tools:` リストを追加。SubAgentRegistry がこれを読み取り、tools あり → `ToolEnabledSubAgent`、なし → 従来の `SubAgent` を生成する。

**理由:**
- エージェントごとに使用するツールを宣言的に管理できる
- Phase 22/23 でツールを追加する際も AGENT.md を更新するだけで対応可能
- 不要なエージェント（RouterNode が使う LLM など）にツールコンテキストを渡さずに済む

**AGENT.md 例:**
```yaml
---
name: general-assistant
description: 汎用アシスタント
model: claude-sonnet-4-6
tools:
  - web_search_stub
  - ping
keywords:
  - 検索
---
```

**SubAgentRegistry の変更:**
- `from_dir()` で `meta.get("tools", [])` を読み取り
- tools が空リスト → 従来の `SubAgent` を生成（変更なし）
- tools が非空 → `ToolEnabledSubAgent(tools=["web_search_stub", ...])` を生成

**ツール名の解決:** `ToolEnabledSubAgent` 初期化時に MCP クライアントの tool_map からツール名でフィルタして `BaseTool` リストを組み立てる。

### 4. MCP クライアント接続管理: Worker 起動時 Singleton

**決定:** arq worker の起動処理（`on_startup`）で `MultiServerMCPClient` を初期化し、全タスクで共有する。

**理由:**
- 接続コストを最小化（ツール呼び出しのたびに接続しない）
- 200名規模での運用で接続数を抑制できる
- ネットワーク障害時の再接続ロジックは Worker の shutdown/restart で対応

**実装仕様:**
```python
# app/jobs/worker.py
async def startup(ctx):
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001") + "/mcp"
    mcp_client = MultiServerMCPClient({
        "copilot-tools": {
            "transport": "streamable_http",
            "url": mcp_url,
        }
    })
    ctx["mcp_tools"] = await mcp_client.get_tools()
    ctx["mcp_client"] = mcp_client

async def shutdown(ctx):
    # MCP client cleanup if needed
    pass
```

`process_chat` タスク内で `ctx["mcp_tools"]` を ToolEnabledSubAgent に渡す。

---

## Folded Todos

- **Integrate LangGraph tool calling with async worker execution** — Phase 21 の TOOL-01〜03 として実装。Worker 内での非同期ツール実行は MCP Singleton + ToolNode で対応。

---

## Deferred Ideas

- **Agent-Skills 統合** (`Investigate Agent-Skills integration mechanism`) — SKILL.md を LangGraph ツールとして登録する仕組みは Phase 21 スコープ外。Phase 24 以降で MCP ツールルーティングが確立した後に検討。
- **ストリーミングツール応答** — Copilot SDK Technical Preview では未対応（REQUIREMENTS.md に記載済み）
- **並列ツール実行** — 現時点は逐次ループ。並列化は v5.1 以降

---

## Architecture Impact

**変更するファイル:**
- `app/providers/copilot.py` — `bind_tools()` メソッド追加、`BoundChatCopilot` 実装
- `app/orchestrator/agent.py` — `ToolEnabledSubAgent` クラス追加、`SubAgentRegistry.from_dir()` 拡張
- `app/jobs/worker.py` — `startup()` に MCP client Singleton 初期化追加

**変更しないファイル:**
- `app/orchestrator/graph.py` — OrchestratorGraph は変更なし
- `app/orchestrator/state.py` — AgentState は変更なし（messages は既に `Annotated[list, operator.add]` で ToolMessage を受け入れる）
- `mcp_server/` — Phase 20 のスタブツールをそのまま使用

**新規ファイル候補:**
- `app/orchestrator/tool_agent.py` — ToolEnabledSubAgent と ReAct グラフビルダー（agent.py への追記でも可）
- `agents/general-assistant/AGENT.md` — `tools:` フラグを追加（既存ファイルを更新）

---

## Open Questions for Planner

1. **`bind_tools` の返り値型:** `ChatCopilot` を mutate して返すか、`BoundChatCopilot(ChatCopilot)` サブクラスを返すか → Planner に委ねる
2. **ステップ制限の実装方法:** `recursion_limit` 設定 vs `step_count` State フィールド → Planner が LangGraph ドキュメントを確認して判断
3. **mini ReAct グラフの checkpointer:** SubAgent 内部の mini グラフにはチェックポインターを使わない（OrchestratorGraph が外側で PostgreSQL に保存する）— この前提を Planner が確認すること
