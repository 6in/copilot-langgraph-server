---
phase: 38
plan: 1
plan_id: 38-01-types-and-roundtrip-gate
subsystem: frontend-types + tests-scaffolding
tags: [worker-output, attachments, kind-discriminator, checkpoint-round-trip, wave-0-risk-gate]
requirements: [FOUT-04]
dependency_graph:
  requires:
    - "Phase 36 AttachmentMeta DTO (frontend/src/types.ts, useAttachments hook)"
    - "Phase 36 AsyncPostgresSaver HumanMessage round-trip (patterns.md L79-85)"
  provides:
    - "AttachmentMeta.kind 'user_upload' | 'generated' discriminator 型 (D-30 案 A 確定)"
    - "AIMessage.additional_kwargs.attachments の AsyncPostgresSaver JSONB round-trip 保証 (Wave 0 risk-gate)"
    - "VALIDATION.md と 1:1 対応する 6 テストファイルの skip scaffold (5 新規 + 1 round-trip green)"
  affects:
    - "Plan 02 (Wave 1): outputs route + attachments_list kind 拡張は本 plan の型契約と scaffold を消費"
    - "Plan 03 (Wave 1): post-process rename / cwd 切替 / claude_code cwd 削除も同 scaffold を消費"
    - "Plan 04 (Wave 2): AIMessage.additional_kwargs.attachments bundle は本 plan の round-trip 検証を前提"
    - "Plan 05 (Wave 3): AttachmentChipRow kind 別描画 / AttachmentModal は本 plan の型を消費"
tech_stack:
  added: []
  patterns:
    - "Wave 0 risk-gate: checkpointer round-trip を MVP 前に潰す (patterns.md L94-99)"
    - "TDD RED → GREEN: types.ts 単独編集で型エラーを誘発 → useAttachments で吸収"
    - "Skip scaffold: 後続 plan の executor が assertion 本体を書くだけで進められる shape"
key_files:
  created:
    - tests/test_langgraph_handler_outputs_bundle.py
    - tests/test_outputs_route.py
    - tests/test_mcp_attachments_kind.py
    - tests/test_post_process_rename.py
    - tests/test_execute_python_output.py
    - tests/test_claude_code_no_cwd_arg.py
    - .planning/phases/38-worker-dl/deferred-items.md
  modified:
    - frontend/src/types.ts
    - frontend/src/hooks/useAttachments.ts
decisions:
  - "D-30 案 A 確定: AttachmentMeta.kind を 'user_upload' | 'generated' literal union に置換 (Plan 04 が Python 側の attachments.py upload route hardcoded 'kind': 'file' を担当する段階的委譲)"
  - "Wave 0 risk-gate = AsyncPostgresSaver round-trip 1 ケース green (test_round_trip_postgres / postgres 未起動環境では pytest.skip で逃がす)"
  - "後続 wave 用 5 テストファイルは shape (import + fixture + skip 付き def) のみ scaffold、本 plan で assertion 本体は書かない"
  - "ChatApp.tsx:147 の item.kind === 'file' は DataTransferItem.kind (browser API) で別 namespace、AttachmentMeta.kind の enum 化と衝突しないため変更不要"
  - "pre-existing TypeScript エラー 7 件 (bulkRemoveThreads not on UseThreadsReturn / MermaidBlock の Theme import) は本 plan scope 外なので deferred-items.md に記録、本 plan の verify ロジックは「本 plan 由来エラーゼロ」を達成基準とする"
metrics:
  duration_minutes: 30
  completed_date: 2026-05-12
  tasks_completed: 3
  files_created: 7
  files_modified: 2
  commits: 3
---

# Phase 38 Plan 01: AttachmentMeta enum 化 + Wave 0 round-trip gate + テスト scaffold Summary

D-30 案 A を確定して `AttachmentMeta.kind` を `'user_upload' | 'generated'` discriminator に enum 化し、AsyncPostgresSaver 経由の AIMessage round-trip を 1 本の green テストで Wave 0 risk-gate を潰しつつ、VALIDATION.md と 1:1 対応する 5 つの skip scaffold で後続 wave の並列展開土台を整備した。

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | AttachmentMeta.kind を enum 化し staging / 描画整合をとる (D-30 案 A 確定) | `e73c692` | frontend/src/types.ts, frontend/src/hooks/useAttachments.ts |
| 2 | AIMessage.additional_kwargs.attachments の AsyncPostgresSaver round-trip 検証 (Wave 0 risk-gate) | `321ca89` | tests/test_langgraph_handler_outputs_bundle.py |
| 3 | 後続 wave 用 5 つの MISSING テストファイルを skip scaffold で作成 | `a46de3a` | tests/test_outputs_route.py, tests/test_mcp_attachments_kind.py, tests/test_post_process_rename.py, tests/test_execute_python_output.py, tests/test_claude_code_no_cwd_arg.py |

## Key Decisions / Implementation

### D-30 案 A の確定 (TS 型契約レベル)

CONTEXT.md `critical_unresolved_decision` で planner 判断とされていた `AttachmentMeta.kind` 衝突問題を本 plan で確定:

- **Before**: `kind: 'file'` (DTO 識別子としての固定リテラル — UI / API / hook いずれも実判定に使っていない死フィールド)
- **After**: `kind: 'user_upload' | 'generated'` (Phase 36 アップロードと Phase 38 worker 生成を識別する single discriminator)

判断根拠:
- UI-SPEC L302-307 と CONTEXT.md D-06 が `kind: 'user_upload' | 'generated'` を要求している
- grep で外部参照ゼロ (`ChatApp.tsx:147` の `item.kind === 'file'` は `DataTransferItem.kind` で別 namespace)
- 段階的委譲: 本 plan は TypeScript 型 + hook + MessageArea スコープに限定。Python 側 (`app/api/routes/attachments.py` の upload route hardcoded `'kind': 'file'`) は Plan 04 の `_messages_to_response` 経由で legacy 値正規化と合わせて扱う

### Wave 0 risk-gate (patterns.md L94-99)

新規データを `BaseMessage.additional_kwargs` に載せる場合、AsyncPostgresSaver の JSONB serialize/deserialize 経路で値が壊れないことを Plan 01 で 1 本のテストで潰す。

- `AIMessage(content="ok", additional_kwargs={"attachments": [{"kind": "generated", "name": "...", "size": 123, "ext": ".png", "modified_at": 1.0}]})` を最小 graph で 1 回 invoke
- 2 つ目の接続から `aget` で復元
- 値・order・kind 全フィールドが完全一致することを assert (`assert restored_atts == [generated_meta]`)
- postgres 未起動環境では TCP probe で skip に逃がす shape (CI でも安定)

ADR-0038 の AIMessage.name 喪失問題と境界を切り、`additional_kwargs` が独立して round-trip することを green テストで証明した。

### Skip scaffold 5 ファイル (VALIDATION.md と 1:1)

後続 plan の executor が skip マーカーを外して assertion 本体を書くだけで進められる shape:

| ファイル | 含む test 関数 | Plan |
|---------|-------------|------|
| `tests/test_outputs_route.py` | `test_get_output_returns_raw_bytes` (38-04-01) / `test_path_traversal_rejected` (38-01-03) / `test_isolation_other_user_blocked` (38-01-02) / `test_get_output_works_for_claude_code` (38-04-02) | 02 / 04 |
| `tests/test_mcp_attachments_kind.py` | `test_returns_both_kinds` (38-02-01) | 02 |
| `tests/test_post_process_rename.py` | `test_snapshot_diff_renames_only_new` (38-03-02) / `test_skips_already_prefixed` (38-03-03) / `test_excludes_pyc_files` | 03 |
| `tests/test_execute_python_output.py` | `test_writes_to_generated_folder` (38-03-01) / `test_falls_back_to_tmp_without_headers` | 03 |
| `tests/test_claude_code_no_cwd_arg.py` | `test_signature_has_no_cwd` (38-03-04) | 03 |

11 件すべて `pytest --collect-only` で列挙可能 / すべて SKIPPED マーカーで実行されない。

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/test_langgraph_handler_outputs_bundle.py::test_round_trip_postgres -x` | ✅ 1 passed in 0.38s (postgres docker compose 経由で実 round-trip 検証) |
| `uv run pytest tests/test_outputs_route.py tests/test_mcp_attachments_kind.py tests/test_post_process_rename.py tests/test_execute_python_output.py tests/test_claude_code_no_cwd_arg.py --collect-only -q` | ✅ 11 tests collected, exit 0 |
| `bun run tsc -b --force` for in-scope changes (`useAttachments.ts` / `types.ts`) | ✅ 本 plan 由来エラー 0 件 |
| Full suite `uv run pytest tests/ --ignore=tests/test_api_chat.py` | ✅ Phase 38 由来の新規 failed ゼロ (22 failed は base ブランチ 7a0c495 でも同じ pre-existing 問題) |
| Source assertion: `grep -E "kind:\\s*'user_upload'\\s*\\|\\s*'generated'" frontend/src/types.ts` | ✅ 1 match |
| Source assertion: `grep -c "kind: 'file'" frontend/src/types.ts` | ✅ 0 |
| Source assertion: `grep -c "kind: 'file'" frontend/src/hooks/useAttachments.ts` | ✅ 0 |
| Source assertion: `grep -c "kind: 'user_upload'" frontend/src/hooks/useAttachments.ts` | ✅ 1 |
| Source assertion: `grep -c "item.kind === 'file'" frontend/src/components/ChatApp.tsx` | ✅ 1 (DataTransferItem.kind は維持) |

### Wave 0 acceptance (CONTEXT.md / patterns.md L94-99)

- ✅ AttachmentMeta.kind が D-30 案 A discriminator として確定
- ✅ AIMessage.additional_kwargs.attachments の JSONB round-trip が green
- ✅ 後続 Plan 02 / 03 が並列展開可能な scaffold 完了

## Deviations from Plan

### Auto-fixed Issues

**None for in-scope work.** All 3 tasks completed exactly as written.

### Scope-Boundary Deferrals (Rule "Scope Boundary")

**1. [Scope] pre-existing TypeScript エラー 7 件は deferred-items.md へ**
- **Found during:** Task 1 verify (`bun run tsc -b --force`)
- **Issue:** `bulkRemoveThreads not on UseThreadsReturn` (5 ファイル) + `MermaidBlock` の `Theme` import (1 ファイル) + `useThreads.ts:94` の type literal mismatch (1 ファイル) = 計 7 件
- **Verification it's pre-existing:** `git checkout 7a0c4950164a43f73113b1d493a16d2fc3182d0d -- tests/ frontend/` で base 復元後に同じ tsc 実行 → 同じ 7 件のエラーが再現することを確認
- **Action:** `.planning/phases/38-worker-dl/deferred-items.md` に詳細記録、本 plan の verify ロジックは「本 plan 由来エラーゼロ」を達成基準とする
- **Why this is appropriate:** これらは Phase 38 のスコープ (`AttachmentMeta.kind` enum 化) とは無関係なため、Rule 4 architectural decisions / Scope Boundary により未修正のまま deferred とする

**2. [Scope] pre-existing pytest failures 22 件は record-only**
- **Found during:** Final verification full suite (`uv run pytest tests/ --ignore=tests/test_api_chat.py`)
- **Issue:** 22 failed (test_graph / test_mcp_server / test_rpc_integration / test_sse / test_tool_catalog_js / test_tool_enabled_subagent / test_tool_registry / test_worker)
- **Verification it's pre-existing:** base ブランチ復元 + 同コマンドで **同じ 22 failed** を再現
- **Action:** 本 plan は触らない。後方互換性 = 「本 plan 由来の新規 failed ゼロ」を達成

### Authentication Gates

なし — 本 plan は frontend 型 + test scaffold のみで認可境界に触れない。

## Deferred Issues

- `bulkRemoveThreads` 未宣言問題 (`useThreads.ts` + 5 consumer) と `MermaidBlock` の `Theme` import 解決は v6.1+ Polish もしくは `/gsd-verify-work` のタイミングで取り上げる (`.planning/phases/38-worker-dl/deferred-items.md` 参照)

## Files Created

- `tests/test_langgraph_handler_outputs_bundle.py` — Wave 0 round-trip green + Plan 04 skip scaffold
- `tests/test_outputs_route.py` — Plan 02 / 04 skip scaffold (4 test)
- `tests/test_mcp_attachments_kind.py` — Plan 02 skip scaffold (1 test)
- `tests/test_post_process_rename.py` — Plan 03 skip scaffold (3 test)
- `tests/test_execute_python_output.py` — Plan 03 skip scaffold (2 test)
- `tests/test_claude_code_no_cwd_arg.py` — Plan 03 skip scaffold (1 test)
- `.planning/phases/38-worker-dl/deferred-items.md` — pre-existing TS 7 件の記録

## Files Modified

- `frontend/src/types.ts` — `AttachmentMeta.kind` を `'user_upload' | 'generated'` literal union に置換、新規 type alias `AIMessageAttachmentsKind` を公開
- `frontend/src/hooks/useAttachments.ts` — staging item の `kind: 'file'` を `kind: 'user_upload'` に置換 (新型整合)

## Self-Check: PASSED

- ✅ `tests/test_langgraph_handler_outputs_bundle.py` exists
- ✅ `tests/test_outputs_route.py` exists
- ✅ `tests/test_mcp_attachments_kind.py` exists
- ✅ `tests/test_post_process_rename.py` exists
- ✅ `tests/test_execute_python_output.py` exists
- ✅ `tests/test_claude_code_no_cwd_arg.py` exists
- ✅ `.planning/phases/38-worker-dl/deferred-items.md` exists
- ✅ Commit `e73c692` exists in git log
- ✅ Commit `321ca89` exists in git log
- ✅ Commit `a46de3a` exists in git log
