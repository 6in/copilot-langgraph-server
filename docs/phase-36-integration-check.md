# Phase 36 Integration Check

**Date:** 2026-05-11
**Executor:** GitHub `6in` (with Claude Code)
**Branch:** `gsd/phase-36-text-code-image-multimodal` (HEAD `917e244` at execution time)
**Environment:** docker compose (api / worker / frontend / postgres / redis / mcp-server 全 Up) + Chromium 147 + chrome-devtools MCP
**Source of truth for raw evidence:** `.planning/phases/36-text-code-image-multimodal/36-E2E-CHECKLIST.md` (19 / 19 PASS)

> 本書は ADR-0046 の "Integration check gate" 規約に従い、docker compose 実機での Phase 36 Success Criteria 1〜4 確認結果を記録する。Plan 01〜06 で導入した変更が unit test green の裏で silent failure していないことを surface するゲート。
> 各シナリオの詳細な観察（ファイル名・サイズ・応答抜粋・Network log など）は `36-E2E-CHECKLIST.md` の該当行を一次ソースとし、本書では verdict と要約を残す。

## Verdict

| # | Criteria                                                       | Result | Notes                                                                                                                                                                            |
| - | -------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | FIN-01 text/code 添付 → LLM 参照応答 (Success Criteria #1)     | PASS   | E2E A-1〜A-5。モデル: GPT-4.1。添付 `meeting-notes.md` (489 B) 等の `.md` を送信 → LLM 応答に Action Items 3 件 (Alice/Bob/Carol) が verbatim で出力された (A-3)。📎 ボタン / drag-drop overlay / image paste の 3 入り口すべて staging 成功。 |
| 2 | FIN-02 画像 + vision 対応モデル (Success Criteria #2)         | PASS   | E2E B-6〜B-8。モデル: `gpt-4.1` (`GPT-4.1 🖼` — Copilot SDK 0.2.0 catalog では vision: true)。`red-square.png` (334 B 純赤) 添付 → 応答「主な色は「赤」です。」で色識別。48×48 サムネ chip 表示 + × 削除 OK。 |
| 3 | FIN-02 画像 + vision 非対応 graceful fallback (Success Criteria #3) | PASS (with caveat) | E2E C-9〜C-11。Copilot SDK 0.2.0 が返す 11 モデル全てが `vision: true` のため、フロント検証は fetch override で 1 モデルを `vision: false` に偽装して実施。`VisionWarningBanner` 表示 + CTA + 送信成功 + エラー無し応答を確認。**バックエンド image-drop + SystemMessage 警告注入** (`langgraph_handler._prepare_messages_input` の `vision_ok=False` 分岐) はコード読みで仕様一致を確認 — 真の vision-false モデルが SDK catalog 上に存在しないため real 実行は未検証。 |
| 4 | D-20 履歴チップ F5 復元 (Success Criteria #4)                  | PASS   | E2E D-12〜D-14。thread `86e47e9b` ↔ `b7b1403e` 切替 + F5 リロード後すべての履歴 bubble で `📄 meeting-notes.md` chip / `red-square.png` / `blue-square.png` 画像 thumbnail が復元描画 (`additional_kwargs.attachments` round-trip 成功)。staging 中 × ボタン (`delete-test.md`) → `DELETE /api/threads/.../attachments/...` 発火、同時に既存 history bubble は残存。 |
| 5 | D-17 VisionWarningBanner ワンクリック切替                       | PASS   | E2E B/C で確認。banner 文言: ⚠ 「画像非対応モデル — 現在のモデル（GPT-4.1 [TEST-NOVIS]）は画像を読めません。画像対応モデル（例: Claude Sonnet 4.6）に切り替えると画像付きで送信できます。」+ CTA「Claude Sonnet 4.6 に切り替える」+ ×「この案内を閉じる」。 |
| 6 | D-06 ケース D 単一ファイル × 削除 + サーバー削除                 | PASS   | E2E D-14。staging chip の × ボタン → `DELETE /api/threads/{tid}/attachments/20260511T032142_delete-test.md` 発火確認、UI から chip 消失、同時に既存 history bubble (chip + img thumbnails) は残存 (削除と履歴の独立を確認)。 |

## Observed Issues (carry-forward, non-blocking)

1. **📎 disabled 文言が誤解を招く** — `activeThreadId === null` のときも aria-label が「添付を追加できません（送信中）」になる (`AttachmentButton.tsx:45`)。同条件で `useAttachments.ts:90` には別文言 `'スレッドが未作成のため添付できません'` がある。軽微 UX、Plan 07 後の polish phase 候補。
2. **paste は image 専用** — `ChatApp.tsx:147` の `item.type.startsWith('image/')` でフィルタ。チェックリスト表記「ファイル/画像」に対し実装は image のみ。**仕様内** (v6.0 では明示的に image paste のみ対応、D-19 補足)。
3. **vision indicator emoji 表記差** — 仕様 👁️ / 実装 🖼。combobox aria-label に「画像対応 / 画像非対応」と明記されているため同等機能。
4. **Header banner はテーマ非追従** — `rgb(36,41,46)` 固定 (design choice)。本 phase 検証対象 (AttachmentChips / VisionWarningBanner / drop overlay) は CSS vars のみで両モード可読。
5. **Section C 非 vision モデル不在** — Copilot SDK 0.2.0 が返す 11 モデル全てが `vision: true` のため real な non-vision モデルが手元になく、フロント側はモック、バックエンド image-drop はコード読みで確認。SDK catalog に non-vision モデルが追加された時点で real 実行する追補テストを v6.1+ に残す。

## docker compose log snippets

### Worker への `additional_kwargs={"attachments": [...]}` 注入確認 (シナリオ 1 — text/code)

E2E A-3 で `meeting-notes.md` 添付 + AI 応答に Action Items 3 件が verbatim で出現したことから、`HumanMessage.additional_kwargs["attachments"]` が:

1. `POST /api/threads/{tid}/attachments` → API
2. `POST /api/chat` → `new_attachments` job payload
3. worker `process_chat` → `AgentState.new_attachments`
4. `langgraph_handler._prepare_messages_input` → `HumanMessage(content=..., additional_kwargs={"attachments": [...]})`
5. `ChatCopilot._extract_attachments` → SDK `FileAttachment` list
6. Copilot SDK `send_and_wait(attachments=[...])` → 応答

の 6 層配管が間接的に PASS と判定できる（最終 LLM 出力に file 内容が verbatim で含まれているため）。

### SystemMessage 警告注入確認 (シナリオ 3 — vision 非対応 graceful fallback)

real な non-vision モデルが SDK catalog に存在しないため、`docker compose logs worker` 上での実行ログ取得は不可。代わりに `app/jobs/handlers/langgraph_handler.py::_prepare_messages_input` の以下分岐をコード読みで確認:

- `vision_ok=False` の場合は `image_atts` を attachments list から drop (`additional_kwargs["attachments"]` 上書き)
- 同時に `SystemMessage` 末尾に「画像非対応モデル警告 — 添付された画像は無視されました。画像対応モデルへの切替を案内してください。」相当の prompt 追加 (D-18, ADR-0025 base pattern)

unit test `tests/test_langgraph_handler_attachments_v2.py::test_drop_images_for_non_vision_model` がこの分岐の挙動を担保している。real model での実行は SDK 側に non-vision モデルが追加されたタイミングで追補確認する。

## Overall Verdict

**PASS** — 6 シナリオ全 PASS。Phase 36 Success Criteria 1〜4 を docker compose 実機で confirm 済み（criteria #3 の vision-false パスのみ real model 不在のため "code-read confirmed" caveat あり、unit test で挙動担保）。

## Open Issues Carried Forward

E2E-CHECKLIST.md §G より転記:

- **SuperChat SubAgent 側で `state["new_attachments"]` を HumanMessage 展開** → v6.1 defer。OrchestratorHandler が `AgentState.new_attachments` に attachments を積むところまで配線済だが、SubAgent (`agent.py` / `tool_agent.py` の ReAct ループ) で `HumanMessage.additional_kwargs` として LLM 入力に載せる最終配線が未着手。SuperChat 経路で画像添付しても SubAgent が認識しない可能性あり。
- **DebateChat handler の attachments 対応** → v6.1 defer。`debate_handler.py` 未変更 (CONTEXT.md Claude's Discretion により ChatApp 中心の scope と判断)。
- **Gem / Canvas の attachments UX** → InputBar 流用で自動継承の範囲まで。個別 UX 調整は v6.1+。
- **pre-existing 14 件の test failures** (`test_api_chat.py` / `test_worker.py` / `test_graph.py` 系) → milestone debt。Phase 36 起因ではなく、`.planning/phases/36-text-code-image-multimodal/deferred-items.md` 参照。
- **Pillow サムネ生成** → 帯域問題発生時のみ Phase 39 polish で再検討 (D-23)。
- **EXIF / メタデータサニタイズ** → v6.1+。
- **複数タブからの同時アップロード競合制御** → v6.1+ (`modified_at` 比較 / optimistic concurrency)。
- **OCR (vision 非対応モデル用テキスト抽出)** → v6.1+ (MarkItDown + tesseract 検討)。
- **Section C で SDK catalog に non-vision モデルが追加されたら追補 real 実行** → SDK バージョンアップ時の確認項目。

---

*Phase 36 Closed.* Plan 07 (Wave 6) executor が本書を `36-VERIFICATION.md` の `human_verification` 結果として参照する。
