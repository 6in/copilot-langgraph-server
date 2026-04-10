# Phase 20: FastMCP Docker サービス基盤 - Research

**Researched:** 2026-04-10
**Domain:** FastMCP (Python MCP サーバー) + langchain-mcp-adapters + Docker Compose 統合
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** top-level `mcp_server/` ディレクトリに FastMCP アプリを配置する（`app/` とは完全分離）
- **D-02:** 将来の独立リポジトリ分離・スケールアウトを見越した構造にする
- **D-03:** `mcp_server/pyproject.toml` を独立した uv プロジェクトとして用意する（親の `pyproject.toml` とは別）
- **D-04:** ベースイメージは `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`（他コンテナと同一、一貫性を保つ）
- **D-05:** docker-compose.yml に `mcp-server` サービスを追加する
- **D-06:** ホストポートは公開しない（`redis` と同様に内部ネットワーク専用）。worker からは `mcp-server:8001` でアクセス
- **D-07:** `worker` サービスが `mcp-server` に依存する（`depends_on`）
- **D-08:** `streamable-http` トランスポートを使用する（FastMCP デフォルト、ROADMAP.md に明記済み）
- **D-09:** エンドポイントパスは `/mcp`（streamable-http 標準）
- **D-10:** Phase 20 で用意するスタブツールは 4 つ: `ping` / `web_search_stub` / `db_query_stub` / `claude_code_stub`
- **D-11:** 各スタブは正しい引数スキーマ（名前・型・説明）を持ち、固定のモックレスポンスを返す
  - `ping` → `{"status": "ok", "timestamp": ...}`
  - `web_search_stub(query: str)` → 固定テキスト結果
  - `db_query_stub(sql: str)` → モック行データ
  - `claude_code_stub(command: str)` → 固定出力文字列
- **D-12:** 本番実装は各スタブを Phase 22/23 で差し替える設計（同名・同スキーマで上書き）
- **D-13:** `GET /health` → `{"status": "ok"}` を返す（Docker ヘルスチェック用）
- **D-14:** docker-compose の `healthcheck` で `/health` を確認し、`worker` が `mcp-server` を待つ

### Claude's Discretion
- FastMCP アプリのエントリポイントファイル名（例: `server.py` or `main.py`）
- `mcp_server/pyproject.toml` の具体的な依存バージョン（fastmcp, langchain-core 等）
- ツールモジュールの分割方法（単一ファイル vs tools/ ディレクトリ）

### Deferred Ideas (OUT OF SCOPE)
- **本番モード Docker Compose 整備** — v5.1+
- **config.yaml ツールルーティング (MCP-03)** — Phase 24
- **langchain-mcp-adapters の worker 側統合 (TOOL-01)** — Phase 21
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MCP-01 | mcp-server が Docker サービスとして起動し、worker コンテナから HTTP 接続できる | D-05/D-06/D-07/D-08 の Docker Compose パターン。FastMCP `mcp.run(transport="http", host="0.0.0.0", port=8001)` で実現。 |
| MCP-02 | `@mcp.tool` でツールを定義し、スタブが正常に呼び出し・応答できる | `@mcp.tool` デコレーター + MultiServerMCPClient streamable_http 接続で実現。D-10/D-11 の 4 スタブ実装。 |
</phase_requirements>

---

## Summary

Phase 20 は FastMCP サーバーを Docker コンテナとして追加し、worker から `MultiServerMCPClient.get_tools()` でスタブツールを取得できる基盤を構築するフェーズ。技術的な判断はほぼ CONTEXT.md で確定済みであり、実装上の注意点の把握が研究の主目的となる。

FastMCP 最新版（3.2.3 as of 2026-04-10）では `transport="http"` が streamable-http 実装に対応し、`mcp.run(transport="http", host="0.0.0.0", port=8001)` でコンテナ外から接続可能な状態で起動できる。カスタムルート（`/health`）は `@mcp.custom_route` デコレーターで追加できるが、バージョン間で挙動変化があった経緯があるため `http_app()` 経由のパターンも把握しておく必要がある。

worker 側では `langchain-mcp-adapters 0.2.2` の `MultiServerMCPClient` を `transport: "streamable_http"` で設定し、`await client.get_tools()` で LangChain `BaseTool` リストを取得する。接続はデフォルトでエフェメラル（呼び出し毎にセッションを開閉）なので、Docker Compose の `depends_on: condition: service_healthy` で mcp-server が完全起動してから worker が起動することが重要。

**Primary recommendation:** `mcp_server/server.py` を FastMCP エントリポイントとし、`mcp_server/tools/stubs.py` にスタブを集約する 2 ファイル構成を採用する。

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastmcp` | 2.14.x または 3.2.3 | MCP サーバーフレームワーク | `@mcp.tool` デコレーター、HTTP トランスポート、カスタムルートをすべて提供。pip latest は 3.2.3。 |
| `langchain-mcp-adapters` | 0.2.2 | MCP → LangChain BaseTool 変換 | `MultiServerMCPClient.get_tools()` が MCP ツールを LangChain 互換に変換する。STATE.md に `[v5.0 Research]` 注記あり。 |
| `mcp` | 1.27.0 | MCP プロトコル本体（fastmcp の依存） | fastmcp が内部で利用。直接参照は不要。 |

**注意 - fastmcp バージョン選択:**
- pip latest: **3.2.3** [VERIFIED: pip index versions]
- `@mcp.custom_route` はバージョン 2.4.0 で一時的に壊れ (issue #556)、その後修正済み
- **推奨: `>=2.14.0,<4.0`** で固定（3.x は 2.x の継続、API 互換性を保ちながら機能追加中）

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `uvicorn[standard]` | >=0.42.0 | ASGI サーバー（本番用） | `http_app()` を直接 uvicorn に渡す場合。今フェーズは `mcp.run()` で十分。 |
| `starlette` | fastmcp が依存 | カスタムルート応答型 (`JSONResponse`) | `@mcp.custom_route` 内で `JSONResponse` を返す場合に import。 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fastmcp>=2.14.0` | `fastmcp==2.14.6` (固定) | 固定版は再現性高いが更新漏れリスク。今回は Technical Preview 相当でないため範囲指定で十分。 |
| `@mcp.custom_route` | `http_app()` + starlette Route 手動追加 | 後者はより確実だが fastmcp の内部 API に依存。公式 docs では `@mcp.custom_route` を推奨。 |

**Installation (mcp_server/pyproject.toml 用):**
```bash
# mcp_server/ ディレクトリで uv init 後
uv add fastmcp langchain-mcp-adapters
```

**Version verification:** [VERIFIED: pip index versions]
- `fastmcp`: 3.2.3 (2026-04-10 時点)
- `langchain-mcp-adapters`: 0.2.2 (2026-04-10 時点)

---

## Architecture Patterns

### Recommended Project Structure

```
mcp_server/
├── pyproject.toml     # 独立 uv プロジェクト (D-03)
├── uv.lock            # 依存ロックファイル
├── server.py          # FastMCP エントリポイント (Claude's Discretion)
└── tools/
    ├── __init__.py
    └── stubs.py       # 4 スタブツール定義 (D-10/D-11)
```

Claude's Discretion 判断: エントリポイントは `server.py` を推奨（`main.py` はアプリサーバーとの混同リスクあり）、ツールは `tools/stubs.py` に集約（Phase 22/23 で各ツールファイルへ分離拡張しやすい）。

### Pattern 1: FastMCP サーバー定義と起動

**What:** `FastMCP` インスタンスを作成し、`@mcp.tool` でツールを登録、`@mcp.custom_route` でヘルスエンドポイントを追加して起動する。
**When to use:** Phase 20 全体のエントリポイントパターン

```python
# Source: https://gofastmcp.com/deployment/http
from fastmcp import FastMCP
from starlette.responses import JSONResponse
from tools.stubs import register_tools
import datetime

mcp = FastMCP("copilot-mcp-server")

# ヘルスチェックエンドポイント (D-13)
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "ok"})

# ツール登録
register_tools(mcp)

if __name__ == "__main__":
    # D-08: streamable-http = transport="http"
    # D-09: エンドポイントは /mcp (FastMCP のデフォルト)
    # D-06: ホストポート非公開なので 0.0.0.0 バインド必須
    mcp.run(transport="http", host="0.0.0.0", port=8001)
```

### Pattern 2: @mcp.tool デコレーターによるスタブ定義

**What:** 型アノテーション付き引数を持つ Python 関数に `@mcp.tool` を付けるだけで MCP ツールとして登録される。
**When to use:** スタブツール 4 本の実装 (D-11)

```python
# Source: https://gofastmcp.com/getting-started/quickstart
import datetime

def register_tools(mcp: FastMCP):

    @mcp.tool
    def ping() -> dict:
        """サーバーの疎通確認"""
        return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}

    @mcp.tool
    def web_search_stub(query: str) -> str:
        """Web 検索スタブ（Phase 22 で差し替え）"""
        return f"[stub] Search results for: {query}"

    @mcp.tool
    def db_query_stub(sql: str) -> list[dict]:
        """DB クエリスタブ（Phase 23 で差し替え）"""
        return [{"id": 1, "stub": True, "sql": sql}]

    @mcp.tool
    def claude_code_stub(command: str) -> str:
        """Claude Code 実行スタブ（Phase 23 で差し替え）"""
        return f"[stub] Executed: {command}\nOutput: stub response"
```

### Pattern 3: MultiServerMCPClient による worker 側接続確認

**What:** worker コンテナから `MultiServerMCPClient` を使って mcp-server に接続し、ツールリストを取得する。
**When to use:** MCP-01/MCP-02 の成功基準検証（接続テスト）

```python
# Source: https://deepwiki.com/langchain-ai/langchain-mcp-adapters/2.1-multiservermcpclient
# transport キー名は "streamable_http"（アンダースコア）
from langchain_mcp_adapters.client import MultiServerMCPClient

async def verify_mcp_connection():
    client = MultiServerMCPClient({
        "copilot-tools": {
            "transport": "streamable_http",
            "url": "http://mcp-server:8001/mcp"
        }
    })
    tools = await client.get_tools()
    # tools は LangChain BaseTool のリスト
    assert all(hasattr(t, "name") for t in tools)
    return tools
```

**CRITICAL:** transport キーは `"streamable_http"`（アンダースコア）。`"streamable-http"` はエラー。[VERIFIED: deepwiki.com/langchain-ai/langchain-mcp-adapters]

### Pattern 4: Docker Compose サービス定義

**What:** 既存の `worker` パターンに倣い `mcp-server` サービスを追加する。
**When to use:** D-05〜D-07 の実装

```yaml
# Source: 既存 docker-compose.yml パターン + D-06/D-13/D-14
  mcp-server:
    image: ghcr.io/astral-sh/uv:python3.12-bookworm-slim
    working_dir: /mcp_server
    command: uv run python server.py
    volumes:
      - ./mcp_server:/mcp_server
    # D-06: ホストポートは公開しない（内部ネットワーク専用）
    # worker からは mcp-server:8001 でアクセス
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
```

```yaml
  worker:
    # ... 既存設定 ...
    environment:
      - MCP_SERVER_URL=http://mcp-server:8001
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      mcp-server:           # D-07: mcp-server に依存
        condition: service_healthy  # D-14: healthy 待ち
```

### Anti-Patterns to Avoid

- **`transport="streamable-http"` (ハイフン) を使う:** FastMCP の run() では `transport="http"` が正解。langchain-mcp-adapters の transport キーは `"streamable_http"` (アンダースコア)。混同しやすい。
- **`async with MultiServerMCPClient(...)` パターンを使う:** STATE.md `[v5.0 Research]` に「v0.2.2 では async with パターン廃止」と明記。`client = MultiServerMCPClient(...)` → `await client.get_tools()` を使う。
- **`create_sse_app()` を直接呼ぶ:** 低レベル API で issue #556 の問題あり。`mcp.run()` または `mcp.http_app()` を使う。
- **worker に langchain-mcp-adapters を追加せず接続確認する:** langchain-mcp-adapters は親 `pyproject.toml` にも追加が必要（worker コンテナは `/app` をマウント）。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP ツール定義 | 手動で JSON Schema + HTTP ハンドラーを実装 | `@mcp.tool` デコレーター | 型アノテーションから自動でスキーマ生成、MCP プロトコル全処理を担う |
| MCP → LangChain 変換 | `BaseTool` サブクラスを手書き | `MultiServerMCPClient.get_tools()` | ツール呼び出し、エラー処理、型変換のすべてを処理済み |
| Docker ヘルスチェック用 HTTP サーバー | 別ポートで Flask/aiohttp を起動 | `@mcp.custom_route("/health")` | FastMCP 内にそのまま定義できる、ポート管理不要 |
| ストリーミング HTTP セッション管理 | SSE/WebSocket 実装 | FastMCP `transport="http"` | MCP streamable-http プロトコルを完全実装済み |

**Key insight:** FastMCP は MCP プロトコルの全複雑性を隠蔽している。`@mcp.tool` + Python 型ヒントだけでスキーマ・バリデーション・プロトコル処理が自動化される。

---

## Common Pitfalls

### Pitfall 1: transport キー名の混同
**What goes wrong:** `MultiServerMCPClient` の config で `"transport": "streamable-http"` (ハイフン) と書くと接続エラー。
**Why it happens:** FastMCP ドキュメントは "streamable-http" と表記するが、langchain-mcp-adapters の TypedDict は `StreamableHttpConnection` でキー名は `"streamable_http"` (アンダースコア)。
**How to avoid:** langchain-mcp-adapters 側は常に `"streamable_http"` (アンダースコア) を使う。
**Warning signs:** `ValueError: Unknown transport` または接続タイムアウト。

### Pitfall 2: async with MultiServerMCPClient の廃止
**What goes wrong:** `async with MultiServerMCPClient({...}) as client:` パターンでコンテキストマネージャーを使うと、v0.2.2 では想定外の動作またはエラー。
**Why it happens:** STATE.md `[v5.0 Research]` に明記: 「v0.2.2 では async with パターン廃止」
**How to avoid:** `client = MultiServerMCPClient({...})` → `tools = await client.get_tools()` を使う。
**Warning signs:** AttributeError または `__aenter__` not found。

### Pitfall 3: mcp-server が 0.0.0.0 にバインドしない
**What goes wrong:** `mcp.run(transport="http", host="127.0.0.1", port=8001)` でループバックバインドすると、他のコンテナから接続できない。
**Why it happens:** Docker コンテナ間通信はコンテナのネットワークインターフェース経由で行われるため、ループバックのみのバインドでは到達不可。
**How to avoid:** 必ず `host="0.0.0.0"` を指定する。
**Warning signs:** worker から `ConnectionRefusedError` または `Connection reset`.

### Pitfall 4: worker が mcp-server より先に起動する
**What goes wrong:** worker 起動時に `MultiServerMCPClient.get_tools()` を呼ぶと mcp-server がまだ healthy でなく接続失敗。
**Why it happens:** Docker Compose デフォルトの `depends_on` は `service_started` のみ確認。
**How to avoid:** `depends_on: mcp-server: condition: service_healthy` を設定し、mcp-server の healthcheck を正しく定義する。D-14 に明記済み。
**Warning signs:** worker 起動直後に `ConnectionRefusedError`.

### Pitfall 5: mcp_server/ の uv プロジェクトに curl がない
**What goes wrong:** `healthcheck: test: ["CMD-SHELL", "curl -f http://localhost:8001/health"]` が `bookworm-slim` イメージに curl がないため失敗。
**Why it happens:** `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` は slim イメージで curl を含まない。
**How to avoid:** `CMD-SHELL` で `python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"` を使うか、Dockerfile で curl をインストールする。Python 標準ライブラリ利用が最もシンプル。
**Warning signs:** `healthcheck: test` が `/bin/sh: curl: not found` で失敗し、コンテナが unhealthy のまま。

---

## Code Examples

### mcp_server/pyproject.toml（独立 uv プロジェクト）

```toml
# Source: D-03 (独立 uv プロジェクト)
[project]
name = "copilot-mcp-server"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=2.14.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Note:** `langchain-mcp-adapters` は worker 側（親 `pyproject.toml`）に追加する。mcp-server 自体には不要。

### Docker ヘルスチェック（curl なし対応）

```yaml
# Source: Pitfall 5 対処 + [VERIFIED: bookworm-slim に curl なし]
healthcheck:
  test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8001/health')\""]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 15s
```

### worker pyproject.toml への追加

```toml
# 親 pyproject.toml に追記 (worker コンテナが /app をマウント)
dependencies = [
    ...
    "langchain-mcp-adapters>=0.2.2",
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FastMCP SSE transport (`transport="sse"`) | streamable-http (`transport="http"`) | MCP仕様更新 2024年末 | SSE はセッションアフィニティ問題あり。Docker スケールアウト非対応。 |
| `async with MultiServerMCPClient(...)` | `client = ...; await client.get_tools()` | langchain-mcp-adapters 0.2.x | Context manager パターン廃止。直接インスタンス化+メソッド呼び出しへ。 |
| `create_sse_app()` 直接呼び出し | `mcp.run()` または `mcp.http_app()` | fastmcp 2.4.0+ | 低レベル API のカスタムルート問題 (issue #556) で高レベル API へ移行推奨。 |

**Deprecated/outdated:**
- `transport="sse"` in FastMCP: STATE.md 記載「sse はセッションアフィニティ問題あり」のため Phase 20 では使わない
- stdio transport: Docker コンテナ間通信不可 (STATE.md `[v5.0 Research]` に明記)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | fastmcp 3.2.3 で `@mcp.custom_route` が正常動作する（issue #556 は 2.4.0 のみ、修正済み） | Common Pitfalls | カスタムルートが 404 → `http_app()` 手動パターンへフォールバック |
| A2 | `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` に curl が含まれない | Common Pitfalls / Code Examples | curl が実は含まれていた場合はヘルスチェック設定を簡略化できる |
| A3 | `uv run python server.py` で mcp_server/ のプロジェクト依存が自動インストールされる | Docker Compose パターン | uv sync が必要な場合は command を `uv sync && uv run python server.py` に変更 |

---

## Open Questions

1. **fastmcp の stateless HTTP モード（`FASTMCP_STATELESS_HTTP=true`）は必要か**
   - What we know: デフォルトはステートフル（サーバーサイドセッション保持）。スケールアウト時は stateless が必要。
   - What's unclear: Phase 20 のシングルインスタンス構成では関係ないが、将来 workers 複数台になった場合に影響。
   - Recommendation: Phase 20 ではデフォルト（stateless 不要）。Phase 24 以降のスケールアウト設計時に再検討。

2. **`uv run` の working_dir と mcp_server/ マウント戦略**
   - What we know: 既存 worker は `working_dir: /app` + `volumes: .:/app`。mcp-server は `working_dir: /mcp_server` + `volumes: ./mcp_server:/mcp_server` の予定（D-01）。
   - What's unclear: uv が `/mcp_server` を独立プロジェクトとして認識するか（`.venv` の配置）。
   - Recommendation: `command: uv run --project /mcp_server python server.py` または Dockerfile を作成して `uv sync` 実行済みイメージを使う方が確実。ただし Dockerfile なしで動くか試みてから判断。

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | mcp-server コンテナ起動 | ✓ | 29.3.1 | — |
| Docker Compose | サービス統合 | ✓ | v5.1.1 | — |
| Python 3.12 | mcp_server/ ランタイム | ✓ | 3.12.3 | — |
| uv | 依存管理 | ✓ | 0.8.4 | — |
| fastmcp | MCP サーバー | ✗（未インストール、PyPI 利用可） | 3.2.3 on PyPI | — |
| langchain-mcp-adapters | worker 側接続確認 | ✗（未インストール、PyPI 利用可） | 0.2.2 on PyPI | — |

**Missing dependencies with no fallback:** なし（すべて PyPI から `uv add` で追加可能）

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` (root) — `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_mcp_server.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01 | mcp-server が healthy で起動し、worker から HTTP 接続できる | integration (Docker 必要) | manual / `docker compose up` smoke test | ❌ Wave 0 |
| MCP-01 | `/health` が 200 OK を返す | unit (httpx ASGI) | `uv run pytest tests/test_mcp_server.py::test_health_endpoint -x` | ❌ Wave 0 |
| MCP-02 | `@mcp.tool` で 4 スタブが登録され `get_tools()` でリストが返る | unit (httpx ASGI または mock) | `uv run pytest tests/test_mcp_server.py::test_stub_tools -x` | ❌ Wave 0 |
| MCP-02 | `ping` スタブが正常レスポンスを返す | unit | `uv run pytest tests/test_mcp_server.py::test_ping_tool -x` | ❌ Wave 0 |

**Note:** MCP-01 の Docker 統合テストはローカル Docker Compose 環境でのみ実行可能（CI は Phase 20 スコープ外）。unit テストは FastMCP の ASGI インターフェース経由で httpx でテスト可能か確認が必要。

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_mcp_server.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green + `docker compose up` での手動 smoke test

### Wave 0 Gaps
- [ ] `tests/test_mcp_server.py` — MCP-01/MCP-02 カバレッジ（`/health`、`get_tools()`、`ping` ツール）
- [ ] FastMCP テストパターン確認（ASGI テストが可能か、または subprocess 起動が必要か）

---

## Project Constraints (from CLAUDE.md)

- **Tech Stack:** Python (FastAPI / LangGraph / LangChain) + Docker Compose。今回追加する mcp-server も同じ Python スタック。
- **ベースイメージ:** `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` — 全コンテナ統一（CLAUDE.md + D-04）
- **Primary startup method:** `docker compose up` — uvicorn 直接起動は開発確認用のみ
- **ブランチ必須:** GSD ワークフロー開始時にブランチを作成すること
- **応答言語:** すべて日本語

---

## Sources

### Primary (HIGH confidence)
- [gofastmcp.com/deployment/http](https://gofastmcp.com/deployment/http) — streamable-http トランスポート設定、`@mcp.custom_route`、`host="0.0.0.0"` バインド
- [deepwiki.com/langchain-ai/langchain-mcp-adapters/2.1-multiservermcpclient](https://deepwiki.com/langchain-ai/langchain-mcp-adapters/2.1-multiservermcpclient) — `MultiServerMCPClient` コンストラクタ、`"streamable_http"` キー名、`get_tools()` パターン
- pip registry — fastmcp 3.2.3、langchain-mcp-adapters 0.2.2、mcp 1.27.0 [VERIFIED: pip index versions]

### Secondary (MEDIUM confidence)
- [github.com/jlowin/fastmcp/issues/556](https://github.com/jlowin/fastmcp/issues/556) — `@custom_route` 問題の経緯と修正確認
- [github.com/jlowin/fastmcp/issues/987](https://github.com/jlowin/fastmcp/issues/987) — `/health` エンドポイント追加パターン
- `.planning/STATE.md` `[v5.0 Research]` セクション — streamable-http 必須、async with 廃止の既往調査結果

### Tertiary (LOW confidence)
- WebSearch: fastmcp Docker health endpoint パターン（コミュニティ記事）

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pip registry で最新バージョン確認済み
- Architecture: HIGH — FastMCP 公式 docs + langchain-mcp-adapters DeepWiki で確認済み
- Pitfalls: HIGH — GitHub Issues で実際の問題と修正を確認済み。curl なし問題は [ASSUMED] だが slim イメージの標準的な注意点

**Research date:** 2026-04-10
**Valid until:** 2026-05-10（fastmcp は活発に開発中のため 30 日以内に再確認推奨）
