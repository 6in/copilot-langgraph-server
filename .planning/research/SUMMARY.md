# Project Research Summary

**Project:** Copilot LangGraph Chat
**Domain:** v5.0 Agent Tool Platform — FastMCP + LangGraph bind_tools 統合（既存プロジェクトへの追加マイルストーン）
**Researched:** 2026-04-09
**Confidence:** MEDIUM-HIGH（FastMCP/LangGraph 部分は HIGH; ChatCopilot bind_tools は LOW — 未実装のため実装前に検証必須）

---

## Executive Summary

v5.0 は既存の Copilot LangGraph Chat に MCP ベースのツール実行レイヤーを追加するマイルストーンである。中心的な変更は 3 点: (1) FastMCP 3.2.2 を Docker サービス（`mcp-server`）として追加し `streamable-http` transport で公開、(2) `langchain-mcp-adapters` の `MultiServerMCPClient` でワーカーからツールリストを取得、(3) `SubAgent.run()` を LangGraph `bind_tools` + `ToolNode` の ReAct ループに拡張する。既存の `OrchestratorGraph`・`RouterNode`・`AgentState`・全 API ルートは変更しない。追加されるツールは Web 検索（Tavily）、DB クエリ（PostgreSQL SELECT-only）、Claude Code CLI の 3 種で、YAML 設定ファイルでエージェントごとに許可するツールを制御する。

最大のリスクは `ChatCopilot.bind_tools()` が未実装である点だ。`BaseChatModel.bind_tools()` はデフォルトで `NotImplementedError` を投げるため、Phase 2（bind_tools 統合）の最初のタスクとして `copilot.py` に実装しなければならない。さらに Copilot SDK はプレーンテキストを返すため、LangGraph `ToolNode` が期待する構造化 `tool_calls` が生成されない。推奨アプローチはシステムプロンプトへのツールスキーマ注入 + `_agenerate` 内でのテキスト解析（Approach A）である。これにより PostgreSQL チェックポイントに完全なツール呼び出し履歴が残り、200 名規模の内部利用における監査要件を満たせる。

その他の注意点: `langchain-mcp-adapters` v0.1.0 で `async with MultiServerMCPClient(...) as client:` パターンが削除されたため、既存チュートリアルのコードは動かない。また `stdio` transport は Docker コンテナ間通信に使えないため `streamable-http` が必須。Claude Code CLI は `CLAUDECODE=1` 環境変数を継承すると即座に失敗するため、subprocess 起動時に env sanitization が必須となる。

---

## Key Findings

### 推奨スタック（v5.0 追加分）

既存スタック（Python 3.12 / FastAPI / LangGraph 1.1.3 / arq + Redis / PostgreSQL）への追加のみ。既存依存を変更しない。

**新規追加ライブラリ:**

| Technology | Version | Purpose |
|------------|---------|---------|
| `fastmcp` | 3.2.2 | MCP サーバー実装。`@mcp.tool` デコレータ、`streamable_http` transport |
| `langchain-mcp-adapters` | 0.2.2 | `MultiServerMCPClient` で MCP ツール → LangChain `BaseTool` 変換 |
| `tavily-python` | 0.5.x | `AsyncTavilyClient` による非同期 Web 検索 |
| `psycopg[binary]` | 3.x | DB クエリツール（既存ライブラリ、追加不要） |

**追加しないライブラリ:** `langchain` フルパッケージ（langchain-core で bind_tools / ToolNode は動く）、`mcp` 低レベルライブラリ（fastmcp が包含）、`requests` / `aiohttp`（httpx が既存）

**Transport:** `streamable-http` 一択。`stdio` は Docker コンテナ間通信不可、`sse` はセッションアフィニティ問題あり。

詳細は `.planning/research/STACK.md` を参照。

### v5.0 追加フィーチャー

**必須（Table Stakes）:**
1. **LangGraph bind_tools + ToolNode ReAct ループ** — SubAgent 内部に mini-graph（agent ↔ ToolNode ループ）を構築。外側の OrchestratorGraph 構造は変更しない。`recursion_limit=10`（最大 5 ツール呼び出しラウンド）。
2. **FastMCP Server（Docker サービス）** — `mcp_server/` ディレクトリに独立 Docker サービス。`@mcp.tool` デコレータでツール定義。ポート 8001 は内部ネットワークのみ（ホスト公開なし）。
3. **langchain-mcp-adapters Client** — `OrchestratorHandler.handle()` 内で `MultiServerMCPClient.get_tools()` を呼び出し。arq `startup()` で初期化してコンテキストに保持するほうが効率的（P4 参照）。
4. **config.yaml ツールルーティング** — エージェント名ごとに許可ツールを宣言。`ToolRegistry` クラスが起動時に読み込み、`SubAgent` コンストラクタに渡す。

**差別化フィーチャー:**
5. **Web 検索ツール（Tavily）** — `include_answer=True` で LLM 向けサマリーを返却。`max_results=3, include_raw_content=False` でコンテキスト肥大化を防止。フリー枠 1000 credits/月（200 名規模で充分）。
6. **DB クエリツール（PostgreSQL SELECT-only）** — `is_select_only()` を Phase 18 から `app/utils/sql_safety.py` に移動して再利用。`mcp_readonly` PostgreSQL ロールで二重防御。
7. **Claude Code CLI ツール** — `asyncio.create_subprocess_exec` で非同期実行。Docker イメージ内に Node.js + claude CLI インストール必要。**スパイク優先**、MVP には含めない。

**Anti-Features（実装禁止）:**
- 全エージェントに全ツールを付与する（ツール混乱・DB アクセス制限破綻）
- ツール結果のストリーミング（Copilot SDK が対応していない）
- ツール結果キャッシュ（200 名規模では不要、v5.1 以降）
- `is_select_only()` の再実装（v4.0 で本番テスト済み）

詳細は `.planning/research/FEATURES.md` を参照。

### アーキテクチャアプローチ

v5.0 の統合点は `OrchestratorHandler` と `SubAgent` の 2 ファイルに集中する。外部コンポーネントとして `mcp-server` Docker サービスが追加され、Worker → HTTP → mcp-server → 外部 API（Tavily / pg / subprocess）という新しいデータフローが確立される。

**新規コンポーネント:**

| Component | Path | Responsibility |
|-----------|------|---------------|
| FastMCP Server | `mcp_server/main.py` | ツール定義と HTTP エンドポイント公開 |
| web_search tool | `mcp_server/tools/web_search.py` | Tavily API ラッパー |
| db_query tool | `mcp_server/tools/db_query.py` | PostgreSQL SELECT + is_select_only ガード |
| claude_code tool | `mcp_server/tools/claude_code.py` | asyncio subprocess ラッパー |
| ToolRegistry | `app/orchestrator/tool_registry.py` | config.yaml 読み込み + エージェント別フィルタリング |

**変更ファイル（リスク順）:**

| File | Change | Risk |
|------|--------|------|
| `app/providers/copilot.py` | `bind_tools()` 実装 | HIGH — SDK と LangGraph 間の impedance mismatch |
| `app/orchestrator/agent.py` | `SubAgent._run_with_tools()` 追加 | MEDIUM — コアクラス、後方互換維持必須 |
| `app/jobs/handlers/orchestrator_handler.py` | MCP クライアント初期化 | MEDIUM — ジョブライフサイクル変更 |
| `docker-compose.yml` | `mcp-server` サービス追加 | LOW — additive |
| `pyproject.toml` | `langchain-mcp-adapters` 追加 | LOW |

**変更なしのファイル（確認済み）:** `AgentState`, `SubAgentRegistry`, `RouterNode`, 全 API ルート, `iframe_rpc_handler`, `langgraph_handler`, `debate_handler`

詳細は `.planning/research/ARCHITECTURE.md` を参照。

### Critical Pitfalls（上位 5 件）

1. **P1 + P2（CRITICAL）: ChatCopilot.bind_tools() 未実装 + Copilot SDK がプレーンテキストを返す** — `llm.bind_tools([...])` を呼ぶと即座に `NotImplementedError`。実装しても Copilot SDK は構造化 `tool_calls` を出力しないため `ToolNode` が一切発火しない。対策: システムプロンプト注入 + `_agenerate` 内 JSON テキスト解析（Approach A）。Phase 2 着手前に設計確定が必須。

2. **P3（HIGH）: MultiServerMCPClient async with パターン削除** — v0.1.0 で `async with client:` が廃止。`client.get_tools()` を直接呼ぶか `client.session()` を使う。多くのチュートリアルが古い API を示しているため注意。

3. **P6（HIGH）: Claude Code CLI が CLAUDECODE=1 を継承して失敗** — Claude Code セッション内で開発している場合、子プロセスが親の `CLAUDECODE=1` を継承して "nested session" エラーで即終了。`_build_claude_env()` で `CLAUDECODE` を unset してから subprocess を起動すること。

4. **P7（HIGH）: tool_calls 無限ループ** — ReAct ループで LLM が終了判定できない場合、`recursion_limit`（デフォルト 25）まで実行し続ける。`AgentState` に `tool_iterations` カウンターを追加し、`should_continue` で上限チェックを入れること。

5. **P8（HIGH）: Shell injection via tool 引数** — LLM 生成の引数を `shell=True` でコマンドに渡すと RCE につながる。必ず `asyncio.create_subprocess_exec(*args_list)` のリスト形式を使用。

詳細（15 件）は `.planning/research/PITFALLS.md` を参照。

---

## Implications for Roadmap

フィーチャー依存グラフから得られる自然な実装順序は 5 フェーズ構成:

```
MCP-01: FastMCP サーバー基盤
    ↓
MCP-02: Worker bind_tools 統合（最高リスク）
    ↓
MCP-03: Web 検索ツール（Tavily）
    ↓
MCP-04: DB クエリツール + セキュリティ
    ↓
MCP-05: per-agent ツールルーティング（オプション）
```

### Phase MCP-01: FastMCP Docker サービス基盤
**Rationale:** MCP-02 以降の全フェーズがこのサービスに依存する。先にスタブで通信確認してから bind_tools の複雑な実装に進む。
**Delivers:** `mcp-server` Docker サービスが起動し、`MultiServerMCPClient.get_tools()` が LangChain BaseTool リストを返す。スタブ `ping` ツールで通信確認。
**Features addressed:** FastMCP Docker サービス（Table Stakes #2）、langchain-mcp-adapters クライアント（#3）
**Pitfalls to avoid:** P9（stdio transport を使わない）、P3（async with を使わない）、P4（arq startup() で初期化）、P14（/health エンドポイント追加）、P10（ツール名衝突回避）

### Phase MCP-02: LangGraph bind_tools + ToolNode 統合
**Rationale:** 最高リスクフェーズ。ChatCopilot.bind_tools() 未実装という根本問題をここで解決する。設計選択（Approach A vs B）が全体アーキテクチャを規定するため、最初のタスクとして設計決定を行う。
**Delivers:** `research-assistant` エージェント 1 本が tool-enabled になり、Web 検索プロンプトでツール呼び出しが発火する end-to-end 検証。
**Features addressed:** LangGraph bind_tools + ToolNode ReAct ループ（Table Stakes #1）
**Pitfalls to avoid:** P1（bind_tools 未実装）、P2（ToolNode が発火しない）、P7（無限ループ）、P13（invalid_tool_calls サイレントドロップ）
**Research flag:** ChatCopilot.bind_tools() 実装方針を Phase 着手前にスパイクで確定すること。

### Phase MCP-03: Web 検索ツール（Tavily）
**Rationale:** 最も価値が高く複雑度が最低のツール。MCP-02 の end-to-end 検証用ツールでもある。
**Delivers:** `web_search` MCP ツールが本番で動作。`research-assistant` エージェントが Tavily 経由でリアルタイム情報を取得してレスポンスに反映。
**Features addressed:** Web 検索ツール（Differentiator #5）
**Pitfalls to avoid:** P11（同期 TavilyClient 使用禁止）、P12（レスポンスサイズ制御）

### Phase MCP-04: DB クエリツール + セキュリティ強化
**Rationale:** `is_select_only()` はすでに本番テスト済みコード。移植コストが低く、セキュリティリスクを二重防御で管理できる。
**Delivers:** `db_query` MCP ツール。`mcp_readonly` PostgreSQL ロール。`app/utils/sql_safety.py` 共有ユーティリティ。
**Features addressed:** DB クエリツール（Differentiator #6）
**Pitfalls to avoid:** `is_select_only()` 再実装禁止（既存コードを `sql_safety.py` に移動して再利用）

### Phase MCP-05: config.yaml ツールルーティング（per-agent フィルタリング）
**Rationale:** ツール数が増えた段階でエージェント別アクセス制御が必要になる。コード変更なしで制御可能にする。
**Delivers:** `config/mcp_tools.yaml` + `ToolRegistry` クラス。`agent_tools` allowlist によりエージェントごとに使えるツールが限定される。
**Features addressed:** config.yaml ツールルーティング（Table Stakes #4）

**v5.1 以降に延期:**
- Claude Code CLI ツール（Docker イメージビルド + 出力フォーマット検証スパイク必要）
- ツール結果キャッシュ
- DB スキーマ検索ツール（`db_schema()` MCP ツール）

### Phase Ordering Rationale

- **依存チェーンが順序を規定:** MCP サービスが動かないと MultiServerMCPClient が意味を持たず、クライアントがないと bind_tools の end-to-end 検証ができない。
- **最高リスクを早期に解決:** ChatCopilot.bind_tools() 問題は MCP-02 の設計中核。遅らせると後続フェーズが全部ブロックされる。
- **Claude Code は最後:** Docker イメージビルドの複雑さ + セキュリティリスク（CVE-2025-59536 等）から、Web 検索・DB クエリが安定してから着手する。

### Research Flags

**フェーズ着手前に検証が必要:**
- **MCP-02 着手前:** `ChatCopilot.bind_tools()` スパイク — Approach A（プロンプト注入 + テキスト解析）が Copilot モデルで正しく動作するか検証。特に JSON-vs-text 終了判定が Copilot SDK の応答形式と整合するか。
- **MCP-03 着手時:** Tavily `search_context(max_tokens=3000)` の実際のトークン削減効果を Copilot モデルのコンテキストウィンドウに対して検証。

**標準パターン（追加調査不要）:**
- **MCP-01:** FastMCP streamable-http 設定は公式ドキュメント HIGH 信頼。`MultiServerMCPClient` の直接呼び出しパターンも確認済み。
- **MCP-04:** `is_select_only()` は v4.0 本番テスト済み。移植のみ。
- **MCP-05:** YAML 設定 + `ToolRegistry` は低リスクの新規クラス実装。

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | fastmcp/langchain-mcp-adapters/tavily は PyPI・公式 docs 検証済み。バージョン固定済み |
| Features | HIGH | LangGraph ToolNode / tools_condition / recursion_limit は複数ソース確認済み。FastMCP @mcp.tool は公式 docs |
| Architecture | HIGH | 既存コードを直接読んで変更範囲を特定。`AgentState`・`OrchestratorGraph` 変更不要を確認 |
| Pitfalls | MEDIUM-HIGH | LangGraph/langchain-mcp-adapters pitfalls は issues/discussions で検証。ChatCopilot bind_tools は未実装のため実際の挙動は MCP-02 スパイクまで LOW |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **ChatCopilot.bind_tools() 実装方針（CRITICAL）:** Approach A（プロンプト注入 + テキスト解析）で Copilot SDK が確実に JSON レスポンスを返すかは、実際の SDK 呼び出しで確認するまで不確実。MCP-02 の最初のタスクをスパイクとして計画し、Approach B（Copilot SDK ネイティブ tool events）へのフォールバックを設計書に明記しておくこと。
- **langchain-mcp-adapters v0.2.2 の async context manager サポート有無:** v0.1.0 で削除されたが v0.2.2 で再実装された可能性がある。インストール後に README を確認し、利用可能なら `async with client.session()` パターンを採用する。
- **Claude Code CLI 出力フォーマット:** `--output-format json` の実際の出力が JSON Lines か単一 JSON オブジェクトかは、インストール済み CLI バージョンで確認が必要。スパイクスクリプトを先に作成すること。

---

## Sources

### Primary (HIGH confidence)
- FastMCP 公式ドキュメント: https://gofastmcp.com/servers/tools, https://gofastmcp.com/deployment/http
- FastMCP PyPI (v3.2.2): https://pypi.org/project/fastmcp/
- langchain-mcp-adapters GitHub: https://github.com/langchain-ai/langchain-mcp-adapters
- langchain-mcp-adapters PyPI (v0.2.2): https://pypi.org/project/langchain-mcp-adapters/
- Tavily API reference: https://docs.tavily.com/documentation/api-reference/endpoint/search
- LangGraph ToolNode reference: https://reference.langchain.com/python/langgraph/agents
- LangGraph recursion_limit: https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT

### Secondary (MEDIUM confidence)
- MultiServerMCPClient DeepWiki: https://deepwiki.com/langchain-ai/langchain-mcp-adapters/2.1-multiservermcpclient
- LangGraph ReAct agent from scratch: https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch-functional/
- Claude Code CLI subprocess: https://platform.claude.com/docs/en/agent-sdk/python
- Google MCP Toolbox config patterns: https://codelabs.developers.google.com/agentic-rag-toolbox-cloudsql
- Software Mansion — Building Agents with LangGraph Part 2

### Tertiary (LOW confidence / validation required)
- anthropics/claude-agent-sdk-python Issue #573 (CLAUDECODE=1 nested session)
- anthropics/claude-code Issue #18666 (zombie subprocess)
- CVE-2025-59536 (RCE via Claude Code config files)
- LangChain Discussion #26146 (bind_tools NotImplementedError)

---
*Research completed: 2026-04-09*
*Milestone: v5.0 Agent Tool Platform*
*Based on: v1.0 research (2026-03-31) — superseded for v5.0 scope*
*Ready for roadmap: yes*
