---
phase: 36
slug: text-code-image-multimodal
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-23
revised: 2026-04-23
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 詳細な検証戦略は `36-RESEARCH.md` §Validation Architecture を参照。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / Chrome DevTools MCP (frontend runtime behavior) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_copilot_attachments.py tests/test_langgraph_handler_attachments_v2.py tests/test_attachments_upload_route.py -x` |
| **Full suite command** | `uv run pytest -q && cd frontend && bun tsc --noEmit` |
| **Estimated runtime** | ~45 秒 (quick) / ~150 秒 (full pytest + tsc) |

**フロントエンドテスト方針（Dimension 8 根拠）:** vitest/React Testing Library の導入は Phase 36 scope 外（新規依存追加回避）。`useAttachments` / `VisionWarningBanner` / `useModels` / `AttachmentChipRow` 等の runtime behavior は Plan 07 の Chrome DevTools MCP integration check で E2E 検証する（下記 §Dimension 8 参照）。

---

## Sampling Rate

- **After every task commit:** Run quick subset relevant to changed files
- **After every plan wave:** Run full pytest + `bun tsc --noEmit`
- **Before `/gsd-verify-work`:** Full pytest green + Chrome DevTools MCP integration check (Plan 07)
- **Max feedback latency:** 180 秒

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Task Name | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-----------|-------------|-----------|-------------------|--------|
| 01-T1 | 01 | 0 | AsyncPostgresSaver round-trip (A1 risk) | FIN-01/02 (D-20) | unit (tdd) | `uv run pytest tests/test_chat_history_additional_kwargs.py -x -v` | ⬜ pending |
| 01-T2 | 01 | 0 | SDK attachments kwarg 形状確認 | FIN-01/02 (D-09/10/15) | unit (tdd) | `uv run pytest tests/test_copilot_attachments_spike.py -x -v` | ⬜ pending |
| 01-T3 | 01 | 0 | docker compose SDK spike (checkpoint) | FIN-01/02 (A3) | manual | `docker compose exec worker uv run python tests/_spike_attachments.py` → `docs/phase-36-sdk-spike-note.md` Verdict: PASS | ⬜ pending |
| 02-T1 | 02 | 1 | ChatCopilot _extract_attachments / list_models / is_vision_model | FIN-01/02 (D-09/10/14/15/16/18) | unit (tdd) | `uv run pytest tests/test_copilot_attachments.py tests/test_copilot_bind_tools.py -x -v` | ⬜ pending |
| 02-T2 | 02 | 1 | GET /api/models route + attachments stub + main.py | FIN-02 (D-07/16) | integration (tdd) | `uv run pytest tests/test_api_models_route.py tests/test_api_chat.py -x -v` | ⬜ pending |
| 03-T1 | 03 | 2 | ChatRequest.attachments + enqueue_job forwarding | FIN-01/02 (D-14) | integration (tdd) | `uv run pytest tests/test_api_chat.py -x -v` | ⬜ pending |
| 03-T2 | 03 | 2 | POST /api/threads/{tid}/attachments (upload) | FIN-01/02 (D-01/02/03/07/08/14) | integration (tdd) | `uv run pytest tests/test_attachments_upload_route.py -x -v` | ⬜ pending |
| 03-T3 | 03 | 2 | GET raw / DELETE + _messages_to_response additional_kwargs | FIN-01/02 (D-07/22/23) | integration (tdd) | `uv run pytest tests/test_attachments_upload_route.py tests/test_attachments_get_delete_route.py tests/test_chat_history_additional_kwargs_api.py tests/test_api_chat.py -x -v` | ⬜ pending |
| 04-T1 | 04 | 3 | worker.process_chat attachments payload | FIN-01/02 (D-14) | unit (tdd) | `uv run pytest tests/test_worker_attachments_payload.py -x -v` | ⬜ pending |
| 04-T2 | 04 | 3 | LangGraphHandler _prepare_messages_input + D-18 vision drop | FIN-01/02 (D-10/14/18) | unit (tdd) | `uv run pytest tests/test_langgraph_handler_attachments_v2.py tests/test_langgraph_handler.py tests/test_langgraph_handler_attachments.py -x -v` | ⬜ pending |
| 04-T3 | 04 | 3 | OrchestratorHandler _prepare_new_attachments + AgentState.new_attachments | FIN-02 (D-14/18/20) | unit (tdd) | `uv run pytest tests/test_orchestrator_handler_attachments.py -x -v` | ⬜ pending |
| 05-T1 | 05 | 4 | types.ts + client.ts (AttachmentMeta / postAttachments / deleteAttachment) | FIN-01/02 (D-14) | type-check + Plan 07 runtime | `cd frontend && bun tsc --noEmit` | ⬜ pending |
| 05-T2 | 05 | 4 | useAttachments hook + AttachmentButton / AttachmentChips + theme.css | FIN-01/02 (D-03/04/05/06/14/19) | type-check + Plan 07 runtime | `cd frontend && bun tsc --noEmit` | ⬜ pending |
| 05-T3 | 05 | 4 | ChatApp drop+paste listener + InputBar slot wiring | FIN-01/02 (D-04) | type-check + Plan 07 runtime | `cd frontend && bun tsc --noEmit` | ⬜ pending |
| 06-T1 | 06 | 5 | useModels + client.getModels + Header 🖼 select | FIN-02 (D-16) | type-check + Plan 07 runtime | `cd frontend && bun tsc --noEmit` | ⬜ pending |
| 06-T2 | 06 | 5 | VisionWarningBanner + InputBar warningSlot + ChatApp wiring | FIN-02 (D-17/18) | type-check + Plan 07 runtime | `cd frontend && bun tsc --noEmit` | ⬜ pending |
| 06-T3a | 06 | 5 | useChat.sendMessage payload attachments + clearAll 契約 (D-06) | FIN-01/02 (D-06/14) | type-check + Plan 07 runtime | `cd frontend && bun tsc --noEmit` | ⬜ pending |
| 06-T3b | 06 | 5 | ChatMessage.additional_kwargs + MessageArea bubble AttachmentChipRow (D-21) | FIN-01/02 (D-21/22) | type-check + Plan 07 runtime | `cd frontend && bun tsc --noEmit` | ⬜ pending |
| 06-T3c | 06 | 5 | ChatApp staging clear + banner/chips 配線 (D-06 4 ケース) | FIN-01/02 (D-06) | type-check + Plan 07 runtime | `cd frontend && bun tsc --noEmit` | ⬜ pending |
| 07-T1 | 07 | 6 | docker compose + Chrome DevTools MCP E2E 6 シナリオ (checkpoint) | FIN-01/02 Success 1-4 + D-06/17 | manual + MCP | `docs/phase-36-integration-check.md` Overall Verdict: PASS | ⬜ pending |
| 07-T2 | 07 | 6 | ADR-0050 起票 + adr-categories.yaml 更新 | FIN-01/02 | automated | `ls docs/adr/0050-*.md && grep -c "0050" .planning/adr-categories.yaml docs/adr/INDEX.md` | ⬜ pending |
| 07-T3 | 07 | 6 | patterns.md 3 エントリ追記 + VERIFICATION.md | FIN-01/02 | automated | `grep -c "additional_kwargs サイドカー\|Vision / model capability fallback\|3 入り口統一 staging" .planning/patterns.md && ls .planning/phases/36-text-code-image-multimodal/36-VERIFICATION.md` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Nyquist Sampling Continuity (8c) 成立根拠:**
- Plan 01-04 (backend): 各 task に pytest automated コマンドあり、連続 2 task 以上の自動 verify 欠如なし
- Plan 05-06 (frontend): 各 task の `bun tsc --noEmit` は型サンプリング。runtime behavior は Plan 07 の Chrome DevTools MCP integration check が 6 シナリオで full sampling することで Wave 6 で連続性を回復する（Wave 4/5 の成果物を Wave 6 が必ず sampling する構造）
- Plan 07 は Wave 4/5 の runtime behavior を E2E で検証する明示的な Nyquist recovery wave として機能

---

## Wave 0 Requirements

- [ ] **A1 Risk 検証** — `HumanMessage.additional_kwargs["attachments"]` が LangGraph `add_messages` reducer + checkpointer で round-trip 保存できる（Plan 01 Task 1、MemorySaver で検証、実 DB は Plan 01 Task 3 の docker compose spike で担保）
- [ ] **SDK 契約固定** — `copilot.FileAttachment` TypedDict / `CopilotSession.send_and_wait(attachments=...)` kwarg / `ModelInfo` dataclass / SDK 隔離原則の 4 契約を `inspect.signature` + import 静的チェックで固定（Plan 01 Task 2）
- [ ] **SDK subprocess 実機スパイク** — `session.send_and_wait(attachments=[FileAttachment(...)])` を docker compose worker で実機 PASS（Plan 01 Task 3, `docs/phase-36-sdk-spike-note.md` Verdict: PASS 必須）
- [ ] **既存フィクスチャ流用** — Phase 37 の `/shared/thread-files/` fixture + realpath guard test を流用（Plan 03 Task 2/3）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ctrl+V paste 画像添付 UX | FIN-02 | ブラウザ clipboard API は jsdom / playwright でも不安定 | 実ブラウザで画像を paste → チップ表示 → 送信 → LLM 応答を確認（Plan 07 シナリオ 2） |
| Drag & Drop 添付 UX | FIN-01/02 | DataTransfer イベントは実 OS ドラッグ相当の再現が難しい | 実ブラウザで OS ファイラからドロップ → チップ表示 → 送信（Plan 07 シナリオ 1/2） |
| vision 非対応モデルでのバナー + ワンクリック切替 | FIN-02 (success criteria 3) | モデル切替後の state 更新タイミングが UI 実機で確認必要 | gpt-4.1 選択中に画像添付 → 警告バナー → `[切り替える]` → claude-sonnet-4.6 へ変更 → バナー消失（Plan 07 シナリオ D-17） |
| スレッド再オープン時の添付チップ表示 | success criteria 4 | PostgreSQL checkpointer round-trip を実 DB で確認 | 画像添付メッセージ送信 → ブラウザリロード → MessageArea bubble にチップが残る（Plan 07 シナリオ 4） |
| モバイル幅 (≤767px) での破綻ゼロ | Phase 35 D-05 継承 | 実デバイス / responsive 表示での視覚確認 | iPhone SE 幅 (375px) で drop zone・paste・チップが最低限動く（Plan 07 で確認、非 blocker） |

---

## Dimension 8 Runtime Behavior Verification Strategy

**背景:** Plan 05 / Plan 06 の frontend task (計 6 task, 分割後) は `bun tsc --noEmit` を automated verify とし、runtime behavior の単体テストを持たない。これは以下の理由による:

1. **vitest / React Testing Library 導入は Phase 36 scope 外** — 新規依存追加を避け、Phase 37 以降 / v6.1+ で frontend テスト基盤整備を検討する（Claude's Discretion 範囲）
2. **frontend 単体挙動 (hook / component interaction) は E2E で確認するほうが価値が高い** — drag & drop / clipboard API / iframe / chatscope ライブラリの挙動は jsdom 再現が不完全なため、実ブラウザでの integration check が Nyquist 有効サンプリング

**対応方針:** Plan 07 の Chrome DevTools MCP integration check を **Dimension 8 (runtime behavior verification) の正式根拠** として扱う。具体的には:

- `useAttachments` の 3 入り口 (click/drop/paste) → Plan 07 シナリオ 1/2 + シナリオ D-06 で sampling
- `VisionWarningBanner` → Plan 07 シナリオ 3 + シナリオ D-17 で sampling
- `useModels` TTL cache + Header 🖼 絵文字 → Plan 07 シナリオ 2/3 で sampling
- `AttachmentChipRow` (bubble 内チップ / D-21) → Plan 07 シナリオ 4 で sampling
- `useChat.sendMessage` attachments payload + D-06 clearAll 契約 → Plan 07 全シナリオ共通で sampling

**Nyquist Sampling Continuity (8c) 成立:** Wave 4 (Plan 05) + Wave 5 (Plan 06) の成果物は Wave 6 (Plan 07) で必ず実機サンプリングされるため、「3 連続 task に自動 verify 欠如」の状態は Wave 6 で回復する。Wave 6 は Wave 4/5 の runtime behavior を E2E で検証する明示的な recovery wave として機能する。

**Fail-safe:** Plan 07 integration check が FAIL した場合、`/gsd-plan-phase --gaps` で gap closure plan を起票し Wave 4/5 の runtime behavior を修正する。これにより Plan 07 が実質的な runtime regression detection net になる。

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify OR Plan 07 integration check が Dimension 8 の正式根拠として明記されている
- [x] Sampling continuity: Plan 07 が Wave 4/5 成果物を sampling することで連続性を回復する構造が記述されている
- [x] Per-Task Verification Map が Plan 01-07 全 task で埋められている
- [ ] Wave 0 covers all MISSING references (A1 risk / SDK スパイク / multipart skeleton) — executor が Plan 01 完了後にチェック
- [ ] Feedback latency < 180 秒 — executor が Plan 01-04 完了後に実測
- [ ] No watch-mode flags — executor が全 task 実装後に `grep "bun.*--watch\|pytest.*--forked" -r` で確認

**Approval:** approved for execution (nyquist dimensions 1-11 verified at plan time; dimensions 12-14 verified post-execution)
