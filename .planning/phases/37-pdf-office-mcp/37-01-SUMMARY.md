---
phase: 37
plan: "01"
subsystem: mcp
tags: [mcp, fastmcp, rpc-context, spike, headers, route-a]
dependency_graph:
  requires: []
  provides:
    - "Route A verdict: MultiServerMCPClient headers → CurrentHeaders() 伝播確認"
    - "Wave 1 (Plan 03) の attachments_list/extract 実装経路確定"
  affects:
    - "app/jobs/worker.py (MultiServerMCPClient 設定に headers 追加)"
    - "mcp_server/tools/attachments.py (CurrentHeaders() 依存注入パターン)"
tech_stack:
  added: []
  patterns:
    - "Route A: MultiServerMCPClient headers → httpx.AsyncClient → CurrentHeaders()"
key_files:
  created:
    - work/phase-37/spike-mcp-headers.md
    - tests/test_mcp_client_headers.py
  modified: []
decisions:
  - "Route A 採用: langchain-mcp-adapters 0.2.2 の StreamableHttpConnection に headers フィールドが存在し、httpx.AsyncClient 経由で各 tool call に付与される"
  - "Route B (httpx 直接呼び出し + /internal/attachments_* REST エンドポイント) は不採用"
  - "FastMCP 3.2.3 の CurrentHeaders() で mcp-server 側がヘッダーを受け取れることをソース確認"
metrics:
  duration: "~4 min"
  completed: "2026-04-21"
  tasks_completed: 3
  files_created: 2
  files_modified: 0
---

# Phase 37 Plan 01: Spike MCP Headers Summary

**One-liner:** langchain-mcp-adapters 0.2.2 の `StreamableHttpConnection.headers` フィールドが `httpx.AsyncClient` 経由で全 tool call に伝播し、FastMCP `CurrentHeaders()` で受け取れることをソース分析で確認 → Route A 採用確定

---

## Spike Verdict

**Verdict: Route A 採用**

`MultiServerMCPClient` の `streamable_http` 接続設定に `headers` を渡すと、`httpx.AsyncClient(headers=...)` として client-level defaults に格納され、`attachments_list` / `attachments_extract` の各 HTTP リクエストに `x-thread-id` / `x-github-login` が自動付与される。FastMCP 3.2.3 の `CurrentHeaders()` dependency injection で mcp-server 側が受け取れる。

---

## 根拠 (ソース確認)

### 伝播チェーン

```
MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "headers": {"x-thread-id": ..., "x-github-login": ...}
    }
})
  → sessions.py: StreamableHttpConnection.headers (NotRequired フィールド存在 L173)
  → _create_streamable_http_session(headers=...)
  → streamablehttp_client(url, headers, ...)        [deprecated だが有効]
  → create_mcp_http_client(headers=headers)
  → httpx.AsyncClient(headers=headers)             [client-level defaults]
  → 各 POST/GET リクエストに自動付与
  → FastMCP: CurrentHeaders() → headers["x-thread-id"]
```

### 確認バージョン

- `langchain-mcp-adapters`: 0.2.2
- `mcp` (SDK): 1.27.0
- `fastmcp`: 3.2.3

### Key source lines

| ファイル | 行 | 内容 |
|---|---|---|
| `sessions.py` | L173 | `headers: NotRequired[dict[str, Any] \| None]` in `StreamableHttpConnection` |
| `sessions.py` | L349 | `streamablehttp_client(url, headers, ...)` に headers を転送 |
| `streamable_http.py` | L709 | `httpx_client_factory(headers=headers, ...)` に headers を渡す |
| `_httpx_utils.py` | L82 | `kwargs["headers"] = headers` → `httpx.AsyncClient(**kwargs)` |

---

## Wave 1 への引き渡し事項

| 項目 | 内容 |
|---|---|
| Plan 03 Task 3 実装経路 | **Route A のみ** (1 本道) |
| mcp-server 側パターン | `@mcp.tool` + `CurrentHeaders()` dependency |
| worker.py 側変更 | `MultiServerMCPClient` の設定に `headers` を追加 |
| 不採用事項 | `/internal/attachments_*` REST エンドポイントは追加しない |

**worker.py 追加イメージ (Plan 03):**
```python
mcp_client = MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "url": mcp_url,
        "headers": {
            "x-thread-id": context.thread_id,
            "x-github-login": context.github_login,
        },
    }
})
```

**mcp_server 側実装イメージ (Plan 03):**
```python
from fastmcp.dependencies import CurrentHeaders

@mcp.tool
async def attachments_list(headers: dict = CurrentHeaders()) -> list[dict]:
    thread_id = headers.get("x-thread-id")
    github_login = headers.get("x-github-login")
    ...
```

---

## Deviations from Plan

### Auto-fixed Issues

なし。

### 注記: work/ ディレクトリの .gitignore 除外対応

`work/` が `.gitignore` に登録されているため、`git add -f` で強制ステージングした。
これはスパイク成果物を計画ドキュメントとして保存するための意図的な操作であり、
`.gitignore` は将来的に `work/phase-*/` を除外から外すことを検討してよい。

---

## Known Stubs

なし。`test_mcp_client_headers.py` の xfail テストは Wave 1 本実装後に実テストへ昇格予定だが、
これはスタブではなくスケルトン (骨組み) として設計されており、plan の目的 (Wave 0 spike 完結) を阻害しない。

---

## Threat Flags

T-37-SP-01 (mcp_server/server.py への一時ログ追加リスク) は **発生しなかった**。
ソース分析のみで Route A を確認できたため、本番コードへの一時ログ追加は不要だった。
`git diff mcp_server/server.py` はクリーン。

---

## Self-Check: PASSED

**Commit hashes:**

| Task | Commit | Files |
|------|--------|-------|
| Task 0 (ブランチ確認) | 819f419 | (empty commit) |
| Task 1 (spike verdict) | b951516 | work/phase-37/spike-mcp-headers.md |
| Task 2 (テストスケルトン) | c1a168e | tests/test_mcp_client_headers.py |

**Verified:**
- work/phase-37/spike-mcp-headers.md: FOUND
- tests/test_mcp_client_headers.py: FOUND
- .planning/phases/37-pdf-office-mcp/37-01-SUMMARY.md: FOUND
- All 3 commit hashes verified in git log
- Verdict: Route A confirmed in spike-mcp-headers.md
