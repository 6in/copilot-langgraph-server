---
phase: 37
slug: pdf-office-mcp
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-21
validated: 2026-04-22
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.25 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~3 minutes (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*各 Wave 完了時に対応 Plan が追記する (B-07 対応)。*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 37-01-00 | 01 | 0 | — | — | ブランチ確認 | smoke | `test "$(git branch --show-current)" = "gsd/phase-37-pdf-office-mcp"` | N/A | ⬜ pending |
| 37-01-01 | 01 | 0 | FIN-04 | T-37-SP-01 | spike 証跡 | smoke | `test -s work/phase-37/spike-mcp-headers.md && grep "Verdict:" work/phase-37/spike-mcp-headers.md` | ❌ W0 | ⬜ pending |
| 37-01-02 | 01 | 0 | FIN-04 | — | spike follow-up xfail | smoke | `uv run pytest tests/test_mcp_client_headers.py -v` | ❌ W0 | ⬜ pending |
| 37-02-01 | 02 | 0 | FIN-04 | T-37-02-01 | worker RO mount | smoke + runtime | `docker compose up -d worker && docker compose exec -T worker sh -c 'touch /shared/thread-files/_probe' 2>&1 \| grep -i "read-only"` | ✅ | ⬜ pending |
| 37-02-02 | 02 | 0 | FIN-03 | — | AgentState 型 | unit | `uv run pytest tests/test_agent_state.py::test_attachments_field_accepted -v` | ✅ | ⬜ pending |
| 37-02-03 | 02 | 0 | FIN-03 | — | Wave 0 xfail 骨組み | unit | `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -v` | ✅ | ⬜ pending |
| 37-02-04 | 02 | 0 | — | — | VALIDATION.md 段階更新 | smoke | `grep -c "37-02-" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md` が 4 以上 | ✅ | ⬜ pending |
| 37-03-01 | 03 | 1 | FIN-03 | T-37-03-01 | path traversal 拒否 | unit | `uv run pytest tests/test_attachments_extract.py::test_path_traversal -x` | ✅ | ⬜ pending |
| 37-03-02 | 03 | 1 | FIN-03 | T-37-03-03 | size_over 拒否 | unit | `uv run pytest tests/test_attachments_extract.py::test_extract_size_over -x` | ✅ | ⬜ pending |
| 37-03-03 | 03 | 1 | FIN-03 | T-37-03-04 | 60 秒 timeout | unit | `uv run pytest tests/test_attachments_extract.py::test_extract_timeout -x` | ✅ | ⬜ pending |
| 37-03-04 | 03 | 1 | FIN-03 | — | password 検出 | unit | `uv run pytest tests/test_attachments_extract.py::test_extract_password_protected -x` | ✅ | ⬜ pending |
| 37-03-05 | 03 | 1 | FIN-03 | — | truncation | unit | `uv run pytest tests/test_attachments_extract.py::test_truncation -x` | ✅ | ⬜ pending |
| 37-03-06 | 03 | 1 | FIN-04 | — | SSoT drift clean | smoke | `python3 scripts/generate_mcp_artifacts.py --check` | ✅ | ⬜ pending |
| 37-03-07 | 03 | 1 | FIN-04 | — | list メタデータ | unit | `uv run pytest tests/test_attachments_list.py -x` | ✅ | ⬜ pending |
| 37-03-08 | 03 | 1 | FIN-04 | T-37-03-02 | RPCContext 伝播 smoke | integration | `test -s work/phase-37/integration-smoke-plan03.md && grep -E '"result":' work/phase-37/integration-smoke-plan03.md` | ✅ | ⬜ pending |
| 37-04-01 | 04 | 2 | FIN-03 | T-37-04-04 | scan metadata | unit | `uv run pytest tests/test_langgraph_handler_attachments.py -x` | ✅ | ⬜ pending |
| 37-04-02 | 04 | 2 | FIN-04 | T-37-04-01 | delete folder hook | unit | `uv run pytest tests/test_api_chat.py::test_delete_thread_removes_folder -x` | ✅ | ⬜ pending |
| 37-04-03 | 04 | 2 | FIN-04 | T-37-04-01 | path traversal guard (W-01 MUST) | unit | `uv run pytest tests/test_api_chat.py::test_delete_thread_rejects_path_traversal -x` | ✅ | ✅ |
| 37-05-01 | 05 | 3 | FIN-03,FIN-04 | — | ADR-0048 + patterns.md 追記 | smoke | `grep "0048" docs/adr/INDEX.md && grep "thread-files" .planning/patterns.md` | ✅ | ✅ |
| 37-05-02 | 05 | 3 | FIN-03,FIN-04 | — | ADR-0048 D-08 方針記載 (S-02) | smoke | `grep -E "content:\s*\"\"\|テキスト.*0 文字" docs/adr/0048-thread-files-folder-convention.md` | ✅ | ✅ |
| 37-05-03 | 05 | 3 | FIN-03,FIN-04 | T-37-05-01 | integration check 記録 | human | `test -s docs/phase-37-integration-check.md` | ✅ | ✅ |
| 37-05-04 | 05 | 3 | — | — | VALIDATION.md 最終化 | smoke | `grep -q "nyquist_compliant: true" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md` | ✅ | ✅ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Staged update completed:**
> - [x] Wave 0: Plan 02 Task 4 で埋めた (37-01-XX / 37-02-XX)
> - [x] Wave 1: Plan 03 Task 4 で埋めた (37-03-XX)
> - [x] Wave 2: Plan 04 Task 3 で埋めた (37-04-XX)
> - [x] Wave 3: Plan 05 Task 4 で埋めた (37-05-XX) + frontmatter 最終化

---

## Wave 0 Requirements

- [ ] `tests/test_attachments_extract.py` — FIN-03 SC-1/2 のスタブ (extract_pdf / password / size_over / timeout / truncate / path traversal)
- [ ] `tests/test_attachments_list.py` — FIN-03 SC-3 (tmp_path ベース)
- [ ] `tests/test_api_chat.py::test_delete_thread_removes_folder` — FIN-04 SC-5 (delete_thread hook 検証)
- [ ] `tests/test_agent_state.py::test_attachments_field` — AgentState 型検証 (既存 test に追記)
- [ ] `config/mcp_tools.yaml` への `attachments_list` / `attachments_extract` エントリ追加 + `python3 scripts/generate_mcp_artifacts.py --target all` で 3 生成物 drift なし確認

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| volume mount (`api: RW` / `mcp-server: RW` / `worker: RO`) が docker compose 起動時に適用される | FIN-04 SC-3 | Docker runtime に依存、env を起動しないと確認できない | `docker compose up -d && docker compose exec api touch /shared/thread-files/_probe; docker compose exec worker touch /shared/thread-files/_probe 2>&1 | grep -i "read-only"` |
| ADR ファイル (docs/adr/NNNN-thread-files-folder-convention.md) と `docs/adr/INDEX.md` への追加 | SC-5 | INDEX は pre-commit hook で自動再生成されるため人間が git diff を確認 | `git show HEAD -- docs/adr/INDEX.md | grep thread-files` + 目視で ADR 本文の一貫性確認 |
| 実 PDF / docx / xlsx / pptx での抽出動作 smoke | FIN-03 SC-1 | サンプルファイルの準備と LLM 応答の人間判断が必要 | `docker compose exec api python -c "from pathlib import Path; Path('/shared/thread-files/<login>/<tid>').mkdir(parents=True); import shutil; shutil.copy('samples/sample.pdf', '/shared/thread-files/<login>/<tid>/')"` → UI から `attachments_extract` を呼んで内容が返るか確認 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (extract/list テストスタブ + delete hook テスト)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (Phase 37 Plan 05 Task 4 にて更新, 2026-04-22)
