# Phase 28: CodeAct パターンの実装 - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

LLM がPythonコードを生成・サンドボックス実行し結果を観察する推論ループ（CodeAct パターン）を実装する。既存の MCP ツール基盤 + ToolEnabledSubAgent の ReAct ループを活用し、`execute_python` MCP ツールと CodeAct 専用エージェントを追加する。フロントエンド変更なし（Markdown 表示で十分）。

</domain>

<decisions>
## Implementation Decisions

### 実行環境とサンドボックス
- **D-01:** worker コンテナ内サブプロセスで Python コードを実行する（claude_code.py の `asyncio.create_subprocess_exec` パターン踏襲）
- **D-02:** リソース制限は中程度 — タイムアウト + メモリ制限 + 一時ディレクトリでファイルI/O制限
- **D-03:** 1回あたりの実行タイムアウトは 60 秒（claude_code.py と同じ設定）

### グラフ設計とループ構造
- **D-04:** `execute_python` MCP ツールとして実装し、既存 ToolEnabledSubAgent の ReAct ループで自然に利用する（専用グラフ不要）。コード生成→ツール呼び出し→結果観察が ReAct ループで自動的に実現される
- **D-05:** CodeAct ループの最大ステップ数は 5 ステップ（コード実行は重いので ToolEnabledSubAgent の recursion_limit を CodeAct エージェント用に調整）
- **D-06:** 実行結果のフィードバックは stdout + stderr + exit_code を返す（ToolMessage として会話履歴に蓄積、LLM が自然に観察）

### エージェント統合とUI表示
- **D-07:** CodeAct 専用エージェント `agents/codeact/AGENT.md` を新規作成。`tools: true` + `mcp_tools: [execute_python]` で ToolEnabledSubAgent として SubAgentRegistry に自動登録される
- **D-08:** コード実行の過程と結果は通常の Markdown テキストとして表示。既存の MarkdownMessage コンポーネントで対応し、フロントエンド変更なし

### 対応言語と制約
- **D-09:** 対応言語は Python のみ。ツール名も `execute_python` で明確に限定
- **D-10:** インポート制限はホワイトリスト方式。許可したモジュールのみインポート可能
- **D-11:** ホワイトリストは設定ファイル（`config/sandbox_allowlist.yaml`）で管理。変更時はコンテナ再起動で反映

### Claude's Discretion
- サブプロセスの具体的なメモリ制限値（ulimit 等）
- ホワイトリストのデフォルト許可モジュール一覧
- CodeAct エージェントのシステムプロンプト文言
- `execute_python` MCP ツールの引数設計（code, timeout 等のパラメータ）
- 実行結果の文字数制限（claude_code.py の 4000 文字パターンを参考にするか）

### Folded Todos
- **CodeAct を実装してみる** — LangGraph エージェントの推論→実行ループを柔軟にするため、LLM がPythonコードを生成・実行し結果を観察する CodeAct パターンを検討。参考記事: https://qiita.com/nogataka/items/9924c97a74f63c5452eb

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 既存 MCP ツール実装（参考パターン）
- `mcp_server/tools/claude_code.py` — サブプロセス実行パターン（env サニタイズ、タイムアウト、SIGKILL エスカレーション、出力切り捨て）
- `mcp_server/server.py` — FastMCP ツール登録パターン（register_tools）
- `mcp_server/tools/stubs.py` — MCP ツールのスタブ実装例

### エージェントフレームワーク
- `app/orchestrator/tool_agent.py` — ToolEnabledSubAgent + build_react_graph（ReAct ループ実装）
- `app/orchestrator/agent.py` — SubAgentRegistry（AGENT.md 自動ロード、tools フラグ判定）
- `app/orchestrator/state.py` — AgentState TypedDict

### ツールルーティング設定
- `config/mcp_tools.yaml` — MCP ツールカタログ（execute_python を追加する必要あり）
- `app/orchestrator/tool_registry.py` — ToolRegistry（YAML と MCP 実ツールの一致検証）

### ADR・パターン
- `.planning/patterns.md` — ADR 由来パターンカタログ
- `docs/adr/INDEX.md` — ADR カテゴリ別索引

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mcp_server/tools/claude_code.py` — サブプロセス実行の完全な参考実装。env サニタイズ（ALLOWED_ENV_KEYS frozenset）、タイムアウト（TIMEOUT_SECS）、SIGTERM→SIGKILL エスカレーション、出力切り捨て（MAX_INLINE_CHARS + shared volume 書き出し）のすべてが再利用可能
- `ToolEnabledSubAgent` — ReAct ループが完成しており、`mcp_tools` に `execute_python` を追加するだけで CodeAct パターンが動く
- `SubAgentRegistry` — `agents/codeact/AGENT.md` を配置するだけで自動登録（ゼロコード）

### Established Patterns
- MCP ツール追加パターン: `mcp_server/tools/` にモジュール作成 → `server.py` で register → `config/mcp_tools.yaml` に追加
- エージェント追加パターン: `agents/<name>/AGENT.md` を配置 → SubAgentRegistry が自動ロード
- サブプロセス安全パターン: 許可リスト env + タイムアウト + SIGKILL + 出力切り捨て

### Integration Points
- `mcp_server/server.py` — execute_python ツールの register_tools 呼び出し追加
- `config/mcp_tools.yaml` — execute_python エントリ追加
- `agents/codeact/AGENT.md` — 新規エージェント定義ファイル

</code_context>

<specifics>
## Specific Ideas

- claude_code.py の実装パターン（env サニタイズ、タイムアウト、出力切り捨て）をベースに `execute_python` MCP ツールを実装
- ホワイトリストのインポートチェックは、コード実行前にAST解析で import 文を検査する方式が安全（exec 前にブロック可能）
- CodeAct エージェントのシステムプロンプトで「コードを書いて execute_python ツールで実行し、結果を観察して次のアクションを決めてください」と指示
- 参考記事: https://qiita.com/nogataka/items/9924c97a74f63c5452eb

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 28-codeact-llm*
*Context gathered: 2026-04-17*
