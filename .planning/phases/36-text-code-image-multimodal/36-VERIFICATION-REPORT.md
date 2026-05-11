---
phase: 36-text-code-image-multimodal
verified: 2026-05-11
status: passed
score: 4/4 must-haves verified
verifier: gsd-verifier (goal-backward audit)
note: |
  本書は人間記述の `36-VERIFICATION.md` (closing record) と別の verifier audit です。
  SUMMARY.md の主張ではなく、コードベース実態に対して goal-backward で確認しました。
---

# Phase 36 — Goal-backward Verification Audit

**Phase Goal (ROADMAP.md):** チャット入力欄からテキスト/コード系ファイルと画像を添付し、LLM がコンテキストとして参照できる基盤を確立する
**Requirements:** FIN-01 (text/code 添付), FIN-02 (画像添付 + multimodal + graceful fallback)
**Branch / HEAD:** `gsd/phase-36-text-code-image-multimodal` / `5f05b7d` (verifier execution time)
**Audit Date:** 2026-05-11

---

## Verdict per Success Criterion

### SC#1 — text/code 系ファイル添付 → LLM 参照応答 (FIN-01)

**Status:** PASS

**Evidence (route → worker → handler → provider → LLM → UI):**

| Layer       | File                                                       | Lines    | Verification                                                           |
| ----------- | ---------------------------------------------------------- | -------- | ---------------------------------------------------------------------- |
| API model   | `app/api/models.py`                                        | 52-55    | `ChatRequest.attachments: list[dict] \| None`                          |
| Upload route| `app/api/routes/attachments.py`                            | 103-169  | `POST /api/threads/{tid}/attachments` — multipart → /shared/thread-files |
| Chat route  | `app/api/routes/chat.py`                                   | 190-191  | `enqueue_job(..., attachments=body.attachments)`                       |
| Worker      | `app/jobs/worker.py`                                       | 146-194  | `process_chat(..., attachments=...)` → `job["attachments"]`            |
| Handler     | `app/jobs/handlers/langgraph_handler.py`                   | 105-155  | `_prepare_messages_input` → `HumanMessage(additional_kwargs=...)`      |
| Provider    | `app/providers/copilot.py`                                 | 394-437  | `_extract_attachments` — last HumanMessage → SDK FileAttachment list   |
| SDK call    | `app/providers/copilot.py`                                 | 188-192  | `session.send_and_wait(prompt, attachments=sdk_atts, ...)`             |
| History API | `app/api/routes/chat.py`                                   | 481-490  | `_messages_to_response` → `additional_kwargs.attachments` 公開         |
| UI staging  | `frontend/src/hooks/useAttachments.ts`                     | 87-134   | 3 入り口統一 upload hook (file picker / drop / paste)                  |
| UI render   | `frontend/src/components/MessageArea.tsx`                  | 52-90, 315-345 | `AttachmentChipRow` for history bubble (D-21)                    |
| Test (unit) | `tests/test_langgraph_handler_attachments_v2.py`           | 75-130   | `test_..._injects_additional_kwargs_text_files` PASS                   |
| Test (E2E)  | `36-E2E-CHECKLIST.md` A-1〜A-5                             | —        | 19/19 PASS (`meeting-notes.md` の Action Items 3 件が応答に verbatim) |
| Integration | `docs/phase-36-integration-check.md` scenario 1            | —        | PASS                                                                  |

End-to-end は完全に配線されており、unit + E2E + integration の三段階で担保されている。

---

### SC#2 — 画像添付 + vision 対応モデルで応答 (FIN-02)

**Status:** PASS

**Evidence (vision path):**

| Layer       | File                                                       | Lines    | Verification                                                           |
| ----------- | ---------------------------------------------------------- | -------- | ---------------------------------------------------------------------- |
| Provider    | `app/providers/copilot.py`                                 | 326-367  | `list_models()` → `vision: bool` を SDK ModelInfo から導出             |
| Provider    | `app/providers/copilot.py`                                 | 369-382  | `is_vision_model(model_id)` — fail-safe (例外時 False)                 |
| Models route| `app/api/routes/models.py`                                 | 32-59    | `GET /api/models` + TTL 1h cache                                        |
| Hook (UI)   | `frontend/src/hooks/useModels.ts`                          | 12-64    | TTL 1h client cache + `suggestedVisionModel` 計算                      |
| Hook (UI)   | `frontend/src/hooks/useAttachments.ts`                     | 32-85    | `vision_limits` pre-validate (D-19)                                    |
| Handler     | `app/jobs/handlers/langgraph_handler.py`                   | 125-154  | `vision_ok=True` 時は画像も `additional_kwargs.attachments` に乗せる   |
| GET raw     | `app/api/routes/attachments.py`                            | 172-194  | `GET /api/threads/{tid}/attachments/{name}` → inline 画像配信          |
| Test (unit) | `tests/test_langgraph_handler_attachments_v2.py`           | 156-170  | `test_..._vision_pass_on_vision_model` PASS                            |
| Test (E2E)  | `36-E2E-CHECKLIST.md` B-6〜B-8                             | —        | `red-square.png` → 「主な色は『赤』です」で色識別 (GPT-4.1)            |

vision モデル経路は real Copilot model (`gpt-4.1`, vision: true) で実機検証されている。

---

### SC#3 — vision 非対応モデルで graceful fallback (FIN-02)

**Status:** PASS (with caveat — 既に VERIFICATION.md / ADR-0050 に明示済み)

**Evidence (fallback path — 多段防御):**

| Layer       | File                                                       | Lines    | Verification                                                           |
| ----------- | ---------------------------------------------------------- | -------- | ---------------------------------------------------------------------- |
| UI banner   | `frontend/src/components/VisionWarningBanner.tsx`          | 1-87     | accent カラー (negative なし) + CTA + dismiss                          |
| UI wiring   | `frontend/src/components/ChatApp.tsx`                      | 100-115, 361-368 | `hasStagedImages` + `!currentModelInfo.vision` で表示制御         |
| Handler     | `app/jobs/handlers/langgraph_handler.py`                   | 130-149  | `vision_ok=False` で画像 drop + SystemMessage に「画像非対応モデル警告」追加 |
| Handler     | `app/jobs/handlers/orchestrator_handler.py`                | 31-64    | `_prepare_new_attachments` — defense-in-depth で画像 drop              |
| Provider    | `app/providers/copilot.py`                                 | 375-382  | `is_vision_model` fail-safe — SDK エラー時 False (画像を誤って送らない) |
| Test (unit) | `tests/test_langgraph_handler_attachments_v2.py`           | 132-153  | `test_..._vision_drop_on_non_vision_model` PASS                        |
| Test (unit) | `tests/test_orchestrator_handler_attachments.py`           | 74-91    | `test_..._vision_false_drops_images` PASS                              |
| Test (E2E)  | `36-E2E-CHECKLIST.md` C-9〜C-11                            | —        | fetch override で vision: false 偽装、banner + 送信成功確認            |

**Caveat:** Copilot SDK 0.2.0 catalog の全 11 モデルが `vision: true` のため、real な non-vision モデルで実機検証する経路が現存しない。VERIFICATION.md line 13、ADR-0050 line 85、integration check line 18 の三箇所で同じ caveat が明示されており、SDK catalog 拡張時の re-test を v6.1+ debt に持ち越し済 (VERIFICATION.md "Section C —" 項目)。

**Note on test naming drift:** VERIFICATION.md L13 と integration check L53 は `test_drop_images_for_non_vision_model` と書かれているが、実際の test 関数名は `test_langgraph_handler_vision_drop_on_non_vision_model` (v2 file L132)。ドキュメントの軽微な drift で機能影響なし。

---

### SC#4 — PostgreSQL checkpointer 永続化 / 履歴再オープン (D-20/D-21/D-22)

**Status:** PASS

**Evidence (additional_kwargs round-trip):**

| Layer       | File                                                       | Lines    | Verification                                                           |
| ----------- | ---------------------------------------------------------- | -------- | ---------------------------------------------------------------------- |
| Test (A1)   | `tests/test_chat_history_additional_kwargs.py`             | 1-164    | 4 テスト全て PASS — D-14 8 フィールド全部保持、空 / レガシー / 画像 |
| Test (API)  | `tests/test_chat_history_additional_kwargs_api.py`         | 12-46    | `_messages_to_response` ロジック単体検証                                |
| History API | `app/api/routes/chat.py`                                   | 481-490  | None-guard 付き `additional_kwargs.attachments` を public_kw に公開    |
| UI bubble   | `frontend/src/components/MessageArea.tsx`                  | 52-90    | `AttachmentChipRow` 画像サムネ URL = GET raw route                     |
| UI bubble   | `frontend/src/components/MessageArea.tsx`                  | 315-345, 408-415 | user / AI 両側で `msg.additional_kwargs?.attachments` 描画       |
| Test (E2E)  | `36-E2E-CHECKLIST.md` D-12〜D-14                           | —        | スレッド切替 → 再オープン + F5 リロードで chip / thumb 復元            |

**Note on test scope:** `test_chat_history_additional_kwargs.py` は MemorySaver で round-trip を検証している (line 7-12 で明示)。AsyncPostgresSaver 実機 round-trip は (a) Wave 0 Plan 01 Task 3 の docker compose SDK spike (`docs/phase-36-sdk-spike-note.md`)、(b) Plan 07 integration check の D-12〜D-14 (F5 リロードで実機 PostgreSQL 経由 chip 復元) で担保。`add_messages` reducer + checkpointer の serialize 挙動は MemorySaver と AsyncPostgresSaver で共通実装のため、unit test と integration check の組み合わせで実態の round-trip が confirm されている。

---

## Implementation Completeness Map (FIN-01 + FIN-02)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FIN-01 (text/code) と FIN-02 (image) を ChatApp で end-to-end 配線済     │
├─────────────────────────────────────────────────────────────────────────┤
│ Frontend (ChatApp)                                                       │
│   useAttachments.ts (file picker / drop / paste 3 入り口統一)             │
│   useModels.ts       (TTL 1h cache + suggestedVisionModel)                │
│   useChat.ts         (sendMessage payload に attachments を載せる)        │
│   AttachmentButton   (📎)                                                 │
│   AttachmentChips    (staging)                                            │
│   VisionWarningBanner (非 vision モデル時の警告 + CTA)                    │
│   InputBar.warningSlot                                                    │
│   MessageArea.AttachmentChipRow (履歴 bubble 内 chip + サムネ)            │
│                                                                           │
│ API                                                                       │
│   POST /api/threads/{tid}/attachments  → multipart upload                 │
│   GET  /api/threads/{tid}/attachments/{name} → raw inline 配信            │
│   DELETE /api/threads/{tid}/attachments/{name} → 単一削除                 │
│   GET  /api/models  → list_models + TTL 1h cache                          │
│   POST /api/chat    → ChatRequest.attachments を worker に forward         │
│   GET  /api/threads/{tid}/messages → additional_kwargs.attachments 返却   │
│                                                                           │
│ Worker / Handler                                                          │
│   worker.process_chat        (attachments kwarg)                          │
│   LangGraphHandler           (_prepare_messages_input — Chat / Canvas)    │
│   OrchestratorHandler        (_prepare_new_attachments — SuperChat 部分配線) │
│   DebateHandler              (未変更 — v6.1 defer)                        │
│                                                                           │
│ Provider                                                                  │
│   ChatCopilot._extract_attachments  (additional_kwargs → SDK FileAttachment) │
│   ChatCopilot.list_models           (ModelInfo → dict, vision 含む)       │
│   ChatCopilot.is_vision_model       (fail-safe judgment)                  │
│                                                                           │
│ Persistence                                                               │
│   HumanMessage.additional_kwargs["attachments"] → add_messages reducer →  │
│   AsyncPostgresSaver JSONB checkpoint → 履歴再オープン時に bubble 復元    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Coverage by app:**

| App        | text/code 添付 | 画像添付 (vision) | 履歴復元 | Notes                                       |
| ---------- | -------------- | ----------------- | -------- | ------------------------------------------- |
| ChatApp    | OK             | OK                | OK       | Plan 05/06 で完全配線                       |
| Canvas     | OK             | OK                | OK       | ChatApp 経路 (build_canvas_graph) を共有     |
| SuperChat  | partial        | partial           | partial  | `_prepare_new_attachments` で AgentState.new_attachments まで; SubAgent 側 HumanMessage 注入は v6.1 defer (ADR-0050 / VERIFICATION.md / 設計コメント orchestrator_handler.py L41 に明示) |
| Gem        | OK             | OK                | OK       | ChatApp 内で gem_id 指定経路、InputBar 共有 |
| DebateChat | 未対応         | 未対応            | 未対応   | `debate_handler.py` は attachments 未触 — v6.1 defer (VERIFICATION.md / ADR-0050 に明示) |

---

## Tests Verification

実行結果 (5月11日, verifier session):

```
tests/test_chat_history_additional_kwargs.py  ........ 4 passed
tests/test_copilot_attachments_spike.py        ........ 4 passed
tests/test_copilot_attachments.py              ........ 11 passed
tests/test_api_models_route.py                 ........ 5 passed
tests/test_attachments_upload_route.py         ........ 8 passed
tests/test_attachments_get_delete_route.py     ........ 8 passed
tests/test_chat_history_additional_kwargs_api.py ...... 4 passed
tests/test_worker_attachments_payload.py       ........ 3 passed
tests/test_langgraph_handler_attachments_v2.py ........ 6 passed
tests/test_orchestrator_handler_attachments.py ........ 4 passed
──────────────────────────────────────────────────────────────
Total: 57 passed                              VERIFICATION.md 主張 57 と一致
```

**A1 risk closure (`tests/test_chat_history_additional_kwargs.py`):** 確認。4 テストで (1) D-14 8-field round-trip、(2) 空 dict、(3) legacy 未指定、(4) 画像 attachment 8 フィールド全部保持 を担保。実 DB は Wave 0 Plan 01 Task 3 の docker compose spike + Plan 07 E2E D-12〜D-14 (F5 リロードで実機 PostgreSQL round-trip) で担保。

**SDK isolation regression guard (`tests/test_copilot_attachments_spike.py::test_sdk_imports_isolated_to_provider`):** 確認。AST grep で `from copilot` / `import copilot` を 1 ファイルに限定 (`app/providers/copilot.py`)。verifier 側でも `grep -rn "from copilot" app/ --include="*.py"` を独立に実行して、`app/providers/copilot.py:36` と `:43` の 2 行のみであることを confirm。

---

## Open Issues Carried Forward to v6.1+

**全て VERIFICATION.md / ADR-0050 / E2E-CHECKLIST §G で明示済の項目です。verifier として再列挙して honest 性を確認:**

| 項目                                                       | 文書化箇所                                                         | Status      |
| ---------------------------------------------------------- | ------------------------------------------------------------------ | ----------- |
| SuperChat SubAgent HumanMessage attachments 注入            | VERIFICATION L33, ADR-0050 L84, orchestrator_handler.py L41 設計コメント, test L13-14 | 明示済 OK   |
| DebateChat handler attachments 対応                         | VERIFICATION L32, ADR-0050 L95, E2E §G                             | 明示済 OK   |
| OCR (vision 非対応モデル用テキスト抽出)                   | VERIFICATION L38, ADR-0050 L104                                    | 明示済 OK   |
| EXIF / メタデータサニタイズ                                 | VERIFICATION L36, ADR-0050 L104                                    | 明示済 OK   |
| Pillow サムネ生成                                           | VERIFICATION L35, ADR-0050 L103, D-23                              | 明示済 OK (Phase 39 polish 検討) |
| 複数タブ同時アップロード競合制御                            | VERIFICATION L37, ADR-0050 L104                                    | 明示済 OK   |
| SDK catalog に non-vision モデル追加時の追補 real 実行      | VERIFICATION L39, ADR-0050 L85, integration check L29              | 明示済 OK   |
| 📎 disabled 文言 polish                                     | VERIFICATION L40, E2E L148                                         | 明示済 OK (軽微 UX) |
| Pre-existing 14 件 test failures + 4 errors                 | VERIFICATION L41, deferred-items.md                                | 明示済 OK (milestone debt; Phase 36 起因ではないことを git stash 再現で確認済) |
| Gem / Canvas attachments UX 個別最適化                     | VERIFICATION L34, ADR-0050 L105                                    | 明示済 OK   |

honest 性 verdict: **PASS** — 残件 10 項目すべてが少なくとも 1 つの正式ドキュメントに carry-forward されており、暗黙的にスキップされた項目は検出されなかった。

---

## Drift Between VERIFICATION.md Claims and Actual Codebase

verifier の独立確認で発見した軽微な drift:

| Item                                                       | Claim                                                      | Actual                                                         | Severity     |
| ---------------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------- | ------------ |
| Vision-drop test 名                                         | VERIFICATION.md L13 + integration check L53 で `test_drop_images_for_non_vision_model` | 実際は `test_langgraph_handler_vision_drop_on_non_vision_model` (v2 L132) | trivial (cosmetic, 機能影響なし) |
| Vision emoji 表記                                           | UI-SPEC や チェックリスト spec で 👁️                       | 実装は 🖼 (combobox aria-label に「画像対応」明記)              | trivial (E2E チェックリストで「同等機能 PASS」と判定済) |
| paste の対象                                                | E2E チェックリスト元仕様で「ファイル/画像」                | 実装は image/* のみ paste (ChatApp.tsx onPaste で type filter) | by design (E2E メモで「仕様内」と確認済、v6.0 では明示 image only) |

これらは VERIFICATION.md と integration check 内で既に「同等機能 PASS」「仕様内」と注釈されている。BLOCKER / WARNING 級の drift は検出されなかった。

---

## Overall Phase Verdict

**PASS — Phase 36 は ROADMAP.md §Phase 36 Success Criteria 1〜4 を実コードで満たしている。**

- Goal-backward: SC#1〜#4 の全 4 経路で route → worker → handler → provider → SDK → UI の全層配線をコードで確認。
- Evidence quality: 57 unit tests + E2E 19/19 PASS + integration check 6 シナリオ PASS の三段検証は文書主張と完全一致 (テスト件数 57 を verifier 側でも独立に再カウント・実行確認)。
- Honesty: 10 件の deferred 項目すべてが VERIFICATION.md / ADR-0050 / E2E §G に carry-forward されている。
- A1 risk: `tests/test_chat_history_additional_kwargs.py` が 4 テストで round-trip を担保、実 DB round-trip は spike + E2E F5 リロードで補完。
- SDK isolation: `test_sdk_imports_isolated_to_provider` が AST grep regression guard として present、verifier 独立 grep でも 2 行のみを confirm。

**Recommend:** Phase 36 をクローズし、v6.0 milestone の次フェーズ (Phase 32 / 38 等) に進めるべき。SuperChat SubAgent / DebateChat / OCR / EXIF 等は v6.1+ の正式 plan で扱う。

---

*Audit completed: 2026-05-11 by gsd-verifier (goal-backward sanity audit, distinct from human-written 36-VERIFICATION.md closing record)*
