---
phase: 22-web-search-tavily
plan: 01
status: complete
commit: 3491bf6
---

# Plan 22-01 Summary: Tavily web_search ツール実装

## What was built

`web_search_stub` を削除し、Tavily API を使う本番 `web_search` ツールに差し替えた。

## Files changed

| File | Change |
|------|--------|
| `mcp_server/tools/web_search.py` | 新規作成 — TavilySearchResults(max_results=3) + 1000文字切り捨て + エラーハンドリング |
| `mcp_server/tools/stubs.py` | `web_search_stub` 関数を完全削除 |
| `mcp_server/server.py` | `register_web_search_tools(mcp)` 追加、import 分離 |
| `mcp_server/pyproject.toml` | `langchain-community>=0.4.1` 追加 |
| `docker-compose.yml` | mcp-server に `TAVILY_API_KEY` 環境変数注入 |
| `agents/general-assistant/AGENT.md` | `web_search_stub` → `web_search` |
| `tests/test_mcp_server.py` | EXPECTED_TOOLS 更新 + 新規テスト3件追加（正常系・切り捨て・エラー） |
| `scripts/test_mcp_tools.py` | ツール名を `web_search` に更新 |

## Verification

```
tests/test_mcp_server.py::test_health_endpoint PASSED
tests/test_mcp_server.py::test_stub_tools_registered PASSED
tests/test_mcp_server.py::test_ping_tool PASSED
tests/test_mcp_server.py::test_stub_schemas_have_required_params PASSED
tests/test_mcp_server.py::test_web_search_normal PASSED        (SEARCH-01)
tests/test_mcp_server.py::test_web_search_truncates_content PASSED  (SEARCH-02)
tests/test_mcp_server.py::test_web_search_error_handling PASSED
7 passed in 0.70s
```

## Key decisions

- mock パッチ先: `langchain_community.tools.tavily_search.TavilySearchResults`（関数内 import のため）
- エラー時は `{"error": "web_search failed: ..."}` を返してジョブ失敗を防ぐ
- `TAVILY_API_KEY` は `.env` 経由で docker-compose に注入（ソースコードにハードコードしない）
