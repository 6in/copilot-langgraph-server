# 0050. Copilot SDK 0.2.0 multimodal attachments の採用と SDK 隔離原則

**Status:** Accepted
**Date:** 2026-05-11
**Phase:** 36 — text/code + image multimodal
**Supersedes:** なし
**Related ADRs:** [0048](0048-thread-files-folder-convention.md) (thread-files フォルダ規約 / 読取側), [0038](0038-superchat-context-messages-and-agent-name-persistence.md) (AIMessage.name 喪失 / 類似 A1 risk の先行例), [0025](0025-datetime-and-user-context-injection-into-agent-prompts.md) (SystemMessage 注入 / D-18 base pattern), [0046](0046-integration-check-surfaced-silent-failures.md) (integration check ゲート), [0021](0021-langgraph-bind-tools-toolnode-via-prompt-engineering.md) (bind_tools プロンプト注入 / LangChain 層 bypass の先行例)

## Context

Phase 36 では v6.0 milestone FIN-01 / FIN-02 を満たすため、Chat アプリから text/code ファイルと画像を添付し、Copilot SDK 0.2.0 の multimodal モデル (Claude Sonnet 4.5+ / 4.6) に渡せる基盤を整備する必要があった。

制約と選択肢:

- Copilot SDK 0.2.0 は `FileAttachment` / `BlobAttachment` TypedDict と `CopilotSession.send_and_wait(attachments=[...])` kwarg で native multimodal を提供（Technical Preview）。
- LangChain の structured multimodal content parts (`[{"type": "text"}, {"type": "image_url"}]`) は text ファイル型が未定義で SDK 互換性なし。
- 過去 ADR-0038 で `AIMessage.name` が LangGraph checkpointer の (de)serialize で喪失する既知問題あり — `additional_kwargs` 経路の round-trip も事前検証必須（A1 risk）。
- Phase 37 が `/shared/thread-files/<login>/<thread_id>/` フォルダ規約（ADR-0048）を読取側 (MCP `attachments_list` / `attachments_extract`) で先行整備済。Phase 36 がその書き込み側（POST/GET/DELETE REST + delete_thread フック）を埋める責務。
- SDK は Technical Preview で外部インターフェースを薄いラッパーで隔離する原則（PROJECT.md L14 / Phase 37 D-17 継承）。

## Decision

### 1. FileAttachment + path-based 渡しを採用 (D-09)

`session.send_and_wait(prompt, attachments=[{"type": "file", "path": ..., "displayName": ...}])` を text/code・画像の両方に使う。`BlobAttachment` (base64 inline) は checkpoint JSONB 肥大を避けるため本 phase では未採用。path 渡しなら worker コンテナの RO mount (`/shared/thread-files`) 経由で SDK subprocess が直接 `open()` できる（Assumption A3 — Phase 36 Wave 0 で実機確認済、`docs/phase-36-sdk-spike-note.md`）。

### 2. HumanMessage.additional_kwargs["attachments"] サイドカー envelope (D-10/D-14/D-15)

per-turn 添付情報を `HumanMessage.additional_kwargs["attachments"]: list[D-14 dict]` で運ぶ。LangGraph `add_messages` reducer と PostgreSQL checkpointer が `BaseMessage` 全体を JSONB シリアライズするため、追加 state フィールドを作らずに透過的に永続化される。D-14 統一 dict スキーマ:

```python
{
    "kind": "text" | "image",
    "name": "<displayName>",
    "storage_name": "<YYYYMMDDTHHMMSS_<original>.<ext>>",
    "path": "/shared/thread-files/<login>/<thread_id>/<storage_name>",
    "size": <bytes>,
    "mime_type": "<mime>",
    "ext": "<extension>",
    "modified_at": <epoch>,
}
```

を全層（REST body / job payload / state / history API / 将来の MCP ツール戻り値）で共有。

### 3. SDK 型の完全隔離 (D-09/D-10/D-15)

`copilot.*` のシンボル (`FileAttachment` / `BlobAttachment` / `ModelInfo`) の import は `app/providers/copilot.py` 内だけに閉じ、他モジュール（route / handler / frontend）は D-14 dict スキーマしか扱わない。ChatCopilot に以下 3 ヘルパーを追加し provider 境界で変換する:

- `_extract_attachments(messages) -> list[FileAttachment] | None` — 最後の `HumanMessage.additional_kwargs["attachments"]` を読み SDK 型に変換
- `list_models() -> list[dict]` — `ModelInfo` を JSON-serializable dict に変換、TTL 1h キャッシュ
- `is_vision_model(model_id) -> bool` — `ModelInfo.capabilities.supports.vision` を single source of truth として返す

`tests/test_copilot_attachments_spike.py::test_sdk_imports_isolated_to_provider` が SDK シンボルの out-of-bounds import を AST 走査で regression 検知する。

### 4. Vision 判定 / fallback の 2 段構造 (D-16/D-17/D-18/D-19)

- **UI 層 (D-17):** vision 非対応モデル選択中に画像を staging すると `<VisionWarningBanner>` を表示、CTA で `suggestedVisionModel` にワンクリック切替（graceful guidance）。
- **Worker 層 (D-18):** defense-in-depth として worker 側でも vision 再検証、非対応なら画像 attachment を `additional_kwargs["attachments"]` から drop + SystemMessage に「画像非対応モデル警告 — 添付された画像は無視されました。」相当を追加注入（ADR-0025 pattern 踏襲、enforcement）。
- **モデル情報の single source of truth:** `GET /api/models` が `list_models()` を TTL 1h キャッシュで提供（D-16）。hardcoded allowlist は作らず SDK 由来 `ModelInfo.capabilities.supports.vision` を唯一の判定源とする。新規モデル追加で UI 更新不要。

### 5. 履歴 UI は additional_kwargs を真実のソースとする (D-20/D-21/D-22/D-23)

`GET /api/threads/{tid}/messages` の返り値に `additional_kwargs.attachments` を含める（D-22 — `_messages_to_response` で None-guard 付き公開）。MessageArea bubble 内に `AttachmentChipRow` を描画し、画像は 48×48 サムネ (`<img src="/api/threads/{tid}/attachments/{name}">`、サムネ生成なし — D-23)、text は `[📄 name size]` pill で表示。フォルダ scan は「現在の手持ち」確認用に限定（Phase 37 pattern 踏襲）、真実は `additional_kwargs`。

### 6. A1 risk (additional_kwargs round-trip) を Wave 0 で先行検証

ADR-0038 の `AIMessage.name` 喪失問題と同系統のリスクを防ぐため、Phase 36 Wave 0 Plan 01 で `tests/test_chat_history_additional_kwargs.py` を作成し LangGraph MemorySaver + `add_messages` reducer で round-trip 保存できることを先に確認（4 tests pass）。加えて docker compose 実機での integration check（ADR-0046 gate, Plan 07 / `docs/phase-36-integration-check.md`）でも F5 リロード後の bubble チップ復元を確認。

## Consequences

**Positive:**

- FIN-01 / FIN-02 を満たしつつ、LangChain の multimodal 標準化を待たずに実装可能。
- SDK 隔離原則により SDK breaking change の影響範囲を `app/providers/copilot.py` の中に閉じる（ADR-0021 と同方針）。
- `additional_kwargs` サイドカー方式は per-message metadata を保持する汎用 pattern として v6.1+ の他機能（トークン使用量・引用・tool_call_id 等）にも応用可能。
- vision 判定の single source of truth 化により、モデル追加時の UI 更新が不要。
- Phase 37 のフォルダ規約（ADR-0048）と接続済み — 書き込み (Phase 36) / 読取 (Phase 37 MCP ツール) / 削除 (Phase 37 delete hook) のライフサイクルが完結。

**Negative:**

- `BlobAttachment` を採用していないので subprocess が path を `open()` できる前提を要求 — Copilot SDK Technical Preview のバージョンアップで subprocess architecture が変わると見直しが必要。
- TTL 1h キャッシュのため、新規モデル追加時に frontend の反映が最大 1 時間遅延する（社内 200 名規模では許容）。
- SuperChat / Gem / Canvas / Debate の 4 アプリで完全対応したのは ChatApp 中心のみ。SubAgent 側の HumanMessage 組み立てへの attachments 伝搬は v6.1 検討事項として VERIFICATION.md に残件計上（D-23 Claude's Discretion）。
- 画像 vision-false モデルが Copilot SDK 0.2.0 catalog 上に存在しないため、`langgraph_handler._prepare_messages_input` の `vision_ok=False` ブランチは unit test + code-read で担保（real model 確認は SDK catalog 拡張待ち）。

**Neutral:**

- `GET /api/threads/{tid}/attachments/{name}` route が追加で発生するが、既存 `/api/me` や `/api/threads` 等と同じく JWT 認証下の内部 API。

## Implementation References

- **Provider:** `app/providers/copilot.py` — `_extract_attachments` / `list_models` / `is_vision_model` の 3 ヘルパー
- **REST:** `app/api/routes/attachments.py` (POST / GET / DELETE), `app/api/routes/models.py` (GET /api/models + TTL cache), `app/api/routes/chat.py::delete_thread` (folder cleanup)
- **Worker:** `app/jobs/worker.py` (`process_chat` 拡張 — `new_attachments` payload を `AgentState` に伝搬), `app/jobs/handlers/langgraph_handler.py::_prepare_messages_input` (HumanMessage 組み立て + vision drop + SystemMessage 警告注入), `app/jobs/handlers/orchestrator_handler.py::_prepare_new_attachments` (SuperChat 経路の attachments 積み), `app/jobs/handlers/debate_handler.py` (初回 user turn のみ — v6.1 で extend 予定)
- **Frontend:** `frontend/src/hooks/useAttachments.ts` (3 入り口統一 staging hook), `frontend/src/hooks/useModels.ts` (TTL cache + suggestedVisionModel), `frontend/src/components/AttachmentButton.tsx` / `AttachmentChips.tsx` / `VisionWarningBanner.tsx`, `frontend/src/components/InputBar.tsx` (warningSlot 追加), `frontend/src/components/MessageArea.tsx` (`AttachmentChipRow` + `type:'custom'` user bubble)
- **Tests:** `tests/test_copilot_attachments.py`, `tests/test_copilot_attachments_spike.py`, `tests/test_api_models_route.py`, `tests/test_attachments_upload_route.py`, `tests/test_attachments_get_delete_route.py`, `tests/test_chat_history_additional_kwargs.py`, `tests/test_chat_history_additional_kwargs_api.py`, `tests/test_worker_attachments_payload.py`, `tests/test_langgraph_handler_attachments_v2.py`, `tests/test_orchestrator_handler_attachments.py`
- **Integration:** `docs/phase-36-integration-check.md` (ADR-0046 gate, 6 scenarios PASS)
- **SDK spike:** `docs/phase-36-sdk-spike-note.md` (Wave 0 Assumption A3 / A1 検証)

## Notes

- 画像サムネ配信は Pillow 生成 (`.thumb/`) せず browser の `<img width=48>` resize で十分 (D-23, 社内 200 名規模)。帯域問題が発生した場合は Phase 39 polish で再検討。
- OCR / EXIF サニタイズ / 複数タブ競合制御は v6.1+ に defer (CONTEXT.md Deferred Ideas)。
- Phase 36 の ChatApp 以外のアプリ (Gem / Canvas / SuperChat / Debate) の attachments UX は InputBar 流用の範囲で自動継承、完全対応は v6.1 以降で検討。
