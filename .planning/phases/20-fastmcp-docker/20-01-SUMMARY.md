---
phase: 20-fastmcp-docker
plan: 01
subsystem: mcp-server
tags: [fastmcp, mcp, stub-tools, uv, python]
dependency_graph:
  requires: []
  provides: [mcp_server/server.py, mcp_server/tools/stubs.py, tests/test_mcp_server.py]
  affects: [Plan 02 Docker integration]
tech_stack:
  added: [fastmcp==3.2.3]
  patterns: [FastMCP in-process Client testing, @mcp.tool stub registration, @mcp.custom_route /health]
key_files:
  created:
    - mcp_server/pyproject.toml
    - mcp_server/server.py
    - mcp_server/tools/__init__.py
    - mcp_server/tools/stubs.py
    - mcp_server/uv.lock
    - mcp_server/README.md
    - tests/test_mcp_server.py
  modified:
    - pyproject.toml (root — added fastmcp to dev deps)
    - uv.lock (root — updated)
decisions:
  - "server.py chosen over main.py for entry point (Claude's Discretion)"
  - "tools/ subdirectory chosen over single stubs file for future extensibility (Claude's Discretion)"
  - "fastmcp added to root dev deps so uv run pytest tests/test_mcp_server.py works from repo root"
  - "fastmcp 3.2.3 installed (satisfies >=2.14.0,<4.0 constraint)"
metrics:
  duration: 4min
  completed: "2026-04-10"
  tasks: 2
  files: 9
---

# Phase 20 Plan 01: FastMCP Server + Stub Tools Summary

FastMCP 3.2.3 ベースの独立 uv プロジェクト `mcp_server/` を作成し、4 スタブツールと `/health` エンドポイントを提供。4 テスト全 PASSED。

## What Was Built

`mcp_server/` ディレクトリを新規作成し、FastMCP サーバーを独立 uv プロジェクト（D-03）として実装した。

- **`mcp_server/pyproject.toml`**: `copilot-mcp-server` uv プロジェクト、`fastmcp>=2.14.0,<4.0` を依存に持つ独立プロジェクト
- **`mcp_server/server.py`**: `FastMCP("copilot-mcp-server")` エントリポイント、`@mcp.custom_route("/health")` で Docker ヘルスチェック対応、`mcp.run(transport="http", host="0.0.0.0", port=8001)` でバインド
- **`mcp_server/tools/stubs.py`**: `register_tools(mcp)` 関数で 4 スタブを `@mcp.tool` 登録（D-10/D-11 準拠）
- **`tests/test_mcp_server.py`**: FastMCP in-process `Client` を使った 4 テスト（MCP-01/MCP-02）

## Test Results

```
tests/test_mcp_server.py::test_health_endpoint PASSED
tests/test_mcp_server.py::test_stub_tools_registered PASSED
tests/test_mcp_server.py::test_ping_tool PASSED
tests/test_mcp_server.py::test_stub_schemas_have_required_params PASSED

4 passed in 0.49s
```

## fastmcp Version

fastmcp **3.2.3** がインストールされた（制約 `>=2.14.0,<4.0` を満たす）。

## fastmcp Root Dev Dependency

**Yes** — fastmcp を root `pyproject.toml` の `[dependency-groups] dev` に追加した。  
理由: `uv run pytest tests/test_mcp_server.py -x` をリポジトリルートから実行するには fastmcp がルート venv に必要。これは D-03（runtime プロジェクトの独立）の例外だが、テストスイートの統合のために必要（プラン指示通り）。

## Claude's Discretion Decisions

1. **エントリポイントファイル名**: `server.py`（vs `main.py`）— FastMCP の慣習に合致し、`server.py` が内容を明示する
2. **ツールモジュール**: `tools/` サブディレクトリ（vs 単一 `stubs.py`）— Phase 22/23 でのツール追加・差し替えに対応した拡張可能な構造を選択

## API Behavior Verified (FastMCP 3.2.3)

- `Client(mcp).call_tool("ping", {})` → `CallToolResult(data={"status": "ok", "timestamp": "..."})` — `.data` フィールドに dict
- `mcp.http_app()` → ASGI app で `/health` が 200 `{"status": "ok"}` を返す
- `Client.list_tools()` → `[Tool(name=..., inputSchema={properties: {query: {type: "string"}}, ...})]`

## Verification

プラン検証コマンドの結果:

```
1. cd mcp_server && uv sync    → exit 0 ✓
2. uv run python -c "from server import mcp; print(mcp.name)"  → copilot-mcp-server ✓
3. uv run pytest tests/test_mcp_server.py -x -v  → 4 passed ✓
4. grep -c "@mcp.tool" mcp_server/tools/stubs.py  → 4 ✓
5. grep -q 'transport="http"' mcp_server/server.py  → exit 0 ✓
6. grep -q 'host="0.0.0.0"' mcp_server/server.py  → exit 0 ✓
7. grep -q "port=8001" mcp_server/server.py  → exit 0 ✓
```

## Deviations from Plan

None — plan executed exactly as written.

## Open Items for Plan 02

- `docker-compose.yml` に `mcp-server` サービスを追加（D-05）
- worker サービスに `depends_on: mcp-server: condition: service_healthy` を追加（D-07/D-14）
- worker 環境変数に `MCP_SERVER_URL=http://mcp-server:8001` を追加
- root `pyproject.toml` に `langchain-mcp-adapters` を追加（worker 側 MCP ツール取得用）
- Docker ヘルスチェック設定（`/health` エンドポイント使用）

## Threat Surface Scan

新規ネットワークエンドポイント（`/mcp`, `/health`）が追加されたが、これはプランの `<threat_model>` に記載済み（T-20-01, T-20-02）。Plan 01 スコープではホストポート非公開（D-06）— Docker 統合は Plan 02 で実施。

## Known Stubs

`mcp_server/tools/stubs.py` の 4 スタブはすべて意図的なスタブ（D-12 に記載）。Phase 22/23 で同名・同スキーマの本番実装に差し替え予定。テストが戻り値を検証するため、意図しないライブデータ漏洩を防いでいる（T-20-04 対応）。

## Self-Check: PASSED

- [x] mcp_server/pyproject.toml 存在確認
- [x] mcp_server/server.py 存在確認
- [x] mcp_server/tools/stubs.py 存在確認
- [x] tests/test_mcp_server.py 存在確認
- [x] Task 1 commit 2dc3a21 存在
- [x] Task 2 commit f78641d 存在
- [x] 4 tests passed
