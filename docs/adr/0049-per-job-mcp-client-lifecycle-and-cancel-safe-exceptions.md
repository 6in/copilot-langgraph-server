# 0049. Per-job MCP client のライフサイクルとキャンセル安全な MCP ツール例外処理 (Phase 37 Code Review)

**Status:** Accepted
**Date:** 2026-04-22
**Phase:** 37 — PDF/Office 添付 MCP 統合（Code Review フェーズ）
**Supersedes:** なし
**Related ADRs:** [0020](0020-fastmcp-docker-service-infrastructure.md), [0024](0024-mcp-tool-catalog-validation.md), [0045](0045-phase-31-observability-jsonl.md), [0048](0048-thread-files-folder-convention.md)

## Context

Phase 37 では worker が MCP サーバーに streamable-http で接続して `attachments_list` / `attachments_extract` を呼び出す。ADR-0048 で決めた規約上、MCP サーバー側が RPC 呼び出し時点で `x-thread-id` / `x-github-login` ヘッダーを読んで thread フォルダを解決する必要がある（D-17）。worker 起動時の共有 `mcp_tools` はヘッダーを持たないため、ジョブ単位で `MultiServerMCPClient` を作り直してヘッダー付きツールを bind する **per-job client** パターンを Phase 37.1 で導入した。

導入後、Phase 37 code review で 3 件の構造的問題が浮上した:

1. **HIGH-01**: `LangGraphHandler` で per-job client を生成していたが `build_graph(llm, checkpointer)` に渡していなかった。通常チャットグラフはツールを受け取らない単純 chatbot であるため、**client が dead code となり添付ツールが LLM に公開されていなかった**。さらに client 参照が即捨てられるため cleanup されない。
2. **MEDIUM-02**: `OrchestratorHandler` では client が実際に使われていたが、`finally` ブロックで cleanup されていなかった。`MultiServerMCPClient` のドキュメント上は context manager 設計だが、実際に 0.1.x を試すと `__aexit__` が `NotImplementedError` を raise する（stateless に再設計済み）。素直に `async with` / `__aexit__(None, None, None)` を呼ぶと毎ジョブで警告ログが出る。
3. **HIGH-02**: `attachments_extract_core` は `_extract_text()` を `except BaseException` で囲んで corrupt エラーに分類していた。Python 3.8+ で `asyncio.CancelledError` は `BaseException` のサブクラスのため、arq worker のジョブキャンセルが握り潰されて worker が協調シャットダウンできない罠が埋まっていた。

3 件はいずれも「MCP 接続の寿命」と「asyncio の例外伝播」という横断的な話で、Phase 38 以降の新規 handler（DebateHandler への添付機能追加など）や新 MCP ツール追加で再発しやすい。パターンとして固定したい。

## Decision

### 1. Per-job MCP client を生成する条件

`MultiServerMCPClient` をジョブ単位で生成するのは、**その client から取得したツールを実際にグラフ／registry に渡す場合のみ**。以下のいずれかを満たすこと:

- `build_graph(...)` / `SubAgentRegistry(...)` / agent ファクトリに `mcp_tools=...` として引き渡す
- ReAct ループの ToolNode に bind する

grep で「生成コードは存在するが `mcp_tools` 引数が caller 側で使われていない」handler があれば dead code。消す。通常チャット（`task_type=langgraph`）のように「チャット本文だけ返せばよい」handler は per-job client を持たない。

### 2. Per-job MCP client cleanup パターン

`finally` ブロックで以下の **前方互換クリーンアップ**を明示的に呼ぶ（`async with` / `__aexit__` は使わない）:

```python
if per_job_mcp_client is not None:
    closer = (
        getattr(per_job_mcp_client, "aclose", None)
        or getattr(per_job_mcp_client, "close", None)
    )
    if closer is not None:
        try:
            result = closer()
            if hasattr(result, "__await__"):
                await result
        except Exception as e:
            logger.warning(
                "per-job MCP client close failed: %s", e,
            )
```

意図:

- `langchain-mcp-adapters` 0.1.x は `MultiServerMCPClient.get_tools()` が内部で各サーバーごとに stateless session を作って即クローズする設計。client 側の cleanup は事実上 no-op
- ただし将来のバージョン（0.2.x 以降）で stateful に戻った場合、`getattr(...)` パターンなら `aclose` / `close` が実装された時点で自動的にフックが効く。コード変更不要
- `__aexit__(None, None, None)` は 0.1.x で `NotImplementedError` を raise するため使わない（ログを汚すだけ）
- `per_job_mcp_client is not None` ガードは、生成時に例外で落ちた場合（ネットワーク失敗等）を考慮

### 3. MCP ツールの Cancel-safe 例外処理

MCP ツールコア（`mcp_server/tools/*.py` の `*_core` 関数）では、長時間走る非同期処理を `except BaseException` で囲まない。以下の 2 段構えを**必ず**使う:

```python
try:
    result = await _long_running_async_op(...)
except asyncio.CancelledError:
    raise  # キャンセルは必ず再 raise
except Exception as e:
    code, msg = _classify_error(e)
    return {**empty, "error": {"code": code, "message": msg}}
```

理由:

- Python 3.8+ で `asyncio.CancelledError` は `BaseException` 直下（`Exception` の外側）。arq worker / `asyncio.wait_for` / タスクキャンセルからの伝播を壊すと worker が協調シャットダウンできず、デプロイ時にハングする
- タイムアウトは `asyncio.TimeoutError` として別途 raise されるので `except Exception` 側で `timeout` コードに分類できる
- `_classify_error(exc)` からは内部例外のスタックトレース／ファイルパスを漏らさない（LOW-01 と整合）。メッセージは一般化された文言のみ

### 4. エラー分類関数のメッセージ設計

`_classify_error(exc: Exception) -> (code, message)` 系の関数で、`corrupt` / `unsupported` など利用者に返すメッセージは**内部例外の `str(exc)` を直接埋め込まない**。

- 悪い例: `f"ファイル変換に失敗しました: {exc}"`（内部パスやスタックの一部が LLM コンテキストに流れる）
- 良い例: `"ファイル変換に失敗しました"` もしくは `f"ファイル変換に失敗しました ({type(exc).__name__})"`

詳細ログが必要なら `logger.warning("...", exc_info=True)` で stdout へ出し、MCP レスポンスには含めない。

## Alternatives Considered

- **`async with per_job_mcp_client:` を使う**: 0.1.x で `__aexit__` が `NotImplementedError` を raise するため即廃案。コードは短く書けるが毎ジョブ警告ログで観測性を悪化させる
- **`MCP_CLIENT_TTL` / pool 化**: 接続プールをグローバルに保持する案。ただし `x-thread-id` / `x-github-login` をヘッダーで切り替える Route A（Phase 37 採用）は「ジョブ単位でヘッダーが違う」のが本質で、pool するなら cache key にヘッダーを含める必要があり複雑化。Phase 37 の 200 名・低 QPS 環境では per-job 生成コストは許容範囲
- **`except BaseException as e: if isinstance(e, asyncio.CancelledError): raise; ...`**: 1 ブロックで書く形。読みにくく、将来別の `BaseException` サブクラス（`KeyboardInterrupt` 等）を増やしたとき再発しやすい。2 段構え (`except CancelledError: raise` + `except Exception`) が明示的でレビューしやすい

## Consequences

### 良い点

- 新規 handler 追加時、per-job client の要否判断基準が明文化される（「tools を registry / graph に渡すか？」のイエス/ノー）
- `langchain-mcp-adapters` のバージョン追従が前方互換: 0.1.x → 0.2.x で stateful cleanup が戻ってもコード変更不要
- MCP ツールコア関数の「キャンセル安全」が設計契約として固定され、observability (ADR-0045) の trace emit とも整合（CancelledError を再 raise すれば trace span も正しく error=true で閉じる）
- エラーメッセージから内部パスが漏れず、LLM コンテキスト汚染を抑制（LOW-01 と継続）

### 悪い点 / トレードオフ

- per-job client 生成は毎ジョブで HTTP 接続を張り直す。200 名規模 × 低 QPS では問題ないが、QPS が 10+/sec に上がると接続オーバーヘッドが顕在化する。その時点で ADR 起票して pool 化を検討する
- cleanup コードは `getattr` チェックの分だけ冗長。0.1.x では no-op だが「将来のため」なので removing は NG
- `except Exception` にしたことで `SystemExit` / `KeyboardInterrupt` もそのまま伝播する。意図通りだが、MCP サーバープロセスの signal handling を変えた際は再度レビューが必要

### 適用範囲

以下 3 ファイルが本 ADR の直接の実装箇所（Phase 37 code review fix で反映済み）:

| ファイル | 適用パターン |
|---------|-------------|
| `app/jobs/handlers/orchestrator_handler.py` | per-job client cleanup (Decision 2) |
| `app/jobs/handlers/langgraph_handler.py` | per-job client を生成しない (Decision 1, dead code 削除) |
| `mcp_server/tools/attachments.py` | Cancel-safe 例外 (Decision 3), メッセージ抑制 (Decision 4) |

以下は**本 ADR 適用候補**（Phase 38 以降で再評価）:

- `app/jobs/handlers/debate_handler.py` — 添付機能を足す時に per-job client 生成するなら Decision 1/2 に従う
- `mcp_server/tools/execute_python.py` / `web_search.py` など既存 MCP ツール — `except BaseException` が残っていれば Decision 3 に合わせる（Phase 37 では attachments.py のみ改修）

## 参考情報

- 先例: ADR-0020 FastMCP Docker サービス基盤（streamable-http transport と RPC コンテキスト）
- 先例: ADR-0024 MCP ツールカタログ検証（ツール登録フロー）
- 先例: ADR-0045 observability JSONL（trace span と例外伝播）
- 実装: commit `b68358b`（HIGH-01）、`3db8294`（HIGH-02）、`cf1f73f`（MEDIUM-02）、`d499ed4`（LOW-01）
- 関連: `.planning/phases/37-pdf-office-mcp/37-REVIEW.md` / `37-REVIEW-FIX.md`
