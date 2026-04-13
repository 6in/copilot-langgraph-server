---
phase: 24
plan: 1
subsystem: orchestrator/tool-registry
tags: [tool-registry, mcp, yaml, worker, validation]
dependency_graph:
  requires: [phase-23-db-claude-code]
  provides: [MCP-03-tool-registry]
  affects: [app/jobs/worker.py, app/orchestrator/tool_registry.py]
tech_stack:
  added: []
  patterns: [YAML catalog validation, mcp_connected flag, try/except 外 RuntimeError 伝播]
key_files:
  created:
    - app/orchestrator/tool_registry.py
    - config/mcp_tools.yaml
    - config/mcp_tools.yaml.example
    - tests/test_tool_registry.py
  modified:
    - app/jobs/worker.py
    - tests/test_worker.py
decisions:
  - mcp_connected フラグで DEGRADED モードと接続成功を区別し、validate() は try/except 外に配置
  - AsyncConnectionPool もモックが必要（config/db_pools.yaml が存在するため）
  - sys.modules スタブで langchain_mcp_adapters 未インストール環境でも worker テストを実行可能にした
metrics:
  duration: 約20分
  completed: "2026-04-13"
  tasks_completed: 3
  files_created: 4
  files_modified: 2
---

# Phase 24 Plan 1: ToolRegistry + mcp_tools.yaml + worker startup 統合 Summary

## One-liner

YAML カタログ（config/mcp_tools.yaml）と MCP 実ツールリストの完全一致を worker 起動時に検証する ToolRegistry クラス実装 + startup() 統合（MCP-03）

## What Was Built

### ToolRegistry クラス（app/orchestrator/tool_registry.py）

```
ToolRegistry(yaml_path: str)
  .expected_tool_names() -> frozenset[str]   — YAML カタログのツール名集合
  .validate(mcp_tools: list[BaseTool]) -> None  — 双方向一致検証、不一致で RuntimeError
```

- `yaml.safe_load()` で YAML を読み込み `frozenset` に変換
- `validate()` は `actual - expected`（MCP のみ）と `expected - actual`（YAML のみ）の差集合を双方向チェック
- 不一致時: `"[ToolRegistry] mcp_tools.yaml と MCP サーバーのツールリストが不一致。 YAML のみ: [...], MCP のみ: [...]"` という RuntimeError を raise

### config/mcp_tools.yaml（4 ツール宣言）

```yaml
tools:
  - name: ping        # MCP ヘルスチェック
  - name: web_search  # Tavily Web 検索
  - name: db_query    # PostgreSQL SELECT-only
  - name: claude_code # Claude Code CLI サブプロセス
```

### worker.py startup() への統合

**挿入パターン（Pitfall 1 対応）:**

```python
# try/except 内: MCP 接続 → mcp_connected = True, mcp_tools_loaded に格納
# except 内: DEGRADED ログ（従来通り）

# try/except の外（= RuntimeError が伝播する位置）:
if mcp_connected:
    registry = ToolRegistry(MCP_TOOLS_CONFIG)
    await registry.validate(mcp_tools_loaded)  # 不一致 → RuntimeError → worker 起動失敗
    ctx["mcp_tools"] = mcp_tools_loaded        # バリデーション成功後のみ代入
```

`mcp_connected` フラグにより DEGRADED モード（MCP 接続失敗）はバリデーションをスキップして従来挙動を維持する。

## テスト結果

```
tests/test_tool_registry.py: 6/6 passed
  - test_tool_registry_expected_names
  - test_tool_registry_empty_yaml_section
  - test_tool_registry_validate_pass
  - test_tool_registry_validate_fail_missing
  - test_tool_registry_validate_fail_extra
  - test_tool_registry_file_not_found

tests/test_worker.py (Phase 24 新規 3 テスト): 3/3 passed
  - test_startup_tool_registry_validate_pass
  - test_startup_tool_registry_validate_fail_propagates
  - test_startup_mcp_connection_failure_still_degraded
```

既存の test_worker.py テスト失敗（5件）は Phase 24 以前から存在するホスト環境の問題（PostgreSQL 未起動、ChatCopilot モック不整合）であり、Phase 24 の変更とは無関係。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] テストモックの2点修正**

**Found during:** タスク 24-01-03

**Issue 1: `langchain_mcp_adapters` がホスト環境に未インストール**
- worker.py の `startup()` は lazy import（try ブロック内）で `langchain_mcp_adapters` を読み込む
- `patch("langchain_mcp_adapters.client.MultiServerMCPClient")` はモジュールが存在しないと `ModuleNotFoundError` を起こす
- **Fix:** `sys.modules` に `types.ModuleType` スタブを注入する `_make_mcp_stub()` ヘルパーと `patch.dict(sys.modules, ...)` パターンに変更

**Issue 2: `config/db_pools.yaml` が存在するため `AsyncConnectionPool` が実際の PostgreSQL に接続**
- `startup()` は `db_pools.yaml` が存在すれば `AsyncConnectionPool.open()` を呼ぶ
- ホスト環境では `postgres` ホストが解決できず 30 秒タイムアウト
- **Fix:** `patch("app.jobs.worker.AsyncConnectionPool", return_value=mock_pool)` を 3 テストすべてに追加

**Files modified:** tests/test_worker.py

## Commits

| Hash | Message |
|------|---------|
| ce841ac | feat(24-01): ToolRegistry クラス + テスト (MCP-03) |
| 8f5370a | feat(24-01): config/mcp_tools.yaml カタログ + example (MCP-03) |
| 217158f | feat(24-01): worker startup に ToolRegistry バリデーション統合 (MCP-03) |

## Known Stubs

なし。実装はすべて本番品質で完成している。

## Threat Flags

なし。新規エンドポイント・認証パス・ネットワーク公開面は追加していない。

## Self-Check

ファイル存在確認:
- app/orchestrator/tool_registry.py: FOUND
- config/mcp_tools.yaml: FOUND
- config/mcp_tools.yaml.example: FOUND
- tests/test_tool_registry.py: FOUND

コミット確認:
- ce841ac: FOUND
- 8f5370a: FOUND
- 217158f: FOUND
