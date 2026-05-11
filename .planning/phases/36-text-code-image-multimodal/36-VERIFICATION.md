# Phase 36 — Verification

**Phase:** 36 (text/code + image multimodal)
**Requirements:** FIN-01, FIN-02
**Closed:** 2026-05-11

## Success Criteria Verdict (from ROADMAP.md)

| # | Criteria                                                                                                  | Status            | Evidence                                                                                                |
| - | --------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------- |
| 1 | ユーザーが .txt / .md / .json / .csv / .py / .js などの text/code 系ファイルを添付し、LLM がその内容を参照して応答できる | PASS              | `docs/phase-36-integration-check.md` シナリオ 1 + E2E-CHECKLIST.md A-1〜A-5                              |
| 2 | ユーザーが .png / .jpg / .webp 画像を添付でき、multimodal 対応モデルで画像内容を踏まえた応答を得られる    | PASS              | `docs/phase-36-integration-check.md` シナリオ 2 + E2E-CHECKLIST.md B-6〜B-8                             |
| 3 | multimodal 非対応モデルが選択されている場合、エラーで止まらず graceful にテキスト要約や警告にフォールバックする | PASS (caveat)     | `docs/phase-36-integration-check.md` シナリオ 3 + UI D-17 banner + worker D-18 SystemMessage 注入。Copilot SDK 0.2.0 catalog に non-vision モデルが存在しないため、フロントは fetch override で偽装テスト、バックエンドは `tests/test_langgraph_handler_attachments_v2.py::test_drop_images_for_non_vision_model` と code-read で挙動担保。 |
| 4 | 添付ファイルがチャット履歴 (PostgreSQL checkpointer) に紐付けされ、スレッドを再オープンしたときも添付情報を確認できる | PASS              | `docs/phase-36-integration-check.md` シナリオ 4 (F5 リロードで bubble チップ復元) + `tests/test_chat_history_additional_kwargs.py` round-trip 担保 |

## Test Coverage

| Plan          | Automated Tests                                                                                                                                                                                                                          | Manual Check                                                  |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| 01 (Wave 0)   | tests/test_chat_history_additional_kwargs.py (4) + tests/test_copilot_attachments_spike.py (4) = 8                                                                                                                                       | docs/phase-36-sdk-spike-note.md (docker compose spike, PASS) |
| 02            | tests/test_copilot_attachments.py (11) + tests/test_api_models_route.py (5) = 16                                                                                                                                                          | —                                                              |
| 03            | tests/test_attachments_upload_route.py (8) + tests/test_attachments_get_delete_route.py (8) + tests/test_chat_history_additional_kwargs_api.py (4) = 20                                                                                  | —                                                              |
| 04            | tests/test_worker_attachments_payload.py (3) + tests/test_langgraph_handler_attachments_v2.py (6) + tests/test_orchestrator_handler_attachments.py (4) = 13                                                                              | —                                                              |
| 05            | `bun tsc --noEmit` (型チェック PASS)                                                                                                                                                                                                       | docker compose で 📎 / drop / paste の 3 入り口手動確認        |
| 06            | `bun tsc --noEmit` (型チェック PASS)                                                                                                                                                                                                       | VisionWarningBanner + 履歴 bubble チップの視覚確認            |
| 07            | —                                                                                                                                                                                                                                          | docs/phase-36-integration-check.md PASS (Overall Verdict)     |

**Total automated tests added:** 57 (pytest) + `bun tsc --noEmit` (型チェック、frontend 全体)

## Open Issues Carried Forward to v6.1+

- **DebateChat handler の attachments 対応:** Phase 36 は CONTEXT.md Claude's Discretion (ChatApp 中心) に基づき `debate_handler.py` を未変更で v6.1 defer とした。DebateChat で画像/text 添付しても初回 user `HumanMessage` に `additional_kwargs.attachments` が載らない。v6.1 で同等の注入パターンを追加する。
- **SuperChat SubAgent 側 HumanMessage attachments 注入:** Phase 36 は `OrchestratorHandler` が `AgentState.new_attachments` に attachments を積むところまで配線。SubAgent 側 (`agent.py` / `tool_agent.py` の ReAct ループ) で `HumanMessage.additional_kwargs` として LLM 入力に載せる最終配線は v6.1 scope。SuperChat 経路で画像添付しても SubAgent が認識しない可能性あり。
- **Gem / Canvas の attachments UX:** InputBar 流用で自動継承の範囲まで。個別 UX 調整 (Gem Knowledge へのファイル取り込み等) は v6.1+。
- **Pillow サムネ生成:** 帯域問題発生時のみ Phase 39 polish で再検討（D-23）。
- **EXIF / メタデータサニタイズ:** v6.1+ 検討。
- **複数タブからの同時アップロード競合制御:** v6.1+ (`modified_at` 比較 / optimistic concurrency)。
- **OCR (vision 非対応モデル用テキスト抽出):** v6.1+ (MarkItDown + tesseract 検討)。
- **Section C — SDK catalog に non-vision モデルが追加されたら追補 real 実行:** Copilot SDK 0.2.0 では全 11 モデルが `vision: true`。SDK バージョンアップで non-vision モデルが追加された時点で `langgraph_handler._prepare_messages_input` の vision-drop パスを real model で再検証する。
- **📎 disabled 文言の polish:** `activeThreadId === null` 時の aria-label が「添付を追加できません（送信中）」になる軽微 UX 課題。`useAttachments.ts:90` 側には別文言 `'スレッドが未作成のため添付できません'` あり。Phase 39 polish 候補。
- **Pre-existing 14 件の test failures:** `test_api_chat.py` / `test_worker.py` / `test_graph.py` 系で Phase 36 起因ではない milestone debt。`deferred-items.md` 参照。

## Security Posture

- **ASVS L1 全カテゴリ該当項目 PASS:** V2 (Auth) / V3 (Session) / V4 (Access Control) / V5 (Input Validation) / V12 (File Upload)。
- **HIGH severity 脅威 mitigation:**
  - Path traversal (`storage_name` parameter): realpath prefix guard を `app/api/routes/attachments.py` で実装、unit test `tests/test_attachments_get_delete_route.py::test_path_traversal_rejected` で担保。
  - Cross-user access: JWT `github_login` で thread フォルダ階層を分離 (`/shared/thread-files/<login>/<thread_id>/`)。
  - Unauthenticated access: 全 attachments route が JWT cookie 必須 (`get_current_user` dependency)。
  - Image-size DoS: multipart upload で `Content-Length` 上限を api 層で 25 MB に制限。
- **監査ログ:** path traversal 試行は `logger.warning` で記録 (`attachments.py` + `chat.py::delete_thread`)。
- **Threat model coverage:** `36-PATTERNS.md` の STRIDE register と Plan 03 / Plan 05 の `<threat_model>` mitigation disposition は全て BLOCKING → mitigated。

## Related ADRs

- [0050](../../../docs/adr/0050-copilot-sdk-multimodal-attachments.md) — Phase 36 本 ADR (Copilot SDK 0.2.0 multimodal attachments)
- [0048](../../../docs/adr/0048-thread-files-folder-convention.md) — thread-files フォルダ規約（書き込み側 Phase 36 で完了、読取側 Phase 37）
- [0046](../../../docs/adr/0046-integration-check-surfaced-silent-failures.md) — integration check ゲート（Plan 07 で適用）
- [0038](../../../docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md) — AIMessage.name 喪失（A1 risk の先行例）
- [0025](../../../docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md) — SystemMessage 注入（D-18 base pattern）
- [0021](../../../docs/adr/0021-langgraph-bind-tools-toolnode-via-prompt-engineering.md) — bind_tools プロンプト注入（SDK 隔離原則の先行例）
- [0014](../../../docs/adr/0014-phase17-security-hardening-jwt-blocklist-redis-and-endpoint-auth.md) — JWT + endpoint auth

## Sign-off

- [x] All plans (01-07) complete
- [x] VALIDATION.md Wave 0 Requirements 全達成
- [x] ROADMAP.md §Phase 36 Success Criteria 1-4 PASS
- [x] Integration check (ADR-0046 gate) PASS — `docs/phase-36-integration-check.md`
- [x] ADR-0050 起票 + patterns.md 3 エントリ追記 (LangGraph・Graph 2 + Frontend・UI 1)
- [x] PROJECT.md "Current focus" 更新は Plan 07 完了後の orchestrator state サイクルで対応

**Phase 36 Closed.** Ready for next phase (Phase 32 / 38 等による v6.0 milestone 進行)。
