# Phase 39 — 開始時点 baseline (test / tsc / grep 実測値)

**計測日:** 2026-05-13
**計測者:** gsd-executor (Plan 39-01 Task 1)
**目的:** Wave 3 close 時の差分計測用の固定値 (後続 plan の verify はここを参照する)。
**前提:** docker compose は未起動のため `bun x tsc` は host 側 (`frontend/` 直下) で実行。

---

## pytest baseline (Python)

**コマンド:** `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no`

**サマリ (実測):**

```
27 failed, 397 passed, 13 skipped, 1 xfailed, 1 xpassed, 57 warnings in 35.60s
```

- **failed = 27**
- **passed = 397**
- **skipped = 13** (うち `tests/test_mcp_server.py` は `fastmcp` 未 install のため `--ignore` で除外、ここに含まれない)
- **xfailed = 1**
- **xpassed = 1**

### 失敗テストフルリスト (27 件)

| # | Test |
|---|------|
| 1 | `tests/test_api_chat.py::test_delete_thread_calls_adelete` |
| 2 | `tests/test_api_chat.py::test_list_threads_app_id_filter` |
| 3 | `tests/test_api_chat.py::test_list_threads_empty` |
| 4 | `tests/test_api_chat.py::test_list_threads_left_join` |
| 5 | `tests/test_api_chat.py::test_list_threads_no_app_id_returns_all` |
| 6 | `tests/test_api_chat.py::test_new_thread_returns_uuid` |
| 7 | `tests/test_api_jobs.py::test_get_job_done` |
| 8 | `tests/test_api_jobs.py::test_get_job_pending` |
| 9 | `tests/test_debate_handler.py::test_handle_calls_build_debate_graph` |
| 10 | `tests/test_generate_mcp_artifacts.py::test_build_docs_header_and_table` |
| 11 | `tests/test_generate_mcp_artifacts.py::test_build_helper_has_four_functions` |
| 12 | `tests/test_generate_mcp_artifacts.py::test_build_js_order` |
| 13 | `tests/test_generate_mcp_artifacts.py::test_load_tools_has_six_tools` |
| 14 | `tests/test_graph.py::test_messages_accumulate` |
| 15 | `tests/test_graph.py::test_single_message_response` |
| 16 | `tests/test_graph.py::test_thread_isolation` |
| 17 | `tests/test_rpc_integration.py::test_orchestrator_handler_injects_context` |
| 18 | `tests/test_sse.py::test_sse_already_done` |
| 19 | `tests/test_sse.py::test_sse_done_signal` |
| 20 | `tests/test_tool_catalog_js.py::test_catalog_contains_six_tools` |
| 21 | `tests/test_tool_enabled_subagent.py::test_tool_enabled_subagent_runs_react_loop` |
| 22 | `tests/test_tool_registry.py::test_tool_registry_real_yaml_contract` |
| 23 | `tests/test_worker.py::test_orchestrator_handler_uses_checkpointer` |
| 24 | `tests/test_worker.py::test_process_chat_closes_llm` |
| 25 | `tests/test_worker.py::test_process_chat_error_handling` |
| 26 | `tests/test_worker.py::test_process_chat_saves_result` |
| 27 | `tests/test_worker.py::test_startup_creates_redis_and_jobstore` |

### 5 パターン分類 (RESEARCH.md L19-25 と一致、実測値)

| Pattern | 件数 | 内訳 | 想定原因 |
|---------|-----:|------|---------|
| **A. JWT cookie 不足 (401)** | 7 | test_api_chat 3 (delete_thread / list_threads_empty / new_thread_returns_uuid) + test_api_jobs 2 + test_sse 2 | route が `Depends(get_jwt_payload)` を要求しているのにテストが JWT cookie なしで呼んでいる |
| **B. psycopg AsyncMock 不整合** | 4 | test_api_chat 3 (list_threads_app_id_filter / list_threads_left_join / list_threads_no_app_id_returns_all) + test_worker 1 (test_startup_creates_redis_and_jobstore) | DB mock の AsyncConnection パターンが現在の実装と不一致 |
| **C. LLM mock `astream` AsyncMock** | 6 | test_graph 3 + test_worker 3 (process_chat_closes_llm / process_chat_error_handling / process_chat_saves_result) | `'async for' got coroutine` — LLM の astream 戻り値が AsyncMock のままで async iterator になっていない |
| **D. mock 経路 (assertion 不整合)** | 4 | test_debate_handler 1 + test_rpc_integration 1 + test_tool_enabled_subagent 1 + test_worker 1 (orchestrator_handler_uses_checkpointer) | 各テストで期待する mock 呼び出し / orchestrator handler 検証が現状実装と乖離 |
| **E. tool catalog drift** | 6 | test_tool_catalog_js 1 + test_tool_registry 1 + test_generate_mcp_artifacts 4 | Phase 37 で attachments_list / attachments_extract 追加時に hardcoded 数値 (`== 6`) / カタログ contract 更新が漏れている |

合計: 7 + 4 + 6 + 4 + 6 = **27 件** ✅

---

## TS baseline (frontend)

**コマンド:** `cd frontend && bun x tsc -b --force` (docker compose 未起動のため host 側で代用)

**サマリ (実測):**

- **error 件数 = 7**

### 全 TS エラーリスト

```
src/components/CanvasChatApp.tsx(69,5): error TS2339: Property 'bulkRemoveThreads' does not exist on type 'UseThreadsReturn'.
src/components/ChatApp.tsx(53,5): error TS2339: Property 'bulkRemoveThreads' does not exist on type 'UseThreadsReturn'.
src/components/DebateChatApp.tsx(545,5): error TS2339: Property 'bulkRemoveThreads' does not exist on type 'UseThreadsReturn'.
src/components/GemChatApp.tsx(47,5): error TS2339: Property 'bulkRemoveThreads' does not exist on type 'UseThreadsReturn'.
src/components/MermaidBlock.tsx(13,15): error TS2459: Module '"../contexts/ThemeContext"' declares 'Theme' locally, but it is not exported.
src/components/SuperChatApp.tsx(135,5): error TS2339: Property 'bulkRemoveThreads' does not exist on type 'UseThreadsReturn'.
src/hooks/useThreads.ts(94,5): error TS2561: Object literal may only specify known properties, but 'bulkRemoveThreads' does not exist in type 'UseThreadsReturn'.
```

### 分類

| グループ | 件数 | 修正方針 |
|---------|-----:|---------|
| `bulkRemoveThreads` 型不足 | 6 | `useThreads` return 型に `bulkRemoveThreads: (ids: string[]) => Promise<void>` 追加 (5 consumer + useThreads 自身) |
| `Theme` 型 export 不足 | 1 | `ThemeContext.ts` を `export type Theme = ...` で公開 (MermaidBlock 側の lazy import 解決) |

### RESEARCH.md L17 (D-08 主張 7 件 + 追加 4 件) との比較

RESEARCH.md 時点では `MermaidBlock.tsx:12` の `html-to-image` 未解決 (TS2307) + implicit any 3 件の追加 4 件が観測されていたが、Plan 01 開始時の `bun install` で `node_modules` が再生成された結果、本 baseline では **7 件のみ**。RESEARCH.md の追加 4 件は node_modules permission 由来 (もしくは未 install) と確定し、本 phase の scope (D-08 7 件) に追加対応は不要。

---

## Dead code grep baseline (UIFIX-03)

**コマンド:** `grep -cE 'register_sse|unregister_sse|self\.queues' app/jobs/job_store.py`

**実測値: 7**

### 詳細 (line 番号付き)

```
13:        self.queues: dict[str, asyncio.Queue] = {}
15:    def register_sse(self, job_id: str) -> asyncio.Queue:
18:        self.queues[job_id] = queue
21:    def unregister_sse(self, job_id: str) -> None:
23:        self.queues.pop(job_id, None)
35:        if job_id in self.queues:
37:            await self.queues[job_id].put(event)
```

- `register_sse` / `unregister_sse` 関数定義 2 件
- `self.queues` 参照 5 件 (定義 1 + 代入 1 + pop 1 + 存在判定 1 + put 1)

**Note:** RESEARCH.md / PLAN.md は "dead code 5+ 件" と表現するが、`-cE` で行マッチカウントすると 7 件 (上記)。各表現は同じ block の異なる集計方法。

---

## cwd= grep baseline (D-09)

**コマンド:** `grep -c 'cwd=' tests/test_mcp_server.py`

**実測値: 6**

### 詳細 (line 番号付き)

```
293:            await claude_code(prompt="test", cwd="/tmp")
316:        result = await claude_code(prompt="test", cwd="/tmp")
341:        result = await claude_code(prompt="test", cwd="/tmp")
372:        result = await claude_code(prompt="test", cwd="/tmp")
394:        result = await claude_code(prompt="test", cwd="/tmp")
410:        result = await claude_code(prompt="test", cwd="/tmp")
```

- claude_code 呼び出し 6 件すべてに `cwd="/tmp"` あり
- CONTEXT.md D-09 は「claude_code 系 7 件 (`test_claude_code_env_sanitized` 他)」と主張するが grep 実測 6 件 (test_db_query は本ファイル内に存在せず、CONTEXT.md の数値は ±1 件の乖離)
- 本 phase の正規化値: **6 件すべての `cwd=` kwarg を削除**

---

## D-10 target reconciliation

CONTEXT.md L57-61 は Phase 36 由来の pre-existing failures を **「14 failures + 4 errors」** と記載するが、これは Phase 36 完了直後 (2026-05-11) の数値で本 phase 開始時点では **obsolete**。

### 本 baseline で採用する数値 (実測 2026-05-13)

- **failed = 27**
- **errors = 0**

### obsolete 解消の根拠

- `tests/test_install_hooks.py` は Phase 36 当時 "4 errors (FileNotFoundError)" だったが、現状 `pytest tests/test_install_hooks.py -q --tb=no` で **4 passed** を確認。本 phase は test_install_hooks に手を触れない。
- 残り failures は Phase 36 deferred-items 記録時点から純増 (Phase 37/38 で追加された hardcoded `== 6` / drift 等が加算) しているため、CONTEXT.md の "14 failures" 数値ではなく本 baseline の 27 件を採用する。
- パターン分類 (A..E) は RESEARCH.md L19-25 で再計測済、本 baseline で固定する。

### Wave 分割への含意

PLAN 06 / 07 (Wave 3) は D-10 範囲を扱う。pattern A (JWT cookie 不足) は本 phase でも UIFIX-03 (Pattern A の test_sse 2 件) と直接重なるため、UIFIX-03 を Wave 2 で先に通したあと、残り 25 件 (= 27 - test_sse 2) を pattern 単位で wave 分割する設計が後続 plan で確定済。

---

## Phase 39 完了時の target

本 phase の close 条件 (Wave 3 完了時点で全達成):

| Metric | Baseline (本 baseline) | Target | 由来 |
|--------|-----------------------:|-------:|------|
| pytest failed (全 suite, `--ignore=tests/test_mcp_server.py`) | 27 | **≤ 2** | 25 件減 (D-10 pattern A..E 全潰し)。残 2 件分の余裕は別 pattern 取りこぼし / mock 環境差吸収のため。test_sse 2 件は Plan 39-04 で潰す |
| TS error (`bun x tsc -b --force`) | 7 | **0** | D-08 確定、6+1 全潰し |
| `grep -c 'cwd=' tests/test_mcp_server.py` | 6 | **0** | D-09 確定、claude_code 系 6 件すべて kwarg 削除 |
| `grep -cE 'register_sse\|unregister_sse\|self\.queues' app/jobs/job_store.py` | 7 | **0** | D-04 確定、dead code 完全削除 |
| `grep -c 'test_register_and_notify\|test_unregister_sse' tests/test_job_store.py` | (未計測、本 baseline 範囲外) | **0** | D-04 確定、テスト側 dead code 削除 |
| 39-VALIDATION.md `wave_0_complete` | false | **true** | Plan 39-01 Task 2 で更新 |
| 39-VALIDATION.md `nyquist_compliant` | false | **true** | Plan 39-01 Task 2 で更新 |

### close 判定の運用

- `/gsd-verify-work` 時点で本 BASELINE.md の Target 欄の値を満たさない metric があれば、deferred-items.md でその差分を明文化する (= Phase 39 close 後の v6.1+ 持ち越し項目とする)。
- 本 BASELINE.md の数値は固定値として保持。本 phase 中に再計測した値は per-plan SUMMARY に追記する形で記録 (BASELINE.md の数値は書き換えない)。

---

## Plan 08 完了時の実測値 (2026-05-13)

**コマンド:** `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no`

**サマリ (Plan 08 単独完了時点、Plan 07 worktree 未マージ):**

```
8 failed, 414 passed, 13 skipped, 1 xfailed, 1 xpassed, 52 warnings in 5.83s
```

### Plan 別の解消件数

| Plan | 解消件数 | 内訳 |
|------|---------:|------|
| Plan 04 | 4 件 | test_sse 2 件削除 + test_job_store dead code テスト 2 件削除 (Pattern A の test_sse 2 件 + D-04 dead code) |
| Plan 06 | 6 件 | Pattern E (mcp catalog drift) — test_generate_mcp_artifacts 4 + test_tool_catalog_js 1 + test_tool_registry 1 |
| Plan 07 | 9 件 (想定) | Pattern A test_api_chat 6 件 (delete_thread/list_threads_*/new_thread) + test_api_jobs 2 件 + Pattern B test_api_chat 3 件のうち重複分を除いた 9 件分 (※並列実行中の別 worktree。本 plan の base には未マージ) |
| Plan 08 | 11 件 | Pattern C 6 件 (test_graph 3 + test_worker 3) + Pattern D 4 件 (test_worker 1 + test_debate_handler 1 + test_rpc_integration 1 + test_tool_enabled_subagent 1) + Pattern B test_worker 1 件 = 11 件 (test_worker.py 内の重複統合により実テスト関数数は 5) |

**累積:** 4 + 6 + 9 + 11 = 30 件分の修正だが、Pattern B の 4 件 (test_api_chat 3 + test_worker 1) と Plan 07/08 の test_worker 重複により実件数は 27 件と一致。

### 残失敗 8 件 (本 plan の base に Plan 07 が未マージのため)

| # | Test | Plan 担当 |
|---|------|-----------|
| 1 | `tests/test_api_chat.py::test_delete_thread_calls_adelete` | Plan 07 |
| 2 | `tests/test_api_chat.py::test_list_threads_app_id_filter` | Plan 07 |
| 3 | `tests/test_api_chat.py::test_list_threads_empty` | Plan 07 |
| 4 | `tests/test_api_chat.py::test_list_threads_left_join` | Plan 07 |
| 5 | `tests/test_api_chat.py::test_list_threads_no_app_id_returns_all` | Plan 07 |
| 6 | `tests/test_api_chat.py::test_new_thread_returns_uuid` | Plan 07 |
| 7 | `tests/test_api_jobs.py::test_get_job_done` | Plan 07 |
| 8 | `tests/test_api_jobs.py::test_get_job_pending` | Plan 07 |

すべて Plan 07 が分担する Pattern A (JWT cookie 不足) / Pattern B (psycopg AsyncMock) 系。Plan 07 worktree (commit 84295fc..ae78211) がマージされた時点で 8 → 0 件に到達する見込み。

### target failed: 27 → 0 の到達計画

Plan 08 単独では Plan 07 担当分を解消できない (別 worktree)。Phase 39 close 時点 (Plan 07 + Plan 08 両マージ後) で **target failed: 27 → 0** を達成する設計。user decision で defer 経路を撤廃した結果、Pattern B 全 4 件 (Plan 07 の test_api_chat 3 + Plan 08 の test_worker 1) は scope 内完遂となる。
