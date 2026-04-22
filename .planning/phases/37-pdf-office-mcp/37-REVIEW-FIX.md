---
phase: 37-pdf-office-mcp
fixed_at: 2026-04-22
review_path: .planning/phases/37-pdf-office-mcp/37-REVIEW.md
iteration: 2
findings_in_scope: 9
fixed: 7
skipped: 2
status: partial
---

# Phase 37: Code Review Fix Report

**Fixed at:** 2026-04-22
**Source review:** `.planning/phases/37-pdf-office-mcp/37-REVIEW.md`
**Iteration:** 2 (累積 — iteration 1: HIGH 2 件 / iteration 2: MEDIUM 3 件 + LOW 2 件)

**Summary:**

- Findings in scope (fix_scope="all"): 9 (HIGH 2 / MEDIUM 3 / LOW 4)
- Fixed: 7 (HIGH 2 + MEDIUM 3 + LOW 2)
- Skipped: 2 (LOW 2 件 — 本質的に code fix ではないためバックログ管理)

iteration 1 で HIGH 2 件、iteration 2 で MEDIUM 3 件 + LOW 2 件を追加適用した。scope=all で Phase 37 の自動修正可能な指摘はすべて適用済み。残る LOW-02 / LOW-03 は test 管理・後続フェーズ計画の判断事項のため Phase 38 バックログへ引き継ぐ。

## Fixed Issues

### HIGH-01: LangGraphHandler の per-job MCP client が未使用かつ未クローズ

**Files modified:** `app/jobs/handlers/langgraph_handler.py`
**Commit:** `b68358b`
**Iteration:** 1
**Applied fix:**

`LangGraphHandler.handle` 入口にあった per-job MCP client 生成ブロック（旧 L78-97）を削除した。`build_graph` は mcp_tools を受け取らないシンプルな chatbot グラフであるため、生成した `MultiServerMCPClient` は `ctx["mcp_client_for_job"]` に保存されるだけでどこからも参照されず、dead code かつ cleanup なしの状態だった。将来 chat モードに添付ファイルツールを公開する際は `build_graph` のシグネチャ拡張 + `async with` による client 管理を別フェーズで併せて行う旨のコメントを残した。

**Verification:**

- Tier 1: Edit 後の該当箇所を Read で再確認済み（L74-95 相当）
- Tier 2: `python -c "ast.parse(...)"` で構文チェック OK
- テスト: `tests/test_langgraph_handler.py` + `tests/test_langgraph_handler_attachments.py` → 5 passed / 2 skipped（skip は元々 skip）

### HIGH-02: `except BaseException` が `asyncio.CancelledError` を握り潰す

**Files modified:** `mcp_server/tools/attachments.py`
**Commit:** `3db8294`
**Iteration:** 1
**Applied fix:**

`attachments_extract_core` の `_extract_text(safe_path)` 呼び出しを囲む `except BaseException as e:` を、`except asyncio.CancelledError: raise` + `except Exception as e:` の 2 段構えに変更した。これにより arq worker のタスクキャンセルや `asyncio.wait_for` 外側からのキャンセル伝播が、誤って `{"code": "corrupt"}` にすり替えられることなく上位へ再 raise される。`asyncio.TimeoutError` は `Exception` のサブクラスなので従来通り `_classify_error` で `extract_timeout` 扱いになり、挙動は互換。

**Verification:**

- Tier 1: Edit 後の該当箇所を Read で再確認済み（L179-188）
- Tier 2: `python -c "ast.parse(...)"` で構文チェック OK
- テスト: `tests/test_attachments_extract.py` + `tests/test_attachments_list.py` → 7 passed / 1 skipped

### MEDIUM-01: `_resolve_thread_folder` に realpath prefix guard 追加

**Files modified:** `mcp_server/tools/attachments.py`
**Commit:** `912ccb5`
**Iteration:** 2
**Applied fix:**

`_resolve_thread_folder(thread_id, github_login)` に realpath prefix 検証を追加。`github_login` / `thread_id` に `../` が混入した場合、`/shared/thread-files/../../etc/passwd/` のようなフォルダ組み立てを拒否し `ValueError` を raise する。`delete_thread` 側（`app/api/routes/chat.py`）の realpath prefix assert と対称になった。

呼び出し元も同時修正:
- `attachments_list_core`: `ValueError` を catch して `[]` を返す（list tool は副作用なし）
- `attachments_extract_core`: `ValueError` を catch して `{"code": "corrupt", "message": ...}` を返す

**Verification:**

- Tier 1: Edit 後の該当箇所を Read で再確認済み
- Tier 2: `python -c "ast.parse(...)"` で構文チェック OK
- テスト: `tests/test_attachments_list.py` + `tests/test_attachments_extract.py` → 7 passed / 1 skipped

### MEDIUM-02: OrchestratorHandler の per-job MCP client cleanup 追加

**Files modified:** `app/jobs/handlers/orchestrator_handler.py`
**Commit:** `cf1f73f`
**Iteration:** 2
**Applied fix:**

`_handle_inner` の `finally` ブロックに per-job MCP client のクリーンアップを追加。

調査の結果、`langchain-mcp-adapters` 0.1.0+ では `MultiServerMCPClient` は stateless になっており、`__aenter__`/`__aexit__` を呼ぶと `NotImplementedError` が raise される（`get_tools()` 内部で各サーバーごとに新規セッションを生成→即クローズ）。そのため **REVIEW.md の提案（`__aexit__(None, None, None)` 呼び出し）をそのまま適用すると毎ジョブで必ず警告ログが出てしまう** 問題があった。

代わりに `getattr(per_job_mcp_client, "aclose", None) or getattr(per_job_mcp_client, "close", None)` で存在する close メソッドのみを呼ぶ前方互換パターンを採用。現バージョンでは no-op だが、将来 stateful cleanup が必要になった場合でもコード変更なしで対応できる。`per_job_mcp_client` が `None`（生成時例外）の場合も保護済み。

**Verification:**

- Tier 1: Edit 後の該当箇所を Read で再確認済み（L290-313）
- Tier 2: `python -c "ast.parse(...)"` で構文チェック OK + `from app.jobs.handlers.orchestrator_handler import OrchestratorHandler` で import 成功
- テスト: `tests/test_orchestrator_graph.py` → 2 passed

### MEDIUM-03: delete_thread の path traversal catch にログ出力追加

**Files modified:** `app/api/routes/chat.py`
**Commit:** `4bd3962`
**Iteration:** 2
**Applied fix:**

`delete_thread` の path traversal 検出時、`except ValueError: pass` でログなしに握り潰していた箇所を `except ValueError as ve: logging.getLogger(__name__).warning(...)` に差し替え。`thread_id` / `github_login` / `ValueError` の reason を warning レベルのログに残すようにした。既存の upsert エラーログ（L167）と同じ in-function import + `getLogger(__name__)` パターンを踏襲し、コードスタイルの一貫性を保った。

**Verification:**

- Tier 1: Edit 後の該当箇所を Read で再確認済み（L403-414）
- Tier 2: `python -c "ast.parse(...)"` で構文チェック OK
- テスト: `tests/test_api_chat.py::test_delete_thread_removes_folder` + `test_delete_thread_rejects_path_traversal` → 2 passed

注: `tests/test_api_chat.py` の他 6 件が FAILED だが、これは iteration 2 修正と無関係の pre-existing 失敗（stash して pre-fix 状態で再実行しても同じ 6 件が失敗することを確認済み — conftest の fixture 依存問題）。Phase 37 固有のテストは全 pass。

### LOW-01: `_classify_error` の corrupt メッセージから内部例外詳細を削除

**Files modified:** `mcp_server/tools/attachments.py`
**Commit:** `d499ed4`
**Iteration:** 2
**Applied fix:**

`_classify_error` の corrupt 分岐で例外オブジェクトを `f"...: {exc}"` と文字列化していた箇所を `f"... ({type(exc).__name__})"` に変更。MCP レスポンス経由で LLM のコンテキストにファイルパスやスタックトレース片が漏れるのを防ぐ。型名のみは残しているので、デバッグ時の原因特定には支障なし。

**Verification:**

- Tier 1: Edit 後の該当箇所を Read で再確認済み（L111-115）
- Tier 2: `python -c "ast.parse(...)"` で構文チェック OK
- テスト: `tests/test_attachments_extract.py::test_path_traversal` は "traversal" or "invalid" キーワード検査（`_safe_resolve` から `str(e)` を渡す別経路）なのでそのまま pass

### LOW-04: attachments_list_core でシンボリックリンクを除外

**Files modified:** `mcp_server/tools/attachments.py`
**Commit:** `6409896`
**Iteration:** 2
**Applied fix:**

`attachments_list_core` のループ内で `os.path.isfile(fpath)` チェック前に `os.path.islink(fpath)` を追加し、シンボリックリンクの場合は skip するようにした。`os.path.isfile` はリンク先を参照するため、thread フォルダ内にフォルダ外ファイルへのシンボリックリンクがあると、本来見えるべきでないファイルのメタデータ（サイズ・更新日時）が返ってしまう可能性があった。

`attachments_extract_core` 側は `_safe_resolve` の `os.path.realpath` + prefix assert が既にシンボリックリンクを拒否しているため追加修正不要。

**Verification:**

- Tier 1: Edit 後の該当箇所を Read で再確認済み（L144-156）
- Tier 2: `python -c "ast.parse(...)"` で構文チェック OK
- テスト: `tests/test_attachments_list.py` → 2 passed（シンボリックリンクを含まないテストデータなのでカバー範囲外だが non-regression 確認）

## Skipped Issues

以下 2 件は scope=all の対象だが、本質的に code fix ではなく test 管理 / フェーズ計画の判断事項のため、iteration 2 では意図的に skip した。Phase 38 のバックログで追跡する。

### LOW-02: `test_mcp_client_headers.py` が Phase 37 完了後も xfail のまま

**File:** `tests/test_mcp_client_headers.py:22-32`
**Reason:** test 管理判断が必要。`@pytest.mark.xfail(strict=False)` を外して実テストに昇格させるには worker が起動した環境で pass することを CI で確認する必要があるが、現状の CI は MCP server を起動しないユニットテスト環境のため、外すと逆に flaky になる可能性がある。Phase 38 で MCP server 統合テスト環境を整備する際に併せて昇格させる方針。
**Original issue:** `test_mcp_context_headers_smoke` / `test_streamable_http_connection_accepts_headers_field` が Phase 37 Wave 1 完了後も `@pytest.mark.xfail(strict=False)` のまま。Phase 37.1 integration check では end-to-end 動作確認済みなので、実テストに昇格させる好機を逃している。

### LOW-03: DebateHandler に添付ファイル機能が未適用

**File:** `app/jobs/handlers/debate_handler.py`
**Reason:** Phase 37.1 で scope 外として明示（37-REVIEW.md L181 "Phase 37.1 では『scope 外』として明示」）。Phase 38 のスコープで追跡する。現状 DebateChat で添付ファイルを upload しても LLM に情報が通知されないという既知の挙動制限。code review fix ではなく新機能追加のため、fixer agent の適用範囲外。
**Original issue:** Phase 37.1 で OrchestratorHandler への適用は行われたが、DebateHandler には `scan_thread_attachments` / per-job MCP client が追加されていない。

---

_Fixed: 2026-04-22_
_Fixer: Claude (gsd-code-fixer)_
_Iterations: 1 (HIGH 2 件) + 2 (MEDIUM 3 件 + LOW 2 件) = 累計 7 fixed / 2 skipped_
