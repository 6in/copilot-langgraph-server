# Phase 37 Spike: MultiServerMCPClient headers サポート

**Date:** 2026-04-21
**Version:** langchain-mcp-adapters 0.2.2 / mcp (SDK) 1.27.0 / fastmcp 3.2.3
Verdict: Route A 採用 / **詳細:** Route A (MCP headers via MultiServerMCPClient)

---

## 証拠

### 1. ソース確認結果

**ファイル:** `.venv/lib/python3.12/site-packages/langchain_mcp_adapters/sessions.py`

`StreamableHttpConnection` TypedDict（L165-193）に `headers` フィールドが **存在する**:

```python
class StreamableHttpConnection(TypedDict):
    """Connection configuration for Streamable HTTP transport."""

    transport: Literal["streamable_http"]
    url: str

    headers: NotRequired[dict[str, Any] | None]   # ← L173: フィールド存在確認
    """HTTP headers to send to the endpoint."""

    timeout: NotRequired[timedelta]
    sse_read_timeout: NotRequired[timedelta]
    terminate_on_close: NotRequired[bool]
    session_kwargs: NotRequired[dict[str, Any] | None]
    httpx_client_factory: NotRequired[McpHttpClientFactory | None]
    auth: NotRequired[httpx.Auth]
```

**ファイル:** `.venv/lib/python3.12/site-packages/langchain_mcp_adapters/sessions.py`

`_create_streamable_http_session`（L316-360）が `headers` を `streamablehttp_client` に引き渡す:

```python
async def _create_streamable_http_session(
    *,
    url: str,
    headers: dict[str, Any] | None = None,  # ← 受け取る
    ...
) -> AsyncIterator[ClientSession]:
    ...
    async with (
        streamablehttp_client(
            url,
            headers,           # ← mcp SDK へ転送
            timeout,
            sse_read_timeout,
            terminate_on_close,
            auth=auth,
            **kwargs,
        ) as (read, write, _),
        ...
    ):
```

**ファイル:** `.venv/lib/python3.12/site-packages/mcp/client/streamable_http.py`

`streamablehttp_client`（L684-722、`@deprecated` だが現在も有効）が `headers` を `httpx_client_factory` に渡す:

```python
async def streamablehttp_client(
    url: str,
    headers: dict[str, str] | None = None,
    ...
    httpx_client_factory: McpHttpClientFactory = create_mcp_http_client,
    ...
):
    client = httpx_client_factory(   # ← factory 呼び出し
        headers=headers,             # ← headers が httpx.AsyncClient へ
        timeout=httpx.Timeout(timeout_seconds, read=sse_read_timeout_seconds),
        auth=auth,
    )
    async with client:
        async with streamable_http_client(url, http_client=client, ...) as streams:
            yield streams
```

**ファイル:** `.venv/lib/python3.12/site-packages/mcp/shared/_httpx_utils.py`

`create_mcp_http_client`（L65-96）が `headers` を `httpx.AsyncClient` のコンストラクタに渡す:

```python
def create_mcp_http_client(
    headers: dict[str, str] | None = None,
    ...
) -> httpx.AsyncClient:
    kwargs: dict[str, Any] = {"follow_redirects": True, ...}
    if headers is not None:
        kwargs["headers"] = headers    # ← httpx.AsyncClient へ格納
    return httpx.AsyncClient(**kwargs)
```

`httpx.AsyncClient` の client-level `headers` はすべてのリクエスト（POST / GET / DELETE）に
自動付与されるため、各 tool call の HTTP リクエストにも `x-thread-id` / `x-github-login` が含まれる。

### 2. FastMCP CurrentHeaders() 確認

```bash
$ python3 -c "
from fastmcp.dependencies import CurrentHeaders
print('CurrentHeaders import OK:', CurrentHeaders)
"
# 出力: CurrentHeaders import OK: <function CurrentHeaders at 0xffff812747c0>
```

FastMCP 3.2.3 で `CurrentHeaders()` が正常にインポートできることを確認。

### 3. 伝播チェーン全体

```
MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "url": "http://mcp-server:8001/mcp",
        "headers": {
            "x-thread-id": "...",
            "x-github-login": "..."
        }
    }
})
    ↓ sessions.py: StreamableHttpConnection["headers"]
    ↓ _create_streamable_http_session(headers=...)
    ↓ streamablehttp_client(url, headers, ...)   [deprecated だが動作]
    ↓ create_mcp_http_client(headers=headers)
    ↓ httpx.AsyncClient(headers=headers)         [client-level defaults]
    ↓ 各 HTTP POST リクエストに自動付与
    ↓ FastMCP server: request.headers["x-thread-id"]
    ↓ CurrentHeaders() dependency injection で取得可能
```

### 4. 留意事項: 非推奨 API について

MCP SDK 1.27.0 で `streamablehttp_client` は `@deprecated` となり、
新 API `streamable_http_client` が導入されている。新 API は `http_client: httpx.AsyncClient | None` 引数を取り、
headers は `httpx.AsyncClient` に直接設定する方式に変更された。

langchain-mcp-adapters 0.2.2 は旧 API を使用しているが、旧 API は引き続き動作し、
`headers` → `httpx.AsyncClient` の変換を内部で処理する。

**影響:** langchain-mcp-adapters が新 API に対応する将来バージョンでは `httpx_client_factory` パターンへの移行が必要になる可能性があるが、現時点では Route A の実装に支障はない。

---

## 結論

- **Route A (MCP headers 採用)**: `MultiServerMCPClient` に `headers` を渡すことで、
  各 tool call の HTTP リクエストに `x-thread-id` / `x-github-login` が自動付与される。
  mcp-server 側の `@mcp.tool` は `CurrentHeaders()` dependency で受け取れる。

### Route A 採用時の実装方針

`attachments_list` / `attachments_extract` ツールは以下のパターンで実装する:

```python
from fastmcp.dependencies import CurrentHeaders

@mcp.tool
async def attachments_list(headers: dict = CurrentHeaders()) -> list[dict]:
    thread_id = headers.get("x-thread-id")
    github_login = headers.get("x-github-login")
    # thread_id でユーザーの添付ファイル一覧を取得
    ...

@mcp.tool
async def attachments_extract(
    attachment_id: str,
    headers: dict = CurrentHeaders()
) -> dict:
    thread_id = headers.get("x-thread-id")
    github_login = headers.get("x-github-login")
    # attachment_id + thread_id でファイルを特定してテキスト抽出
    ...
```

worker.py 側は `MultiServerMCPClient` の設定に `headers` を追加するだけでよい:

```python
mcp_client = MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "url": mcp_url,
        "headers": {
            "x-thread-id": ctx.thread_id,
            "x-github-login": ctx.github_login,
        },
    }
})
```

---

## Wave 1 への影響

Plan 03 Task 3 は **Route A (CurrentHeaders()) の 1 経路のみ実装**する。
Route B (httpx 直接呼び出し) のコードは導入しない。

具体的には:
- `mcp_server/tools/attachments.py`: `@mcp.tool` + `CurrentHeaders()` で実装
- `app/jobs/worker.py`: `MultiServerMCPClient` の `headers` フィールドに RPCContext を渡す
- `/internal/attachments_*` REST エンドポイントは **追加しない**（Route B 不採用）

**pip show 実ログ:**

```
Name: langchain-mcp-adapters
Version: 0.2.2
```

（`.venv/lib/python3.12/site-packages/langchain_mcp_adapters-0.2.2.dist-info/METADATA` より確認）
