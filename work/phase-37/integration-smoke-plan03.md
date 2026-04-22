# Phase 37 Plan 03 — Integration Smoke Results

**Date:** 2026-04-21
**Route:** A (MultiServerMCPClient headers → CurrentHeaders() DI)
**Status:** Unit-level smoke PASSED; Docker compose smoke deferred to Plan 05 (live environment)

## Unit Smoke (in-process, Plan 03 Task 3)

全8ケースが mcp_server venv 経由で GREEN:

```
PYTHONPATH=mcp_server/.venv/lib/python3.12/site-packages:mcp_server uv run pytest \
    tests/test_attachments_extract.py tests/test_attachments_list.py -v
```

```
8 passed in 1.25s
```

## RPCContext Propagation Verified

Route A の伝搬チェーン:
1. `langgraph_handler.py`: per-request `MultiServerMCPClient` with `"x-thread-id"` / `"x-github-login"` headers
2. `mcp_server/tools/attachments.py`: `CurrentHeaders()` DI で受け取り → `attachments_list_core / attachments_extract_core` に渡す
3. `execute_python.py`: `CurrentHeaders()` DI → subprocess env `X_THREAD_ID` / `X_GITHUB_LOGIN`
4. `mcp_helper_utils._call_tool()`: env から読み取り → `X-Thread-Id` / `X-Github-Login` ヘッダーで `/internal/call_tool` に転送

## Docker Compose Smoke (Expected)

```bash
# mcp-server /internal/call_tool 経由の期待レスポンス:

curl -X POST http://localhost:8001/internal/call_tool \
    -H "Content-Type: application/json" \
    -H "X-Thread-Id: testthread" \
    -H "X-Github-Login: testuser" \
    -d '{"tool": "attachments_list", "args": {}}'
# 期待: {"result": [{"name": "sample.docx", "size": N, ...}]}

curl -X POST http://localhost:8001/internal/call_tool \
    -H "Content-Type: application/json" \
    -H "X-Thread-Id: testthread" \
    -H "X-Github-Login: testuser" \
    -d '{"tool": "attachments_extract", "args": {"filename": "sample.docx"}}'
# 期待: {"result": {"content": "...", "error": null, "truncated": false, ...}}
```

Live docker compose integration は Plan 05 Task 3 で実施予定。
SC-3 (D-17 / ROADMAP SC-3) は Route A の実装が成立しており、
Plan 05 のエンドツーエンド検証で完全クローズする。

## Deviations

- `test_extract_password_protected` はルート venv では `markitdown` 未インストールのため skip。
  mcp_server venv (PYTHONPATH 付き) では PASSED。
  Plan 05 の Docker 環境テストで完全 GREEN になる予定。
