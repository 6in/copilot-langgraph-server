# Phase 36: ファイル入力 — text/code + image multimodal - Research

**Researched:** 2026-04-23
**Domain:** Copilot SDK 0.2.0 multimodal attachments / FastAPI multipart upload / LangGraph checkpointer additional_kwargs / React file-drop-paste UX
**Confidence:** HIGH（SDK 実装 / 既存 coding patterns を実地確認済）

## Summary

Phase 36 は **Phase 37 が敷いたフォルダ規約 (ADR-0048) の "書き込み側"** を実装し、Copilot SDK 0.2.0 の **native `FileAttachment` API** を `app/providers/copilot.py` のラッパー内に閉じ込めつつ、`HumanMessage.additional_kwargs["attachments"]` サイドカー方式で worker 経由の配線を通すフェーズ。SDK 側調査の結果、`CopilotSession.send_and_wait(prompt, *, attachments=[...], timeout=...)` / `CopilotSession.send(prompt, *, attachments=[...])` の 2 経路ともに attachments 引数がサポートされていることが確認できた（`session.py:122-164`、`session.py:166-228`）。

FastAPI 側は `python-multipart>=0.0.22` が既に `pyproject.toml` に含まれており、新規 multipart upload route (`POST /api/threads/{thread_id}/attachments` 等 4 本) を Phase 19 で定着した `APIRouter` + JWT Dependency パターンで実装すれば追加依存なし。LangGraph checkpointer は `AsyncPostgresSaver` が `BaseMessage` 全体を JSONB シリアライズするため `additional_kwargs` も透過的に永続化される（ADR-0038 で AIMessage.name の喪失事例はあるが、これは `name` 専用の LangGraph 既知問題。`additional_kwargs` は独立した dict 領域で影響を受けない）。

**Primary recommendation:** D-09〜D-23 の 23 決定は既に locked。本 phase は 4 Area（provider 配線 / upload API / vision fallback / 履歴 UI）を並行に分解してプランを作る。provider 拡張は既存 `_agenerate` / `_astream` の最後の HumanMessage から `additional_kwargs["attachments"]` を取り出して TypedDict `FileAttachment` に変換するだけ（SDK 型は `TypedDict`, dataclass ではないため dict リテラルで組む）。`list_models()` は `CopilotClient._models_cache` が内部で永続キャッシュしているため独自 TTL キャッシュは軽量ラップで十分。vision fallback は UI (D-17 バナー) + worker (D-18 drop + SystemMessage 注入) の 2 段で defense-in-depth を作る。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01〜D-02 — 受付ポリシー**
- text/code 系: 1 ファイル最大 100 MB（Phase 37 D-09 踏襲）、抽出後 50,000 文字/ファイル・200,000 文字/スレッド（Phase 37 D-13 踏襲）、拡張子は Success Criteria 1 の例示 + `text/*` MIME は受諾
- 画像: 1 枚最大 10 MB、同時 5 枚まで、対応形式は `.png / .jpg (.jpeg) / .webp` の 3 種のみ。`ModelVisionLimits.max_prompt_image_size / max_prompt_images / supported_media_types` がこれより厳しければモデル由来値を優先

**D-03〜D-08 — Upload UX と API 設計**
- **D-03:** アップロードは即時永続化。📎/drop/paste の瞬間に `POST /api/threads/{thread_id}/attachments` で `/shared/thread-files/<github_login>/<thread_id>/` へ書き込む
- **D-04:** 入り口は 3 種：📎 + `<input type="file" multiple>`（必須）／ Drag & Drop（InputBar 領域 + MessageArea 全体）／ Ctrl+V paste（textarea focus 中、`clipboardData.items` から `image/*` 抽出）
- **D-05:** PreviewSlot の見せ方：画像は 48×48 または 64×64 サムネ + `×`、text/code は `[📄 name size ×]` pill
- **D-06:** エラー・キャンセル時：(B) 技術的失敗 → folder 自動削除、(A) ユーザー明示キャンセル → 残す、(C) graceful fallback → 残す、(D) `×` 手動削除 → 確実 DELETE
- **D-07:** 新規 REST 4 本：`POST /api/threads/{thread_id}/attachments`、`GET /api/threads/{thread_id}/attachments/{name}`、`DELETE /api/threads/{thread_id}/attachments/{name}`、`GET /api/models`。`GET /api/threads/{thread_id}/attachments` 一覧 route は **作らない**
- **D-08:** 既存 `adelete_thread` の folder rm hook は変更なし。新規 DELETE route は Phase 37 の realpath guard を踏襲

**D-09〜D-13 — ChatCopilot provider 拡張（multimodal 配線）**
- **D-09:** `session.send_and_wait(prompt, attachments=[...])` を採用、`FileAttachment(path, displayName)` を text/code・画像の両方で使う（`BlobAttachment` は本 phase 未採用）
- **D-10:** envelope は `HumanMessage.additional_kwargs["attachments"]` サイドカー方式。`ChatCopilot._agenerate` / `_astream` が最後の HumanMessage の `additional_kwargs["attachments"]` を読んで SDK 型に変換（SDK 型は `app/providers/copilot.py` 内に閉じ込める）
- **D-11:** text/code も画像も毎 turn eager に送るが、attach するのは **新規添付分のみ**。過去 turn の情報は Phase 37 既存パターン（SystemMessage prepend）で「ファイルの存在」を知らせ、内容が必要なら `attachments_extract` MCP ツールを使う
- **D-12:** `attachments_extract` MCP ツール（Phase 37 D-14）の責務は変更しない。text/code eager と attachments_extract lazy は並存
- **D-13:** `ChatCopilot._messages_to_prompt` は attachments を文字列化しない（prompt 文字列と別路で SDK に渡す）

**D-14〜D-15 — Attachment 標準スキーマ**
- **D-14:** Request / job payload / `AgentState.attachments` / `HumanMessage.additional_kwargs["attachments"]` / `attachments_list` MCP ツール戻り値で **統一 dict スキーマ**：
  ```python
  {
      "kind": "file",           # 現状は "file" のみ
      "name": "original.png",   # LLM に見せるオリジナル名
      "storage_name": "20260423T120000_original.png",  # folder 内実ファイル名
      "path": "/shared/thread-files/<login>/<tid>/20260423T120000_original.png",
      "size": 12345,
      "mime_type": "image/png",
      "ext": "png",
      "modified_at": "2026-04-23T12:00:00Z",
  }
  ```
  Phase 37 `attachments_list` の `{name, size, modified_at, ext}` を拡張する形（互換）
- **D-15:** `kind == "file"` → `copilot.FileAttachment(type="file", path=..., displayName=name)` に変換。`kind == "blob"` は将来拡張余地（本 phase 未採用）

**D-16〜D-19 — vision 判定と fallback**
- **D-16:** vision 対応判定は `client.list_models()` をソース。hardcoded allowlist なし。TTL 1 時間キャッシュ、`GET /api/models` は `[{id, name, vision: bool, vision_limits: {...}?}, ...]` を返す
- **D-17:** vision 非対応モデル時、📎 は常に active（text/code 用）、画像を添付した瞬間に InputBar 上部に警告バナー + ワンクリック切替
- **D-18:** 非対応モデルで送信した場合の worker 側 graceful fallback：画像は `attachments` から除外、SystemMessage に「画像非対応のため内容を読めません。vision 対応モデルへの切替えを案内してください」を注入
- **D-19:** `ModelVisionLimits` を UI pre-validate + worker defense-in-depth 再検証の 2 段

**D-20〜D-23 — チェックポイント保存と履歴 UI**
- **D-20:** 履歴の真実のソースは `HumanMessage.additional_kwargs["attachments"]`（LangGraph checkpointer 自動 JSONB シリアライズ）。folder scan は「現在の手持ち」確認用のみ
- **D-21:** 履歴 UI は「メッセージバブル内の末尾にチップ行」：画像 48×48 サムネ + text/code pill。クリック時アクションは Claude's Discretion
- **D-22:** `GET /api/chat/history` は `BaseMessage.additional_kwargs` をそのまま JSON で返す（別 endpoint は作らない、既存 `get_thread_messages` に `additional_kwargs` フィールドを足すだけ）
- **D-23:** 画像サムネ配信は `GET /api/threads/{id}/attachments/{name}` の raw bytes（JWT 認証付き）。**Pillow サムネ生成なし**、browser resize で十分、ADR-0048 フォルダ規約にサムネディレクトリを追加しない

### Claude's Discretion

研究・計画・実装段階で判断する項目：

- upload progress UX（percent bar / spinner / 完了 toast の有無・位置）
- DELETE endpoint の返り値設計（204 / 200 + JSON）
- エラー表示 UI パーツ選択（既存 `ConfirmModal` 流用 / 新規 toast / inline banner — Phase 35 既存 dialog 系パターンに合わせる）
- SystemMessage 注入文言（日本語/英語・hint 粒度 — ADR-0025 の既存パターン踏襲）
- `/api/models` キャッシュ TTL の具体値（目安 1 時間、SDK 呼び出しコストで調整）
- サムネのピクセルサイズ（48 vs 64 vs 96）、クリック時の modal 有無
- upload 中のキャンセル UX（個別 cancel AbortController 等）
- 複数タブ同時アップロード時の挙動（楽観更新 / `modified_at` 競合検知は Phase 36 では扱わない想定、v6.1+）
- Gem / SuperChat / Canvas / DebateChat の添付サポート範囲（Phase 36 は ChatApp 中心、InputBar 流用範囲で自動継承、個別対応は planner 判断で wave 追加）
- モバイル幅 (≤767px) の drop zone / paste 挙動（Phase 35 D-05 "破綻ゼロ" 保証内で最低限）
- EXIF / メタデータサニタイズ（削除推奨・v6.1+ でも可）
- MIME sniff（サーバー側 magic byte 確認するかは planner 判断）
- multipart upload のサイズ制限実装方式（`UploadFile.spool_max_size` / chunked streaming）
- `ChatCopilot._astream` での attachments 対応の足並み（`_agenerate` と共通ヘルパー化するか）

### Deferred Ideas (OUT OF SCOPE)

- **外部ストレージ連携**（GitHub / Google Drive / URL import）— 新 phase or v6.1+
- **Gem / SuperChat / Canvas / DebateChat 各アプリの個別添付 UX 調整** — 本 phase は ChatApp 中心
- **専用サムネ生成 (Pillow 64×64 キャッシュ)** — Phase 39 polish で再検討
- **EXIF / メタデータサニタイズ** — v6.1+ でよい
- **複数タブからの同時アップロード競合制御** — v6.1+
- **`attachments_read_bytes` のような新 MCP tool** — execute_python sandbox の直接 open() で十分（Phase 37 deferred 継承）
- **OCR（画像テキスト抽出）** — v6.1+ で MarkItDown + tesseract 検討
- **過去 turn 添付の一括管理 UI** — MessageArea bubble チップで十分
- **ダウンロード UI / 画像拡大 modal** — Discretion 範囲で最小対応、本格 viewer は Phase 38 (FOUT) へ
- **Phase 38 (worker 生成 DL + プレビュー + ユーザー別保持) / Phase 32-33 (AI-UI 基盤) / Phase 39 (UI バグ潰し)** — 明示的に scope 外

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIN-01 | ユーザーがチャット入力欄からテキスト・コード系ファイル（.txt/.md/.json/.csv/.py/.js 等）を添付し、LLM がコンテキストとして参照できる | **SDK 調査で `FileAttachment(type="file", path, displayName)` が text/code ファイルに使えることを確認**。`send_and_wait(prompt, attachments=[{"type": "file", "path": ..., "displayName": ...}])` で subprocess (worker → SDK CLI) が path から直接ファイルを読む。worker は RO mount、SDK CLI プロセスも同コンテナなのでパス解決は共通 |
| FIN-02 | ユーザーが画像ファイル（.png/.jpg/.webp）を添付し、multimodal 対応モデルで参照できる（Copilot SDK 未対応モデルでは graceful にフォールバック） | **SDK は画像にも `FileAttachment` 利用可能**（`BlobAttachment` は base64 inline 用で本 phase 未採用）。`ModelInfo.capabilities.supports.vision: bool` + `limits.vision: ModelVisionLimits \| None` で判定。未対応時は D-18 の worker drop + SystemMessage 注入で graceful 継続 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

以下は本 phase 実装時に **必ず守る** プロジェクトルール（RESEARCH/PLAN で alternative を提案しないこと）:

- **応答言語：日本語**（GSD バナー・SUMMARY・エラーメッセージ含む）
- **Tech Stack 固定：** Python 3.12 / `langgraph-checkpoint-postgres` / `github-copilot-sdk==0.2.0` / FastAPI / React 19 + Vite + Bun
- **Auth：Device Flow のみ**、新規 attachment route も JWT httpOnly cookie で認証（Phase 17 ADR-0014）
- **SDK 隔離原則：** `copilot.*` の import は `app/providers/copilot.py` の中だけ（他モジュールは dict スキーマ D-14 で扱う）
- **Primary startup：`docker compose up`**、開発 URL `http://localhost:5173/orochi/`（VITE_APP_BASE の prefix 前提）
- **MCP ツールは SSoT：** `config/mcp_tools.yaml` が唯一のソース。手書き／自動生成の境界（`mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md` は自動生成）を破らない — 本 phase では新規 MCP ツール追加予定なし
- **ADR 索引は自動生成：** `docs/adr/INDEX.md` は `scripts/generate_adr_index.py` による pre-commit hook 生成。新規 ADR 追加時は `.planning/adr-categories.yaml` にも番号とカテゴリを追記
- **新規 ADR 起票時：** `/create-adr` 実行後にパターンを `.planning/patterns.md` へ手動追記（D-15）
- **マージは必ず squash merge**（`git merge --squash <branch>`）、変更なし worktree は削除
- **pre-commit hook の install：** 新規クローン直後は `bash scripts/install-hooks.sh` を 1 回実行

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 📎 / drop / paste による file staging | Browser / Client | — | ユーザー入力イベントは DOM 内で処理。FastAPI は staging を持たない |
| multipart upload 受付 + folder 書き込み + realpath guard | API / Backend | — | JWT 認証・folder path 構築・ファイル書き込み権限の 3 点を持つのは API 層のみ |
| サーバー保存名 (`YYYYMMDDTHHMMSS_<original>.<ext>`) の採番 | API / Backend | — | 衝突回避のため server 側 atomic 採番。ADR-0048 が規定する命名規則はここで実装される |
| `/api/models` キャッシュ | API / Backend | — | `list_models()` は CopilotClient から引く → API lifespan で warm cache。frontend は REST で取得 |
| UI の vision pre-validate（D-19） | Browser / Client | API | `selectedModel` の `vision_limits` は `/api/models` 由来、UI で拒否 |
| worker の vision 再検証（D-19） | API / Backend (worker) | — | UI を bypass されても最終防御。worker が payload を受けた時点で drop |
| Copilot SDK 型への変換 | API / Backend (provider) | — | SDK 隔離原則により `app/providers/copilot.py` の内部でのみ `FileAttachment` TypedDict を作る |
| SDK subprocess による実ファイル読み取り | API / Backend (worker container filesystem, shared volume mount) | — | `/shared/thread-files` は named volume、worker (RO) / api (RW) / mcp-server (RW) で共有 |
| LangGraph checkpointer への `additional_kwargs` 永続化 | Database / Storage (PostgreSQL JSONB) | — | `langgraph_checkpoints.checkpoint` JSONB 列に `BaseMessage` 全体がシリアライズされる |
| 履歴 UI の bubble 内チップ描画 | Browser / Client | — | `GET /api/chat/history` から `additional_kwargs.attachments` を受けて React で描画 |

## Dependencies and Libraries

### 新規依存ライブラリ

**追加不要** — すべて既存依存で実装できる。具体内訳：

| ライブラリ | 現状 | 用途 |
|------------|------|------|
| `github-copilot-sdk==0.2.0` | 既存 pinned | `FileAttachment` TypedDict / `CopilotClient.list_models()` / `CopilotSession.send_and_wait(..., attachments=[...])` |
| `python-multipart>=0.0.22` | 既存（`pyproject.toml` L14） | FastAPI `UploadFile` / `File(...)` の parser |
| `fastapi>=0.135.2` | 既存 | `UploadFile` / multipart handling / JWT Dependency |
| `langgraph-checkpoint-postgres>=3.0.5` | 既存 | `BaseMessage.additional_kwargs` を JSONB に透過シリアライズ |
| React 19 + TypeScript + Vite | 既存 | `<input type="file" multiple>` / DataTransfer / clipboardData.items |

### 既存 import 経路（参考）

- Provider: `from copilot import CopilotClient, SubprocessConfig, PermissionHandler, FileAttachment, ModelInfo` （新たに `FileAttachment, ModelInfo` を import し、`app/providers/copilot.py` 内部で閉じる）
- FastAPI: `from fastapi import APIRouter, UploadFile, File, Depends, HTTPException`（既存 `chat.py` に同じ pattern）
- 既存 JWT Dependency: `get_jwt_payload` / `get_github_token`（`app/api/routes/chat.py:74-108`）
- attachments_helper: `from app.jobs.handlers.attachments_helper import scan_thread_attachments, build_attachments_hint`（Phase 37 既存）

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────── Browser (React) ──────────────────────────────┐
│  [InputBar]                                                        │
│   ├─ toolbarSlot: <AttachmentButton 📎> ──── onClick / onDrop /    │
│   │                                          onPaste               │
│   └─ previewSlot: <AttachmentChips> ←── staging state              │
│                                                                    │
│  [useChat.sendMessage]                                             │
│   └── POST /api/chat { ..., attachments: [{kind, name, ...}] }     │
└──────────────────┬─────────────────────────────────────────────────┘
                   │
                   │ (1) per-file multipart upload (async, 即時永続化)
                   │ POST /api/threads/{tid}/attachments
                   │     (multipart/form-data, List[UploadFile])
                   │     → サーバー保存名 "YYYYMMDDTHHMMSS_<original>.<ext>"
                   │     → 200 OK { attachments: [D-14 dict, ...] }
                   ▼
┌─────────────── FastAPI (api) ────────────────────────────────────┐
│  [app/api/routes/attachments.py] NEW                               │
│    POST   /api/threads/{tid}/attachments   — multipart → folder 書き込み │
│    GET    /api/threads/{tid}/attachments/{name} — raw bytes (画像サムネ含む) │
│    DELETE /api/threads/{tid}/attachments/{name} — realpath guard → unlink │
│                                                                    │
│  [app/api/routes/models.py] NEW                                    │
│    GET    /api/models — TTL 1h キャッシュ → list_models() → 整形   │
│                                                                    │
│  [app/api/routes/chat.py:send_message] 既存                        │
│    POST /api/chat — ChatRequest に attachments: list[D-14 dict] 追加 │
│    GET  /api/threads/{tid}/messages — additional_kwargs 返却追加 (D-22) │
│    DELETE /api/threads/{tid} — folder rm hook (Phase 37 変更なし)  │
└────────────┬───────────────────────────────────────────────────────┘
             │
             │ (2) job_id immediately returned → SSE polls for completion
             │ arq enqueue_job("process_chat", attachments=[...])
             ▼
┌─────────────── Worker (arq) ─────────────────────────────────────┐
│  [app/jobs/worker.py:process_chat] 既存                            │
│    → routes to LangGraphHandler (chat) or OrchestratorHandler (super) │
│                                                                    │
│  [app/jobs/handlers/langgraph_handler.py] 拡張                     │
│    ┌─ scan_thread_attachments(tid, login) — Phase 37 既存          │
│    ├─ build_attachments_hint(meta)  ──→ SystemMessage prepend      │
│    │                                   (過去 turn の "ファイル存在" 情報) │
│    ├─ 画像 drop + SystemMessage 注入 (D-18, vision 非対応時)        │
│    └─ HumanMessage(content=prompt,                                 │
│                    additional_kwargs={"attachments": [D-14, ...]}) │
│                                                                    │
│    graph.astream_events(state_input) → on_chat_model_stream        │
└────────────┬───────────────────────────────────────────────────────┘
             │
             │ (3) ChatCopilot._agenerate or _astream
             ▼
┌─── ChatCopilot (app/providers/copilot.py) ───────────────────────┐
│  最後の HumanMessage から additional_kwargs["attachments"] を取り出す │
│    → [{kind: "file", path, name, ...}] → FileAttachment TypedDict │
│       {"type": "file", "path": ..., "displayName": ...}           │
│    → session.send_and_wait(prompt, attachments=[...])             │
└────────────┬───────────────────────────────────────────────────────┘
             │
             │ (4) JSON-RPC to local copilot CLI subprocess
             ▼
┌─── Copilot CLI subprocess ───────────────────────────────────────┐
│   subprocess が直接 path から attachments を open() する           │
│   /shared/thread-files/<login>/<tid>/<storage_name> を読み込む    │
│   (worker container の RO mount 経由でも CLI プロセスは read-only  │
│    で開くだけなので問題ない)                                       │
└───────────────────────────────────────────────────────────────────┘

(5) Checkpoint：add_messages reducer が HumanMessage 全体を checkpoint JSONB 列に保存
    → 再オープン時、get_thread_messages が additional_kwargs を JSON で返却
    → React MessageArea が bubble 内チップ行を描画 (D-21)
```

### Recommended Project Structure

```
app/
  api/
    routes/
      attachments.py   # NEW: POST / GET raw / DELETE
      models.py        # NEW: GET /api/models
      chat.py          # CHANGE: ChatRequest.attachments + get_thread_messages に additional_kwargs
    main.py            # CHANGE: include_router(attachments), include_router(models)
    models.py          # CHANGE: ChatRequest.attachments: list[dict] | None を追加
  providers/
    copilot.py         # CHANGE: _agenerate / _astream に attachments 取り出し + SDK 型変換
                       #         BoundChatCopilot._agenerate / _astream も同様に経路追加
  jobs/
    handlers/
      langgraph_handler.py    # CHANGE: job payload.attachments を HumanMessage.additional_kwargs に注入
                              #          D-18 vision drop + SystemMessage 注入
      orchestrator_handler.py # CHANGE: 同上（SuperChat/Gem/Canvas 対応）
    worker.py          # CHANGE: process_chat に attachments パラメータ追加

frontend/src/
  api/
    client.ts                     # CHANGE: apiFetch multipart 対応 (Content-Type 非設定)
                                  #         新 endpoint 関数 postAttachments / deleteAttachment / getModels
  components/
    InputBar.tsx                  # 変更なし — slots 経由で差し込む
    AttachmentButton.tsx          # NEW: 📎 button + hidden <input type="file" multiple>
    AttachmentChips.tsx           # NEW: staging list 描画 + × 削除
    VisionWarningBanner.tsx       # NEW: D-17 モデル非対応時の警告 + ワンクリック切替
    MessageArea.tsx               # CHANGE: bubble 内チップ行描画 (D-21)
    Header.tsx                    # CHANGE: MODEL_OPTIONS ハードコード → /api/models 由来 (fallback 残す)
  hooks/
    useChat.ts                    # CHANGE: sendMessage に attachments staging 組み込み
    useAttachments.ts             # NEW: staging state + upload + cancel
    useModels.ts                  # NEW: /api/models fetch + キャッシュ
```

### Pattern 1: additional_kwargs サイドカー envelope
**What:** LangChain `BaseMessage` の `additional_kwargs: dict` 領域を使ってメッセージに付随情報を運ぶ。LangGraph `add_messages` reducer と PostgreSQL checkpointer は `BaseMessage` 全体を JSONB シリアライズするため、追加フィールドを作らずに透過的に永続化できる。
**When to use:** メッセージ本文 (content) とは独立に、特定メッセージに紐付くメタデータ（この turn の attachments、ask_user_question、tool_call_id 等）を保持したいとき
**Example:**
```python
# Source: app/jobs/handlers/langgraph_handler.py (本 phase で変更)
from langchain_core.messages import HumanMessage

attachments_for_turn = [  # job payload から取る (D-14 dict)
    {"kind": "file", "name": "sample.png", "storage_name": "20260423T120000_sample.png",
     "path": "/shared/thread-files/octocat/t-1/20260423T120000_sample.png",
     "size": 98765, "mime_type": "image/png", "ext": "png",
     "modified_at": "2026-04-23T12:00:00Z"},
]
# 過去 turn の folder scan は SystemMessage prepend で伝える (Phase 37 既存)
user_msg = HumanMessage(
    content=prompt,
    additional_kwargs={"attachments": attachments_for_turn} if attachments_for_turn else {},
)
```

**注意：** `AIMessage.name` は checkpoint シリアライズ時に失われる既知問題が ADR-0038 で報告されている（`_wrap_agent_run` で workaround）。しかし `additional_kwargs` は `BaseMessage` 基底クラスの独立フィールドで、LangChain コア側が `model_dump()` でシリアライズする正式経路。`name` 問題とは別系統で影響を受けない見込み（ただし実装後に **再オープン時の additional_kwargs 復元** を integration check で必ず確認する — 後述 Pitfall 参照）。

### Pattern 2: SDK 隔離原則（provider 内に SDK 型を閉じる）
**What:** `copilot.*` のシンボル (`FileAttachment` / `BlobAttachment` / `ModelInfo` / 各種 TypedDict) を `app/providers/copilot.py` の中だけで import し、外部モジュールは dict スキーマ (D-14) で扱う。
**When to use:** SDK が Technical Preview でバージョン互換が保証されないとき、もしくは将来 provider を差し替える可能性があるとき
**Example:**
```python
# Source: app/providers/copilot.py (本 phase で追加)
from copilot import FileAttachment  # TypedDict, NOT dataclass

def _build_sdk_attachments(atts: list[dict]) -> list[FileAttachment]:
    """D-14 dict → SDK TypedDict に変換。provider 内部のみで使う。"""
    out: list[FileAttachment] = []
    for a in atts or []:
        if a.get("kind") != "file":
            continue  # D-15: 未採用の blob は skip (本 phase では発生しない想定)
        out.append({"type": "file", "path": a["path"], "displayName": a["name"]})
    return out

# _agenerate 内で：
last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
attachments_meta = (last_human.additional_kwargs or {}).get("attachments") if last_human else None
sdk_atts = _build_sdk_attachments(attachments_meta or [])
response = await session.send_and_wait(
    prompt,
    attachments=sdk_atts if sdk_atts else None,
    timeout=self.send_timeout,
)
```

### Pattern 3: FastAPI `UploadFile` + `File(...)` + JWT Dependency
**What:** multipart upload は `UploadFile` 型引数で受ける。`UploadFile.file` は `SpooledTemporaryFile`、`await UploadFile.read()` で bytes を得る。既存の JWT Dependency と共存可能。
**When to use:** 複数ファイルの multipart upload（本 phase の `POST /api/threads/{tid}/attachments`）
**Example:**
```python
# Source: app/api/routes/attachments.py (本 phase で新規作成)
from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile
from typing import List

router = APIRouter(prefix="/api", tags=["attachments"])

@router.post("/threads/{thread_id}/attachments")
async def upload_attachments(
    request: Request,
    thread_id: str = Path(..., description="Thread ID (UUID4)"),
    files: List[UploadFile] = File(...),
    payload: dict = Depends(get_jwt_payload),  # app/api/routes/chat.py の既存 Dependency
) -> dict:
    github_login = payload.get("github_login", "unknown")
    # thread フォルダ解決 + realpath guard (Phase 37 D-18 パターン踏襲)
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    real = os.path.realpath(folder)
    root = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(root + os.sep):
        raise HTTPException(status_code=400, detail="invalid thread path")
    os.makedirs(real, exist_ok=True)

    saved: list[dict] = []
    for uf in files:
        # D-01/D-02 サイズ・MIME 検証、D-14 スキーマで返す
        # timestamp prefix 採番：現在 UTC を YYYYMMDDTHHMMSS で付与
        storage_name = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{uf.filename}"
        dest = os.path.join(real, storage_name)
        # chunked write で 100MB 超過を段階的にチェック
        total = 0
        with open(dest, "wb") as fh:
            while chunk := await uf.read(1024 * 1024):  # 1MB chunks
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    fh.close()
                    os.remove(dest)
                    raise HTTPException(status_code=413, detail=f"{uf.filename} exceeds size limit")
                fh.write(chunk)
        saved.append({
            "kind": "file", "name": uf.filename, "storage_name": storage_name,
            "path": dest, "size": total, "mime_type": uf.content_type or "application/octet-stream",
            "ext": os.path.splitext(uf.filename)[1].lower().lstrip("."),
            "modified_at": datetime.utcnow().isoformat() + "Z",
        })
    return {"attachments": saved}
```

**重要な注意：** `request: Request` を引数に含めても、`get_jwt_payload(request: Request)` の依存解決は FastAPI が自動的にリクエストコンテキストから解決する。multipart と JWT Depends は `app/api/routes/chat.py:send_message` (line 111-117) と同じ pattern で共存可能。

### Pattern 4: `/api/models` の 1 時間 TTL キャッシュ
**What:** `CopilotClient.list_models()` は SDK 内部で `_models_cache` を既に持つ（`client.py:976-1024`）ため、別途独自キャッシュは最小限でよい。ただし `/api/models` エンドポイントは lifespan 経由で warm させ、1h TTL で再呼び出しする。
**When to use:** モデル一覧の高頻度参照（`selectedModel` 変更の都度 UI がチェック）
**Example:**
```python
# Source: app/api/routes/models.py (本 phase で新規作成)
from dataclasses import dataclass, field
import time
from fastapi import APIRouter, Depends, Request
from app.api.routes.chat import get_jwt_payload, get_github_token

_TTL_SECS = 3600

@dataclass
class _Cache:
    at: float = 0.0
    payload: list[dict] = field(default_factory=list)

_cache = _Cache()

router = APIRouter(prefix="/api", tags=["models"])

@router.get("/models")
async def list_models(
    request: Request,
    github_token: str = Depends(get_github_token),
) -> list[dict]:
    now = time.time()
    if now - _cache.at < _TTL_SECS and _cache.payload:
        return _cache.payload

    # app.state.llm は CopilotClient instance（lifespan で起動済み）
    llm = request.app.state.llm
    await llm._ensure_client()  # 未 init なら起動
    models = await llm._client.list_models()  # SDK が内部 _models_cache で管理
    payload = [
        {
            "id": m.id,
            "name": m.name,
            "vision": m.capabilities.supports.vision,
            "vision_limits": m.capabilities.limits.vision.to_dict()
                if m.capabilities.limits.vision else None,
            "billing_multiplier": m.billing.multiplier if m.billing else None,
        }
        for m in models
    ]
    _cache.at = now
    _cache.payload = payload
    return payload
```

**注意：** `llm._client` は private attribute だが、ChatCopilot の enforcement 範囲内（`app/providers/copilot.py` 内で定義、api からは lifespan 経由の制御されたアクセス）。清潔にしたければ `ChatCopilot` に `async def list_models() -> list[dict]` を追加して SDK 型を dict に変換してから返す（推奨 — SDK 隔離原則）。

### Pattern 5: React file / drag-drop / paste 3 入り口の統一 staging
**What:** 3 種の入力元（click / drop / paste）を同じ staging reducer に流す hook を書く。ブラウザ側の差異（drop の dragover preventDefault / paste の clipboardData items）を hook 内部で吸収する。
**When to use:** InputBar + MessageArea 両方が drop target 候補のとき（D-04）
**Example:**
```typescript
// Source: frontend/src/hooks/useAttachments.ts (本 phase で新規作成)
import { useCallback, useRef, useState } from 'react';

export interface StagingItem {
  kind: 'file';
  name: string;
  storage_name: string;  // upload 後にサーバーから返る
  path: string;
  size: number;
  mime_type: string;
  ext: string;
  modified_at: string;
  // client-only 追加
  localId: string;        // UI キー (crypto.randomUUID())
  status: 'uploading' | 'done' | 'error';
  error?: string;
  abortCtrl?: AbortController;
}

export function useAttachments(threadId: string | null) {
  const [items, setItems] = useState<StagingItem[]>([]);
  const latestItemsRef = useRef(items);
  latestItemsRef.current = items;

  const upload = useCallback(async (files: File[]) => {
    if (!threadId) return;
    for (const f of files) {
      // pre-validate: size / ext / MIME（D-01/D-02）
      const ext = f.name.split('.').pop()?.toLowerCase() ?? '';
      const localId = crypto.randomUUID();
      const ctrl = new AbortController();
      setItems(p => [...p, {
        kind: 'file', name: f.name, storage_name: '', path: '',
        size: f.size, mime_type: f.type, ext,
        modified_at: new Date().toISOString(), localId,
        status: 'uploading', abortCtrl: ctrl,
      }]);
      try {
        const fd = new FormData();
        fd.append('files', f, f.name);
        const resp = await fetch(`${API_BASE}/api/threads/${threadId}/attachments`, {
          method: 'POST', body: fd, credentials: 'include', signal: ctrl.signal,
        });
        if (!resp.ok) throw new Error(`upload failed: ${resp.status}`);
        const json: { attachments: StagingItem[] } = await resp.json();
        const served = json.attachments[0];  // per-file で送るので必ず 1 件
        setItems(p => p.map(x => x.localId === localId
          ? { ...x, ...served, status: 'done' as const } : x));
      } catch (e) {
        setItems(p => p.map(x => x.localId === localId
          ? { ...x, status: 'error', error: (e as Error).message } : x));
      }
    }
  }, [threadId]);

  const removeItem = useCallback(async (localId: string) => {
    const item = latestItemsRef.current.find(x => x.localId === localId);
    setItems(p => p.filter(x => x.localId !== localId));
    if (item?.abortCtrl && item.status === 'uploading') {
      item.abortCtrl.abort();
      return;
    }
    if (item?.status === 'done' && threadId) {
      // D-06 ケース D: ユーザー明示削除 → サーバー側も削除
      await fetch(`${API_BASE}/api/threads/${threadId}/attachments/${encodeURIComponent(item.storage_name)}`,
        { method: 'DELETE', credentials: 'include' });
    }
  }, [threadId]);

  const clearAll = useCallback(() => setItems([]), []);
  const getReadyItems = useCallback(
    () => latestItemsRef.current.filter(x => x.status === 'done'),
    [],
  );

  return { items, upload, removeItem, clearAll, getReadyItems };
}
```

UI 側：
- InputBar の drop zone：`onDragOver={e => e.preventDefault()}` + `onDrop={e => { e.preventDefault(); upload([...e.dataTransfer.files]); }}`
- textarea onPaste：`for (const item of e.clipboardData.items) if (item.type.startsWith('image/')) { const file = item.getAsFile(); if (file) upload([file]); }`

### Anti-Patterns to Avoid

- **prompt embed：** 添付内容を prompt 文字列に詰めない（D-13）。FIN-02 の画像対応は満たせず、FileAttachment native API のメリットを捨てることになる
- **LangChain structured content (multimodal content parts)：** `[{"type": "text", ...}, {"type": "image_url", ...}]` 方式は text ファイル型が標準未定義で Copilot SDK 側の解釈も保証されない。D-09 で却下
- **BlobAttachment (base64 inline)：** 画像を base64 で prompt に詰めると token 浪費 + checkpoint JSONB 肥大。D-09 で FileAttachment (path) 方式を採用済み
- **専用サムネ生成 (Pillow 64×64 キャッシュ)：** ADR-0048 のフォルダ規約にサブディレクトリ `.thumb/` を追加しない方針（D-23）。browser resize で十分
- **folder scan を履歴ソースにする：** 単独 turn の添付と紐付かないので、再オープン時にどのメッセージに何が付いたのか表現できない。D-20 により真実のソースは `additional_kwargs["attachments"]`
- **`/api/threads/{tid}/attachments` 一覧 route：** D-07 により作らない。履歴は checkpointer の `additional_kwargs` から取る

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Copilot へのファイル渡し | 自作 prompt embed で base64 埋め込み | `copilot.FileAttachment` + `session.send_and_wait(attachments=[...])` | SDK native 対応、path 渡しなので token 効率良い、画像も同経路 |
| Multipart upload の parser | `starlette.formparsers` 直接使用 | FastAPI `UploadFile` + `File(...)` | `SpooledTemporaryFile` 管理・content_type 推定を自動化、依存は既に入っている |
| Thread フォルダ削除 hook | 新規 `adelete_thread` callback | Phase 37 既存の `delete_thread` 内 realpath guard + `shutil.rmtree` | 既に動作確認済、ADR-0048 の lifecycle 契約と整合 |
| `attachments_list` / `attachments_extract` | 新規 MCP ツール追加 | Phase 37 既存ツールの流用 | 既に `sandbox_exposed: true` / RPCContext 解決も含めて整っている |
| モデル一覧のクライアント側ハードコード | Header.tsx の MODEL_OPTIONS を更新し続ける | `/api/models` エンドポイント + `list_models()` | SDK がモデル追加するたびに UI 修正が不要になる、vision フラグも同経路で取れる |
| Path traversal 対策 | 各 route で個別チェック | Phase 37 パターン（`os.path.realpath` + prefix assert） | 既に `attachments_extract` と `delete_thread` の両方で動作確認済、同じパターンを新 DELETE / GET raw route で適用 |
| 画像サムネ生成 | Pillow で 48/64px PNG を作って `.thumb/` に保存 | `<img src=... width=48>` で browser resize | ADR-0048 のフォルダ規約にサムネディレクトリを足さない、200 名規模では帯域問題にならない |
| LangGraph state に additional_kwargs 相当を作る | `AgentState` に新フィールド `per_turn_attachments` を追加 | `HumanMessage.additional_kwargs["attachments"]` | Message に紐付く情報はメッセージ自身が持つのが自然、checkpoint serialization も自動で乗る |

**Key insight:** 本 phase の大半は「既に Phase 37 で敷いた土台の上に **書き込み側** を足すだけ」で成立する。Phase 37 のフォルダ規約（ADR-0048）/ attachments_helper / realpath guard / per-job MCP client pattern / SystemMessage prepend がすべて再利用可能。新規発明は（1）Copilot SDK attachments 配線、（2）multipart upload endpoint、（3）`/api/models` キャッシュ、（4）frontend の file/drop/paste + staging state — の 4 つだけに閉じる。

## Runtime State Inventory

本 phase は **新規実装 phase** であり、rename/refactor/migration ではない — よってこのセクションは軽量に運用する。ただし Phase 37 との接続面で既存 runtime state との整合確認が必要なので最小限を記す：

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **PostgreSQL `langgraph_checkpoints.checkpoint` (JSONB)** — 既存 HumanMessage は `additional_kwargs={}` で保存済み。新 turn から `{"attachments": [...]}` が入り始める | 新規書き込みのみ。既存行の migration は不要（None-guard で読み取り側を対応） |
| Stored data | **`/shared/thread-files/<login>/<tid>/`** — Phase 37 が既に読み取り側を実装、本 phase で書き込み側を追加 | ライフサイクル hook (adelete_thread) は既存、**変更なし** |
| Live service config | なし — 新規添付は全て per-thread runtime 書き込み、外部サービスの config は触らない | — |
| OS-registered state | なし | — |
| Secrets/env vars | なし（新規秘密情報を追加しない） | — |
| Build artifacts | なし | — |

**canary 動作確認事項：**
- 既存 (Phase 35 まで) で作成された thread の `HumanMessage` が `additional_kwargs=={}` であることを確認（read 側は `.get("attachments", [])` で None-guard）
- `/shared/thread-files/` volume が存在しない環境（unit test 環境）では `THREAD_FILES_DIR` を tmp に差し替え

## Common Pitfalls

### Pitfall 1: `additional_kwargs` が checkpoint 復元で失われる懸念（ADR-0038 類似問題）
**What goes wrong:** `AIMessage.name` は LangGraph checkpoint の (de)serialization で落ちる既知問題がある（ADR-0038）。`additional_kwargs` も同様に落ちる可能性を排除できない。
**Why it happens:** LangGraph は `BaseMessage` を内部で `dict` に dump → JSONB → reload のラウンドトリップを行う。LangChain 側が `model_dump(include_kw=True)` 相当で serialize していれば復元される想定だが、バージョン次第で挙動が変わる。
**How to avoid:**
- **integration check 必須：** 実際に 1 turn 送信 → DB 再接続 → `get_thread_messages` で `additional_kwargs.attachments` が返ることを docker compose 実環境で確認する（ADR-0046 gate）
- 落ちていたら `_wrap_agent_run` 相当の workaround を handler に足す（Phase 37 OrchestratorHandler の `_wrap_agent_run` は `AIMessage.name` 用、新規 `_wrap_human_message_attachments` 相当が必要になる可能性）
**Warning signs:** リロード後に bubble チップが消える、worker log で `additional_kwargs={}` が出る

### Pitfall 2: per-job MCP client を LangGraphHandler にも追加するかどうか
**What goes wrong:** Phase 37.1 で OrchestratorHandler は per-job MCP client を headers 付きで作り直しているが、LangGraphHandler（通常 chat）は worker startup の client を使っている。Phase 36 の `attachments_extract` tool が通常 chat から呼ばれるケースでは、headers が無いため空 thread_id で scan してしまう（Phase 37 HIGH-01 で確認済みの問題）。
**Why it happens:** 現状 chat の `build_graph` は mcp_tools を渡していない（Phase 37 Code Review で dead code 削除済み）ため、attachments_extract は chat 経路からは呼べない。
**How to avoid:**
- **Phase 36 は「eager attach」で text/code を毎 turn 送るのでこの経路は主系路ではない**（D-11）。ただし LLM が `attachments_extract` を使いたい判断をしたとき通常 chat では呼べないので、その場合の UX 劣化を planner が明示的に受容するか、build_graph + LangGraphHandler 側にも per-job MCP client 配線を足すかを決める
- 主系路（eager attach）は Pitfall 2 の影響を受けない — SDK `session.send_and_wait(attachments=[...])` で直接 path を渡すので MCP client を経由しない
**Warning signs:** 通常 chat で LLM が「attachments_extract を呼びました」と言うのに tool call が空応答、または worker log で `x-thread-id` が空

### Pitfall 3: FastAPI `UploadFile` の 100MB 制限 enforce
**What goes wrong:** `UploadFile` は `SpooledTemporaryFile` で 1MB を超えるとディスクに spool する。サイズチェックを `await uf.read()` 全部取ってから行うと、悪意あるユーザーが 10GB ファイルを送りつけてディスクを埋められる。
**Why it happens:** FastAPI 自体には request body 上限がない。uvicorn には `--limit-max-requests` はあるがサイズ上限ではない。リバースプロキシ（nginx）に `client_max_body_size` を設定しないと無制限。
**How to avoid:**
- **chunked read でサイズ累計チェック：** 1MB ずつ `await uf.read(1024 * 1024)` し、累計が 100MB を超えた時点で即 close + 部分書き込みファイルの unlink + 413
- nginx 側にも `client_max_body_size 110m;` 相当を設定（docs/nginx.md 該当あれば確認。社内 nginx 運用設定 — planner 判断で documentation 追加）
- FastAPI の Request body を直接 streaming で受けるより UploadFile の chunked read のほうが簡潔
**Warning signs:** `/tmp` が埋まる、api container OOM

### Pitfall 4: iOS Safari の paste / drop 挙動差
**What goes wrong:** iOS Safari では `clipboardData.items` が同期 getter で File オブジェクトを返さないケース、`DataTransfer.files` が空の場合がある。
**Why it happens:** ブラウザ仕様差 + iOS Safari の clipboard API 制限（HTTPS かつユーザー gesture 内でのみアクセス可）。
**How to avoid:**
- モバイル幅では 📎 ボタンの使用を主系路とする（drag-drop はデスクトップ主用）
- paste 経路は desktop focus + HTTPS の前提で実装
- Phase 35 D-05 の mobile policy に沿って「破綻ゼロ」を保証、完全な iOS 対応は v6.1+
**Warning signs:** iPhone で paste しても何も起きない、drop 後に file が消える

### Pitfall 5: 複数タブからの同時アップロード競合
**What goes wrong:** 同一 thread を 2 タブで開き、両方から同時に添付アップロードすると、folder scan が別の turn の添付を拾う（D-11 の「新規添付分のみ」と矛盾）。
**Why it happens:** folder scan + `additional_kwargs` 注入は request 単位で行われ、他セッションの進行状態を知らない。
**How to avoid:**
- 本 phase では対応しない（Claude's Discretion に defer）。送信時点で staging state のみを `additional_kwargs` に入れ、folder scan は「過去 turn の存在通知」(SystemMessage prepend) 専用に限定する
- v6.1+ で `modified_at` 比較 / optimistic concurrency 検討
**Warning signs:** LLM が「別の会話で添付されたファイルがあります」と言い出す

### Pitfall 6: `_astream` と `_agenerate` の重複コード vs 共通ヘルパー
**What goes wrong:** `ChatCopilot._agenerate` と `_astream` の両方に同じ「最後の HumanMessage から `additional_kwargs["attachments"]` を取って SDK 型に変換」コードを書くと DRY 違反。
**Why it happens:** 既存コードが `_messages_to_prompt` は共通化しているが、`session.send_and_wait` と `session.send` は分かれている。
**How to avoid:**
- プライベートヘルパー `_extract_attachments(messages: Sequence[BaseMessage]) -> list[FileAttachment] | None` を ChatCopilot に追加、両メソッドから呼ぶ
- `BoundChatCopilot` は `_agenerate` を override しているが `super()._agenerate(augmented_messages, ...)` を呼ぶのでヘルパーは親クラスのまま使える
**Warning signs:** `_astream` で text/code は動くのに画像だけ付いていない、unit test で片方経路の attachments アサーションが通り片方が落ちる

### Pitfall 7: Canvas / debate グラフでの attachments 扱い
**What goes wrong:** Canvas 専用グラフ（`build_canvas_graph`）と Debate グラフ（`DebateGraph`）も同じ provider を使うが、`additional_kwargs["attachments"]` を入口で state に流すかどうかが決まっていない。
**Why it happens:** 複数アプリで handler が分かれているが、provider は共通。
**How to avoid:**
- 本 phase scope は ChatApp 中心（CONTEXT.md D-Discretion）。Canvas / Debate / SuperChat / Gem の attachments 対応は InputBar 流用範囲で自動継承（InputBar はこれら全アプリで共有されている — ChatApp.tsx / CanvasChatApp.tsx / DebateChatApp.tsx / GemChatApp.tsx / SuperChatApp.tsx が全て InputBar を使用）
- 各 handler（langgraph_handler / orchestrator_handler / debate_handler）で `HumanMessage(additional_kwargs={...})` への注入点を揃える planner タスクを立てる
- DebateChat は per-turn で SubAgent を切り替えるので、debate_handler 側で「どの turn の attachments を誰に見せるか」の判断が必要（最初の user message にのみ載せる案が妥当）
**Warning signs:** SuperChat で画像を添付しても SubAgent が画像を見ない、Canvas で添付したデータが HTML 生成に使われない

### Pitfall 8: `UploadFile.filename` の Unicode / path 埋め込み
**What goes wrong:** `UploadFile.filename` はクライアントから送られた生文字列で、`..` や `/` が含まれる可能性がある。そのまま storage_name 採番に使うと path traversal。
**Why it happens:** HTTP multipart spec 的に filename は任意文字列。ブラウザは basename だけを送ることが多いが、悪意ある client は任意値を送れる。
**How to avoid:**
- **`os.path.basename(uf.filename)` で正規化、さらに NFC normalize + 危険文字 (`/\\?*|:<>"`) を `_` 置換**
- path 生成後に realpath prefix assert（Phase 37 D-18 パターン）
- 許可 extension のホワイトリスト検証
**Warning signs:** `../../../etc/passwd.txt` がそのまま保存される、Unicode 正規化崩れ (`ﬁle.txt` vs `file.txt`)

### Pitfall 9: `GET /api/threads/{tid}/attachments/{name}` の MIME / Content-Disposition
**What goes wrong:** 画像を `<img src>` で読むとき `Content-Type` が `application/octet-stream` だとブラウザがレンダリングしない。HEIC を間違って png 拡張子で保存した場合も問題。
**Why it happens:** raw bytes をそのまま返すので MIME の責任はサーバー側。
**How to avoid:**
- `mimetypes.guess_type(name)` で推測、`FileResponse(path, media_type=mime)` で返す
- `Content-Disposition: inline; filename="<original>"` で inline 表示（download 強制しない）
- Phase 36 では 3 種形式のみ受け付ける（D-02）ので MIME 誤判定リスクは低い
**Warning signs:** img が表示されない、download dialog が勝手に出る

### Pitfall 10: `HumanMessage(additional_kwargs=None)` レガシーメッセージの読み取り
**What goes wrong:** 既存 (Phase 35 以前) の checkpoint 行を復元すると `additional_kwargs` が None / 欠損している可能性がある。frontend が `msg.additional_kwargs.attachments` を無条件 access すると crash。
**Why it happens:** LangChain のデフォルトは `additional_kwargs={}` だが、古いバージョンの serialize では `None` になることがある。
**How to avoid:**
- `get_thread_messages` 側で `entry["additional_kwargs"] = getattr(msg, "additional_kwargs", None) or {}` と None-guard
- frontend 側も `msg.additional_kwargs?.attachments ?? []` のデフォルト値で参照
**Warning signs:** TypeError: cannot read property 'attachments' of null

## Code Examples

### Example A: Provider で additional_kwargs を取り出して SDK 型に変換

```python
# Source: app/providers/copilot.py (本 phase で追加 — _agenerate / _astream 共通ヘルパー)
from copilot import FileAttachment  # TypedDict - NOT dataclass

class ChatCopilot(BaseChatModel):
    # ... 既存コード ...

    def _extract_attachments(self, messages: Sequence[BaseMessage]) -> list[FileAttachment] | None:
        """最後の HumanMessage の additional_kwargs["attachments"] を SDK 型に変換する。

        D-10/D-14/D-15: サイドカー envelope から TypedDict FileAttachment へ。
        他 kind (blob, directory, selection) は本 phase 未採用 — skip する。
        存在しなければ None を返す（session.send_and_wait は attachments=None を許容）。
        """
        last_human = None
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_human = m
                break
        if last_human is None:
            return None

        atts_meta = (last_human.additional_kwargs or {}).get("attachments") or []
        sdk_atts: list[FileAttachment] = []
        for a in atts_meta:
            if not isinstance(a, dict):
                continue  # 防御的: 想定外の型は skip
            if a.get("kind") != "file":
                continue  # D-15: blob 等は本 phase 未採用
            path = a.get("path")
            if not isinstance(path, str) or not path:
                continue
            entry: FileAttachment = {"type": "file", "path": path}
            display_name = a.get("name")
            if isinstance(display_name, str) and display_name:
                entry["displayName"] = display_name
            sdk_atts.append(entry)
        return sdk_atts or None

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        await self._ensure_client()
        prompt = self._messages_to_prompt(messages)
        sdk_atts = self._extract_attachments(messages)  # 新規
        try:
            session = await self._client.create_session(
                on_permission_request=PermissionHandler.approve_all,
                model=self.model,
            )
            self._register_usage_hook(session)
            response = await session.send_and_wait(
                prompt,
                attachments=sdk_atts,   # 新規
                timeout=self.send_timeout,
            )
            # ... 以下既存 ...
```

### Example B: Worker handler で job payload → HumanMessage.additional_kwargs

```python
# Source: app/jobs/handlers/langgraph_handler.py (本 phase で変更)
# 既存コード line 164:
# messages_input: list = [HumanMessage(content=prompt)]
# ↓ ↓ ↓ 変更
new_attachments = job.get("attachments") or []  # job payload から (D-14 dict のリスト)
if new_attachments:
    # D-18: vision 非対応モデル時の drop + SystemMessage 警告注入
    vision_ok = await self._is_vision_model(model)  # 新規ヘルパー（llm._client.list_models() 参照）
    if not vision_ok:
        image_atts = [a for a in new_attachments if a.get("ext", "").lower() in ("png", "jpg", "jpeg", "webp")]
        non_image_atts = [a for a in new_attachments if a not in image_atts]
        if image_atts:
            names = ", ".join(a["name"] for a in image_atts)
            warn_msg = SystemMessage(content=(
                f"以下の画像が添付されましたが、このモデル (`{model}`) は画像非対応のため内容を読めません: {names}。"
                "vision 対応モデル (例: claude-sonnet-4.6) への切替えをユーザーに案内してください。"
            ))
            # SystemMessage prepend は既存の effective_system_prompt に追記する形で注入
            effective_system_prompt = (effective_system_prompt or "") + "\n\n" + warn_msg.content
        new_attachments = non_image_atts

human_msg = HumanMessage(
    content=prompt,
    additional_kwargs={"attachments": new_attachments} if new_attachments else {},
)
messages_input: list = [human_msg]
```

### Example C: `GET /api/threads/{tid}/messages` に additional_kwargs を追加

```python
# Source: app/api/routes/chat.py:get_thread_messages 内 _messages_to_response (本 phase で変更)
def _messages_to_response(raw_messages: list) -> list[dict]:
    messages = []
    for msg in raw_messages:
        if isinstance(msg, (SystemMessage, ToolMessage)):
            continue
        role = "user" if isinstance(msg, HumanMessage) else "ai"
        entry: dict = {"role": role, "content": _normalize_content(msg.content)}
        sender = getattr(msg, "name", None)
        if sender:
            entry["senderName"] = sender
        # 新規 (D-22): additional_kwargs を透過的に返す
        kw = getattr(msg, "additional_kwargs", None) or {}
        if kw:
            # None-guard + 限定サブセットだけを返す（D-22: 最小限の公開）
            public_kw: dict = {}
            if "attachments" in kw and isinstance(kw["attachments"], list):
                public_kw["attachments"] = kw["attachments"]
            if public_kw:
                entry["additional_kwargs"] = public_kw
        messages.append(entry)
    return messages
```

### Example D: Frontend staging → POST /api/chat

```typescript
// Source: frontend/src/hooks/useChat.ts (本 phase で変更)
// 既存 sendMessage の中:
const readyAttachments = attachments.getReadyItems();  // useAttachments から
const { job_id } = await postChat({
  message: text,
  thread_id: resolvedThreadId,
  model: selectedModel,
  // ... 既存フィールド
  ...(readyAttachments.length > 0 ? {
    attachments: readyAttachments.map(x => ({
      kind: x.kind, name: x.name, storage_name: x.storage_name,
      path: x.path, size: x.size, mime_type: x.mime_type,
      ext: x.ext, modified_at: x.modified_at,
    })),
  } : {}),
});
// 送信成功 → clear
attachments.clearAll();
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Copilot SDK 0.1 の非対応により prompt embed | `FileAttachment` native API | SDK 0.2.0 (2026 early) | 画像 / text 両方に SDK 経由で渡せる、token 効率向上 |
| LangChain multimodal content parts の text ファイル型不定 | SDK 直渡しで LangChain 層を bypass | 本 phase D-09 | LangChain の standardization 待たずに実装可能 |
| Phase 35 までの MODEL_OPTIONS ハードコード | `GET /api/models` で SDK 由来 | 本 phase D-16 | モデル追加時の UI 修正不要、vision フラグも同経路で取れる |
| 画像 base64 inline (`BlobAttachment`) | path 渡し (`FileAttachment`) | 本 phase D-09 | checkpoint JSONB 肥大を避ける、folder 規約と整合 |

**Deprecated / outdated:**
- （本 phase 時点では特になし — Phase 37 の基盤が直近成立したばかり）

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | LangGraph `add_messages` reducer + PostgreSQL checkpointer は `HumanMessage.additional_kwargs` を JSONB で透過永続化する | Pattern 1 / Pitfall 1 | **MEDIUM** — ADR-0038 で `AIMessage.name` 喪失前例あり。integration check 必須。ダメなら handler 側で `_wrap_human_message_attachments` workaround が必要 |
| A2 | `ChatRequest.attachments: list[dict] \| None` は既存 pydantic ChatRequest に後方互換で追加できる | Dependencies | **LOW** — pydantic v2 は optional field 追加を許容 |
| A3 | Copilot CLI subprocess は worker container の `/shared/thread-files` RO mount からファイルを open() できる | SDK 調査 / Architecture | **LOW** — subprocess は同コンテナ内で、RO mount は read-only access を許すのでセマンティックは正常。ただし attachments_list/extract が既に RO で動いているため確度高い |
| A4 | `CopilotClient._models_cache` は lifespan 寿命で有効、明示的に stop() するまで持続 | Pattern 4 | **LOW** — client.py 確認済み（line 234, 404, 466）。stop/force_stop で clear される |
| A5 | `python-multipart>=0.0.22` の既存 installation で FastAPI `UploadFile` + `File(...)` がそのまま動く | Dependencies | **LOW** — pyproject.toml で確認、`fastapi>=0.135.2` は UploadFile 対応のメインストリーム |
| A6 | SDK `FileAttachment` TypedDict は dict リテラル `{"type": "file", "path": ..., "displayName": ...}` で組める（dataclass ではない） | Code Example A | **VERIFIED: copilot/types.py:42-47** — TypedDict であることを確認済み |
| A7 | SDK `session.send_and_wait(attachments=...)` のフィールド名は `attachments`（キー名 `attachments`、kwargs 経由） | Code Example A | **VERIFIED: copilot/session.py:166-222** — `attachments: list[Attachment] \| None = None` を確認済み |
| A8 | `ModelInfo.capabilities.supports.vision: bool` で vision 有無を判定、`.limits.vision: ModelVisionLimits \| None` で制約を取得 | Pattern 4 | **VERIFIED: copilot/types.py:750-854** — dataclass 定義を確認済み |
| A9 | worker の `/shared/thread-files` は RO mount だが、SDK subprocess の読み取りのみなので問題ない | Architecture | **LOW** — docker-compose.yml:117 `thread-files:/shared/thread-files:ro` を確認、SDK は open() read-only のみ |

**Risk Mitigation：** A1 は最大リスク。Wave 0 で `additional_kwargs` 永続化の smoke test（unit test で MemorySaver 経由・integration test で PostgreSQL 実物）を入れるのが必須。

## Open Questions (RESOLVED)

1. **Canvas / DebateChat / SuperChat での attachments 対応の具体境界**
   - What we know: InputBar は全アプリ共有なので UI 層は自動継承、D-Discretion で範囲を planner に委ねている
   - What's unclear: Debate の per-turn 切替で「最初の user message の添付」を全 agent に見せる vs turn ごとに別添付 という UX 仕様
   - Recommendation: **ChatApp 中心で完成させ**、他アプリは InputBar 流用で動く範囲（添付 → staging → POST /api/chat）だけ動かす。debate_handler / orchestrator_handler の `HumanMessage.additional_kwargs` 注入は同じ pattern で足すのみ。UI 仕様の詳細は Phase 38 / v6.1+ で再検討 → RESOLVED (採用)

2. **`/api/models` で CopilotClient 未初期化時の挙動**
   - What we know: lifespan で `llm = ChatCopilot(auth_manager=auth_manager)` を作るが、`_ensure_client()` は最初の chat で初めて起動する
   - What's unclear: ログインしていないユーザーが `/api/models` を叩いたとき、`list_models()` が失敗すべきか fallback 返すか
   - Recommendation: JWT Dependency で認証必須。未認証は 401。認証済みなら `await llm._ensure_client()` で lazy init。token が revoked なら `list_models()` 例外 → 503（`MODEL_OPTIONS` fallback は frontend 側で保持） → RESOLVED (採用)

3. **`ModelVisionLimits.supported_media_types` が `null` のモデル（= vision 非対応）の dict shape**
   - What we know: `supports.vision: bool` が False のモデルは `limits.vision` も None の可能性が高い
   - What's unclear: `supports.vision: True` だが `limits.vision: None` のケース（= 制約なし）があるか
   - Recommendation: UI 側は `vision_limits` が null なら「対応、制約情報なし」として pre-validate をスキップ。worker 側は画像サイズ / 枚数をベスト努力で通す（defense-in-depth に `IMAGE_HARD_LIMIT_BYTES=10_485_760 / MAX_IMAGES_PER_TURN=5` の hard cap を実装） → RESOLVED (採用)

4. **`AttachmentButton` / `AttachmentChips` / `VisionWarningBanner` の分割粒度**
   - What we know: CONTEXT は「具体分割は planner 判断」
   - What's unclear: どこまで reusable にするか（Phase 38 の出力 DL UI と共通化するか）
   - Recommendation: Phase 38 を見越した reusable な `FileChip` を切り出し、入力側は `AttachmentChips`（staging + upload progress + ×）、出力側は Phase 38 で `GeneratedFileChip` を別途作る想定（今回は参考情報として残す） → RESOLVED (採用)

5. **paste した画像のデフォルトファイル名（`image.png` 衝突問題）**
   - What we know: clipboardData から取った image は `blob` として file 名がないか `image.png` 固定になることが多い
   - What's unclear: 同一 thread で連続 paste 時の衝突回避
   - Recommendation: timestamp prefix (`YYYYMMDDTHHMMSS_pasted_<uuid4短縮>.png`) で衝突回避。サーバー側の storage_name 採番が tm prefix を既につけるので client 側は `image.png` のままで OK（サーバーがユニーク化） → RESOLVED (採用)

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `copilot` Python SDK | provider 配線 / `list_models()` | ✓ | 0.2.0 pinned | — |
| `python-multipart` | FastAPI UploadFile parser | ✓ | >=0.0.22 (pyproject.toml) | — |
| `fastapi` | `UploadFile` / `File(...)` | ✓ | >=0.135.2 | — |
| `langgraph-checkpoint-postgres` | `additional_kwargs` JSONB 永続化 | ✓ | >=3.0.5 | — |
| PostgreSQL | checkpointer backend | ✓ | pg17 (docker compose) | — |
| Redis | arq job queue + SSE | ✓ | 7-alpine | — |
| React 19 / Vite / Bun | frontend runtime | ✓ | 既存 | — |
| `/shared/thread-files` named volume | 書き込み / RO read | ✓ | docker-compose.yml:158 | — |
| nginx (本番時) | リバースプロキシ `client_max_body_size` | ✗（開発環境には無い — Vite dev server 直アクセス） | — | 本番デプロイ時に設定追加（Claude's Discretion 範囲外、docs/nginx.md に記載追加を planner が判断） |
| Pillow (画像リサイズ) | **使わない** (D-23 で不採用) | — | — | browser resize で十分 |

**Missing dependencies with no fallback:** なし

**Missing dependencies with fallback:**
- nginx `client_max_body_size`：開発環境は Vite dev server 経由で FastAPI に直接届くため 100MB 制限は FastAPI 側の chunked read で enforce する。本番 nginx は別途設定追加（planner が運用メモに記載）

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.25+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"`, `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_copilot_bind_tools.py tests/test_langgraph_handler.py -x` (関連 unit のみ) |
| Full suite command | `uv run pytest tests/ -x --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIN-01 | text/code ファイル添付 → `FileAttachment` に変換され `send_and_wait(attachments=[...])` が呼ばれる | unit | `pytest tests/test_copilot_attachments.py::test_text_file_attached -x` | ❌ Wave 0 (新規 test) |
| FIN-01 | worker が `additional_kwargs["attachments"]` を HumanMessage に注入する | unit | `pytest tests/test_langgraph_handler_attachments_v2.py::test_injects_additional_kwargs -x` | ❌ Wave 0 |
| FIN-01 | `POST /api/threads/{tid}/attachments` で multipart upload → folder 書き込み → D-14 dict 返却 | integration | `pytest tests/test_attachments_upload_route.py -x` | ❌ Wave 0 |
| FIN-01 | 100MB 超過は 413 で拒否 + 部分書き込みファイル削除 | integration | `pytest tests/test_attachments_upload_route.py::test_size_over -x` | ❌ Wave 0 |
| FIN-01 | path traversal (`../..`) を含む filename が拒否される | unit | `pytest tests/test_attachments_upload_route.py::test_path_traversal_blocked -x` | ❌ Wave 0 |
| FIN-02 | 画像添付 (png/jpg/webp) が同じ `FileAttachment` 経路で渡される | unit | `pytest tests/test_copilot_attachments.py::test_image_attached -x` | ❌ Wave 0 |
| FIN-02 | vision 対応モデルと非対応モデルで worker が画像を正しく drop / pass する | unit | `pytest tests/test_langgraph_handler_attachments_v2.py::test_vision_drop_on_non_vision_model -x` | ❌ Wave 0 |
| FIN-02 Success 3 | 非対応モデルで送信してもエラー停止せず、SystemMessage 警告が注入される | unit | `pytest tests/test_langgraph_handler_attachments_v2.py::test_non_vision_system_message_injected -x` | ❌ Wave 0 |
| FIN-02 Success 4 | checkpoint 再接続時に `additional_kwargs.attachments` が復元される | integration | `pytest tests/test_chat_history_additional_kwargs.py::test_roundtrip -x` | ❌ Wave 0 |
| D-22 | `GET /api/chat/history` が `additional_kwargs.attachments` を含む | integration | `pytest tests/test_api_chat.py::test_history_includes_additional_kwargs -x` | ❌ Wave 0 (既存ファイルに追加) |
| D-16 | `GET /api/models` が `[{id, name, vision, vision_limits, ...}]` を返す | integration | `pytest tests/test_api_models_route.py -x` | ❌ Wave 0 |
| D-17 UI | vision 非対応モデル選択時に画像を staging すると banner が出る | manual / e2e | chromium DevTools MCP + visual inspection | Manual — integration check |
| D-04 UI | 📎 / drop / paste 3 経路から staging される | manual / e2e | chromium DevTools MCP + Playwright-like steps | Manual — integration check |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_copilot_attachments.py tests/test_langgraph_handler_attachments_v2.py tests/test_attachments_upload_route.py -x` (関連 unit のみ、< 30 秒目標)
- **Per wave merge:** `uv run pytest tests/ -x --tb=short` (全 unit + integration)
- **Phase gate:** 全 unit green + docker compose 実環境で 1 経路 E2E（ADR-0046 integration check pattern）

### Wave 0 Gaps

- [ ] `tests/test_copilot_attachments.py` — provider レベル unit (FIN-01, FIN-02)：mock `session.send_and_wait` で `attachments` kwarg が正しい TypedDict リストで呼ばれることをアサート
- [ ] `tests/test_langgraph_handler_attachments_v2.py` — handler レベル unit（job payload → HumanMessage.additional_kwargs → provider）
- [ ] `tests/test_attachments_upload_route.py` — `POST` / `GET raw` / `DELETE` 3 route integration（`httpx.AsyncClient` + `fastapi` test client）
- [ ] `tests/test_api_models_route.py` — `GET /api/models` integration、TTL キャッシュ挙動、SDK 失敗時 fallback
- [ ] `tests/test_chat_history_additional_kwargs.py` — `AsyncPostgresSaver` で round-trip（**最重要**：A1 risk 検証）
- [ ] `tests/test_api_chat.py` への追加テスト — `additional_kwargs` 返却フィールド
- [ ] フロントエンド unit：`useAttachments.ts` は React Testing Library で staging state / upload / cancel / remove のシナリオをカバー（既存 frontend は unit test 構成なし — Phase 36 で入れる価値はあるが Claude's Discretion）
- [ ] E2E（docker compose 実機）：InputBar drop → chat → SDK 呼び出しログ確認（integration check として `docs/phase-36-integration-check.md` を作成）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | 全 attachments route で JWT httpOnly cookie（既存 `get_jwt_payload` Dependency） |
| V3 Session Management | yes | Redis JTI ブロックリスト（Phase 17 ADR-0014）、JWT expiry |
| V4 Access Control | yes | `thread_id` の所有者チェック — `threads.github_login == JWT github_login` を DELETE / POST で検証。ただし本 phase の upload は「thread 作成時点で ownership upsert 済」前提（chat.py:154 と同 pattern）。DELETE は既存 `delete_thread` で verify 済なので、単一ファイル DELETE route も同じチェックを通す |
| V5 Input Validation | yes | pydantic v2（request body）+ `os.path.basename` + realpath prefix assert + extension allowlist + MIME/size 上限 |
| V6 Cryptography | no | 本 phase では暗号化ストレージ不要。既存 JWT 暗号化（cryptography>=46.0.0）を流用 |
| V12 File upload | **yes (最重点)** | 下表 threat patterns 参照 |

### Known Threat Patterns for multipart upload + shared folder

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal (`../../etc/passwd`) | Tampering | `os.path.basename(uf.filename)` + storage_name timestamp prefix で正規化、最終 path で `os.path.realpath` + prefix assert（Phase 37 既存 pattern） |
| Zip bomb / 極大ファイル | DoS | chunked read で 1MB ずつ累計チェック、100MB 超過で 413 + 部分書き込み削除。nginx `client_max_body_size` 設定（本番） |
| MIME spoofing（偽 ext） | Tampering | extension allowlist（`.png/.jpg/.jpeg/.webp` for 画像、`text/*` MIME + `.txt/.md/.json/.csv/.py/.js` 等 for text）。magic byte sniff は Claude's Discretion |
| 他ユーザー folder への書き込み | Access Control | JWT github_login → path 組み立て（ユーザーが指定する余地なし）、realpath prefix assert |
| checkpointer 経由の機密情報漏洩 | Information Disclosure | `additional_kwargs["attachments"]` は name / path / size / mime / modified_at だけで機密内容は含めない（**content は SDK subprocess 経由でしか読まない**） |
| UI bypass での vision 非対応モデル送信 | Tampering / DoS | D-19 defense-in-depth：worker 側で画像を drop + warning SystemMessage、例外を上げない |
| EXIF / メタデータ漏洩 | Information Disclosure | 本 phase scope 外（社内 200 名、Claude's Discretion に defer）。v6.1+ 対応 |
| 複数タブ競合での thread ownership 競合 | Tampering | Phase 36 scope 外（Pitfall 5 参照） |
| CSRF（multipart upload への偽造 POST） | Tampering | SameSite=Lax cookie + CORS credentials 制御（既存 CORS middleware）で抑止 |
| XSS via filename（`<script>` 等） | Tampering | `filename` を HTML に表示する際は React の自動エスケープで通常は安全、D-14 `name` に `<` `>` 等が来たら `FileChip` の text rendering のみで使う（`dangerouslySetInnerHTML` 禁止） |

## Key File References

**Planner が読むべきファイル一覧（最小必要セット）:**

### Upstream contracts（これから書くコードが満たすべき契約）
- `.planning/phases/36-text-code-image-multimodal/36-CONTEXT.md` — D-01..D-23 + Claude's Discretion + Deferred
- `.planning/REQUIREMENTS.md` §FIN-01 / §FIN-02
- `.planning/ROADMAP.md` §Phase 36
- `docs/adr/0048-thread-files-folder-convention.md` — フォルダ規約 / ライフサイクル / realpath guard
- `.planning/phases/37-pdf-office-mcp/37-CONTEXT.md` — 隣接 phase 確定事項（再議論しない）
- `.planning/patterns.md` — 既存 ADR パターンカタログ

### Provider / SDK 配線（D-09〜D-13）
- `app/providers/copilot.py` — `_agenerate` (line 152-202) / `_astream` (line 204-280) / `_messages_to_prompt` (line 316-336)
- `.venv/lib/python3.12/site-packages/copilot/__init__.py` — SDK public symbols
- `.venv/lib/python3.12/site-packages/copilot/types.py` — `FileAttachment` (line 42-47), `ModelInfo` / `ModelCapabilities` / `ModelVisionLimits` (line 748-956)
- `.venv/lib/python3.12/site-packages/copilot/session.py` — `send` (line 122-164), `send_and_wait` (line 166-228)
- `.venv/lib/python3.12/site-packages/copilot/client.py` — `list_models` (line 976-1024), `_models_cache`
- `docs/adr/0031-copilot-sdk-token-streaming-three-layer-plumbing.md` — `_astream` 3 層配管の既存前提
- `docs/adr/0021-langgraph-bind-tools-toolnode-via-prompt-engineering.md` — BoundChatCopilot の tool 注入経路との共存

### Worker handler（D-11 / D-18）
- `app/jobs/handlers/langgraph_handler.py` — 既存 SystemMessage prepend (line 137-151), messages_input (line 164-170)
- `app/jobs/handlers/orchestrator_handler.py` — 同 prepend + per-job MCP client (line 104-125)
- `app/jobs/handlers/attachments_helper.py` — scan / build_hint ヘルパー（Phase 37 既存、変更不要）
- `app/jobs/handlers/debate_handler.py` — debate 経路への追加検討（planner 判断）
- `app/jobs/handlers/iframe_rpc_handler.py` — 本 phase scope 外（iframe RPC は attachments 経路を持たない）
- `app/jobs/worker.py` — `process_chat` シグネチャ拡張（attachments パラメータ追加）
- `app/orchestrator/state.py` — `AgentState.attachments` は既存、役割は「現在の folder 状態」に縮退

### API 層（D-03 / D-07 / D-08 / D-16 / D-22）
- `app/api/routes/chat.py` — `send_message` (line 111-192), `get_thread_messages` (line 441-567), `delete_thread` folder rm (line 350-413), `get_jwt_payload` / `get_github_token` Dependency (line 74-108)
- `app/api/models.py` — `ChatRequest` pydantic model（`attachments` フィールド追加）
- `app/api/main.py` — `include_router()` に `attachments` / `models` 追加 (line 371-382)
- `mcp_server/tools/attachments.py` — 既存 MCP ツール（realpath guard / basename 抽出の pattern 参照）

### Frontend（D-04 / D-05 / D-17 / D-21 / D-23）
- `frontend/src/components/InputBar.tsx` — toolbarSlot / previewSlot 既存、props 経由で `<AttachmentButton />` / `<AttachmentChips />` を差し込む
- `frontend/src/components/MessageArea.tsx` — bubble 描画 (line 223-325), 中でチップ行を追加 (D-21)
- `frontend/src/components/Header.tsx` — MODEL_OPTIONS 既存ハードコード (line 20-43), `/api/models` 由来へ移行 + fallback
- `frontend/src/hooks/useChat.ts` — `sendMessage` (line 132-369)：attachments を payload に含める
- `frontend/src/api/client.ts` — `apiFetch` 既存 (line 31-37)、multipart 対応の postAttachments / deleteAttachment / getModels を追加
- `frontend/src/components/ConfirmModal.tsx` — dialog UI 流用（削除確認等）

### テスト基盤
- `tests/conftest.py` — `jwt_cookie` / `mock_auth_manager` / `mock_graph` fixture
- `tests/test_langgraph_handler_attachments.py` — Phase 37 attachments_helper unit の参考形
- `tests/test_copilot_bind_tools.py` — ChatCopilot / BoundChatCopilot のモック pattern
- `tests/test_api_chat.py` — chat route integration pattern

### Docker / Build
- `docker-compose.yml` — volumes 定義 (line 154-159), api / mcp-server / worker の thread-files mount (line 45, 87, 117)
- `pyproject.toml` — `python-multipart>=0.0.22` / `github-copilot-sdk==0.2.0` / `fastapi>=0.135.2`

### Observability / Security 参照
- `docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md` — SystemMessage 注入パターン（D-18 踏襲）
- `docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md` — AIMessage.name 喪失問題（A1 risk 根拠）
- `docs/adr/0046-integration-check-surfaced-silent-failures.md` — unit green でも silent failure する経路（A1 検証 gate）
- `docs/adr/0014-phase17-security-hardening-jwt-blocklist-redis-and-endpoint-auth.md` — JWT / blocklist / endpoint auth
- `docs/adr/0043-chat-history-content-normalization-defense-in-depth.md` — `additional_kwargs` 経路でも content normalize を壊さないこと

## Recommended Implementation Approach

CONTEXT.md の D-01〜D-23 を尊重した上での **How**。planner がこの順で wave / task を切ると最小衝突で並列化できる。

### Wave 0: スキャフォールド + スパイク検証（risk 潰し）

1. **Test harness 新設**
   - `tests/test_copilot_attachments.py` の骨格（赤状態で OK）
   - `tests/test_chat_history_additional_kwargs.py` で A1 risk（additional_kwargs round-trip）を **最初に** 検証
   - `AsyncPostgresSaver` 経由で `HumanMessage(additional_kwargs={"attachments": [...]})` → checkpoint → 再 load → assert that attachments came back intact

2. **SDK 実験スパイク（docker compose 実環境）**
   - ad-hoc script で `session.send_and_wait("画像を見て", attachments=[{"type": "file", "path": "/tmp/test.png"}])` を実行し、実際に画像が読まれるか確認
   - 失敗したら即エスカレーション（SDK バージョン or path 仕様不一致）

### Wave 1: 配線 3 並列（Area 独立）

**Task 1-A: Provider 配線（app/providers/copilot.py）**
- `_extract_attachments` ヘルパー追加
- `_agenerate` / `_astream` の両方で ヘルパー呼び出し → `session.send_and_wait(attachments=...)` / `session.send(attachments=...)`
- `BoundChatCopilot` は `super()._agenerate()` 経由なので自動的に恩恵を受ける（要 unit test で確認）
- D-13 `_messages_to_prompt` は変更なし（attachments を文字列化しない）

**Task 1-B: Upload API 4 route（app/api/routes/attachments.py + models.py）**
- `POST /api/threads/{tid}/attachments` (multipart, chunked size check)
- `GET /api/threads/{tid}/attachments/{name}` (FileResponse raw bytes, JWT, realpath guard)
- `DELETE /api/threads/{tid}/attachments/{name}` (JWT + ownership check + realpath guard)
- `GET /api/models` (TTL 1h cache, SDK 由来)
- `app/api/main.py` に `include_router()` 追加
- `app/api/models.py` の `ChatRequest` に `attachments: list[dict] | None = None` 追加

**Task 1-C: Worker handler 拡張（langgraph_handler + orchestrator_handler + worker.py）**
- `worker.py:process_chat` シグネチャに `attachments: list[dict] | None = None` 追加、job dict に詰める
- LangGraphHandler：job.attachments を読んで `HumanMessage(additional_kwargs={...})` を作る
- D-18 vision drop ロジック：`ChatCopilot` に `async def is_vision_model(model_id: str) -> bool` を追加（`/api/models` と同じ経路）
- OrchestratorHandler 同様に追加（SuperChat 経路）
- debate_handler：最初の user message にのみ添付を載せる（Pitfall 7）

### Wave 2: Frontend 並列（3 コンポーネント + 2 hook）

**Task 2-A: AttachmentButton / AttachmentChips**
- `<AttachmentButton />`：📎 button + `<input type="file" multiple accept="image/png,image/jpeg,image/webp,text/*,.md,.py,.js,...">` + `ref.current.click()`
- `<AttachmentChips />`：画像 48x48 サムネ（`<img src=... width=48>`）/ pill（text/code）、× 削除ハンドラ
- Phase 35 の CSS 変数 / 暗黒モード / モバイル破綻ゼロ原則に従う

**Task 2-B: useAttachments hook**
- staging state + upload + cancel (AbortController) + removeItem (サーバー DELETE 連動)
- 3 入り口（click / drop / paste）を 1 関数 `upload(files: File[])` に集約
- pre-validate（ext / size / `vision_limits`）を内部で実行

**Task 2-C: VisionWarningBanner + /api/models 連携**
- `useModels()` hook：`/api/models` fetch + 1h TTL（localStorage ではなく in-memory）
- `<VisionWarningBanner />`：画像添付かつ `model.vision === false` のときに表示、「切り替える」ボタンで `setSelectedModel(claude-sonnet-4.6)` 相当
- `Header.tsx` の MODEL_OPTIONS を `/api/models` 由来に切替（未取得時は既存ハードコードを fallback）

**Task 2-D: MessageArea bubble チップ行（D-21）**
- User bubble / AI bubble の `Message.Footer` の前に `{msg.additional_kwargs?.attachments && <AttachmentChipRow atts={...} threadId={...} />}`
- 画像は `<img src={`/api/threads/${tid}/attachments/${storage_name}`} width={48}>`、text/code は pill
- クリック時アクションは最小（新タブで raw 開く / クリップボードへパス copy）、詳細は Claude's Discretion

**Task 2-E: useChat.sendMessage の payload 拡張**
- `readyAttachments` を postChat に渡す（useAttachments の `getReadyItems()` から取得）
- 送信成功で clear、技術失敗で clear（サーバー folder 削除と連動、D-06 ケース B）
- ユーザー明示キャンセル時は保持（D-06 ケース A）

### Wave 3: 履歴 UI 配線 + integration check

**Task 3-A: `GET /api/threads/{tid}/messages` に additional_kwargs**
- `_messages_to_response` の entry に `additional_kwargs.attachments` を追加（D-22）
- `loadThreadMessages` (`client.ts`) の型定義 `ChatMessage` に `additional_kwargs?: {attachments?: StagingItem[]}` を追加

**Task 3-B: `get_thread_messages` の全 thread 種別対応**
- chat / orchestrator / debate の 3 分岐すべてで `additional_kwargs` を通す
- None-guard（Pitfall 10）

**Task 3-C: Integration check gate（ADR-0046）**
- docker compose 実環境で以下を手動/chromium MCP で確認：
  1. text ファイル添付 → AI が内容言及
  2. 画像添付 + vision 対応モデル → AI が画像言及
  3. 画像添付 + vision 非対応モデル (`gpt-5-mini` 等) → エラーなし、AI が SystemMessage hint どおりに案内
  4. リロード後に bubble チップ復元
- `docs/phase-36-integration-check.md` に実トレース添付

### Wave 4: ADR + patterns.md + VALIDATION.md クローズ

- 新規 ADR 起票：「Phase 36: Copilot SDK 0.2.0 multimodal 添付の採用と隔離原則」
  - カテゴリ：LangGraph・Graph (primary) + Frontend・UI (secondary) — `.planning/adr-categories.yaml` に追記
- `.planning/patterns.md` に 2 エントリ追記：
  - LangGraph・Graph: 「HumanMessage.additional_kwargs サイドカー envelope で per-turn 添付情報を運ぶ」
  - Frontend・UI: 「3 入り口 (click/drop/paste) 統一 staging + AbortController キャンセル」
- VALIDATION.md クローズ、VERIFICATION.md 作成

### Implementation Ordering の合理性

- **Wave 0 を最初に** → A1 risk（additional_kwargs round-trip）を Phase 途中で発見すると workaround が plan 全体に影響するため
- **Wave 1 の A/B/C は完全並列** → provider / route / worker は interface 越しの I/O だけで結合、contract は D-14 dict スキーマで固定済み
- **Wave 2 UI は Wave 1 後（`/api/models` が動く必要）** → 5 タスクは hook / component レベルで並列化可能
- **Wave 3 は Wave 1 + 2 の合流** → 履歴 UI は backend と frontend の両方に依存
- **Wave 4 最後に ADR** → 実装が落ち着いてから起票（手戻り防止）

## Sources

### Primary (HIGH confidence)
- `copilot/session.py` (L122-228, L166-228): `send` / `send_and_wait` attachments kwarg
- `copilot/types.py` (L42-80, L748-956): `FileAttachment` / `Attachment` / `ModelInfo` / `ModelCapabilities` / `ModelVisionLimits`
- `copilot/client.py` (L168-234, L976-1024): `list_models` + internal cache
- `.planning/phases/36-text-code-image-multimodal/36-CONTEXT.md`: 全 D-XX 決定 locked
- `.planning/phases/37-pdf-office-mcp/37-CONTEXT.md`: 既存 Phase 37 contracts
- `docs/adr/0048-thread-files-folder-convention.md`: フォルダ規約
- `docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md`: AIMessage.name 喪失問題（A1 risk の根拠）
- `docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md`: SystemMessage 注入既存 pattern
- `docs/adr/0046-integration-check-surfaced-silent-failures.md`: integration check gate rationale
- `app/providers/copilot.py` 実装全文
- `app/jobs/handlers/langgraph_handler.py` / `orchestrator_handler.py` / `attachments_helper.py` 実装
- `app/api/routes/chat.py` 実装全文
- `app/api/main.py` lifespan 実装
- `docker-compose.yml` volumes 定義
- `pyproject.toml` 依存定義
- `frontend/src/components/InputBar.tsx` / `MessageArea.tsx` / `Header.tsx` / `hooks/useChat.ts` / `api/client.ts` 実装

### Secondary (MEDIUM confidence)
- FastAPI multipart upload docs（公式）の `UploadFile` + `File(...)` pattern — Pattern 3 で実証例に基づき記述
- LangChain `BaseMessage.additional_kwargs` の PostgreSQL JSONB ラウンドトリップ挙動 — ADR-0038 の部分逆証から推定（AIMessage.name だけが落ちる＝`additional_kwargs` は独立）、Wave 0 test で検証必須

### Tertiary (LOW confidence)
- iOS Safari の clipboardData / DataTransfer 挙動差（Pitfall 4）— 一般的な Web 開発常識だが、Phase 36 実機検証はモバイル scope 外なので LOW
- nginx `client_max_body_size` の本番運用値（Pitfall 3）— docs/nginx.md 要確認、planner 判断

## Metadata

**Confidence breakdown:**
- Standard stack / SDK API: **HIGH** — 実際に `.venv/lib/python3.12/site-packages/copilot/*.py` を読んで FileAttachment TypedDict / send_and_wait kwargs / list_models cache の 3 点をすべて確認済み
- Architecture / 配線設計: **HIGH** — 既存 Phase 37 の OrchestratorHandler + attachments_helper がそのまま再利用でき、provider / handler / API / frontend の各面で変更点が明確
- FastAPI multipart: **HIGH** — `python-multipart` 依存 + pydantic v2 が既存、新規発明は導入パターンのみ
- `additional_kwargs` 永続化（A1）: **MEDIUM** — AIMessage.name 喪失前例があるため 100% 保証はできない。Wave 0 でテストによる検証を必須化
- Pitfalls: **HIGH** — ADR-0038 / Phase 37 Code Review で現れた具体的失敗パターンを引用している
- Validation architecture: **HIGH** — 既存テスト基盤（pytest-asyncio + conftest.py fixture）が十分整備されており、追加は機械的に可能
- Security: **HIGH** — Phase 37 の realpath guard が確立 pattern、JWT Dependency は既存

**Research date:** 2026-04-23
**Valid until:** 2026-05-23（30 日 — SDK 0.2.0 pinning + Copilot モデルカタログは月次更新程度と想定）
