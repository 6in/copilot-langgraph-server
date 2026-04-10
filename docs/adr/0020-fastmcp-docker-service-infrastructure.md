# ADR 0020: FastMCP Docker サービス基盤 (Phase 20)

**Date**: 2026-04-10
**Status**: Accepted
**Phase**: 20 — FastMCP Docker サービス基盤

---

## Context

v5.0 Agent Tool Platform の第1フェーズとして、LangGraph エージェントが外部ツールを
MCP (Model Context Protocol) 経由で呼び出すための基盤を構築する必要があった。

ツール実装を API サーバー (`app/`) に直接組み込む方法もあったが、
ツールの独立デプロイ・スケールアウト・言語非依存な追加を将来的に可能にするため、
FastMCP による独立サービスとして分離する方針を採用した。

---

## Decisions

### 1. MCP サーバーを独立 Docker サービスとして構成する

`mcp_server/` を独立した uv プロジェクトとし、`docker-compose.yml` に `mcp-server` サービスを追加。
ホストポートは公開せず、Docker 内部ネットワーク (`http://mcp-server:8001`) でのみアクセス可能にした。

**理由**: ツール実装の変更がアプリコアに影響しない。将来的に mcp-server だけをスケールアウトできる。

### 2. transport は `http` (server) / `streamable_http` (client) を使用する

FastMCP サーバー側は `transport="http"`、langchain-mcp-adapters の `MultiServerMCPClient` 側は
`transport="streamable_http"` を指定する。

**理由**: FastMCP と langchain-mcp-adapters でパラメータ名が異なる（アンダースコアの有無）。
混同するとサイレントな接続失敗を招く。

### 3. Phase 20 ではスタブ実装のみ提供する

4 tools (ping, web_search_stub, db_query_stub, claude_code_stub) はすべてスタブ実装。
実装は Phase 22 (Tavily), Phase 23 (db_query / claude_code) で行う。

**理由**: Docker 統合と LangGraph bind_tools の検証を先行させ、ツール実装のリスクと分離する。

### 4. `mcp_server/` は root `pyproject.toml` から独立させる

`mcp_server/` は独自の `pyproject.toml` + `uv.lock` を持つ独立プロジェクト。
root の依存には `fastmcp` を dev dep として追加するにとどめる。

**理由**: MCP サーバーと API サーバーの依存関係を分離し、それぞれが独立してビルド・テストできる。

---

## Lessons Learned (Phase 20 固有)

### 大量削除マージの発生と対策

GSD ワークフローの `isolation="worktree"` で生成された worktree が `main` を起点にしていたため、
`gsd/phase-20-fastmcp-docker` ブランチとのマージ時に 81 files / 8933 deletions が発生した。
`static/js/iframe-rpc.js`, `parent-bridge.js`, Phase 18/19 の実装ファイルが削除された。

**対策として追加したルール（CLAUDE.md に反映済み）**:
- マージ前に `git diff --stat HEAD <branch>` で削除規模を必ず確認
- 削除行数 > 追加行数 × 2 はストップサイン
- `.planning/` 以外のアプリコードが削除される場合は一件ずつ意図確認

### 新ブランチ再作成による収束

旧ブランチの履歴が汚染されたため、`main` から `gsd/phase-20-fastmcp-docker-v2` を作成し、
問題のある cherry-pick（`2dc3a21` — worktree 起点コミットが削除を内包）を回避して
`mcp_server/` ディレクトリだけを `git checkout <branch> -- mcp_server/` で取り出す方法で解決した。

---

## Consequences

- worker コンテナから `http://mcp-server:8001/mcp` へ streamable_http で接続し、
  4 tools を LangChain BaseTool として取得・呼び出しできることを確認済み
- Phase 21 で `ChatCopilot.bind_tools()` を実装すれば、LLM がツールを選択する ReAct ループが動く
- `canvas.py` の `$URL_PREFIX` 置換バグと Vite `/js/` proxy 不足も本フェーズで修正済み
