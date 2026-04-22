---
status: concerns
phase: 37-pdf-office-mcp
reviewer: gsd-code-reviewer
date: 2026-04-22
files_reviewed: 20
critical: 0
high: 2
medium: 3
low: 4
---

# Phase 37 Code Review

## Summary

Phase 37 は PDF/Office 添付ファイルの MCP ツール統合として適切に設計・実装されており、セキュリティの要所（path traversal 防御、RO/RW volume 分離、JWT 所有権チェック）は概ね押さえられている。主要なリスクは **HIGH 2 件**：`attachments_extract_core` が `asyncio.CancelledError` を握り潰すこと、および `LangGraphHandler` の per-job MCP client が実際には使われておらず未クローズのまま放置されること（接続リーク + 添付ファイル機能がチャットルートで実質未動作）。MEDIUM 3 件は defense-in-depth のギャップと監査ログの欠如で、ローカル限定の脅威モデルでは許容範囲内だが修正を推奨する。

---

## Findings

### HIGH-01: LangGraphHandler の per-job MCP client が未使用かつ未クローズ

**File:** `app/jobs/handlers/langgraph_handler.py:82-97`

**Issue:**
`_mcp_client_for_job` を生成して `ctx["mcp_client_for_job"]` に保存しているが、その後 `build_graph(llm, checkpointer)` に渡されていない。`build_graph` は MCP tools を一切使わないシンプルな chatbot グラフであるため、通常チャット（`task_type=langgraph`）では添付ファイルツールが LLM に公開されない。つまり **一般チャット画面での `attachments_list` / `attachments_extract` は動作しない**（Phase 37 FIN-04 の要件が chat モードで未達成）。

加えて `MultiServerMCPClient` は `__aenter__`/`__aexit__` を持つ context manager 設計であり、`get_tools()` を呼ばずに参照が切れるとセッションがクリーンアップされない。実際のリソースリークの重大度は `MultiServerMCPClient` の内部実装依存だが、ジョブごとにインスタンスが増え続けるリスクがある。

```python
# 現状（機能しない）
_mcp_client_for_job = MultiServerMCPClient({...})
ctx["mcp_client_for_job"] = _mcp_client_for_job
# ↑ build_graph に渡していないため ToolNode が存在せず、LLM はツールなしで動く

# 修正: chatbot グラフがツールを使わないなら client 生成自体を削除
# もし chat グラフにもツールを追加するなら build_graph のシグネチャを変更して渡す
```

**Recommendation:**
(a) 現時点で通常チャットにツール機能が不要なら、`langgraph_handler.py` の per-job client 生成ブロック全体（L78-97）を削除し、dead code を除去する。(b) 将来的に通常チャットにも添付ファイルツールを追加するなら、`build_graph` に `mcp_tools` を渡せるよう拡張し、`async with` で client を管理する。

---

### HIGH-02: `except BaseException` が `asyncio.CancelledError` を握り潰す

**File:** `mcp_server/tools/attachments.py:181`

**Issue:**
`_extract_text(safe_path)` の呼び出しを `except BaseException as e:` で囲んでいる。Python 3.8 以降、`asyncio.CancelledError` は `BaseException` のサブクラスであるため、arq ワーカーのタスクキャンセルや `asyncio.wait_for` の外側からのキャンセルが発生した場合、この catch に引っかかって `{"code": "corrupt", "message": "ファイル処理エラー: ..."}` として返されてしまい、キャンセルが無視される。

`asyncio.wait_for` は内部タイムアウトを `asyncio.TimeoutError` として raise するが、外部キャンセルは `asyncio.CancelledError` として伝播する。これを catch することで協調的マルチタスクが破綻し、ワーカープロセスがシャットダウンできなくなる可能性がある。

```python
# 現状（問題あり）
try:
    text = await _extract_text(safe_path)
except BaseException as e:
    code, msg = _classify_error(e)
    return {**empty, "error": {"code": code, "message": msg}}

# 修正
try:
    text = await _extract_text(safe_path)
except asyncio.CancelledError:
    raise  # キャンセルは必ず再 raise する
except Exception as e:
    code, msg = _classify_error(e)
    return {**empty, "error": {"code": code, "message": msg}}
```

**Recommendation:** `except BaseException` を `except asyncio.CancelledError: raise` + `except Exception` の 2 段構えに変更する。

---

### MEDIUM-01: `attachments_list_core` / `attachments_extract_core` でフォルダパス自体の realpath 検証なし

**File:** `mcp_server/tools/attachments.py:122, 160`

**Issue:**
`_safe_resolve` は `filename` のパストラバーサルを防いでいるが、`_resolve_thread_folder(thread_id, github_login)` で構築するフォルダパス自体の realpath 検証がない。`github_login` や `thread_id` に `../` が含まれていた場合、`/shared/thread-files/../../etc/passwd/` のようなフォルダが生成される。

現時点では `x-github-login` / `x-thread-id` ヘッダーはワーカー内部（JWT 検証後の値）が設定するため直接攻撃面は限定的だが、将来的なヘッダー注入やワーカーバグに対して防御がない。`delete_thread` では実施済みの realpath prefix ガードと対称性が取れていない。

```python
def _resolve_thread_folder(thread_id: str, github_login: str) -> str:
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    # 追加: realpath が base より外を指していたら ValueError
    real = os.path.realpath(folder)
    base = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(base + os.sep):
        raise ValueError(f"path traversal in folder: {folder!r}")
    return real
```

**Recommendation:** `_resolve_thread_folder` に realpath prefix ガードを追加し、`attachments_list_core` も `ValueError` を `[]` ではなく適切にハンドルする。

---

### MEDIUM-02: `OrchestratorHandler` の per-job MCP client が未クローズ

**File:** `app/jobs/handlers/orchestrator_handler.py:105-124, 291`

**Issue:**
`per_job_mcp_client = MultiServerMCPClient({...})` で生成した client は `get_tools()` 呼び出し後に `__aexit__` が呼ばれない。`finally` ブロックには `registry.close()` のみ存在し、`per_job_mcp_client` のクリーンアップがない。

`LangGraphHandler` と異なり OrchestratorHandler では client が実際に機能しており（`mcp_tools = await per_job_mcp_client.get_tools()` の結果が registry に渡る）、接続が維持されたままジョブごとに増殖するリスクがある。

```python
# 修正例: finally ブロックに追加
finally:
    await registry.close()
    if per_job_mcp_client is not None:
        try:
            await per_job_mcp_client.__aexit__(None, None, None)
        except Exception:
            pass
```

**Recommendation:** `per_job_mcp_client` を `async with` で管理するか、`finally` で明示的にクリーンアップする。`MultiServerMCPClient` が実際に接続を保持するかどうかはバージョンにより異なるが、コードの意図を明確にするためにも cleanup を追加すること。

---

### MEDIUM-03: path traversal 検出が 204 を返しつつログを残さない

**File:** `app/api/routes/chat.py:403-406`

**Issue:**
`delete_thread` の path traversal 検出時、`ValueError` を `raise` してから直後の `except ValueError: pass` で握り潰し、204 を返して終了する。`pass` のみでログ出力がないため、攻撃試行が監査ログに残らない。200名規模の社内ツールであっても、セキュリティイベントは記録すべきである。

```python
# 現状
except ValueError:
    pass  # traversal 検出 — ログだけ残して無視 (thread の論理削除は既に完了)
# ↑ コメントは "ログだけ残して" と書いているが実際はログ出力がない

# 修正
except ValueError as ve:
    import logging
    logging.getLogger(__name__).warning(
        "path traversal attempt blocked in delete_thread: thread_id=%r github_login=%r reason=%s",
        thread_id, github_login, ve,
    )
```

**Recommendation:** `except ValueError: pass` を `except ValueError as ve: logger.warning(...)` に変更する。`logger` はモジュールレベルに定義されていないため追加が必要。

---

### LOW-01: `_classify_error` の `corrupt` ケースで内部例外メッセージが漏洩

**File:** `mcp_server/tools/attachments.py:100-101`

**Issue:**
`f"ファイル変換に失敗しました: {exc}"` で例外オブジェクトをそのまま文字列化している。`exc` がファイルパスや内部スタックトレースを含む場合、MCP レスポンス経由で LLM のコンテキストウィンドウに内部パスが露出する。

**Recommendation:** `f"ファイル変換に失敗しました"` として詳細は省くか、`str(exc)` を `repr(type(exc).__name__)` 程度に留める。

---

### LOW-02: `test_mcp_client_headers.py` が Phase 37 完了後も xfail のまま

**File:** `tests/test_mcp_client_headers.py:22-32`

**Issue:**
`test_mcp_context_headers_smoke` / `test_streamable_http_connection_accepts_headers_field` が Phase 37 Wave 1 完了後も `@pytest.mark.xfail(strict=False)` のまま。Phase 37.1 integration check では end-to-end 動作確認済みなので、実テストに昇格させる好機を逃している。`strict=False` は予期せぬ PASS を検出しないため regression として機能しない。

**Recommendation:** Phase 37 マージ後に両テストを実テスト（xfail 外し）に昇格させるか、チケットを切って追跡する。

---

### LOW-03: `DebateHandler` に添付ファイル機能が未適用

**File:** `app/jobs/handlers/debate_handler.py`（変更なし）

**Issue:**
Phase 37.1 で `OrchestratorHandler` への適用は行われたが、`DebateHandler` には `scan_thread_attachments` / per-job MCP client が追加されていない。DebateChat スレッドで添付ファイルをアップロードした場合、LLM にファイル情報が通知されない。

**Recommendation:** Phase 37.1 では「scope 外」として明示されているが、37-05-SUMMARY.md のバックログに記録するか、Phase 38 のスコープとして追跡することを推奨する。

---

### LOW-04: `attachments_list` が `fpath` のシンボリックリンクを辿る可能性

**File:** `mcp_server/tools/attachments.py:128-130`

**Issue:**
`os.path.isfile(fpath)` はシンボリックリンクのターゲットが通常ファイルであれば `True` を返す。`os.stat(fpath)` も同様にリンク先を参照する。thread フォルダ内にシンボリックリンクが作成されていた場合（mcp-server が RW マウントなので可能）、フォルダ外のファイルのメタデータ（サイズ・更新日時）が返される。

`attachments_extract_core` 側では `_safe_resolve` が `os.path.realpath` でシンボリックリンクを解決してから prefix チェックを行うため保護されているが、`attachments_list_core` 側は保護がない。

**Recommendation:** `os.path.isfile` を `os.path.isfile and not os.path.islink` とするか、`os.lstat` で S_ISLNK チェックを追加する。

---

## Per-file notes

| ファイル | 評価 | 主な所見 |
|--------|------|---------|
| `mcp_server/tools/attachments.py` | 概ね良好 | HIGH-02 (`except BaseException`) / MEDIUM-01（フォルダ realpath 検証なし）/ LOW-01・04 |
| `app/api/routes/chat.py` | 良好 | realpath ガードは正しく実装。MEDIUM-03（ログ欠如）は軽微 |
| `app/jobs/handlers/orchestrator_handler.py` | 良好 | Phase 37.1 修正として正しく機能。MEDIUM-02（client 未クローズ）は要修正 |
| `app/jobs/handlers/langgraph_handler.py` | 要修正 | HIGH-01 — per-job MCP client が dead code。通常チャットで添付機能未動作 |
| `app/jobs/handlers/attachments_helper.py` | 良好 | 軽量・明快。path traversal ガードなし（MEDIUM-01 参照）だが caller 責任範囲 |
| `app/orchestrator/state.py` | 良好 | `attachments` フィールド追加は最小限で適切 |
| `app/providers/copilot.py` | 良好 | `send_timeout=300s` + env var override は合理的 |
| `mcp_server/server.py` | 良好 | `register_attachments_tools` 登録は正しい |
| `mcp_server/tools/execute_python.py` | 良好 | CurrentHeaders DI ラッパーパターンは正しく実装 |
| `mcp_server/tools/mcp_helper_utils.py` | 良好 | X-Thread-Id / X-Github-Login ヘッダー付与は正しく実装 |
| `agents/general-assistant/AGENT.md` | 良好 | ツール追加とシステムプロンプト指示は適切 |
| `config/mcp_tools.yaml` | 良好 | attachments_list / attachments_extract エントリは完全。SSoT 整合済み |
| `docker-compose.yml` | 良好 | RW/RW/RO の volume 権限設計は正しい。healthcheck start_period 延長も適切 |
| `mcp_server/pyproject.toml` | 良好 | バージョン上限 `<0.2.0` 設定は適切 |
| `tests/test_attachments_extract.py` | 良好 | 6 ケース網羅。path traversal / timeout / size_over / truncation すべて検証済み |
| `tests/test_attachments_list.py` | 良好 | 基本的なメタデータ検証あり |
| `tests/test_langgraph_handler_attachments.py` | 良好 | helper 関数の unit test として十分 |
| `tests/test_api_chat.py` | 良好 | delete_thread + path traversal の両テストが適切に実装 |
| `tests/test_agent_state.py` | 良好 | `attachments` フィールド確認は最小限だが十分 |
| `tests/test_mcp_client_headers.py` | 要追跡 | Phase 37 完了後も xfail のまま（LOW-02 参照）|

---

## Recommendations

### マージ前に修正すること（HIGH）

1. **HIGH-01**: `langgraph_handler.py` の per-job MCP client ブロック（L78-97）を削除する。通常チャットは `build_graph` がツールなしのシンプルグラフであるため、ここで client を生成しても効果がない。もし通常チャットに添付機能を追加したいなら、それは別フェーズとして計画する。

2. **HIGH-02**: `attachments.py:181` の `except BaseException` を `except asyncio.CancelledError: raise` + `except Exception` に変更する。

### マージ前推奨（MEDIUM）

3. **MEDIUM-02**: `orchestrator_handler.py` の `finally` ブロックに `per_job_mcp_client` の cleanup を追加する。

4. **MEDIUM-03**: `delete_thread` の path traversal catch に `logger.warning(...)` を追加する。

### 後続フェーズで対応（MEDIUM / LOW）

5. **MEDIUM-01**: `_resolve_thread_folder` に realpath prefix ガードを追加（defense-in-depth）。
6. **LOW-02**: `test_mcp_client_headers.py` の xfail テストを Phase 38 または最初の機会に昇格させる。
7. **LOW-03**: `DebateHandler` への添付ファイル機能追加をバックログとして記録。
8. **LOW-04**: `attachments_list_core` でのシンボリックリンク対策を検討。

---

_Reviewed: 2026-04-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
