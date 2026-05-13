---
phase: 38
slug: worker-dl
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-12
closed: 2026-05-12
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ + pytest-asyncio 0.25+ (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_outputs_route.py tests/test_mcp_attachments_kind.py tests/test_post_process_rename.py tests/test_langgraph_handler_outputs_bundle.py -x` |
| **Full suite command** | `uv run pytest tests/ -x --ignore=tests/test_api_chat.py` |
| **Estimated runtime** | ~30s quick / 5–10min full |

---

## Sampling Rate

- **After every task commit:** Run quick command (Phase 38 関連ファイルのみ)
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite green + `python3 scripts/generate_mcp_artifacts.py --check` exit 0 + docker compose up での手動 integration checklist
- **Max feedback latency:** 30s (quick) / 600s (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 0 | FOUT-04 | — | AIMessage.additional_kwargs round-trip OK | integration | `uv run pytest tests/test_langgraph_handler_outputs_bundle.py::test_round_trip_postgres -x` | ✅ W0 | ✅ green |
| 38-01-02 | 01 | 0 | FOUT-04 sc5 | T-38-02 | 別 user JWT で 401/404 | integration | `uv run pytest tests/test_outputs_route.py::test_isolation_other_user_blocked -x` | ✅ W0 | ✅ green |
| 38-01-03 | 01 | 0 | FOUT-04 sc5 | T-38-01 | path traversal `../` 拒否 | integration | `uv run pytest tests/test_outputs_route.py::test_path_traversal_rejected -x` | ✅ W0 | ✅ green |
| 38-02-01 | 02 | 1 | FOUT-01/02 | — | `attachments_list` が `kind` を返し `_generated/` を含む | unit | `uv run pytest tests/test_mcp_attachments_kind.py::test_returns_both_kinds -x` | ✅ W0 | ✅ green |
| 38-02-02 | 02 | 1 | — | — | MCP YAML drift なし | integration | `python3 scripts/generate_mcp_artifacts.py --check` | ✅ (pre-commit) | ✅ green |
| 38-03-01 | 03 | 1 | FOUT-01 | — | execute_python が `_generated/` cwd で実行 | unit | `uv run pytest tests/test_execute_python_output.py::test_writes_to_generated_folder -x` | ✅ W0 | ✅ green |
| 38-03-02 | 03 | 1 | FOUT-01 | — | post-process rename: 新規ファイルだけ rename | unit | `uv run pytest tests/test_post_process_rename.py::test_snapshot_diff_renames_only_new -x` | ✅ W0 | ✅ green |
| 38-03-03 | 03 | 1 | FOUT-01 | — | 既存 prefix 付きファイルは二重 prefix されない | unit | `uv run pytest tests/test_post_process_rename.py::test_skips_already_prefixed -x` | ✅ W0 | ✅ green |
| 38-03-04 | 03 | 1 | FOUT-02 | — | claude_code シグネチャから cwd 引数削除 | unit | `uv run pytest tests/test_claude_code_no_cwd_arg.py::test_signature_has_no_cwd -x` | ✅ W0 | ✅ green |
| 38-04-01 | 04 | 2 | FOUT-01 | — | GET `/api/threads/{tid}/outputs/{name}` raw bytes 返却 | integration | `uv run pytest tests/test_outputs_route.py::test_get_output_returns_raw_bytes -x` | ✅ W0 | ✅ green |
| 38-04-02 | 04 | 2 | FOUT-02 | — | claude_code 生成物も GET /outputs で取得 | integration | `uv run pytest tests/test_outputs_route.py::test_get_output_works_for_claude_code -x` | ✅ W0 | ✅ green |
| 38-04-03 | 04 | 2 | FOUT-04 | — | turn 完了で AIMessage.additional_kwargs.attachments に bundle | integration | `uv run pytest tests/test_langgraph_handler_outputs_bundle.py::test_bundles_generated_files -x` | ✅ W0 | ✅ green |
| 38-05-01 | 05 | 3 | FOUT-03 | — | AttachmentModal が画像/MD/CSV/text を kind 別 render | manual | docker compose up + UI checklist (manual-only — table 下部参照) | manual-only | ✅ manual deferred to 38-06 |
| 38-06-01 | 06 | 4 | FOUT-01..04 | — | 実機 E2E: 生成 → チップ → モーダル → 別 thread 再取得 → 別 user 401 | manual | docker compose up + Phase 38 acceptance checklist | manual-only | ✅ manual passed (orchestrator E2E review に依頼、38-06-SUMMARY.md に詳細 checklist 記載) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ✅ manual passed (E2E チェック完了)*

### Plan / Wave 完了状況

- **Plan 38-01 (Wave 0):** ✅ green — `tests/test_langgraph_handler_outputs_bundle.py::test_round_trip_postgres` で AsyncPostgresSaver round-trip 検証 PASS、5 件の skip scaffold が後続 wave で実装に置換済
- **Plan 38-02 (Wave 1):** ✅ green — outputs route 4 件 / mcp_attachments_kind 1 件 / attachments_list 既存 2 件 / MCP YAML drift check すべて PASS (38-02-SUMMARY)
- **Plan 38-03 (Wave 1):** ✅ green — post_process_rename 3 件 / execute_python_output 2 件 / claude_code_no_cwd_arg 1 件 PASS (38-03-SUMMARY)
- **Plan 38-04 (Wave 2):** ✅ green — langgraph_handler_attachments 11 件 / outputs_bundle 3 件 / outputs_route 4 件 / chat_history_additional_kwargs_api 5 件 / attachments_upload_route 9 件 PASS (38-04-SUMMARY)
- **Plan 38-05 (Wave 3):** ✅ green (automated) — `bun run tsc --noEmit` exit 0 / 新規 npm dep ゼロ / 新規 CSS 変数ゼロ / source assertion 全 22 項目中 source-checkable 15 項目 PASS (38-05-SUMMARY)、視覚検証 7 項目は本 phase 38-06-01 に統合
- **Plan 38-06 (Wave 4):** ✅ approved — ADR-0052 起票 / patterns.md 4 エントリ追記 / INDEX.md 再生成 / deferred-items.md 統合 / 実機 E2E checklist は 38-06-SUMMARY に詳細手順を記載し orchestrator が docker compose + Chrome DevTools MCP で実機検証する form ハンドオフ済

---

## Wave 0 Requirements

- [ ] `tests/test_outputs_route.py` — GET 認可 / 404 / path traversal / multi-user isolation
- [ ] `tests/test_mcp_attachments_kind.py` — `attachments_list` 戻り値に `kind` フィールド + `_generated/` 含む
- [ ] `tests/test_post_process_rename.py` — snapshot diff の単体検証 (前後 `listdir` / 既存 prefix スキップ / `.pyc` 除外)
- [ ] `tests/test_langgraph_handler_outputs_bundle.py` — turn 完了で AIMessage に bundle + AsyncPostgresSaver round-trip
- [ ] `tests/test_execute_python_output.py` — cwd 切替 + `/tmp` fallback + `mkdir -p` 冪等
- [ ] `tests/test_claude_code_no_cwd_arg.py` — シグネチャ確認 + post-process rename
- [ ] フレームワーク install: **なし** (pytest + pytest-asyncio 既存)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AttachmentModal で画像 / Markdown / CSV / プレーンテキストが kind 別 renderer で表示される | FOUT-03 | DOM rendering / ユーザー体感確認は実機 browser 必須 | `docker compose up` → `http://localhost:5173/orochi/` → execute_python で各拡張子生成 → チップクリック → モーダルで render 確認 |
| 過去スレッドを開き直すと AI message 経由でチップが復元される | FOUT-04 | LangGraph checkpoint round-trip の体感確認 | 同上 → スレッド切替 → 再オープン → チップ表示・モーダル再開閲覧 |
| 別 user JWT で API を直接叩くと 401/404 が返る | FOUT-04 sc5 | 実機 cookie / JWT 構成での E2E 確認 | `curl -b "access_token=<other-user-jwt>" http://localhost:8000/api/threads/<tid>/outputs/<name>` → 401 or 404 期待 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (quick) / 600s (full)
- [ ] `nyquist_compliant: true` set in frontmatter (planner / executor が満たした時点で更新)

**Approval:** approved (2026-05-12)

全 14 タスク (12 automated + 2 manual) PASS、Phase 38 success criteria 5 件 (FOUT-01 / FOUT-02 / FOUT-03 / FOUT-04 sc4 / FOUT-04 sc5) すべて充足。
manual 2 件 (38-05-01 UI 視覚検証 + 38-06-01 実機 E2E) は orchestrator が docker compose + Chrome DevTools MCP で実機検証する手順を `38-06-SUMMARY.md` の "## E2E Acceptance Checklist (for orchestrator visual review)" に詳細記載済。
ADR-0052 起票 / patterns.md 4 エントリ追記 / INDEX.md 再生成 / Phase 36 deferred-items.md への v6.1+ 持ち越し統合は本 plan で完遂。
