---
phase: 38-worker-dl
verified: 2026-05-12T12:00:00Z
status: human_needed
score: 5/5 must-haves verified (automated); 7 visual/E2E items require human verification
overrides_applied: 0
human_verification:
  - test: "FOUT-03 のチャット画面プレビュー (画像/Markdown/CSV/text の各 renderer dispatch 実機動作)"
    expected: "AttachmentModal で kind 別 renderer (image=<img>, markdown=react-markdown, csv=ag-grid, text=Monaco) が破綻なく描画され、PDF/unsupported はフォールバック案内 + DL CTA を出す"
    why_human: "DOM rendering と視覚体感の確認は実機 browser 必須 (UI-SPEC Checker #11-13, #20)。コードの存在 + classify dispatch 経路は automated に確認済だが、実際の renderer 動作は browser からしか観測できない"
  - test: "Dark mode (`[data-theme=\"dark\"]`) で Modal / 4 renderer が破綻なく表示"
    expected: "ダーク/ライト切替で Modal overlay / 4 renderer 全てがコントラスト破綻なく表示される"
    why_human: "視覚的コントラスト判定は人間判断 (UI-SPEC Checker #16)"
  - test: "Mobile 375px viewport で Modal が full-screen 化、CTA が full-width block 化"
    expected: "DevTools viewport を 375×667 にすると Modal が full-screen に展開、ダウンロード CTA が full-width 化"
    why_human: "responsive 視覚判定は実機 browser 必須 (UI-SPEC Checker #17)"
  - test: "Multi-user isolation の curl 直接叩き (User B JWT で User A の outputs を取得)"
    expected: "401 or 404 が返り、AttachmentModal を別 user session で開くとエラーバナー 「このファイルにはアクセスできません」表示"
    why_human: "FOUT-04 sc5 — 2 つの GitHub アカウント実機 JWT 取得 + curl 検証 + Modal エラーバナー視覚確認 (UI-SPEC Checker #18)。コード上は Phase 36 helper の import 再利用で防御済だが、E2E 実機 isolation は人間判断"
  - test: "Size cap UX (>1MB text / >10MB image で size cap 案内 + DL CTA)"
    expected: "閾値超過時に accent-subtle banner + DL CTA が表示され destructive 色が使われない"
    why_human: "視覚的色合い + 文言確認 (UI-SPEC Checker #19)"
  - test: "PDF / unsupported 形式のフォールバック (UI-SPEC Checker #20)"
    expected: "PDF を Modal で開くと 「Download only」案内 + DL CTA を表示しプレビューは実行されない"
    why_human: "実際の PDF 生成 → Modal 表示 → フォールバック描画は実機 browser 必須"
  - test: "Accent reserved-for / destructive 色限定 (UI-SPEC Checker #7, #8)"
    expected: "AttachmentChipRow / AttachmentModal で --color-accent の使用箇所が UI-SPEC L173-192 の用途内に収まり、destructive はエラーバナーのみで使われる"
    why_human: "デザインシステム遵守は CSS 用途観察が必要 (人間判断)"
deferred:
  - truth: "Orchestrator (SuperChat) 経由の AI 生成ファイル bundle 対応"
    addressed_in: "v6.1+ (deferred-items.md 統合済)"
    evidence: "Plan 38-04 SUMMARY scope 限定の明示判断 / 36 deferred-items.md 'orchestrator_handler bundle 対応' 行 / 38-CONTEXT.md `<deferred>` 経由"
  - truth: "横断 'My Files' 画面 / 一覧 endpoint / 個別削除 UI"
    addressed_in: "v6.1+ (D-02 / D-16 / D-17 否定的決定として deferred-items.md に保存)"
    evidence: "38-CONTEXT.md D-02 / D-16 / D-17 + deferred-items.md (Phase 36) Phase 38 完了報告 + v6.1+ 持ち越し"
---

# Phase 38: ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持 Verification Report

**Phase Goal:** execute_python / claude_code が生成したファイルをユーザーがチャット UI から DL・プレビュー・再取得できる、ユーザー別ストレージを備えた成果物管理基盤
**Verified:** 2026-05-12T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | execute_python sandbox で生成された PDF / 画像 / CSV 等をユーザーがチャット UI からダウンロードできる | ✓ VERIFIED (automated) | `app/api/routes/outputs.py` の GET /api/threads/{tid}/outputs/{name} 実装 (L37-66、FileResponse + inline Content-Disposition) + `mcp_server/tools/execute_python.py:241` (`cwd = _resolve_generated_folder(headers)`) + post-process snapshot-diff rename (`_rename_new_outputs` L101)。`app/api/main.py:387` で `include_router(outputs.router)` 配線済。実機 DL は #1 human-verify |
| 2 | claude_code 実行 workspace の成果物 (生成された .md / .py / 画像等) もユーザーが同じ UI から取得できる | ✓ VERIFIED (automated) | `mcp_server/tools/claude_code.py:55` 新シグネチャ `(prompt, headers=None)` から cwd 引数削除、L85-95 で execute_python の `_resolve_generated_folder` を import 再利用、L170-184 `claude_code_with_headers` wrapper が post-process rename。outputs route は execute_python と同じ `_generated/` を読むため経路統合済。`tests/test_outputs_route.py::test_get_output_works_for_claude_code` green (38-VALIDATION.md 38-04-02 ✅) |
| 3 | 画像 / CSV / Markdown 等の生成ファイルは DL せずチャット画面上でプレビューできる | ⚠ PARTIAL (code present, visual unverified) | `AttachmentModal.tsx` L25-66 (IMAGE_CAP_BYTES / TEXT_CAP_BYTES / classify / buildFileUrl) + L174 kind ラベル + L333-355 switch dispatch (image/markdown/csv/text/unsupported)、各 preview file 存在 (ImagePreview 25行 / MarkdownPreview 122行 / CsvPreview 247行 / TextPreview 161行)。classify と dispatch 経路は automated 検証済だが、実機 DOM 描画は #1 human-verify |
| 4 | 生成ファイルがユーザー別ストレージに保持され、過去スレッドや一覧画面から再取得できる | ✓ VERIFIED (automated) | `app/jobs/handlers/langgraph_handler.py:248-266` で turn 完了時に `scan_thread_attachments` 再 scan → `prev_generated_names` との diff → `final_msg.additional_kwargs = existing_kw \| {"attachments": turn_generated}` で AIMessage に bundle。AsyncPostgresSaver round-trip は Plan 01 の `test_round_trip_postgres` で green (38-VALIDATION.md 38-01-01 / 38-04-03 ✅)。frontend は `MessageArea.tsx:513` で `msg.additional_kwargs?.attachments` を描画 |
| 5 | ユーザー A のファイルにユーザー B が API 直接叩きでもアクセスできない (multi-user isolation) | ⚠ PARTIAL (code present, E2E unverified) | `outputs.py:25-29` で attachments.py の `_resolve_thread_folder` / `_safe_resolve_file` / `_normalize_basename` を import 再利用 → Phase 36 で確立した isolation を間接継承 (D-19)。Pitfall 10 対策で `os.path.join(thread_folder, "_generated")` を `_safe_resolve_file` に渡す (outputs.py:57)。`tests/test_outputs_route.py::test_isolation_other_user_blocked` + `test_path_traversal_rejected` green (38-VALIDATION.md 38-01-02 / 38-01-03 ✅)。実機 curl は #4 human-verify |

**Score:** 5/5 truths code-level verified (automated tests / source assertions); 3 truths require human E2E validation for full sign-off (#1, #4, #5 are partial-verified at automated level only)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `app/api/routes/outputs.py` | GET /api/threads/{tid}/outputs/{name} route, helper import 再利用 | ✓ VERIFIED | 66 行、`get_output` 実装、`_resolve_thread_folder` / `_safe_resolve_file` / `_normalize_basename` を attachments.py から import (L25-29)、新規 helper ゼロ |
| `app/api/main.py` | outputs.router include | ✓ VERIFIED | L387 `app.include_router(outputs.router)` |
| `mcp_server/tools/execute_python.py` | _resolve_generated_folder / _rename_new_outputs / _is_already_prefixed + cwd 切替 + wrapper post-process | ✓ VERIFIED | 319 行、3 helper 全て実装 (L65/86/101)、subprocess L241 `cwd = _resolve_generated_folder(headers)`、wrapper L308-314 で snapshot diff |
| `mcp_server/tools/claude_code.py` | headers 引数追加 + cwd 削除 + execute_python helper 再利用 | ✓ VERIFIED | 184 行、新シグネチャ L55 `(prompt, headers=None)`、L85 で `_resolve_generated_folder` import、L170-184 claude_code_with_headers wrapper、overflow output (`_save_overflow_output` / `OUTPUT_DIR`) は維持 (D-09) |
| `mcp_server/tools/attachments.py` | attachments_list_core が kind + `_generated/` 含む flat list を返す | ✓ VERIFIED | 306 行、L170 `"kind": "user_upload"` + L192 `"kind": "generated"` 両方付与、L175 `gen_folder = os.path.join(folder, "_generated")` 第二ループ、L157/L179 `os.path.islink` で symlink 除外、`os.walk` / `rglob` 不在 (確認済) |
| `config/mcp_tools.yaml` | attachments_list docstring に kind フィールド明記 | ✓ VERIFIED | Plan 02 SUMMARY 記載 + `python3 scripts/generate_mcp_artifacts.py --check` exit 0 確認済 (本検証で再確認 ✓) |
| `mcp_server/tools/mcp_helper.py` | YAML SSoT から自動再生成 (DO NOT EDIT) | ✓ VERIFIED | drift check exit 0 |
| `static/js/tool-catalog-generated.js` | YAML SSoT から自動再生成 (DO NOT EDIT) | ✓ VERIFIED | drift check exit 0 |
| `docs/mcp-tools.md` | YAML SSoT から自動再生成 (DO NOT EDIT) | ✓ VERIFIED | drift check exit 0 |
| `app/jobs/handlers/attachments_helper.py` | scan_thread_attachments が `_generated/` + kind 対応、build_attachments_hint が kind ラベル | ✓ VERIFIED | 107 行、L56 `"kind": "user_upload"` + L81 `"kind": "generated"`、L60 `gen_folder = os.path.join(folder, "_generated")`、L99 `kind_label = "[AI 生成]" if a.get("kind") == "generated" else "[添付]"` |
| `app/jobs/handlers/langgraph_handler.py` | turn 完了時に AIMessage.additional_kwargs.attachments に bundle | ✓ VERIFIED | 314 行、L248-266 で post_turn_meta scan + prev_generated_names diff + dict union merge `existing_kw \| {"attachments": turn_generated}`。`_rename_new_outputs` 呼び出し無し (Pitfall 5 — handler は rename しない) |
| `app/api/routes/chat.py` | _messages_to_response で legacy 'file' → 'user_upload' 正規化 | ✓ VERIFIED | L488-496 で非破壊コピー (`a_copy = dict(a)`) → `if a_copy.get("kind") == "file": a_copy["kind"] = "user_upload"` |
| `app/api/routes/attachments.py` | upload route の kind 値が 'user_upload' に統一 | ✓ VERIFIED | L160-162 `"kind": "user_upload"` 直書き、L0 grep で `"kind": "file"` 検出ゼロ |
| `frontend/src/types.ts` | AttachmentMeta.kind が 'user_upload' \| 'generated' literal union | ✓ VERIFIED | L70 `kind: 'user_upload' \| 'generated';` (D-30 案 A) |
| `frontend/src/hooks/useAttachments.ts` | staging item で kind: 'user_upload' を埋め込み | ✓ VERIFIED | Plan 01 SUMMARY 記載 (`grep -c "kind: 'user_upload'"` count >= 1) |
| `frontend/src/components/AttachmentModal.tsx` | 4 種 renderer dispatch + portal dialog + focus trap + size cap | ✓ VERIFIED | 506 行、L42 buildFileUrl (kind === 'generated' ? 'outputs' : 'attachments')、L53 classify、L180 role="dialog" + L181 aria-modal、L25-26 size cap、L126-148 Tab focus trap、L333-355 switch case 'image'/'markdown'/'csv'/'text' + default unsupported |
| `frontend/src/components/preview/ImagePreview.tsx` | raw bytes 直配信 | ✓ VERIFIED | 25 行、`<img src={url}>` で raw bytes 直接表示、size cap は Modal 側で gate |
| `frontend/src/components/preview/MarkdownPreview.tsx` | react-markdown 直呼び (MarkdownMessage を呼ばない) | ✓ VERIFIED | 122 行、Plan 05 SUMMARY で `grep -c "MarkdownMessage"` 0 件確認済 |
| `frontend/src/components/preview/CsvPreview.tsx` | 簡易 CSV パース + ChatAgGridTable 流用 + 1000 行 cap | ✓ VERIFIED | 247 行、Plan 05 SUMMARY で `grep -c "ChatAgGridTable"` count 4 確認済 |
| `frontend/src/components/preview/TextPreview.tsx` | Monaco read-only Editor + LANG_ALIASES + 1MB cap | ✓ VERIFIED | 161 行、Plan 05 SUMMARY で `grep -c "readOnly: true"` count 1 確認済 |
| `frontend/src/components/MessageArea.tsx` | AttachmentChipRow に kind 別 micro-badge + button 化 + AttachmentModal mount | ✓ VERIFIED | 659 行、L22 AttachmentModal import、L66 micro-badge コメント、L104 `badgeText = isGenerated ? '✨ AI 生成' : '📎 添付'`、L116/174 aria-haspopup="dialog"、L339 activeAttachment state、L649 conditional Modal mount |
| `docs/adr/0052-worker-generated-outputs-storage-and-preview.md` | Phase 38 D-01..D-19 + D-30 設計サマリ ADR | ✓ VERIFIED | Status: Accepted、Date 2026-05-12、Related ADRs 9件 (0048/0050/0044/0038/0023/0014/0046/0049/0051)、Phase 38 言及 14 件、FOUT-01..04 全て言及 |
| `docs/adr/INDEX.md` | 0052 エントリ追加 (auto-generated) | ✓ VERIFIED | `grep -c "0052"` count >= 1 |
| `.planning/adr-categories.yaml` | 0052 のカテゴリマッピング | ✓ VERIFIED | `"0052": { primary: "Data・Persistence", secondary: "Frontend・UI" }` |
| `.planning/patterns.md` | Phase 38 由来 4 エントリ手動追記 | ✓ VERIFIED | `grep -c "0052"` count 4 (4 エントリすべてに ADR-0052 リンク)、`grep -c "^### "` count 51 (47 既存 + 4 新規) |
| `.planning/phases/38-worker-dl/38-VALIDATION.md` | nyquist_compliant: true でクローズ | ✓ VERIFIED | frontmatter `status: complete` / `nyquist_compliant: true` / `wave_0_complete: true` / `closed: 2026-05-12` / Approval: approved (2026-05-12) |
| `.planning/phases/36-text-code-image-multimodal/deferred-items.md` | Phase 38 完了報告 + v6.1+ 持ち越し 15 項目統合 | ✓ VERIFIED | `grep -c "Phase 38 完了報告"` count 1、`grep -c "v6.1+"` count 10 |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `frontend/src/types.ts AttachmentMeta` | `frontend/src/hooks/useAttachments.ts` + `MessageArea.tsx` | kind フィールド 'user_upload' literal | ✓ WIRED | types.ts L70 で literal union、useAttachments / MessageArea が consume |
| `app/api/routes/outputs.py` | `app/api/routes/attachments.py` の `_resolve_thread_folder` / `_safe_resolve_file` / `_normalize_basename` | import で再利用 | ✓ WIRED | outputs.py L25-29 import (`from app.api.routes.attachments import _normalize_basename, _resolve_thread_folder, _safe_resolve_file`) |
| `app/api/main.py` | `outputs.router` | include_router | ✓ WIRED | main.py L387 `app.include_router(outputs.router)` |
| `mcp_server/tools/attachments.py attachments_list_core` | `{folder}/_generated/` listdir | os.path.join + listdir + kind 付与 | ✓ WIRED | L175 `gen_folder = os.path.join(folder, "_generated")` + L179 `os.path.islink` 除外 + L192 kind=generated |
| `config/mcp_tools.yaml` | auto-generated 3 files | `scripts/generate_mcp_artifacts.py --target all` | ✓ WIRED | `--check` exit 0 (本検証で再確認) |
| `mcp_server/tools/execute_python.py asyncio.create_subprocess_exec` | `_resolve_generated_folder(headers)` | `cwd=cwd` 渡し | ✓ WIRED | L241 `cwd = _resolve_generated_folder(headers)` → L248 `cwd=cwd` |
| `mcp_server/tools/claude_code.py` | `mcp_server/tools/execute_python._resolve_generated_folder` + `_rename_new_outputs` | import で DRY 再利用 | ✓ WIRED | L85, L165 で import |
| `register_tools wrapper` | snapshot diff (before/after listdir) | wrapper 内で before snapshot + 後に `_rename_new_outputs(folder, before)` | ✓ WIRED | execute_python.py L308-314 + claude_code.py L172-179 |
| `app/jobs/handlers/langgraph_handler.py L240+ final_state` | `scan_thread_attachments(thread_id, github_login)` | 再呼び出し → delta 抽出 → AIMessage merge | ✓ WIRED | L248-266 (post_turn_meta + prev_generated_names + turn_generated + dict union merge) |
| `app/api/routes/chat.py _messages_to_response` | legacy 'file' → 'user_upload' 正規化 | API 出力時に置換 | ✓ WIRED | L488-496 非破壊正規化 |
| `app/jobs/handlers/attachments_helper.py scan_thread_attachments` | `{folder}/_generated/` 配下 | 第二ループで kind=generated 付与 | ✓ WIRED | L60-83 第二ループ、kind=generated、再帰禁止 |
| `MessageArea.tsx` | `AttachmentModal` mount | activeAttachment state + AttachmentChipRow.onOpenModal | ✓ WIRED | L339 state、L445/L517 onOpenModal={setActiveAttachment}、L649-655 conditional mount |
| `MessageArea.tsx AttachmentChipRow` | button + AttachmentModal | onClick={() => onOpenModal(a)} + aria-haspopup="dialog" | ✓ WIRED | L115/L173 button onClick + aria-haspopup |
| `AttachmentModal classify(ext)` | ImagePreview / MarkdownPreview / CsvPreview / TextPreview | lazy import + Suspense + switch dispatch | ✓ WIRED | L333-355 switch case 全 4 種 + unsupported default |
| `buildFileUrl(threadId, name, kind)` | /outputs/ vs /attachments/ | `kind === 'generated' ? 'outputs' : 'attachments'` | ✓ WIRED | AttachmentModal.tsx L47 |
| `frontend/src/components/MessageArea.tsx:513` | `msg.additional_kwargs?.attachments` | conditional render | ✓ WIRED | AIMessage に bundle された attachments を AttachmentChipRow に渡す |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `AttachmentModal.tsx` | `text` (preview content) | `fetch(buildFileUrl(threadId, name, kind))` → 実 outputs/attachments route | Yes — `_generated/` の実ファイル bytes が FileResponse で返る | ✓ FLOWING |
| `MessageArea.tsx AttachmentChipRow` | `attachments` prop | `msg.additional_kwargs?.attachments` (LangGraph state 復元) | Yes — langgraph_handler が turn-delta bundle した generated エントリが復元される | ✓ FLOWING |
| `outputs.py FileResponse` | `safe_path` | `_safe_resolve_file(os.path.join(thread_folder, "_generated"), name)` | Yes — sandbox subprocess が直接書いた `_generated/{ts}_{name}` を返す | ✓ FLOWING |
| `langgraph_handler turn_generated` | `post_turn_meta` | `scan_thread_attachments(thread_id, github_login)` の戻り値 | Yes — `_generated/` の実 listdir 結果を kind 付き flat list で返す | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| MCP YAML drift check (T-38-02-04 mitigation 確認) | `python3 scripts/generate_mcp_artifacts.py --check` | exit 0 | ✓ PASS (本検証で再確認) |
| ADR-0052 file 存在 | `test -f docs/adr/0052-worker-generated-outputs-storage-and-preview.md` | exit 0 | ✓ PASS |
| Phase 38 由来の debt marker (TBD/FIXME/XXX) 検出 | `grep -nE "TBD\|FIXME\|XXX" {modified files}` | 0 件 | ✓ PASS |
| Phase 38 由来の warning marker (TODO/HACK/PLACEHOLDER) 検出 | `grep -nE "TODO\|HACK\|PLACEHOLDER" {modified files}` | 0 件 | ✓ PASS |
| Backend pytest target suite (Phase 38 関連 8 ファイル) | `uv run pytest tests/test_*.py -x` | local 環境では .venv の shebang が docker pathに固定されて実行不可。SUMMARY で 11+3+4+5+9 = 32 passed 記録あり (Plan 04 SUMMARY) + VALIDATION.md 12/12 automated ✅ | ? SKIP — executor が記録した結果を信頼 (本検証で再実行不可) |
| Frontend TypeScript build | `cd frontend && bun run tsc --noEmit` | Plan 01/05 SUMMARY で exit 0 確認済 | ? SKIP — bun が local 環境に無いため再実行不可 |

### Probe Execution

該当なし — Phase 38 には `scripts/*/tests/probe-*.sh` 等の probe ファイルが declared / conventional ともに存在しない (migration/CLI tool phase ではない)。

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| FOUT-01 | 38-02, 38-03, 38-04, 38-05, 38-06 | execute_python sandbox 生成ファイルを UI から DL | ✓ SATISFIED (automated) + ? NEEDS HUMAN (E2E) | outputs.py + execute_python cwd 切替 + post-process rename + AttachmentModal DL CTA。実機 DL は human-verify #1 |
| FOUT-02 | 38-02, 38-03, 38-04, 38-05, 38-06 | claude_code workspace 成果物を UI から取得 | ✓ SATISFIED (automated) + ? NEEDS HUMAN (E2E) | claude_code 新シグネチャ + helper 再利用 + outputs route 経路統合。`test_get_output_works_for_claude_code` ✅。実機 DL は human-verify #1 |
| FOUT-03 | 38-05, 38-06 | チャット内プレビュー (画像 / Markdown / CSV / text) | ⚠ PARTIAL (code) + NEEDS HUMAN | 4 renderer dispatch + classify + lazy import 経路 automated 確認済、実機描画は human-verify #1 |
| FOUT-04 | 38-01, 38-02, 38-04, 38-05, 38-06 | ユーザー別ストレージ保持 + 再取得 + multi-user isolation | ✓ SATISFIED (sc4 automated) + ? NEEDS HUMAN (sc5 E2E) | sc4: AIMessage bundle + AsyncPostgresSaver round-trip + frontend 復元描画。sc5: Phase 36 helper import 再利用 + automated isolation test ✅。実機 curl は human-verify #4 |

**Orphaned requirements check:** REQUIREMENTS.md L40-44 が Phase 38 に FOUT-01..04 をマップ。全 4 ID が plan frontmatter `requirements:` で参照されており、orphan ゼロ。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| (none) | — | — | — | Phase 38 由来の TBD / FIXME / XXX / TODO / HACK / PLACEHOLDER ゼロ。スタブ実装ゼロ (全 artifact が実体を持つ) |

**Pre-existing failures (not Phase 38 regressions):**

| Source | Failure | Pre-existing? | Severity |
|---|---|---|---|
| `tests/test_generate_mcp_artifacts.py::test_load_tools_has_six_tools` | hardcoded `== 6` (Phase 37 で 2 ツール追加で 8 に増加した取りこぼし) | Yes (Plan 02 deferred-items 確認済) | ℹ Info (Phase 38 scope 外) |
| `tests/test_mcp_server.py::test_claude_code_*` 7 件 | Plan 03 で claude_code から cwd 引数削除した意図的破壊変更の fallout (D-09) | Yes (Plan 03 SUMMARY + Plan 04 deferred-items 確認済) | ℹ Info (Phase 38 D-09 意図) |
| `bulkRemoveThreads` 等 frontend TypeScript エラー 7 件 | Phase 38 着手前から base ブランチに存在 (Plan 01 deferred-items で `git stash` 確認済) | Yes | ℹ Info (Phase 38 scope 外) |

これらは全て deferred-items.md に記録済で、Phase 38 由来の regression は無し。

### Human Verification Required

```
1. FOUT-03 のチャット画面プレビュー (画像/Markdown/CSV/text の各 renderer dispatch 実機動作)
   - **Test:** docker compose up + http://localhost:5173/orochi/ で execute_python 経由で画像 .png / Markdown .md / CSV .csv / プレーンテキスト .py を生成、AttachmentModal を開いて各 renderer が破綻なく描画されることを確認
   - **Expected:** kind 別 renderer (image=<img>、markdown=react-markdown、csv=ag-grid、text=Monaco) が正常に描画、PDF / unsupported は「Download only」フォールバック + DL CTA
   - **Why human:** DOM rendering / 視覚体感は実機 browser 必須 (UI-SPEC Checker #11-13, #20)

2. Dark mode 視覚整合性確認
   - **Test:** `[data-theme="dark"]` 切替で Modal / 4 renderer 全てを表示
   - **Expected:** ダーク/ライト切替で破綻なし、コントラスト OK
   - **Why human:** 視覚的コントラスト判定は人間 (UI-SPEC Checker #16)

3. Mobile 375px viewport で Modal full-screen 化
   - **Test:** DevTools viewport を 375×667 に切替
   - **Expected:** Modal が full-screen 化、CTA が full-width block 化
   - **Why human:** responsive 視覚判定 (UI-SPEC Checker #17)

4. Multi-user isolation の curl 直接叩き
   - **Test:** User A / User B 両方の JWT cookie を取得し `curl -b "access_token=<USER_B_JWT>" http://localhost:8000/api/threads/<USER_A_TID>/outputs/<filename>` を実行
   - **Expected:** 401 or 404 が返る + Modal で別 user session 開いた場合に「このファイルにはアクセスできません」エラーバナー表示
   - **Why human:** FOUT-04 sc5 — 実機 JWT 取得 + E2E curl 検証 (UI-SPEC Checker #18)。コード上は Phase 36 helper の import 再利用で防御済だが、実機 isolation は人間判断

5. Size cap UX
   - **Test:** >1MB の text / >10MB の画像を生成
   - **Expected:** size cap 案内 banner (accent-subtle 色) + DL CTA が出る、destructive 色は使わない
   - **Why human:** 視覚的色合い + 文言確認 (UI-SPEC Checker #19)

6. PDF / unsupported 形式のフォールバック描画
   - **Test:** PDF を Modal で開く
   - **Expected:** 「Download only」案内 + DL CTA、プレビュー試行ゼロ
   - **Why human:** 実 PDF 生成 → Modal 表示 → フォールバック描画は実機 browser 必須 (UI-SPEC Checker #20)

7. Accent reserved-for / destructive 色限定の deepdive
   - **Test:** AttachmentChipRow / AttachmentModal で `--color-accent` の使用箇所一覧化、destructive 用法も全箇所列挙
   - **Expected:** accent 用途が UI-SPEC L173-192 の reserved-for 範囲内、destructive はエラーバナーのみ
   - **Why human:** デザインシステム遵守 (UI-SPEC Checker #7, #8)
```

これら 7 項目は Plan 38-05 / 38-06 の checkpoint:human-verify (UI-SPEC §"Phase 38 Checker Acceptance Criteria" 22 項目のうち実機検証が必要な 7 項目) として orchestrator にハンドオフ済。38-06-SUMMARY.md の "## E2E Acceptance Checklist (for orchestrator visual review)" に詳細手順を記載済 (本検証で確認)。

### Deferred Items

Items not yet met but explicitly addressed in v6.1+ deferred-items.md (Phase 36) や 38-CONTEXT.md `<deferred>`。これらは Phase 38 の goal 範囲外で、否定的決定として明示記録されている。

| # | Item | Addressed In | Evidence |
|---|---|---|---|
| 1 | Orchestrator (SuperChat) 経由の AI 生成ファイル bundle 対応 | v6.1+ | 38-04-PLAN.md Task 2 action #2 / 38-04-SUMMARY.md "scope 限定" 節 / .planning/phases/36-text-code-image-multimodal/deferred-items.md "orchestrator_handler bundle 対応" 行 |
| 2 | 横断 "My Files" 画面 / Header dropdown | v6.1+ (D-16 否定的決定) | 38-CONTEXT.md D-16 / 38-06-SUMMARY.md / 36 deferred-items.md |
| 3 | 一覧 endpoint `GET /api/threads/{tid}/outputs` | v6.1+ (D-17 否定的決定) | 38-CONTEXT.md D-17 |
| 4 | 個別ファイル削除 UI (`DELETE /api/threads/{tid}/outputs/{name}`) | v6.1+ (D-02 否定的決定) | 38-CONTEXT.md D-02 |
| 5 | PDF preview / HTML preview | v6.1+ (D-12 範囲外) | 38-CONTEXT.md D-12 |
| 6 | AI 生成ファイル GC / TTL / quota | v6.1+ (観察ベース) | 38-CONTEXT.md `<deferred>` / 38-RESEARCH.md §"Phase 38 で新規出現するセキュリティ懸念" |
| 7 | AttachmentModal size cap 閾値の観察ベース調整 | v6.1+ | 38-RESEARCH.md §"Open Question 3" |
| 8 | papaparse 追加検討 | v6.1+ | UI-SPEC §Standard Stack §6 / RESEARCH §6 |
| 9 | AI 生成完了 toast / 通知 | v6.1+ UI polish | 38-CONTEXT.md `<deferred>` |
| 10 | Phase 38 独自 isolation 単体テスト (新規追加なし) | v6.1+ (D-19 否定的決定) | 38-CONTEXT.md D-19 / Phase 36 helper 再利用で間接継承 |

これらは Phase 38 goal の「ユーザーがチャット UI から DL・プレビュー・再取得できる成果物管理基盤」の最小実装で意図的に scope 外にされた項目で、本検証では gap として扱わない。

### Gaps Summary

**Hard gaps (blocking goal achievement): なし**

全 5 つの ROADMAP success criteria に対応する artifact + key link + データフローが automated レベルで verified。Phase 38 由来の anti-pattern / debt marker / stub 実装はゼロ。MCP YAML drift check exit 0。Phase 38 由来の test regression ゼロ (pre-existing 35 件は全て deferred-items.md に明示記録済)。

**Soft gaps (require human verification): 7 項目**

これらは coding artifact は実装済で grep / source assertion レベルで confirmed だが、観測対象が以下のいずれかであるため自動検証では closing できない:

- 視覚的描画 (DOM rendering / 色 / レイアウト) — UI-SPEC Checker #11-13, #16-17, #19-20
- E2E 認可 (実 JWT / 実 user session / curl 直接叩き) — UI-SPEC Checker #18
- デザインシステム遵守 (accent / destructive 用法観察) — UI-SPEC Checker #7-8

これらは Plan 38-05 / 38-06 の checkpoint:human-verify として orchestrator にハンドオフ済で、38-06-SUMMARY.md "## E2E Acceptance Checklist" に詳細手順を記載済。本検証では `status: human_needed` で escalate する。

### Status Determination Trace

- Truths VERIFIED: 2 (sc1: execute_python DL, sc4 sc4: 再取得) — code-level + automated tests green
- Truths PARTIAL: 3 (sc2: claude_code DL, sc3: preview, sc5: isolation) — code-level verified だが E2E human-verify が UI-SPEC で要求されている
- Artifacts MISSING: 0
- Artifacts STUB: 0
- Artifacts ORPHANED: 0
- Key Links NOT_WIRED: 0
- Data-Flow DISCONNECTED / HOLLOW: 0
- Anti-Patterns Blockers: 0
- Pre-existing failures (deferred): 3 categories, all recorded

決定木:
1. ✗ gaps_found 該当無し (BLOCKER ゼロ)
2. ✓ human_verification 項目 7 件あり → **status: human_needed**

---

_Verified: 2026-05-12T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
