---
phase: 37
plan: "04"
subsystem: handler-system-prompt-delete-hook
tags: [langgraph-handler, system-prompt, delete-hook, path-traversal-guard, attachments]
dependency_graph:
  requires: ["37-02", "37-03"]
  provides: ["handler-prepend", "delete-folder-hook"]
  affects: ["app/jobs/handlers/langgraph_handler.py", "app/api/routes/chat.py"]
tech_stack:
  added: []
  patterns:
    - "thread フォルダ scan (os.listdir + os.stat, RO mount 対応)"
    - "realpath prefix assert によるパストラバーサル遮断"
    - "SystemMessage prepend パターン (ADR-0025 拡張)"
key_files:
  created:
    - tests/test_langgraph_handler_attachments.py
  modified:
    - app/jobs/handlers/langgraph_handler.py
    - app/api/routes/chat.py
    - tests/test_api_chat.py
    - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md
decisions:
  - "W-05 対応: handler 側に shutil を import しない (scan = listdir/stat のみ)"
  - "W-01 MUST 化: realpath prefix assert を必須処理として常時実行 (SHOULD → MUST)"
  - "psycopg mock は cursor() を MagicMock(return_value=AsyncMock()) で構成 (AsyncMock では coroutine が await されずエラー)"
  - "test_delete_thread_removes_folder は inline helper _make_delete_app_state で app.state を完全構成"
metrics:
  duration_minutes: 45
  completed_date: "2026-04-21"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 5
---

# Phase 37 Plan 04: Handler Prepend + Delete Hook Summary

**One-liner:** thread フォルダ scan → SystemMessage prepend + delete_thread での realpath guard 付き shutil.rmtree hook を LangGraphHandler と chat ルートに組み込んだ。

## What Was Built

### Task 1: LangGraphHandler に scan + prepend ロジックを追加 (commit: a17d26e)

`app/jobs/handlers/langgraph_handler.py` に以下を追加:

- `THREAD_FILES_DIR` 定数 — worker / api / mcp-server 共通の base path (D-01/D-04)
- `_scan_thread_attachments(thread_id, github_login) -> list[dict]` — `os.listdir` + `os.stat` のみ使用 (scan only, shutil 不使用 W-05)。フォルダ不在・権限エラー・空フォルダはすべて `[]` として扱う
- `_build_attachments_hint(attachments) -> str` — ファイル名・サイズ・拡張子と `attachments_extract` / `attachments_list` ツール呼び出し指示を含む hint 文字列を生成
- `_handle_inner()` 内で毎 turn scan を実行し、`attachments_hint` があれば system prompt 末尾に `## 添付ファイル\n` セクションとして prepend (D-11)
- `state_input` に `"attachments": attachments_meta or None` を追加 (D-12)

新規テストファイル `tests/test_langgraph_handler_attachments.py` (5件 passed):
- `test_scan_returns_sorted_metadata` — name/size/modified_at(float)/ext を確認
- `test_scan_empty_folder` — フォルダ不在時は []
- `test_scan_missing_context` — 空文字引数で即 []
- `test_build_hint_empty` — 空リストで空文字
- `test_build_hint_contains_filename_and_tool_instruction` — ツール名が hint に含まれる

### Task 2: delete_thread に shutil.rmtree hook を追加 (commit: 9353eff)

`app/api/routes/chat.py` に以下を追加:

- `import os, shutil` 追加
- `THREAD_FILES_DIR` 定数
- `adelete_thread` 直後に realpath prefix guard + `shutil.rmtree(real_folder, ignore_errors=True)` (D-03)
- path traversal 検出時 (realpath が `THREAD_FILES_DIR + os.sep` 配下でない) は `ValueError` を raise して rmtree をスキップ、204 は返す (T-37-04-01 MUST)

`tests/test_api_chat.py` の Wave 0 xfail を除去して実テストに置き換え (2件追加):
- `test_delete_thread_removes_folder` — rmtree が 1 回呼ばれ、`ignore_errors=True` が確認される
- `test_delete_thread_rejects_path_traversal` — `../../etc` が混入した場合に rmtree が呼ばれない

### Task 3: VALIDATION.md に Wave 2 行を追記 (commit: cadbe1c)

`37-VALIDATION.md` の Per-Task Verification Map に 3 行追記:
- `37-04-01`: scan metadata unit test
- `37-04-02`: delete folder hook unit test
- `37-04-03`: path traversal guard (W-01 MUST) unit test

## Test Results

| Test File | Count | Result |
|-----------|-------|--------|
| `tests/test_langgraph_handler_attachments.py` | 5 | passed |
| `tests/test_api_chat.py::test_delete_thread_removes_folder` | 1 | passed (xfail → GREEN) |
| `tests/test_api_chat.py::test_delete_thread_rejects_path_traversal` | 1 | passed |
| `tests/test_agent_state.py` | 3 | passed (regression なし) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] psycopg AsyncMock cursor 構成の修正**
- **Found during:** Task 2 テスト実行時 (503 エラー)
- **Issue:** プランのテンプレートでは `mock_conn.cursor.return_value.__aenter__ = AsyncMock(...)` を設定していたが、`cursor()` が `AsyncMock` の場合 coroutine が未 await のまま context manager に渡りエラー
- **Fix:** `cursor_ctx = AsyncMock(); cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)` とし `mock_conn.cursor = MagicMock(return_value=cursor_ctx)` で正しく構成
- **Files modified:** tests/test_api_chat.py
- **Commit:** 9353eff

**2. [Rule 2 - Missing] app.state.db_uri が未設定で AttributeError**
- **Found during:** Task 2 テスト実行時 (delete_thread が `request.app.state.db_uri` を参照)
- **Fix:** `_make_delete_app_state()` ヘルパーで `app.state.db_uri` を含む完全な app.state セットアップを実施
- **Files modified:** tests/test_api_chat.py
- **Commit:** 9353eff

### Pre-existing Issues (Deferred)

`tests/test_api_chat.py::test_new_thread_returns_uuid` が本 Plan 実行前から失敗していることを確認 (git stash で検証)。`POST /api/threads` が 401 を返す問題で、本 Plan の変更とは無関係。スコープ外のため修正せず記録のみ。

## Threat Flags

なし (新規ネットワークエンドポイント・スキーマ変更なし)

## Known Stubs

なし

## Self-Check

### Created files exist

- [x] `tests/test_langgraph_handler_attachments.py` — FOUND
- [x] `.planning/phases/37-pdf-office-mcp/37-04-SUMMARY.md` — FOUND (本ファイル)

### Modified files contain expected patterns

- [x] `grep "_scan_thread_attachments" app/jobs/handlers/langgraph_handler.py` — 2 件
- [x] `grep "shutil.rmtree" app/api/routes/chat.py` — 1 件
- [x] `grep -c "^| 37-04-" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md` — 3 件

### Commits exist

- [x] a17d26e: feat(37-04): LangGraphHandler に thread フォルダ scan + SystemMessage prepend + attachments 注入を追加
- [x] 9353eff: feat(37-04): delete_thread に shutil.rmtree hook + realpath prefix guard を追加 (Wave 0 xfail → GREEN)
- [x] cadbe1c: docs(37-04): VALIDATION.md Per-Task Map に Wave 2 (37-04-XX) 行を追記

## Self-Check: PASSED
