---
phase: 39
slug: ui-polish
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-13
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 詳細は `39-RESEARCH.md` § "Validation Architecture" を参照。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 (asyncio_mode=auto) / vitest (frontend は tsc 中心) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` / `frontend/tsconfig.json` |
| **Quick run command** | `pytest tests/test_sse.py tests/test_job_store.py tests/test_generate_mcp_artifacts.py -q --tb=short` (UIFIX-03 / D-09 系) + `docker compose exec frontend bun run tsc -b --force` (TS 系) |
| **Full suite command** | `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no` + `docker compose exec frontend bun run tsc -b --force` |
| **Estimated runtime** | ~60 秒 (pytest full) + ~20 秒 (tsc) |

---

## Sampling Rate

- **After every task commit:** Run quick run command for the touched area (Python or TS)
- **After every plan wave:** Run the full suite — failures 数を計測して対前 wave の改善量を記録
- **Before `/gsd-verify-work`:** Full suite must be green for in-scope tests; D-10 範囲は target 件数達成
- **Max feedback latency:** ~80 秒 (Python full + tsc)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 39-XX-01 | UIFIX-01 | 1 | UIFIX-01 | — | N/A | static (grep) | `grep -c 'UIFIX-01\|ADR-0053' frontend/src/components/MermaidBlock.tsx` → ≥1 | ✅ | ⬜ pending |
| 39-XX-02 | UIFIX-01 | 1 | UIFIX-01 | — | N/A | static (file exists) | `test -f docs/adr/0053-mermaid-source-default-rationale.md` | ❌ W0/1 | ⬜ pending |
| 39-XX-03 | UIFIX-01 | 1 | UIFIX-01 | — | N/A | hook | `python3 scripts/generate_adr_index.py --check` | ✅ | ⬜ pending |
| 39-XX-04 | UIFIX-02 | 1 | UIFIX-02 | — | N/A | static (grep) | `grep -c 'cs-message__custom-content' frontend/src/theme.css` → ≥2 | ✅ | ⬜ pending |
| 39-XX-05 | UIFIX-02 | 1 | UIFIX-02 | — | N/A | manual (chrome-devtools) | `/orochi/chat` で 50 行 python ブロックを含む応答 — bubble 幅 inspect | manual | ⬜ pending |
| 39-XX-06 | UIFIX-03 | 1 | UIFIX-03 | — | N/A | automated | `pytest tests/test_sse.py::test_sse_done_signal -v` → green | ✅ | ⬜ pending |
| 39-XX-07 | UIFIX-03 | 1 | UIFIX-03 | — | N/A | automated | `pytest tests/test_sse.py::test_sse_already_done -v` → green | ✅ | ⬜ pending |
| 39-XX-08 | UIFIX-03 | 1 | UIFIX-03 | — | N/A | static (grep) | `grep -cE 'register_sse\|unregister_sse\|self\.queues' app/jobs/job_store.py` → 0 | ✅ | ⬜ pending |
| 39-XX-09 | UIFIX-03 | 1 | UIFIX-03 | — | N/A | static (grep) | `grep -c 'test_register_and_notify\|test_unregister_sse' tests/test_job_store.py` → 0 | ✅ | ⬜ pending |
| 39-XX-10 | UIFIX-03 | 1 | UIFIX-03 | — | API 不変 | static (diff) | `git diff main..HEAD -- app/jobs/notifier.py` 変更行数 0 | manual | ⬜ pending |
| 39-XX-11 | UIFIX-04 D-07 | 2 | UIFIX-04 | — | N/A | static (grep) | `grep -lE 'MessageArea[^>]*onAskMe' frontend/src/components/{ChatApp,SuperChatApp,GemChatApp,CanvasChatApp,DebateChatApp}.tsx \| wc -l` → 5 | ✅ | ⬜ pending |
| 39-XX-12 | UIFIX-04 D-07 | 2 | UIFIX-04 | — | N/A | manual (chrome-devtools) | 5 chat apps 起動して AskMe ボタンが表示 | manual | ⬜ pending |
| 39-XX-13 | UIFIX-04 D-08 | 2 | UIFIX-04 | — | N/A | automated | `bun run tsc -b --force 2>&1 \| grep -cE 'bulkRemoveThreads\|TS2459.*Theme'` → 0 | ✅ | ⬜ pending |
| 39-XX-14 | UIFIX-04 D-09 | 2 | UIFIX-04 | — | N/A | automated | `pytest tests/test_generate_mcp_artifacts.py -v` 4 件 green (`== 8`) | ✅ | ⬜ pending |
| 39-XX-15 | UIFIX-04 D-09 | 2 | UIFIX-04 | — | N/A | static (grep) | `grep -c 'cwd=' tests/test_mcp_server.py` → 0 | ✅ | ⬜ pending |
| 39-XX-16 | UIFIX-04 D-10 | 3 | UIFIX-04 | — | N/A | automated | `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no` failed 件数 < {plan で target} | manual (plan 確定) | ⬜ pending |
| 39-XX-17 | UIFIX-04 D-11 | 2 | UIFIX-04 | — | N/A | static (grep) + manual | `grep -c 'スレッドが未作成' frontend/src/components/AttachmentButton.tsx` → ≥1 + 新規 `/chat` で tooltip 確認 | ✅ | ⬜ pending |
| 39-XX-18 | UIFIX-04 D-12 | 3 | UIFIX-04 | — | N/A | manual | `test -f .planning/phases/39-ui-polish/deferred-items.md` + log で追記項目数を確認 | manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> Task ID は planner が確定後に書き換える。Plan / Wave 番号も planner 判断で確定。

---

## Wave 0 Requirements

- [ ] **chatscope override reality-check** — **Plan 03 (Wave 1) Task 1 (checkpoint:human-verify task) で実施**。chrome-devtools MCP を使い、`/orochi/chat` 上の現在の bubble 幅と `.cs-message__custom-content` の computed style を確認。UIFIX-02 の override が 1 行で足りるか実証する (A1 assumption 解消)。Plan 01 (Wave 0) は baseline 計測のみに保ち、reality-check は Wave 1 冒頭で先行検証する設計。
- [ ] **pre-existing failures 件数の baseline 取得** — `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no` を実行し、開始時点の failed 件数 (実測 27 件) を記録。Phase 39 完了時の target 値 (plan で確定) との差分計測に使用
- [ ] **`tests/test_install_hooks` の現状確認** — CONTEXT.md D-10 主張 4 errors は実測 0 件。Wave 0 で確認後、D-10 から該当項目を消去 (deferred-items.md 不要、既に解決済)
- [ ] **TS error 件数 baseline** — `docker compose exec frontend bun run tsc -b --force` で 11 件 (CONTEXT 主張 7 件 + 追加 4 件) のうち scope 内 7 件のみ修正対象、残り 4 件は deferred-items.md へ送る運用を確定

*すべての Wave 0 完了後に `wave_0_complete: true` を frontmatter に書き込み*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mermaid View hang 再現と回避策確認 | UIFIX-01 | OS レベル hang のため自動テスト不可、手動で View default を試行して chromium hang を再現できないことを確認 (恒久化された `'source'` default が機能) | 1) `/orochi/chat` を開く 2) Mermaid を含む応答を表示 3) 描画モード切替ボタンで View に切り替え 4) chromium がフリーズしないことを目視 |
| CollapsibleCodeBlock 縦長で潰れない | UIFIX-02 | bubble 幅は viewport 依存で CI 困難、chrome-devtools で目視 | 1) `/orochi/chat` で 50 行 python ブロックを含む応答 2) bubble がフルバルーン幅で表示 3) 表 / 引用 / Mermaid でも同様に確認 |
| 5 chat apps の AskMe ボタン表示 | UIFIX-04 D-07 | UI 描画判定は manual | ChatApp / SuperChat / GemChat / CanvasChat / DebateChat を順に開き、InputBar に AskMe ボタンが緑枠で表示 |
| 📎 tooltip 文言出し分け | UIFIX-04 D-11 | UI hover 動作の確認 | 新規 `/chat` を開き activeThreadId が null の状態で 📎 にホバー、tooltip が `'スレッドが未作成のため添付できません'` であることを確認 |
| `notifier.py` API 不変 | UIFIX-03 D-05 | 表面 API を温存したか diff レビュー | `git diff main..HEAD -- app/jobs/notifier.py` を `/gsd-verify-work` で目視 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (chatscope reality-check / baseline 件数)
- [ ] No watch-mode flags
- [ ] Feedback latency < 80s
- [ ] `nyquist_compliant: true` set in frontmatter after Wave 0 完了

**Approval:** pending
