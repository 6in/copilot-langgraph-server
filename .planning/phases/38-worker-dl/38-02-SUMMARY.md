---
phase: 38
plan: 2
plan_id: 38-02-backend-route-and-mcp-list
subsystem: api-route + mcp-tool + yaml-ssot
tags: [outputs-route, mcp-attachments, kind-discriminator, _generated, ssot-regeneration]
requirements: [FOUT-01, FOUT-02, FOUT-04]
dependency_graph:
  requires:
    - "Plan 38-01: AttachmentMeta.kind を 'user_upload' | 'generated' に enum 化 (frontend 型契約)"
    - "Plan 38-01: tests/test_outputs_route.py + tests/test_mcp_attachments_kind.py の skip scaffold"
    - "Phase 36: app/api/routes/attachments.py の _resolve_thread_folder / _safe_resolve_file / _normalize_basename helper"
    - "Phase 37: mcp_server/tools/attachments.py::attachments_list_core (kind フィールド未対応の旧 shape)"
    - "Phase 30 / ADR-0044: config/mcp_tools.yaml SSoT + scripts/generate_mcp_artifacts.py"
  provides:
    - "GET /api/threads/{tid}/outputs/{name} (_generated/ 配下を JWT 認証下で inline 配信)"
    - "attachments_list_core が kind フィールド + `_generated/` scan を含む flat list を返す (D-06)"
    - "config/mcp_tools.yaml SSoT に kind フィールド宣言 + 自動生成 3 ファイル決定論的再生成 (drift ゼロ)"
  affects:
    - "Plan 38-03: post-process rename / execute_python cwd 切替 / claude_code cwd 引数削除は本 plan の _generated/ scan 経路を消費"
    - "Plan 38-04: AIMessage.additional_kwargs.attachments bundle / handler scan は本 plan の kind 統合戻り値を消費"
    - "Plan 38-05: AttachmentChipRow / AttachmentModal の AI 生成チップは本 plan の outputs route を介して raw bytes を取得"
tech_stack:
  added: []
  patterns:
    - "Phase 36 helper の import 再利用による new-route 実装ゼロ追加 (新規 isolation/path-traversal/auth ロジックを書かない、D-19)"
    - "`_generated/` サブフォルダ 1 段限定 scan + kind discriminator 付与 (再帰禁止、Pitfall 4)"
    - "YAML SSoT 単一編集 → `scripts/generate_mcp_artifacts.py --target all` で 3 ファイル決定論的再生成 (ADR-0044)"
    - "TDD RED → GREEN: 既存 scaffold の skip マーカー除去で RED 確認、実装で GREEN 化"
key_files:
  created:
    - app/api/routes/outputs.py
  modified:
    - app/api/main.py
    - mcp_server/tools/attachments.py
    - config/mcp_tools.yaml
    - mcp_server/tools/mcp_helper.py
    - static/js/tool-catalog-generated.js
    - docs/mcp-tools.md
    - tests/test_outputs_route.py
    - tests/test_mcp_attachments_kind.py
    - .planning/phases/38-worker-dl/deferred-items.md
decisions:
  - "D-05 確定: outputs.py は attachments.py の helper 3 つを import 再利用するだけで isolation/path-traversal/auth は Phase 36 から自動継承 (新規 helper 不在)"
  - "D-06 確定: attachments_list_core 拡張で kind: 'user_upload' | 'generated' を single discriminator に。新規 outputs_list ツールを作らない (Phase 30 ツール数膨張ゼロ)"
  - "Pitfall 10 対策: outputs.py 内で thread_folder を直接 _safe_resolve_file に渡さず、os.path.join(thread_folder, '_generated') を渡すことで realpath prefix guard を `_generated/` 配下に絞り込む"
  - "Pitfall 4 対策: _generated/ サブフォルダ scan は 1 段のみ降りる (os.walk / rglob 不使用、`__pycache__/*.pyc` 等の中間ファイル漏出回避)"
  - "後方互換性: attachments_list 戻り値への kind フィールド追加は dict キー追加だけで既存テスト test_attachments_list.py 2 件 green 維持"
metrics:
  duration_minutes: 35
  completed_date: 2026-05-12
  tasks_completed: 3
  files_created: 1
  files_modified: 8
  commits: 5
---

# Phase 38 Plan 02: Backend route + MCP attachments_list 拡張 + YAML SSoT 更新 Summary

worker / MCP tool が `_generated/` サブフォルダに書き出した出力ファイルを、JWT cookie 認証配下で raw bytes を inline 配信する新規 endpoint (`GET /api/threads/{tid}/outputs/{name}`) を実装し、MCP `attachments_list` を `_generated/` 配下 + `kind: "user_upload" | "generated"` discriminator 対応に拡張、`config/mcp_tools.yaml` SSoT 更新と自動生成 3 ファイル決定論的再生成を完遂した。

## Tasks Completed

| # | Task | Commits | Files |
|---|------|---------|-------|
| 1 | `app/api/routes/outputs.py` を新規作成し `main.py` に include | `13bc4a6` (RED), `effe8c4` (GREEN) | app/api/routes/outputs.py (new), app/api/main.py, tests/test_outputs_route.py |
| 2 | `mcp_server/tools/attachments.py::attachments_list_core` を `_generated/` + `kind` 対応に拡張 | `95c3ebd` (RED), `1c0d981` (GREEN) | mcp_server/tools/attachments.py, tests/test_mcp_attachments_kind.py |
| 3 | `config/mcp_tools.yaml` docstring を更新し `scripts/generate_mcp_artifacts.py --target all` を実行 | `0636aff` | config/mcp_tools.yaml, mcp_server/tools/mcp_helper.py, static/js/tool-catalog-generated.js, docs/mcp-tools.md, .planning/phases/38-worker-dl/deferred-items.md |

## Key Decisions / Implementation

### Task 1: outputs.py 設計 — helper 再利用による D-19 自動継承

attachments.py の 3 helper (`_resolve_thread_folder` / `_safe_resolve_file` / `_normalize_basename`) を **import 再利用** することで、Phase 36 で確立済みの multi-user isolation / realpath prefix guard / NFC basename サニタイズを Phase 38 outputs route にも **新規実装ゼロで継承**。Pitfall 10 対策として thread_folder を直接渡さず `os.path.join(thread_folder, "_generated")` を `_safe_resolve_file` に渡すことで、realpath prefix guard が `_generated/` 配下に絞り込まれ、親 thread フォルダ直下の user upload 領域 (Phase 36) との混同を物理的に防ぐ。

```python
github_login = payload.get("github_login", "unknown")
thread_folder = _resolve_thread_folder(github_login, thread_id)  # API 側引数順
gen_folder = os.path.join(thread_folder, "_generated")
safe_path = _safe_resolve_file(gen_folder, name)  # ← Pitfall 10: gen_folder を渡す
```

### Task 2: attachments_list_core の二重ループ拡張 — single discriminator 通底

既存ループ末尾の dict append に `"kind": "user_upload"` を追加、return out 前に同形の二重目ループを `kind="generated"` で追加。サブフォルダは 1 段のみ降りる (Pitfall 4 — `os.walk` / `rglob` 不使用、`__pycache__/*.pyc` 等の中間ファイル漏出回避)。両ループとも `os.path.islink` で symlink 除外 (LOW-04)。

D-06 の `kind: "user_upload" | "generated"` single discriminator が MCP 戻り値・AttachmentChip props (Plan 01 で確定済)・AgentState・SystemMessage prepend (Plan 04 担当) を **同じ enum で貫く** 設計の根幹。

### Task 3: YAML SSoT 更新 + 自動生成 3 ファイル決定論的再生成

`config/mcp_tools.yaml` の `attachments_list` ブロックで `description` を「現在の thread に添付されたファイル + AI 生成ファイルの一覧を返す」に更新、`python_wrapper.docstring` の Returns 例に `kind: "user_upload" | "generated"` フィールドを追記、Example loop を `print(f["name"], f["kind"], f["size"])` に更新。`python3 scripts/generate_mcp_artifacts.py --target all` で 3 自動生成ファイル (`mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md`) を再生成し、`--check` 実行で drift ゼロを確認。他ブロック (claude_code / db_query / web_search 等) には変更なし (deterministic 再生成)。pre-commit hook が drift 検査を通過。

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/test_outputs_route.py -x -v` | 3 passed, 1 skipped (Plan 04 担当の `test_get_output_works_for_claude_code` のみ skip) |
| `uv run pytest tests/test_mcp_attachments_kind.py::test_returns_both_kinds -x -v` | 1 passed |
| `uv run pytest tests/test_attachments_list.py -x -v` | 2 passed (既存テストを kind フィールド追加で壊さないこと確認) |
| `python3 scripts/generate_mcp_artifacts.py --check` | exit 0 (drift ゼロ) |
| `grep -c "async def get_output" app/api/routes/outputs.py` | 1 |
| `grep "from app.api.routes.attachments import" app/api/routes/outputs.py` | hit (helper 再利用) |
| `grep "_generated" app/api/routes/outputs.py` | hit (gen_folder 連結) |
| `grep -c "include_router(outputs.router)" app/api/main.py` | 1 |
| `grep -cE "^def _resolve_thread_folder\|^def _safe_resolve_file" app/api/routes/outputs.py` | 0 (新規 helper 不在) |
| `grep -c '"kind": "user_upload"' mcp_server/tools/attachments.py` | 2 (実コード 1 + docstring 1) |
| `grep -c '"kind": "generated"' mcp_server/tools/attachments.py` | 1 |
| `grep -c "os.path.islink" mcp_server/tools/attachments.py` | 2 (両ループ symlink 除外) |
| `grep -cE "os.walk\|rglob" mcp_server/tools/attachments.py` | 0 (再帰 scan 不在) |
| `grep -c "DO NOT EDIT" mcp_server/tools/mcp_helper.py static/js/tool-catalog-generated.js docs/mcp-tools.md` | 全 3 ファイルに 1 つずつ存在 |

### Threat Model 自動継承確認 (D-19 / threat_model)

| Threat ID | Mitigation | 確認方法 |
|-----------|-----------|---------|
| T-38-02-01 (URL 注入 path traversal) | `_safe_resolve_file(gen_folder, name)` の realpath prefix guard | `test_path_traversal_rejected` green |
| T-38-02-02 (別 user の _generated/ 直接アクセス) | `_resolve_thread_folder(github_login, thread_id)` 経路 (Phase 36 helper) | `test_isolation_other_user_blocked` green |
| T-38-02-03 (MCP attachments_list で他 user 漏出) | RPCContext (x-thread-id / x-github-login) → helper 経由 | core 関数が realpath guard で `_resolve_thread_folder` を経由 (実装確認済) |
| T-38-02-04 (自動生成ファイル手書き drift) | pre-commit hook `generate_mcp_artifacts.py --check` | Task 3 で drift ゼロ確認 |
| T-38-02-05 (symlink 経由でフォルダ外脱出) | `os.path.islink` 除外 (両ループ) | 実装で 2 箇所、grep 確認済 |

## Deviations from Plan

### Auto-fixed Issues

**None for in-scope work.** All 3 tasks completed exactly as written.

### Scope-Boundary Deferrals (Rule "Scope Boundary")

**1. [Scope] pre-existing pytest failure `test_load_tools_has_six_tools`**
- **Found during:** Task 3 acceptance check (`uv run pytest tests/test_generate_mcp_artifacts.py -x`)
- **Issue:** `assert len(tools) == 6` だが Phase 37 で 2 tools 追加されて 8 になっている。`tests/test_generate_mcp_artifacts.py:40` の hardcoded 値が更新されていない (Phase 37 のテスト管理外データ)。
- **Verification it's pre-existing:** base ブランチ `0422b3b` で `git stash` → 同コマンドで同じ AssertionError を再現確認。
- **Action:** `.planning/phases/38-worker-dl/deferred-items.md` に追記、本 plan の verify ロジックは「本 plan 由来エラーゼロ」を達成基準とする。
- **Why this is appropriate:** 本 plan は tools 数を変更しない (8 のまま) ため Phase 38 の責務外。1 行修正 (`6 → 8`) だが Phase 37 の取りこぼし。

### Authentication Gates

なし — 本 plan は backend 単体テスト + YAML SSoT + 自動生成のみで auth 境界を新規に踏まない (Phase 36 JWT cookie 認証経路を helper 経由で継承)。

## Files Created

- `app/api/routes/outputs.py` — Phase 38 D-05 GET /api/threads/{tid}/outputs/{name} route (44 行、helper 再利用設計)

## Files Modified

- `app/api/main.py` — routes import に `outputs` 追加 + `attachments.router` 直後で `include_router(outputs.router)` 追加
- `mcp_server/tools/attachments.py` — `attachments_list_core` に `kind` フィールド付与 + `_generated/` サブフォルダ 1 段 scan の二重目ループを追加
- `config/mcp_tools.yaml` — `attachments_list` ブロックの `description` 更新 + `python_wrapper.docstring` に `kind` フィールド説明追記
- `mcp_server/tools/mcp_helper.py` — 自動再生成 (DO NOT EDIT)
- `static/js/tool-catalog-generated.js` — 自動再生成 (DO NOT EDIT)
- `docs/mcp-tools.md` — 自動再生成 (DO NOT EDIT)
- `tests/test_outputs_route.py` — Plan 01 scaffold の 3 ケース (`test_get_output_returns_raw_bytes` / `test_path_traversal_rejected` / `test_isolation_other_user_blocked`) の skip マーカーを外して assertion 実装、`test_get_output_works_for_claude_code` は Plan 04 担当のため skip 維持
- `tests/test_mcp_attachments_kind.py` — Plan 01 scaffold の `test_returns_both_kinds` の skip マーカーを外して assertion 実装
- `.planning/phases/38-worker-dl/deferred-items.md` — pre-existing pytest failure (`test_load_tools_has_six_tools` の hardcoded == 6) を追記

## Known Stubs

なし — 本 plan で導入したコードはすべて実体を持つ (route は実 file 配信、attachments_list は実 directory scan、YAML は実 docstring)。

## Threat Flags

なし — 本 plan で追加された新規セキュリティ surface (outputs route) は、threat model の T-38-02-01..05 にすべて記載済で、Phase 36 helper の import 再利用 + realpath prefix guard + symlink 除外で mitigation 完了。

## Self-Check: PASSED

- ✅ `app/api/routes/outputs.py` exists
- ✅ Commit `13bc4a6` (RED Task 1) exists in git log
- ✅ Commit `effe8c4` (GREEN Task 1) exists in git log
- ✅ Commit `95c3ebd` (RED Task 2) exists in git log
- ✅ Commit `1c0d981` (GREEN Task 2) exists in git log
- ✅ Commit `0636aff` (Task 3 + deferred-items 追記) exists in git log
- ✅ `python3 scripts/generate_mcp_artifacts.py --check` exit 0
- ✅ Plan target tests 6 passed, 1 skipped (Plan 04 担当)
