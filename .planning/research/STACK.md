# Technology Stack — v5.0 Agent Tool Platform

**Project:** Copilot LangGraph Chat
**Researched:** 2026-04-09
**Overall confidence:** HIGH (derived from Architecture + Features + Pitfalls research + PyPI verification)

---

## New Dependencies for v5.0

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `fastmcp` | 3.2.2 | MCP サーバー実装 | `@mcp.tool` デコレータでツール定義、`streamable_http` transport で Docker サービスとして配信。`mcp` 低レベルライブラリより高レベルで扱いやすい | HIGH |
| `langchain-mcp-adapters` | 0.2.2 | MCP ツール → LangChain Tool 変換 | `MultiServerMCPClient` で FastMCP サーバーに接続し、ToolNode が使える LangChain Tool として取得。**v0.1.0 で `async with` パターン削除** — `.get_tools()` を直接呼ぶ | MEDIUM |
| `tavily-python` | 0.5.x | Web 検索 API クライアント | `AsyncTavilyClient` でノンブロッキング検索。`include_answer=True` で LLM 向けサマリーを取得。フリー枠 1000 credits/月 | HIGH |
| `psycopg[binary]` | 3.x (既存) | DB クエリツール | Phase 18 の `is_select_only()` ガードを `app/utils/sql_safety.py` に移動して再利用。追加ライブラリ不要 | HIGH |

## Transport: streamable-http (必須)

`stdio` transport は FastMCP のデフォルトだが **Docker コンテナをまたぐことができない**。
`worker` コンテナと `mcp-server` コンテナ間の通信には `streamable_http` transport を使用する。

```python
# mcp-server/main.py
mcp = FastMCP("tool-server", transport="streamable-http", port=8001)
```

```python
# worker 側 (MultiServerMCPClient)
client = MultiServerMCPClient({
    "tools": {"url": "http://mcp-server:8001/mcp", "transport": "streamable_http"}
})
tools = await client.get_tools()  # async with は使わない (v0.1.0 で削除)
```

## Docker Compose 変更

```yaml
# 追加サービス
mcp-server:
  build: ./mcp-server
  environment:
    - TAVILY_API_KEY=${TAVILY_API_KEY}
    - DATABASE_URL=${DATABASE_URL}
  networks:
    - internal
```

## What NOT to Add

| 候補 | 理由 |
|------|------|
| `langchain` (full) | `langchain-core` で bind_tools / ToolNode は動く。フル langchain は不要 |
| `mcp` (低レベル) | `fastmcp` がラップしている。両方入れると依存競合のリスク |
| `requests` / `aiohttp` | `httpx` が既存。Tavily async client は内部で httpx を使う |
| `subprocess32` | Python 3.12 標準 `asyncio.create_subprocess_exec` で十分 |

## Critical Risk: ChatCopilot.bind_tools()

`app/providers/copilot.py` の `ChatCopilot(BaseChatModel)` は `bind_tools()` を実装していない。
Copilot SDK は plain text を返すため、構造化 `tool_calls` が生成されない可能性が高い。

**Phase 2 着手前に必ず検証し、以下のどちらかを選択する:**
- **Approach A**: `ChatCopilot.bind_tools()` を実装し tool_calls を XML/JSON プロンプト注入でパース
- **Approach B**: ReAct プロンプトで tool_calls を模倣し、出力を正規表現でパース

## Existing Stack (変更なし)

Python 3.12 / FastAPI 0.135.2 / LangGraph 1.1.3 / langchain-core / arq + Redis / PostgreSQL (pgvector) / React 19 + TypeScript + Vite
