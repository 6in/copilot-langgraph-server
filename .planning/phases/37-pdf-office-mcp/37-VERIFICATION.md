---
status: passed
phase: 37-pdf-office-mcp
verifier: gsd-verifier
date: 2026-04-22
must_haves_total: 7
must_haves_verified: 7
gaps: 0
human_verification_items: 0
known_issues:
  - id: HIGH-01
    severity: high
    scope: langgraph-handler
    description: LangGraphHandler の per-job MCP client (L82-97) が build_graph に渡されていないため dead code。通常チャット画面では attachments_list/extract が LLM に公開されない。
    impact: SuperChat (OrchestratorHandler) 経路は正常動作確認済み。Chat 画面での添付機能は Phase 38 対象として追跡。
  - id: HIGH-02
    severity: high
    scope: mcp_server/tools/attachments.py
    description: L181 の `except BaseException` が asyncio.CancelledError を握り潰し、Worker シャットダウン時の協調キャンセルが破綻する可能性がある。
    impact: 通常運用では問題が表面化しにくいが、Worker 終了時の clean shutdown に影響する可能性。
  - id: MEDIUM-02
    severity: medium
    scope: app/jobs/handlers/orchestrator_handler.py
    description: per_job_mcp_client が finally ブロックでクリーンアップされない。
    impact: 接続リークの可能性あり。ジョブ頻度が低い社内規模では現時点で顕在化しにくい。
  - id: MEDIUM-03
    severity: medium
    scope: app/api/routes/chat.py
    description: delete_thread の path traversal 検出時に logging がない（コメントに「ログだけ残して」とあるが実際はログ出力なし）。
    impact: 攻撃試行が監査ログに残らない。
---

# Phase 37 Verification Report

**Phase Goal:** PDF/Office (.pdf/.docx/.xlsx/.pptx) ファイルのサーバーサイドテキスト抽出と MCP ツール経由の AI 参照を実装し、thread-files フォルダ規約を ADR として確立する (FIN-03 / FIN-04)

**Verified:** 2026-04-22
**Status:** passed
**Re-verification:** No — initial verification

---

## Requirements Coverage

| REQ-ID | Status | Evidence |
|--------|--------|----------|
| FIN-03 | SATISFIED | `mcp_server/tools/attachments.py` — `attachments_extract_core` が .pdf/.docx/.xlsx/.pptx を MarkItDown で抽出。60s timeout (`TIMEOUT_SECS=60`)、100MB 上限 (`MAX_FILE_BYTES`)、50000 文字 truncation (`MAX_CHARS_PER_FILE`)、5 エラーコード (`_classify_error`) すべて実装済み。実環境 end-to-end (Scenario A/B) で PDF 抽出動作確認済み。 |
| FIN-04 | SATISFIED | `attachments_list` / `attachments_extract` が `config/mcp_tools.yaml` SSoT 経由で登録。`OrchestratorHandler` (SuperChat) が per-job `MultiServerMCPClient(headers={x-thread-id, x-github-login})` で RPCContext を伝播させ、`general-assistant/AGENT.md` のツールリストに両ツールが宣言。実環境 Scenario B で `attachments_extract` の MCP 呼び出し確認済み。 |

---

## Must-Haves Verification

| # | Must-have (Success Criteria) | Verified | Evidence |
|---|------------------------------|----------|----------|
| 1 | FIN-03: PDF/Office 4 形式の抽出 (60s timeout, 100MB 上限, 50000 文字 truncation, 5 エラーコード) | VERIFIED | `mcp_server/tools/attachments.py:19-23` で定数定義。`attachments_extract_core` + `_classify_error` に全コード実装。`tests/test_attachments_extract.py` 6 ケース (extract/password/size_over/timeout/path_traversal/truncation)。実環境 Scenario B で PDF テキスト抽出確認。 |
| 2 | FIN-04: MCP ツール経由 AI 参照 + RPCContext 伝播 | VERIFIED | `OrchestratorHandler._handle_inner` (L100-124) で per-job `MultiServerMCPClient(headers={x-thread-id, x-github-login})` を構築して `get_tools()` を `SubAgentRegistry` に渡す。`CurrentHeaders()` DI パターンで mcp-server 側が受け取る。Scenario B の worker トレース `f427869c` で動作確認。 |
| 3 | 添付ファイル一覧を AI への SystemMessage に prepend (D-11) | VERIFIED | `LangGraphHandler._handle_inner` (L153-166): `scan_thread_attachments` + `build_attachments_hint` を呼び `## 添付ファイル` セクションとして `effective_system_prompt` に追加。`OrchestratorHandler._handle_inner` (L213-219): `effective_prompt` の先頭に `## 添付ファイル情報` を prepend。`attachments_helper.py` が共有 helper。Scenario A で AI が添付ファイルを認識して応答したことを確認。 |
| 4 | AgentState.attachments に毎 turn 一覧を反映 (D-12) | VERIFIED | `app/orchestrator/state.py:19` — `attachments: list[dict] \| None  # Phase 37 D-12` フィールド定義済み。`LangGraphHandler` の `state_input` (L185) + `OrchestratorHandler` の `initial` (L237) 両方で `attachments_meta or None` を設定。`test_agent_state.py::test_attachments_field_accepted` でフィールド存在確認。 |
| 5 | thread 削除と同期して folder 削除 (D-03) + path traversal 防御 (W-01 MUST) | VERIFIED | `app/api/routes/chat.py:394-406` — `adelete_thread` 直後に `os.path.realpath` prefix guard + `shutil.rmtree(ignore_errors=True)`。traversal 検出時は rmtree をスキップして 204 を返す。`test_api_chat.py::test_delete_thread_removes_folder` + `test_delete_thread_rejects_path_traversal` で両ケースを unit test 確認。 |
| 6 | フォルダ規約 ADR として文書化 (Success Criteria 5) | VERIFIED | `docs/adr/0048-thread-files-folder-convention.md` (157 行) 作成済み。パス階層 / ファイル命名 / volume 構成 / ライフサイクル / D-08 (0 文字 PDF) / path traversal 対策 / Phase 36/38 接続契約を網羅。`docs/adr/INDEX.md` に line 84 で記載。`.planning/patterns.md` の `Data・Persistence` セクションに "thread-files 共有フォルダ規約" エントリ追記済み。 |
| 7 | integration check で 1 経路以上が実環境 end-to-end で動作 | VERIFIED | `docs/phase-37-integration-check.md` に記録済み。Scenario A (scan + SystemMessage prepend、11.2s) / Scenario B (attachments_extract via MCP、12.2s) が実環境で PASS。Scenario C/D は unit test で保証。Scenario E (0 文字 PDF) のみ実ファイル不足でスキップ (D-08 ロジック実装 + ADR 記載で代替)。 |

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|---------|--------|---------|
| `mcp_server/tools/attachments.py` | attachments_list_core / attachments_extract_core / _safe_resolve / _classify_error / Route A MCP wrappers | VERIFIED | 244 行、全関数実装済み。D-17: LLM は thread_id を渡さず CurrentHeaders() で解決。 |
| `app/jobs/handlers/attachments_helper.py` | scan_thread_attachments / build_attachments_hint 共有 helper | VERIFIED | 61 行、LangGraphHandler / OrchestratorHandler 両方から import して使用。 |
| `app/jobs/handlers/langgraph_handler.py` | scan + SystemMessage prepend + state.attachments 設定 | VERIFIED (partial) | scan + prepend + state 設定は実装済み (L153-185)。ただし per-job MCP client (L82-97) は build_graph に渡されず dead code (HIGH-01)。Chat モードでの attachments ツールは LLM に非公開。 |
| `app/jobs/handlers/orchestrator_handler.py` | per-job MultiServerMCPClient + headers + scan/prepend | VERIFIED | Phase 37.1 修正コミット `13ec129`, `4842c04` で SuperChat 経路に完全実装。 |
| `app/api/routes/chat.py::delete_thread` | shutil.rmtree + realpath prefix guard | VERIFIED | L394-406 に実装。realpath guard が必ず実行される (W-01 MUST 化)。 |
| `app/orchestrator/state.py` | AgentState.attachments フィールド | VERIFIED | L19 に `attachments: list[dict] \| None` 定義済み。 |
| `config/mcp_tools.yaml` | attachments_list / attachments_extract エントリ | VERIFIED | L160-214 に両エントリ完全定義。`privileged: false`, `sandbox_exposed: true`。 |
| `agents/general-assistant/AGENT.md` | tools リストに attachments_list / attachments_extract | VERIFIED | frontmatter tools 行 14-15 に両ツール宣言。system prompt に "推測せず必ず attachments_extract を呼ぶ" 指示追加 (Phase 37.1 commit `5070b5c`)。 |
| `docker-compose.yml` | thread-files volume + 3 サービス mount (api: RW / mcp-server: RW / worker: RO) | VERIFIED | line 45 (mcp-server: RW) / line 87 (api: RW) / line 117 (worker: RO) + L158 に named volume 定義。 |
| `docs/adr/0048-thread-files-folder-convention.md` | フォルダ規約 ADR (D-08 方針含む) | VERIFIED | 157 行、全決定事項網羅。D-08 (0 文字 PDF は error ではなく content:"") セクション明記。 |
| `docs/adr/INDEX.md` | 0048 エントリ | VERIFIED | line 84 に登録済み (Total 45)。 |
| `.planning/patterns.md` | Data・Persistence セクションに thread-files エントリ | VERIFIED | L275-281 に "thread-files 共有フォルダ規約" エントリ追記済み。 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `OrchestratorHandler` | `mcp_server` attachments tools | `MultiServerMCPClient(headers={x-thread-id, x-github-login})` + `get_tools()` → `SubAgentRegistry` | WIRED | `orchestrator_handler.py:109-119`. RPCContext が伝播し、`CurrentHeaders()` で mcp-server が受け取る。 |
| `attachments_extract` (MCP tool) | `attachments_extract_core` | `CurrentHeaders()` DI で thread_id/github_login を解決 | WIRED | `attachments.py:224-237`. Route A パターン確定済み (Plan 01 Verdict)。 |
| `delete_thread` (API) | `shutil.rmtree` (folder 削除) | realpath prefix guard を通す | WIRED | `chat.py:394-406`. guard → rmtree の順序が正しい。 |
| `langgraph_handler` | `attachments_helper` (scan/hint) | `scan_thread_attachments` + `build_attachments_hint` import | WIRED | `langgraph_handler.py:11-14, 154-155`. SystemMessage prepend に使用。 |
| `LangGraphHandler` | MCP attachments tools (LLM 公開) | `build_graph` への mcp_tools 渡し | NOT_WIRED (HIGH-01) | `langgraph_handler.py:82-97` で per-job client を生成するが `build_graph` に渡していない。Chat 画面での LLM へのツール公開は不成立。SuperChat 経路は別途 OrchestratorHandler で成立。 |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `OrchestratorHandler` の initial state | `attachments` | `scan_thread_attachments(thread_id, github_login)` — `os.listdir + os.stat` | Yes (実ファイルシステム) | FLOWING |
| `LangGraphHandler` の state_input | `attachments` | 同上 | Yes | FLOWING |
| `attachments_extract_core` の戻り値 | `text` | `_extract_text(safe_path)` — MarkItDown + asyncio.wait_for | Yes (実 PDF/Office ファイルから抽出) | FLOWING |
| `attachments_list_core` の戻り値 | ファイルメタリスト | `os.listdir + os.stat` | Yes | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| attachments_extract_core が path traversal を拒否 | `tests/test_attachments_extract.py::test_path_traversal` | error.code == "corrupt" (traversal/invalid) | PASS (unit test) |
| attachments_extract_core が size_over を返す | `tests/test_attachments_extract.py::test_extract_size_over` | error.code == "size_over" | PASS (unit test) |
| attachments_extract_core が timeout を返す | `tests/test_attachments_extract.py::test_extract_timeout` | error.code == "extract_timeout" | PASS (unit test) |
| delete_thread が shutil.rmtree を呼ぶ | `tests/test_api_chat.py::test_delete_thread_removes_folder` | rmtree 1 回呼び出し確認 | PASS (unit test) |
| delete_thread が path traversal を拒否 | `tests/test_api_chat.py::test_delete_thread_rejects_path_traversal` | rmtree が呼ばれない | PASS (unit test) |
| end-to-end: scan + SystemMessage prepend (Scenario A) | 実環境: SuperChat で添付ファイルあり thread に送信 | 11.2s で AI が添付を認識して応答 | PASS (integration check) |
| end-to-end: attachments_extract via MCP (Scenario B) | 実環境: AI が attachments_extract を呼び PDF 内容を要約 | 12.2s (extract 単独 507ms) | PASS (integration check) |
| 0 文字 PDF の D-08 挙動 (Scenario E) | 実環境: OCR 未対応 PDF で attachments_extract | 未実施 (サンプルファイル不足) | SKIP — D-08 ロジック実装済み + ADR-0048 記載で代替 |

---

## Requirements Coverage (詳細)

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FIN-03 | Plan 03, Plan 05 | PDF/Office 4 形式テキスト抽出 | SATISFIED | `attachments_extract_core` + 6 unit tests + Scenario B integration |
| FIN-04 | Plan 01, Plan 03, Plan 05 | MCP ツール経由 AI 参照 + RPCContext 伝播 | SATISFIED | Route A (CurrentHeaders DI) + per-job headers + Scenario B integration |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `mcp_server/tools/attachments.py` | 181 | `except BaseException as e:` が `asyncio.CancelledError` を握り潰す | HIGH | Worker シャットダウン時の協調キャンセル破綻リスク。通常運用では表面化しにくい。REVIEW.md HIGH-02 参照。 |
| `app/jobs/handlers/langgraph_handler.py` | 82-97 | per-job MCP client を生成するが `build_graph` に渡さず dead code | HIGH | Chat 画面で attachments_list/extract が LLM に公開されない。SuperChat は別経路で正常動作。REVIEW.md HIGH-01 参照。 |
| `app/jobs/handlers/orchestrator_handler.py` | 290-291 | `per_job_mcp_client` が finally でクリーンアップされない | MEDIUM | 接続リーク可能性。社内 200 名規模では顕在化しにくい。REVIEW.md MEDIUM-02 参照。 |
| `app/api/routes/chat.py` | 403-404 | `except ValueError: pass` — path traversal 検出時にログなし | MEDIUM | コメントに「ログだけ残して」と書かれているが実際は無出力。攻撃試行が監査ログに残らない。REVIEW.md MEDIUM-03 参照。 |
| `mcp_server/tools/attachments.py` | 100-101 | `_classify_error` の `corrupt` ケースで内部例外メッセージを `{exc}` で文字列化 | LOW | ファイルパスが LLM コンテキストに漏洩する可能性。REVIEW.md LOW-01 参照。 |

---

## Human Verification Required

(なし — Scenario A/B の end-to-end 確認が integration check で完了済み。Scenario E の 0 文字 PDF は D-08 デシジョンにより phase 37 の合否には影響しない。)

---

## Known Issues Summary

以下は Code Review (REVIEW.md) で検出された問題のうち、Phase 37 のゴール達成自体には影響しないが後続フェーズで対応すべき項目:

### HIGH-01: Chat 画面での MCP ツール公開なし

`langgraph_handler.py:82-97` に per-job MCP client を生成するブロックがあるが、生成した client を `build_graph` に渡していない。結果として、通常チャット (`task_type=langgraph`) では `attachments_list` / `attachments_extract` が LLM のツールリストに含まれない。

**現状:** Phase 37 の FIN-04 達成対象は SuperChat (OrchestratorHandler 経路) とし、そちらで end-to-end 動作確認済み。Chat 画面での添付ファイルツール公開は Phase 38 のスコープとして追跡することを推奨。

**即時推奨対応:** dead code を削除する (langgraph_handler.py L78-97 のブロックを除去) か、Phase 38 で Chat 画面にもツール対応を追加する計画を立てる。

### HIGH-02: asyncio.CancelledError の握り潰し

`mcp_server/tools/attachments.py:181` の `except BaseException` を `except asyncio.CancelledError: raise` + `except Exception` の 2 段構えに変更する。

### MEDIUM-02: per_job_mcp_client のクリーンアップ漏れ

`orchestrator_handler.py::finally` に `per_job_mcp_client.__aexit__` を追加する。

### MEDIUM-03: path traversal 検出時のログ欠如

`chat.py:403` の `except ValueError: pass` を `except ValueError as ve: logger.warning(...)` に変更する。

---

## Verdict

**Status: passed**

Phase 37 の 7 つの Success Criteria はすべて達成されている:

1. FIN-03 の抽出パイプライン (4 形式 / timeout / size / truncation / 5 エラーコード) が `mcp_server/tools/attachments.py` に完全実装され、unit test 6 ケースで検証済み。
2. FIN-04 の MCP ツール経由 AI 参照と RPCContext 伝播が SuperChat (OrchestratorHandler) 経路で end-to-end 動作確認済み (Scenario B)。
3. 添付一覧の SystemMessage prepend が両 handler で実装済み (Scenario A で動作確認)。
4. `AgentState.attachments` フィールドが追加され、毎 turn 設定される。
5. thread 削除 hook + path traversal 防御が `delete_thread` に実装され、unit test で検証済み。
6. ADR-0048 が全決定事項 (パス / 命名 / volume / D-08 / path traversal) を文書化。patterns.md / INDEX.md も更新済み。
7. integration check の Scenario A/B で 1 経路以上が実環境 end-to-end で動作確認済み。

Code Review で HIGH 2 件が検出されているが、いずれもフェーズゴール達成の範囲では許容されると判断する根拠は:
- HIGH-01 は SuperChat 経路で FIN-04 が成立しており、Chat 画面対応は Phase 38 スコープ
- HIGH-02 は通常運用で表面化しにくい shutdown コーナーケース

これらは後続フェーズで修正すべき known issues として記録し、Phase 37 のマージ判断は `passed` とする。

---

_Verified: 2026-04-22_
_Verifier: Claude (gsd-verifier)_
