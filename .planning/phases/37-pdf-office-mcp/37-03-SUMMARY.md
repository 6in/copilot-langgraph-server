---
phase: 37
plan: "03"
subsystem: mcp
tags: [mcp-tool, markitdown, security, rpc-context, route-a, path-traversal]
dependency_graph:
  requires:
    - "37-01 spike verdict (Route A: CurrentHeaders DI confirmed)"
    - "37-02 volume + markitdown dep + AgentState + xfail skeletons"
  provides:
    - "mcp_server/tools/attachments.py — attachments_list + attachments_extract 実装"
    - "config/mcp_tools.yaml — 2 エントリ追加 + SSoT drift clean"
    - "Route A RPCContext 伝播 — langgraph_handler → execute_python → mcp_helper_utils"
    - "Wave 0 xfail 8 ケース → GREEN (mcp_server venv 経由)"
    - "VALIDATION.md Wave 1 (37-03-XX) 8 行追記"
  affects:
    - "mcp_server/server.py (register_attachments_tools)"
    - "mcp_server/tools/mcp_helper.py (生成: list_attachments / extract_attachment)"
    - "static/js/tool-catalog-generated.js (生成: 2 ツール追加)"
    - "docs/mcp-tools.md (生成: 2 ツール追加)"
    - "app/jobs/handlers/langgraph_handler.py (per-request MCP client)"
    - "mcp_server/tools/execute_python.py (CurrentHeaders DI + X_THREAD_ID/X_GITHUB_LOGIN)"
    - "mcp_server/tools/mcp_helper_utils.py (X-Thread-Id/X-Github-Login ヘッダー付与)"
tech_stack:
  added: []
  patterns:
    - "Route A: MultiServerMCPClient headers → CurrentHeaders() DI → subprocess env → HTTP ヘッダー (D-17 RPCContext 伝播)"
    - "MCP tool core / wrapper 分離 — core 関数 (純関数) + FastMCP tool ラッパー (CurrentHeaders DI)"
    - "_classify_error lazy import — asyncio.TimeoutError を markitdown import より前にチェック"
key_files:
  created:
    - mcp_server/tools/attachments.py
    - work/phase-37/integration-smoke-plan03.md
  modified:
    - mcp_server/server.py
    - config/mcp_tools.yaml
    - mcp_server/tools/mcp_helper.py
    - static/js/tool-catalog-generated.js
    - docs/mcp-tools.md
    - mcp_server/tools/execute_python.py
    - mcp_server/tools/mcp_helper_utils.py
    - app/jobs/handlers/langgraph_handler.py
    - tests/test_attachments_extract.py
    - tests/test_attachments_list.py
    - tests/test_mcp_server.py
    - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md
decisions:
  - "_classify_error で asyncio.TimeoutError を markitdown import より先にチェック — ルート環境 (markitdown 未インストール) でもタイムアウトを正しく分類できる"
  - "test_extract_password_protected は pytest.importorskip('markitdown') でルート環境では skip — mcp_server venv (PYTHONPATH 付き) では PASSED"
  - "per-request MCP client を langgraph_handler に追加 — worker startup の singleton は RPCContext を持てないため handler 内で都度作る (Route A 設計)"
  - "execute_python の register_tools をラッパー関数パターンに変更 — CurrentHeaders DI を名前変更なしで FastMCP に登録する"
metrics:
  duration: "~8 min"
  completed: "2026-04-21"
  tasks_completed: 4
  files_created: 2
  files_modified: 12
---

# Phase 37 Plan 03: MCP Attachments Tools Summary

**One-liner:** MarkItDown + CurrentHeaders() DI で attachments_list / attachments_extract を実装し、Route A (MultiServerMCPClient headers) で RPCContext を execute_python sandbox まで伝搬、Wave 0 xfail 8 ケースを GREEN に転換

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | attachments.py 新規作成 (MarkItDown 抽出 + 5 エラーコード + path traversal 防御) | 1a19266 | mcp_server/tools/attachments.py |
| 2 | server.py 登録 + YAML 追加 + generate_mcp_artifacts.py --target all | d5007eb | mcp_server/server.py, config/mcp_tools.yaml, mcp_helper.py, tool-catalog-generated.js, mcp-tools.md, tests/test_mcp_server.py |
| 3 | Route A RPCContext 伝播 + Wave 0 xfail → GREEN | a3efa13 | langgraph_handler.py, execute_python.py, mcp_helper_utils.py, tests/test_attachments_*.py, work/phase-37/integration-smoke-plan03.md |
| 4 | VALIDATION.md Wave 1 行追記 (37-03-XX) | 1c54d2d | .planning/phases/37-pdf-office-mcp/37-VALIDATION.md |

---

## Verification Results

### MCP ツールカタログ (Phase 30 SSoT)

```
python3 scripts/generate_mcp_artifacts.py --check
→ exit 0 (drift clean)
```

- `config/mcp_tools.yaml`: `attachments_list` / `attachments_extract` エントリ追加済み
- `mcp_server/tools/mcp_helper.py`: `list_attachments()` / `extract_attachment(filename)` 生成済み
- `static/js/tool-catalog-generated.js`: 2 ツール追加済み
- `docs/mcp-tools.md`: 2 ツール追加済み

### テスト結果 (mcp_server venv 経由)

```
PYTHONPATH=mcp_server/.venv/lib/python3.12/site-packages:mcp_server uv run pytest \
    tests/test_attachments_extract.py tests/test_attachments_list.py -v
→ 8 passed in 1.00s
```

| テスト | 結果 |
|--------|------|
| test_extract_pdf | PASSED |
| test_extract_password_protected | PASSED (mcp_server venv) / SKIPPED (root env) |
| test_extract_size_over | PASSED |
| test_extract_timeout | PASSED |
| test_path_traversal | PASSED |
| test_truncation | PASSED |
| test_list_returns_metadata | PASSED |
| test_list_empty_folder | PASSED |

### attachments.py acceptance criteria

- 251 行 (150 行以上) ✅
- `TIMEOUT_SECS = 60` ✅
- `MAX_FILE_BYTES = 100 * 1024 * 1024` ✅
- `MAX_CHARS_PER_FILE = 50_000` ✅
- 4 拡張子 `.pdf/.docx/.xlsx/.pptx` ✅
- `os.path.realpath` path traversal 防御 ✅
- `real.startswith(real_folder + os.sep)` (W-04 条件) ✅
- `asyncio.wait_for` + `asyncio.to_thread` ✅
- 5 エラーコード (password / corrupt / size_over / unsupported / extract_timeout) ✅
- `float(stat.st_mtime)` (S-03) ✅
- `def register_tools` ✅

### Route A / W-02 (片方の経路のみ)

- `/internal/attachments_list` / `/internal/attachments_extract` が server.py に **0 件** (Route B なし) ✅
- `langgraph_handler.py` に `MultiServerMCPClient` + `"x-thread-id"` headers ✅
- `execute_python.py` に `X_THREAD_ID` / `X_GITHUB_LOGIN` subprocess env ✅
- `mcp_helper_utils.py` に `X-Thread-Id` / `X-Github-Login` HTTP ヘッダー付与 ✅

### VALIDATION.md

- `37-03-` 行: 8 件 (37-03-01..08) ✅

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _classify_error の lazy import 順序修正**
- **Found during:** Task 3 テスト実行
- **Issue:** `_classify_error` が `from markitdown import ...` を `asyncio.TimeoutError` チェックより前に実行していた。ルート環境では markitdown 未インストールのため `test_extract_timeout` が `ModuleNotFoundError` で失敗した
- **Fix:** `asyncio.TimeoutError / TimeoutError` チェックを markitdown import より前に移動。さらに `try/except ImportError` で markitdown 未インストール環境にも対応
- **Files modified:** `mcp_server/tools/attachments.py`
- **Commit:** a3efa13

**2. [Rule 1 - Bug] test_extract_password_protected の markitdown 依存**
- **Found during:** Task 3 テスト実行
- **Issue:** テストが `from markitdown import FileConversionException` をトップレベルで実行しており、ルート環境では `ModuleNotFoundError`
- **Fix:** `pytest.importorskip("markitdown")` に変更し、mcp_server venv 経由では PASSED、ルート環境では SKIP に変更
- **Files modified:** `tests/test_attachments_extract.py`
- **Commit:** a3efa13

**3. [Rule 2 - Missing] execute_python.register_tools を CurrentHeaders DI ラッパーパターンに変更**
- **Found during:** Task 3 実装
- **Issue:** execute_python の FastMCP tool 登録で `headers` パラメータに `CurrentHeaders()` をデフォルト値として直接使えない (FastMCP の関数シグネチャの制約)
- **Fix:** `register_tools` 内でクロージャ `execute_python_with_headers` を作り、`mcp.tool(func, name="execute_python")` で登録
- **Files modified:** `mcp_server/tools/execute_python.py`
- **Commit:** a3efa13

### Integration Smoke の Docker compose 実施延期

- **理由:** worktree 環境では docker compose が利用できない
- **記録:** `work/phase-37/integration-smoke-plan03.md` に Route A の伝搬チェーンと期待レスポンスを記載
- **Plan 05** でエンドツーエンド検証を実施する

---

## Known Stubs

- `test_extract_password_protected`: ルート環境では `pytest.importorskip("markitdown")` で skip。Plan 05 の Docker 環境で完全 GREEN になる予定。これはテスト環境の制約であり、実装のスタブではない。

---

## Threat Flags

なし。新規ネットワークエンドポイント・auth パス追加はなし。
attachments.py の path traversal 防御 (T-37-03-01) と size gate (T-37-03-03) が実装済み。

---

## Self-Check: PASSED

**Created files:**
- mcp_server/tools/attachments.py: FOUND
- work/phase-37/integration-smoke-plan03.md: FOUND
- .planning/phases/37-pdf-office-mcp/37-03-SUMMARY.md: (this file)

**Commit hashes:**

| Task | Commit | Verified |
|------|--------|---------|
| Task 1 | 1a19266 | OK |
| Task 2 | d5007eb | OK |
| Task 3 | a3efa13 | OK |
| Task 4 | 1c54d2d | OK |
