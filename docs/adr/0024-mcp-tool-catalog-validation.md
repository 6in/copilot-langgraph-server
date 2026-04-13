# 0024. MCP ツールカタログ検証（ToolRegistry）と関連バグ修正

**Date:** 2026-04-13  
**Status:** Accepted

## Context

Phase 20〜23 で MCP サーバーに `ping` / `web_search` / `db_query` / `claude_code` の 4 ツールを実装した。しかしデプロイ後に YAML 設定と MCP サーバーの実装が乖離しても、worker は何も検知せず動き続けてしまう（無言不整合）。

また、動作確認の過程で 2 つの独立したバグが発覚した：

1. **ルーティングバグ** — SuperChat でエージェント候補が 1 つの場合でも LLM に振り分けを聞いてしまい、Copilot が質問に直接回答してしまう (`routing_fallback`)
2. **UUID シリアライズバグ** — `db_query` ツールの `_json_default` が `uuid.UUID` 型を未処理のため、UUID カラムを含むテーブルのクエリが失敗する

## Decision

### ToolRegistry（MCP-03）

`config/mcp_tools.yaml` に MCP ツールのカタログを宣言し、`app/orchestrator/tool_registry.py` の `ToolRegistry` クラスが worker 起動時に YAML と MCP サーバーの実ツールリストを **双方向** で照合する。不一致は `RuntimeError` を伝播させて worker 起動を失敗させる。

**重要な配置判断：** `validate()` の呼び出しを既存の `try/except Exception` ブロックの **外側** に置く。ブロック内に置くと RuntimeError が DEGRADED として握りつぶされる（Pitfall 1）。`mcp_connected` フラグで MCP 接続成功・失敗を区別し、接続失敗時（DEGRADED モード）はバリデーションをスキップして既存挙動を維持する。

### ルーティングバグ修正

`RouterNode` に Stage 1.5 を追加：利用可能なエージェントが 1 つなら LLM を呼ばずに直接ルーティングする。

```python
if len(agents) == 1:
    return {"next": agents[0].name}
```

### UUID シリアライズバグ修正

`mcp_server/tools/db_query.py` の `_json_default` に `uuid.UUID → str()` の変換を追加。

## Alternatives Considered

**per-agent YAML allowlist** — `mcp_tools.yaml` でエージェントごとにアクセス可能なツールを制限する案。CONTEXT.md D-02 で明示的に defer。エージェント別ツール選択は引き続き `agents/*/AGENT.md` の `tools:` フィールドで管理する。

**ホットリロード** — YAML 変更をコンテナ再起動なしに反映する案。スコープ外。`docker compose restart worker` で十分とした。

**ルーター修正の代替** — `ROUTER_PROMPT` を強化して「必ずエージェント名のみを返せ」と指示する案。Copilot モデルの特性上、制約付きプロンプトでも長文回答を返すことがあるため、構造的な修正（単一候補の早期返し）を選択した。

## Consequences

**正の影響：**
- MCP サーバーにツールを追加・削除した際に YAML の更新漏れを worker 起動時に検知できる
- SuperChat でエージェントを明示指定した場合のルーティングが安定する
- UUID カラムを含む任意のテーブルに対して `db_query` が動作する

**注意点・落とし穴：**
- `mcp_tools.yaml` に新ツールを追加する際は MCP サーバー側の実装と同時にデプロイしないと worker が起動しない（意図的な厳格さ）
- DEGRADED モード（MCP 接続失敗）では ToolRegistry バリデーションはスキップされる。MCP サーバーが落ちていても worker は起動し続ける
- `routing_fallback` ログは今後も発生しうる（複数エージェント候補で LLM が期待外の出力をした場合）。`stage: "single"` ログを追加しているので、単一エージェント経路の追跡は可能
