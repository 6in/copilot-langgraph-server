# 0021. LangGraph bind_tools + ToolNode の実装: プロンプトエンジニアリング方式

**Date:** 2026-04-10
**Status:** Accepted

## Context

LangGraph の `ToolNode` は `AIMessage.tool_calls` フィールドに `ToolCall` オブジェクトが入っていることを前提とする。これは通常、LLM プロバイダーが OpenAI 互換の function calling API を持つことで実現される。

しかし本プロジェクトの `ChatCopilot` は GitHub Copilot SDK（Technical Preview）を JSON-RPC で呼び出す独自実装であり、OpenAI 互換の `tool_calls` レスポンスをネイティブに返す仕組みを持たない。そのため `llm.bind_tools([...])` を呼び出すと `NotImplementedError` が発生し、LangGraph の ReAct ループが成立しなかった。

また、エージェントに複数ツールを持たせて ReAct ループを実行するには、既存の `SubAgent` クラスに手を入れずに ToolNode 対応のエージェントを追加する構造が必要だった。既存の SuperChat ルーティングへの影響を最小化しながら、ツール有効エージェントと通常エージェントを共存させることが要件だった。

## Decision

### 1. bind_tools: プロンプトエンジニアリング方式（Approach A）

`ChatCopilot.bind_tools(tools)` を実装し、`BoundChatCopilot` サブクラスを返す。`BoundChatCopilot._agenerate()` はツール定義を JSON スキーマとしてシステムプロンプトに注入し、LLM レスポンスが `{"tool": "name", "args": {...}}` 形式の JSON であれば `AIMessage(tool_calls=[ToolCall(...)])` に変換して返す。

```
TOOL_SYSTEM_PROMPT_TEMPLATE:
  You have access to the following tools: {tool_schemas}
  To call a tool, respond ONLY with valid JSON: {"tool": "<tool_name>", "args": {...}}
  If no tool is needed, respond normally in plain text.
```

JSON パースは 2 段階: 直接パース → markdown コードフェンス除去後パース。`"tool"` キーの存在を必須チェック（ハルシネーション対策）。

### 2. ReAct グラフ: SubAgent 内部の mini ReAct グラフ

`ToolEnabledSubAgent` クラスを新規作成し、`run()` 内部に `build_react_graph()` で構築した mini LangGraph StateGraph（`agent → tools_condition → ToolNode → agent → END`）を持つ。外側の `OrchestratorGraph` は変更しない。

- チェックポインタなし（mini グラフはステートレス、外側の SQLite チェックポインタが永続化を担う）
- `DEFAULT_RECURSION_LIMIT = 25`（10 ループ × 2 ノード + バッファ）で DoS 対策
- `GraphRecursionError` をキャッチして部分結果を返す（ジョブ失敗にしない）

### 3. SubAgentRegistry の tools フラグ対応

`SubAgentRegistry.__init__` に `mcp_tools: list | None = None` を追加。AGENT.md frontmatter の `tools: [...]` リストと `mcp_tools` を照合し、一致するツールがあれば `ToolEnabledSubAgent`、なければ従来の `SubAgent` を生成する。後方互換性を維持。

### 4. 循環インポートの回避

`ToolEnabledSubAgent` を `app/orchestrator/tool_agent.py` に独立実装し、`agent.py` とのモジュール相互参照を断った。`agent.py` が `tool_agent.py` を一方向にインポートする構成。

## Alternatives Considered

**Approach B: ChatOpenAI(base_url=...) で Copilot エンドポイントを叩く**
Copilot SDK は JSON-RPC 通信であり、OpenAI 互換 HTTP エンドポイントが存在しないため不可。

**SubAgent 継承でツール対応する**
`ToolEnabledSubAgent(SubAgent)` と書くと `agent.py` ↔ `tool_agent.py` の循環インポートが発生する。`from_dir()` ファクトリをコピーして独立実装する方が依存関係がシンプル。

**MagicMock(spec=BaseTool) でテストする**
`ToolNode` は `BaseTool.args_schema` を Pydantic で内省するため、`MagicMock` では再帰エラーが発生した。`@tool` デコレータで本物の `BaseTool` インスタンスを作る必要がある。

**send_and_wait を直接パッチするテスト**
`BoundChatCopilot` は `_agenerate()` を override しているため、SDK レイヤーの `send_and_wait` をパッチするより `_agenerate` を直接パッチする方が確実でシンプル。

## Consequences

**正の影響:**
- 既存の SuperChat ルーティング・通常 SubAgent に影響ゼロで tool-enabled エージェントを追加できる
- Copilot SDK のバージョンアップで native function calling が実装された場合、`BoundChatCopilot` 一箇所を差し替えるだけで全体が恩恵を受ける
- AGENT.md に `tools:` を追記するだけで SubAgentRegistry がツール有効化を判断するため、コード変更不要でエージェントを tool-enabled にできる

**注意点・落とし穴:**
- `BoundChatCopilot` の `_bound_tools` は `PrivateAttr` + `object.__setattr__` で初期化する。Pydantic v2 サブクラスで `__init__` の `super()` 呼び出し後に PrivateAttr を設定するには `object.__setattr__` が必要（通常の代入はエラー）
- `ToolNode` に渡すツールは `@tool` デコレータを使った実 `BaseTool` インスタンスでなければならない。`MagicMock(spec=BaseTool)` では `args_schema` の Pydantic 内省に失敗する
- プロンプト注入方式のため、Copilot モデルが JSON を返さず自然言語で答えた場合はツール呼び出しがスキップされる（通常の AIMessage として処理）。これは意図的な設計（フォールバック）
- `DEFAULT_RECURSION_LIMIT = 25` はノード単位（エッジ通過ごとにカウント）なので、ツール呼び出し上限は実質約 10 回
