---
phase: 28-codeact-llm
plan: "01"
subsystem: mcp-tools
tags: [execute_python, sandbox, ast-whitelist, subprocess, mcp, security]
dependency_graph:
  requires: []
  provides:
    - execute_python MCP ツール (mcp_server/tools/execute_python.py)
    - sandbox_allowlist.yaml (config/sandbox_allowlist.yaml)
  affects:
    - mcp_server/server.py
    - config/mcp_tools.yaml
    - tests/test_mcp_server.py
tech_stack:
  added:
    - pyyaml (execute_python.py で sandbox_allowlist.yaml を読む)
    - resource stdlib (RLIMIT_AS メモリ制限)
    - ast stdlib (インポートホワイトリストチェック)
  patterns:
    - claude_code.py サブプロセス実行パターン踏襲 (D-01)
    - ALLOWED_ENV_KEYS frozenset env サニタイズ (D-08)
    - SIGTERM→SIGKILL エスカレーション (D-03)
    - preexec_fn=_set_limits RLIMIT_AS 512MB (D-02)
key_files:
  created:
    - mcp_server/tools/execute_python.py
    - config/sandbox_allowlist.yaml
  modified:
    - mcp_server/server.py
    - config/mcp_tools.yaml
    - tests/test_mcp_server.py
decisions:
  - "execute_python は claude_code.py のサブプロセスパターンを完全踏襲 — 同一の env サニタイズ・タイムアウト・SIGTERM/SIGKILL 設計で一貫性を確保"
  - "sandbox_allowlist.yaml は環境変数 SANDBOX_ALLOWLIST で上書き可能 — コンテナ再起動なしでパス変更に対応"
  - "_cached_allowlist でプロセス起動時に一度だけ YAML を読み込み — 毎リクエストのファイルI/Oを回避"
  - "SEARCH-02 テストの切り捨て文字数を 1000→500 に修正 (Rule 1 Bug Fix) — web_search.py は Phase 22 以降 500 文字に変更されていたがテストが追従していなかった"
metrics:
  duration: 4min
  completed_date: "2026-04-17"
  tasks_completed: 2
  files_changed: 5
---

# Phase 28 Plan 01: execute_python MCP サンドボックスツール Summary

AST インポートホワイトリスト + env サニタイズ + RLIMIT_AS 512MB + 60s タイムアウトによる Python サンドボックス実行 MCP ツールを実装し FastMCP サーバーに登録した。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | execute_python MCP ツール + sandbox_allowlist.yaml 作成 | dc5fe2d | mcp_server/tools/execute_python.py, config/sandbox_allowlist.yaml |
| 2 | MCP サーバー登録 + mcp_tools.yaml 更新 + テスト追加 | 2c2954d | mcp_server/server.py, config/mcp_tools.yaml, tests/test_mcp_server.py |

## What Was Built

### execute_python MCP ツール (`mcp_server/tools/execute_python.py`)

`claude_code.py` のサブプロセス実行パターンを踏襲した Python サンドボックス実行ツール。

**セキュリティ機構:**
- **AST インポートホワイトリスト (D-10/D-11)**: `_check_imports()` が `ast.walk()` で全 import/from 文を解析し、`sandbox_allowlist.yaml` に掲載されていないモジュールをブロック
- **env サニタイズ (D-08)**: `ALLOWED_ENV_KEYS = {"PATH", "HOME", "LANG", "LC_ALL", "TERM"}` のみ子プロセスに渡す — DATABASE_URL・SECRET_KEY 等を遮断
- **メモリ制限 (D-02)**: `preexec_fn=_set_limits` で `RLIMIT_AS = 512MB` を子プロセスに適用
- **タイムアウト + エスカレーション (D-03)**: 60s で SIGTERM、5s grace 後に SIGKILL

**レスポンス形式:**
```
{"stdout": str, "stderr": str, "exit_code": int, "truncated": bool}
エラー時: + "error": str
```

### sandbox_allowlist.yaml (`config/sandbox_allowlist.yaml`)

31 個の標準ライブラリモジュールを許可。危険なモジュール（`os`, `subprocess`, `sys`, `shutil`, `socket` 等）は含まれていない。

### MCP サーバー統合

- `mcp_server/server.py`: `register_execute_python_tools(mcp)` を `register_claude_code_tools(mcp)` の直後に追加
- `config/mcp_tools.yaml`: `execute_python` エントリ追加（`privileged: true`）

### テスト追加 (`tests/test_mcp_server.py`)

| テスト | 対応要件 | 内容 |
|--------|---------|------|
| `test_execute_python_returns_stdout` | EXEC-01 | 正常出力が stdout に含まれる |
| `test_execute_python_env_sanitized` | EXEC-02 | DATABASE_URL/SECRET_KEY がサブプロセスに渡らない |
| `test_execute_python_timeout` | EXEC-03 | タイムアウト時に terminate が呼ばれ error が返る |
| `test_execute_python_blocks_disallowed_import` | EXEC-04 | subprocess import がブロックされる |
| `test_execute_python_allows_whitelisted_import` | EXEC-05 | math import は通過する |

## Verification Results

```
31 passed, 2 deselected (integration tests require live PostgreSQL), 2 warnings
```

- `grep -c "execute_python" mcp_server/server.py` → 2 (import + 登録)
- `grep "execute_python" config/mcp_tools.yaml` → エントリ存在
- `grep "privileged: true" config/mcp_tools.yaml | wc -l` → 2 (claude_code + execute_python)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SEARCH-02 テストの切り捨て文字数不整合を修正**
- **Found during:** Task 2 テスト実行
- **Issue:** `test_web_search_truncates_content` が `len(...) == 1000` を期待していたが、`web_search.py` は Phase 22 以降 `max_content = 500` に変更されており、テストが追従していなかった
- **Fix:** テストのアサートを `== 1000` → `== 500` に修正し、ドキュメントコメントで理由（Copilot SDK タイムアウト対策）を追記
- **Files modified:** `tests/test_mcp_server.py`
- **Commit:** 2c2954d

## Threat Surface

実装は計画の `<threat_model>` で定義された全 5 脅威（T-28-01〜05）に対応済み。新規の未計画ネットワークエンドポイント・認証パス・スキーマ変更なし。

## Self-Check: PASSED

| Item | Status |
|------|--------|
| mcp_server/tools/execute_python.py | FOUND |
| config/sandbox_allowlist.yaml | FOUND |
| mcp_server/server.py | FOUND |
| config/mcp_tools.yaml | FOUND |
| tests/test_mcp_server.py | FOUND |
| .planning/phases/28-codeact-llm/28-01-SUMMARY.md | FOUND |
| commit dc5fe2d (Task 1) | FOUND |
| commit 2c2954d (Task 2) | FOUND |
