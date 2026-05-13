---
phase: 38
plan: 4
plan_id: 38-04-handler-bundle-and-helper
subsystem: handler + attachments-helper + api-normalization
tags: [langgraph-handler, attachments-helper, message-bundle, additional_kwargs, legacy-normalization, d-15, d-18, d-30]
requirements: [FOUT-01, FOUT-02, FOUT-04]
dependency_graph:
  requires:
    - "Plan 38-01: AttachmentMeta.kind を 'user_upload' | 'generated' に enum 化 (D-30 案 A) + 5 ファイルの skip scaffold"
    - "Plan 38-02: outputs route + attachments_list の _generated/ + kind 拡張 (FOUT-02 経路)"
    - "Plan 38-03: sandbox cwd → _generated/ 切替 + post-process rename ({ts}_{name} 命名規約)"
    - "Phase 36 helper (_resolve_thread_folder / _safe_resolve_file / _normalize_basename) — outputs route から helper 経由で再利用"
    - "Phase 37 attachments_helper.scan_thread_attachments / build_attachments_hint (D-11)"
  provides:
    - "attachments_helper.scan_thread_attachments が `_generated/` 含む flat list + 各 entry の `kind` discriminator を返す (D-18)"
    - "attachments_helper.build_attachments_hint が `[AI 生成]` / `[添付]` ラベルを表示する (D-18 表示層)"
    - "langgraph_handler.py が turn 完了時に AIMessage.additional_kwargs.attachments へ generated delta を merge (D-15) — AsyncPostgresSaver で JSONB 透過保存される"
    - "API _messages_to_response が legacy `kind: 'file'` → `'user_upload'` を非破壊正規化 (D-30 案 A 完遂)"
    - "attachments.py upload route が新規 upload で `kind: 'user_upload'` を直接書く (legacy 'file' 生成を停止)"
  affects:
    - "Plan 38-05 (frontend renderer): `'user_upload' | 'generated'` の union 型契約で AttachmentChipRow / AttachmentModal を実装できる"
    - "Plan 38-05 / 38-06: SystemMessage prepend と AIMessage bundle 経路に kind が乗ったため、過去スレッド再オープン時の復元が新型のみで完結"
tech_stack:
  added: []
  patterns:
    - "Wave 0 risk-gate (patterns.md L94-99): AIMessage.additional_kwargs round-trip を Plan 01 で潰し、本 plan の bundle を安全に依存させる"
    - "RESEARCH §Pattern 2: handler 再 scan + delta 抽出 + dict union merge (tool wrapper 側 rename と二重カウントしない設計)"
    - "RESEARCH §Pattern 3: SystemMessage prepend を kind 付き flat list に拡張 (件数制限なし、件数フィルタを prepend 側でも適用しない)"
    - "RESEARCH §Example 1: API 層で legacy 'file' を 'user_upload' に non-mutating 正規化 (LangGraph state 破壊回避)"
    - "Pitfall 2: additional_kwargs を `(existing or {}) | {…}` で merge し既存フィールドを潰さない"
    - "Pitfall 4: `_generated/` サブフォルダは 1 段だけ降り、`os.walk` / `rglob` を使わない"
    - "TDD: 各タスクで RED コミット (test 単独) → GREEN コミット (impl) で履歴に gate を残す"
key_files:
  created: []
  modified:
    - app/jobs/handlers/attachments_helper.py
    - app/jobs/handlers/langgraph_handler.py
    - app/api/routes/chat.py
    - app/api/routes/attachments.py
    - tests/test_langgraph_handler_attachments.py
    - tests/test_langgraph_handler_outputs_bundle.py
    - tests/test_outputs_route.py
    - tests/test_chat_history_additional_kwargs_api.py
    - tests/test_attachments_upload_route.py
    - .planning/phases/38-worker-dl/deferred-items.md
decisions:
  - "D-18 実装確定: scan_thread_attachments は input/output 両方を flat list で返し、各 entry に kind を必須付与する (件数フィルタなし)"
  - "D-15 実装確定: turn 完了時 (final_state 確定直後) に handler レベルで再 scan して generated delta を抽出し、final AIMessage の additional_kwargs に dict union で merge する。tool wrapper 側の rename とは独立 (二重カウントしない)"
  - "D-30 (案 A) 完遂: API _messages_to_response で legacy 'file' を 'user_upload' に非破壊正規化、attachments.py upload route も新規行は 'user_upload' で書く。frontend は新型 union のみを扱う"
  - "scope 限定: bundle ロジックは langgraph_handler のみに入れ、orchestrator_handler (SuperChat) は Plan 06 deferred-items 観察ベース判断 — PLAN.md Task 2 action 2 の明示判断"
  - "forcing function pattern: chat.py の _messages_to_response が closure で直接 import できないため、ソース文字列に 'user_upload' + 'file' 比較が含まれることを assert する `test_chat_py_contains_legacy_kind_normalization` を追加 (回帰防止)"
metrics:
  duration_minutes: 45
  completed_date: 2026-05-12
  tasks_completed: 3
  files_created: 0
  files_modified: 10
  commits: 7
---

# Phase 38 Plan 04: handler turn-delta bundle + attachments_helper kind 拡張 + API 正規化 Summary

worker / API / DB / frontend の persistence path を Phase 38 D-15 / D-18 / D-30 仕様に整合させた。Plan 02 で確立した outputs route と Plan 03 で確立した `_generated/` への永続化を、attachments_helper と langgraph_handler で結びつけ、turn 完了時に AIMessage に kind=generated 添付を bundle して AsyncPostgresSaver で透過保存する経路を完成させた。同時に API `_messages_to_response` で legacy `kind: 'file'` を `'user_upload'` に非破壊正規化し、attachments.py upload route も最新型で書くように更新して、frontend が `'user_upload' | 'generated'` の union 型のみを扱える状態にした (D-30 案 A 完遂)。

## Tasks Completed

| # | Task | Test commit | Impl commit | Files |
|---|------|-------------|-------------|-------|
| 1 | attachments_helper の scan_thread_attachments を `_generated/` + kind 対応に拡張し build_attachments_hint で kind ラベル表示する | `e760ba5` (RED) | `6aa9458` (GREEN) | app/jobs/handlers/attachments_helper.py, tests/test_langgraph_handler_attachments.py |
| 2 | langgraph_handler.py の turn 完了で AIMessage.additional_kwargs.attachments に kind=generated を bundle する | `08a7a47` (RED) | `c1b83bb` (GREEN) | app/jobs/handlers/langgraph_handler.py, tests/test_langgraph_handler_outputs_bundle.py |
| 3 | API _messages_to_response で legacy kind='file' を 'user_upload' に正規化し、attachments.py upload route の hardcoded 値も置換する | `b00259b` (RED) | `bfe9f78` (GREEN) | app/api/routes/chat.py, app/api/routes/attachments.py, tests/test_outputs_route.py, tests/test_chat_history_additional_kwargs_api.py, tests/test_attachments_upload_route.py |
| - | deferred-items.md に Plan 03 由来の test_mcp_server failure を記録 | — | `7902248` | .planning/phases/38-worker-dl/deferred-items.md |

## Key Decisions / Implementation

### Task 1: attachments_helper の二重ループ + kind ラベル (D-18)

既存の user_upload 直下 scan loop はそのまま、末尾の append dict に `"kind": "user_upload"` を追加。直後に `gen_folder = os.path.join(folder, "_generated")` を別途読む第二ループを置き、`kind: "generated"` を付与する。

サブフォルダは 1 段のみ降りる (Pitfall 4): `os.path.isfile` チェックでサブフォルダエントリを除外し、`os.walk` / `rglob` は使わない (`grep -cE "os.walk|rglob"` count 0)。Plan 02 で mcp_server/tools/attachments.py に同形の二重ループを入れた構造と完全に揃え、AI 側 (`attachments_list` MCP tool) と handler 側 (SystemMessage prepend) が同じファイル群を 2 経路で見ても unique source of structure を共有する。

`build_attachments_hint` は `kind_label = "[AI 生成]" if a.get("kind") == "generated" else "[添付]"` のシンプル分岐で `[AI 生成]` / `[添付]` ラベルを各行末に付与する。kind フィールド欠落の legacy entry は防御的に `[添付]` に縮退 (test_build_hint_legacy_entry_without_kind_defaults_to_attached_label が forcing function として gate)。後段の「内容を読むには `attachments_extract` ツール…」案内文は維持。

### Task 2: turn-delta bundle in LangGraphHandler (D-15)

`_handle_inner` 内、final_state 確定直後 (`if final_state is None: …` のあと) に Phase 38 D-15 bundle ブロックを挿入。Pattern 2 の核心は **handler レベルで再 scan して kind=generated だけ抽出** する設計 — tool wrapper 側の rename (Plan 03 で snapshot diff 採用済) とは独立し、二重カウントしない (Pitfall 5)。

```python
post_turn_meta = scan_thread_attachments(thread_id, github_login)
prev_generated_names = {
    a["name"]
    for a in (attachments_meta or [])
    if isinstance(a, dict) and a.get("kind") == "generated"
}
turn_generated = [
    m for m in post_turn_meta
    if m.get("kind") == "generated"
    and m["name"] not in prev_generated_names
]
if turn_generated:
    final_msg = final_state["messages"][-1]
    existing_kw = getattr(final_msg, "additional_kwargs", None) or {}
    final_msg.additional_kwargs = existing_kw | {"attachments": turn_generated}
```

- **delta 抽出**: turn 開始時の `attachments_meta` (state_input にも入れている) に既に含まれていた generated names を除外。frontend は kind=='generated' の entry が前 turn の bundle として既に restore されているケースを想定。
- **None-guard + dict union merge** (Pitfall 2): 既存 `additional_kwargs` の他 sidecar フィールドを潰さない。
- **AsyncPostgresSaver round-trip**: Plan 01 Wave 0 risk-gate (`test_round_trip_postgres`) で AIMessage 側の JSONB round-trip が green になっているため、本 plan の bundle は安全に永続化に乗る。

**scope 限定**: orchestrator_handler.py には bundle を入れない — Plan 06 deferred-items / 観察ベース判断 (PLAN.md Task 2 action 2)。FOUT-01/02 の主経路は Chat / Canvas であり、SuperChat (orchestrator) は v6.1+ で必要なら同じパターンで追加する。

### Task 3: API 層の D-30 正規化 + upload route 更新

`app/api/routes/chat.py::_messages_to_response` 内の `kw.get("attachments")` 処理を、**非破壊 (copy-before-edit)** な正規化に書き換え:

```python
normalized_atts = []
for a in atts:
    if isinstance(a, dict):
        a_copy = dict(a)
        if a_copy.get("kind") == "file":
            a_copy["kind"] = "user_upload"
        normalized_atts.append(a_copy)
    else:
        normalized_atts.append(a)
public_kw["attachments"] = normalized_atts
```

- 元 dict (`atts[*]`) は touch しない — LangGraph state を破壊しないことを `test_messages_to_response_logic_includes_attachments` の追加 assertion (`assert atts[0]["kind"] == "file"`) で gate。
- kind が `'user_upload'` / `'generated'` の場合は素通り。
- `_messages_to_response` は closure のため直接 import 不可。回帰防止のため `inspect.getsource(chat_module)` でソースを文字列マッチする `test_chat_py_contains_legacy_kind_normalization` を forcing function として追加。

`app/api/routes/attachments.py` の upload route L160 の `"kind": "file"` を `"kind": "user_upload"` に置換。新規 upload 行は最新型で永続化され、legacy 行は chat.py 経路で吸収される段階的移行が完成。

### Plan 02 で導入された claude_code 経路の E2E (FOUT-02)

`tests/test_outputs_route.py::test_get_output_works_for_claude_code` の skip を外して実装。`_generated/` 配下に markdown 出力ファイル相当 (`{ts}_result.md`) を配置し、outputs route が 200 + bytes 一致 + `text/*` MIME + `inline` content-disposition で返すことを assert。claude_code 起源と execute_python 起源は同じ `_generated/` cwd 設計 (Plan 03 で固定済) のため、本 test は **route 層で「claude_code 起源も execute_python 起源も同じ経路で取得できる」** という前提を 1 本の green で固定する。

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/test_langgraph_handler_attachments.py -v` | ✅ 11 passed (Phase 37 既存 5 件 + Phase 38 新規 6 件) |
| `PYTEST_DATABASE_URL=postgresql://postgres:postgres@172.18.0.3:5432/... uv run pytest tests/test_langgraph_handler_outputs_bundle.py -v` | ✅ 3 passed (round_trip_postgres + bundles_generated_files + handler_does_not_double_count) |
| `uv run pytest tests/test_outputs_route.py -v` | ✅ 4 passed (test_get_output_works_for_claude_code skip 外し含む) |
| `uv run pytest tests/test_chat_history_additional_kwargs_api.py -v` | ✅ 5 passed (D-30 正規化 + chat.py forcing function 含む) |
| `uv run pytest tests/test_attachments_upload_route.py -v` | ✅ 9 passed (kind='user_upload' 移行確認) |
| `uv run pytest tests/test_attachments_get_delete_route.py tests/test_chat_history_additional_kwargs.py -v` | ✅ 12 passed (回帰なし) |
| Full suite (`PYTEST_DATABASE_URL=… uv run pytest tests/ --ignore=tests/test_api_chat.py`) | 28 failed / 417 passed / 13 skipped — **fail 28 件は全て本 plan 由来ではない** (Plan 01/02 deferred-items 記載分 + Plan 03 claude_code signature 変更の test_mcp_server fallout) |
| Source: `grep -c '"kind": "user_upload"' app/jobs/handlers/attachments_helper.py` | ✅ 1 |
| Source: `grep -c '"kind": "generated"' app/jobs/handlers/attachments_helper.py` | ✅ 1 |
| Source: `grep "gen_folder = os.path.join(folder, \"_generated\")" app/jobs/handlers/attachments_helper.py` | ✅ hit |
| Source: `grep -cE '"\[AI 生成\]"\|"\[添付\]"' app/jobs/handlers/attachments_helper.py` | ✅ 1 (1 行に両ラベル) |
| Source: `grep -cE "os.walk\|rglob" app/jobs/handlers/attachments_helper.py` | ✅ 0 (再帰禁止) |
| Source: `grep -c "scan_thread_attachments" app/jobs/handlers/langgraph_handler.py` (>=2) | ✅ 3 (import + 既存 prepend + 新規 post-turn) |
| Source: `grep -cE "turn_generated\|post_turn_meta" app/jobs/handlers/langgraph_handler.py` | ✅ 5 |
| Source: `grep -cE "existing_kw \| \{\|additional_kwargs.*\|.*\{" app/jobs/handlers/langgraph_handler.py` | ✅ 1 (dict union merge) |
| Source: `grep -cE "_rename_new_outputs\|os.rename" app/jobs/handlers/langgraph_handler.py` | ✅ 0 (Pitfall 5: handler は rename しない) |
| Source: `grep -c '"kind": "user_upload"' app/api/routes/attachments.py` | ✅ 1 |
| Source: `grep -c '"kind": "file"' app/api/routes/attachments.py` | ✅ 0 (legacy 値が消えている) |
| Source: `grep -cE 'kind.*==.*"file"' app/api/routes/chat.py` | ✅ 1 (正規化分岐) |
| Source: `grep -c "user_upload" app/api/routes/chat.py` | ✅ 3 |

### Threat Mitigation Coverage

| Threat ID | Disposition | 実装による mitigation |
|-----------|-------------|----------------------|
| T-38-04-01 (Tampering: additional_kwargs merge で既存フィールドを潰す) | mitigate | `(existing_kw or {}) \| {...}` 形式の dict union で既存 sidecar を保持 — Pitfall 2 |
| T-38-04-02 (Spoofing: kind フィールドに任意値が入る) | mitigate | scan_thread_attachments が文字列リテラル `"user_upload"` / `"generated"` のみ append、Enum 混在ゼロ (Pitfall 6 遵守) |
| T-38-04-03 (Information Disclosure: turn-delta scan で他 user の `_generated/` が漏れる) | mitigate | scan_thread_attachments は `THREAD_FILES_DIR/<login>/<tid>/_generated` を構築、`github_login` が JWT 経由で worker に渡る (Phase 11-04 経路) |
| T-38-04-04 (Tampering: legacy 'file' 正規化漏れで frontend type error) | mitigate | chat.py _messages_to_response で `'file'` → `'user_upload'` 非破壊変換 + attachments.py upload route で新規行は `'user_upload'` 直書き |

## Deviations from Plan

### Auto-fixed Issues

**None for in-scope work.** 3 タスクすべて PLAN.md 記載通りに実装。chat.py の正規化 forcing function (`test_chat_py_contains_legacy_kind_normalization`) を追加した点は Plan acceptance criteria の `grep -E 'kind.*==.*"file"' app/api/routes/chat.py` ヒット要件に整合する形で実装側の確実な実装を担保する補強で、PLAN.md `<action>` の指示範囲内。

### Scope-Boundary Deferrals (Rule "Scope Boundary")

**1. [Scope] Plan 03 由来の test_mcp_server claude_code 関連 7 件 fail**

- **Found during:** 全体回帰確認 (`uv run pytest tests/ --ignore=tests/test_api_chat.py`)
- **Issue:** `TypeError: claude_code() got an unexpected keyword argument 'cwd'` (test_claude_code_env_sanitized など 7 件)
- **Verification it's pre-existing:** Plan 04 開始前 commit `cef2bd1` で `git checkout cef2bd1 -- tests/ app/ mcp_server/` 復元後に同一テスト fail 再現を確認
- **Action:** `.planning/phases/38-worker-dl/deferred-items.md` に記録 (commit `7902248`)
- **Why this is appropriate:** Plan 03 の意図的破壊変更 (claude_code から cwd 引数削除) の fallout で、本 plan の handler/API/helper の scope と無関係

### Authentication Gates

なし — 本 plan は handler / helper / API / 既存 helper 経由再利用のみで認可境界に触れない (outputs route の JWT 認証は Plan 02 helper 経由で確立済)。

## Files Created

なし。

## Files Modified

- `app/jobs/handlers/attachments_helper.py` — `_generated/` 二重目ループ + 各 entry の `kind` フィールド追加 + build_attachments_hint の `[AI 生成]` / `[添付]` ラベル表示
- `app/jobs/handlers/langgraph_handler.py` — final_state 確定直後の D-15 bundle ブロック挿入 (post_turn_meta scan + delta 抽出 + None-guard merge)
- `app/api/routes/chat.py` — `_messages_to_response` 内に legacy `'file'` → `'user_upload'` 非破壊正規化分岐を追加
- `app/api/routes/attachments.py` — upload route hardcoded `"kind": "file"` を `"kind": "user_upload"` に置換
- `tests/test_langgraph_handler_attachments.py` — Phase 37 既存 5 件は維持、Phase 38 用 6 件追加 (kind / `_generated/` / 再帰禁止 / hint ラベル)
- `tests/test_langgraph_handler_outputs_bundle.py` — Plan 01 で skip scaffold 済の `test_bundles_generated_files` + `test_handler_does_not_double_count` を実装
- `tests/test_outputs_route.py` — `test_get_output_works_for_claude_code` の skip を外して claude_code 経路 E2E を実装 (FOUT-02)
- `tests/test_chat_history_additional_kwargs_api.py` — legacy 正規化 inline ロジック更新 + `test_chat_py_contains_legacy_kind_normalization` 追加 (forcing function)
- `tests/test_attachments_upload_route.py` — `test_upload_single_text_file` の `kind == 'file'` assertion を `kind == 'user_upload'` に更新 (D-30 移行)
- `.planning/phases/38-worker-dl/deferred-items.md` — Plan 03 由来の test_mcp_server fallout を追記

## Known Stubs

なし — 本 plan で導入したコードはすべて実体を持つ (helper は実 directory scan、handler は実 attribute mutation、API は実 normalization、テストは実 assertion)。

## Threat Flags

なし — 本 plan で追加された新規 surface (handler bundle / API normalization / kind ラベル文字列) は、threat model の T-38-04-01..04 にすべて記載済で、None-guard + dict union + 文字列リテラル + helper 再利用で mitigation 完了。

## Self-Check: PASSED

- ✅ `app/jobs/handlers/attachments_helper.py` modified with `_generated/` loop + kind
- ✅ `app/jobs/handlers/langgraph_handler.py` modified with turn_generated bundle block
- ✅ `app/api/routes/chat.py` modified with legacy kind normalization
- ✅ `app/api/routes/attachments.py` modified with kind='user_upload' for new uploads
- ✅ Commit `e760ba5` (RED Task 1) exists in git log
- ✅ Commit `6aa9458` (GREEN Task 1) exists in git log
- ✅ Commit `08a7a47` (RED Task 2) exists in git log
- ✅ Commit `c1b83bb` (GREEN Task 2) exists in git log
- ✅ Commit `b00259b` (RED Task 3) exists in git log
- ✅ Commit `bfe9f78` (GREEN Task 3) exists in git log
- ✅ Commit `7902248` (deferred-items 更新) exists in git log
- ✅ Plan target tests: 11 + 3 + 4 + 5 + 9 = 32 passed, 0 failed (本 plan 由来)
- ✅ All Plan acceptance criteria source assertions verified
