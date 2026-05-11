# Phase 36: ファイル入力 — text/code + image multimodal - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

チャット入力欄から **text/code 系ファイル** と **画像** を添付し、LLM が追加コンテキストとして参照できる基盤を確立する（FIN-01 / FIN-02）。Phase 37 が確立した `/shared/thread-files/<github_login>/<thread_id>/` フォルダ規約（ADR-0048）への **書き込み側** を実装し、Copilot SDK 0.2.0 の native attachments API（`FileAttachment` / `BlobAttachment` / `ModelCapabilities`）をラッパー経由で利用可能にする。

**Success Criteria（ROADMAP.md より）:**

1. .txt / .md / .json / .csv / .py / .js などの text/code 系ファイルを添付し、LLM が内容を参照して応答できる
2. .png / .jpg / .webp 画像を添付でき、multimodal 対応モデルで画像内容を踏まえた応答が得られる
3. multimodal 非対応モデル選択時に **エラーで止まらず** graceful にテキスト要約や警告にフォールバックする
4. 添付ファイルがチャット履歴（PostgreSQL checkpointer）に紐付き、スレッド再オープン時も確認できる

**scope 前提 — このフェーズの外:**

- 外部ストレージ連携（GitHub / Google Drive / URL import）は defer（新 phase / v6.1+）
- PDF / Office 抽出および MCP ツール経由参照は Phase 37 で完了済み — 本 phase では触らない
- 生成ファイルのダウンロード UI は Phase 38 の責務
- AI-UI 操作基盤（data-ai-role 属性）は Phase 32/33 の責務

</domain>

<decisions>
## Implementation Decisions

### 受付ポリシー（サイズ・件数・拡張子）

- **D-01:** text/code 系ファイルは **Phase 37 規定踏襲** とする:
  - 1 ファイル最大 100 MB
  - 抽出後 1 ファイル最大 50,000 文字 / 1 スレッド最大 200,000 文字（Phase 37 D-13）
  - 拡張子は success criteria 1 の例示（`.txt / .md / .json / .csv / .py / .js` 等）+ MIME が `text/*` であれば受諾
  - 超過時の挙動は Phase 37 の `attachments_extract` と整合（truncate + `truncated: true` 通知）
- **D-02:** 画像は **Phase 36 新規ポリシー**:
  - 1 枚最大 10 MB
  - 1 メッセージあたり同時添付 5 枚まで
  - 対応形式: `.png / .jpg (.jpeg) / .webp` の 3 種のみ（.gif / .bmp / .svg / .heic 等は非対応）
  - `ModelVisionLimits.max_prompt_image_size` / `max_prompt_images` / `supported_media_types` がこれより厳しければ **モデル由来の値を優先** する（UI 側で pre-validate）

### Upload UX と API 設計（Area 2）

- **D-03:** アップロードは **即時永続化方式**。📎 クリック / drop / paste した瞬間に `POST /api/threads/{thread_id}/attachments`（multipart/form-data）で `/shared/thread-files/<github_login>/<thread_id>/` へ書き込む。チップは永続化済みファイル（サーバー保存名）を指す。ChatGPT / Claude と同じメンタルモデル。
- **D-04:** 添付の入り口は **3 種サポート**:
  - 📎 ボタン + `<input type="file" multiple>`（必須）
  - Drag & Drop（InputBar 領域および MessageArea 全体への drop を受け付ける）
  - Ctrl+V / クリップボード画像ペースト（textarea focus 中の paste イベントから `image/*` blob を拾う）
- **D-05:** PreviewSlot（Phase 35 D-08 の予約スロット）の見せ方:
  - 画像: 48×48 または 64×64 のサムネ + 削除 `×` ボタン
  - text/code: `[📄 foo.py 2.4KB ×]` の pill 形式チップ
  - 全画面 modal zoom / 全文表示の実装は **Claude's Discretion**（planner / 実装判断）
- **D-06:** エラー / キャンセル時の挙動:
  - ケース B（**技術的失敗**: worker エラー、timeout、LLM 例外）→ 添付を folder から **自動削除**
  - ケース A（**ユーザー明示キャンセル**: stop / ESC）→ **残す**（再送信意図を尊重）
  - ケース C（**graceful fallback**: multimodal 非対応警告等 — 実行は成功扱い）→ **残す**
  - ケース D（**X ボタン手動削除**）→ `DELETE /api/threads/{thread_id}/attachments/{name}` で確実削除
- **D-07:** 新規 REST エンドポイントは **4 本**:
  - `POST /api/threads/{thread_id}/attachments` — multipart upload（複数ファイル対応）
  - `GET /api/threads/{thread_id}/attachments/{name}` — raw bytes 配信（画像は `<img src>` で直接読む）
  - `DELETE /api/threads/{thread_id}/attachments/{name}` — 単一ファイル削除
  - `GET /api/models` — `list_models()` キャッシュされた `ModelInfo` リスト（vision flag + limits 含む）
  - `GET /api/threads/{thread_id}/attachments`（一覧）は **作らない** — 履歴は `/api/chat/history` の `additional_kwargs` で取る（D-11 参照）
- **D-08:** 既存の `adelete_thread` → folder rm hook（Phase 37 D-03, ADR-0048）に **変更なし**。新規 DELETE 単一削除 route は realpath guard を踏襲し、thread folder prefix の外へは絶対に書き換え / 削除しない。

### ChatCopilot provider 拡張（multimodal 配線 — Area 1）

- **D-09:** Copilot SDK の **`session.send_and_wait(prompt, attachments=[...])` を採用**。`FileAttachment(path, displayName)` を text/code・画像の **両方** で使う（`BlobAttachment` は現時点では採用しない）。worker コンテナは thread-files volume を RO mount しているため、SDK subprocess が直接 path から読み込める前提。prompt embed は FIN-02 を満たせず、LangChain multimodal content-parts は text ファイル型が未定義なので却下。
- **D-10:** ラッパーが attachments を **受け取る envelope は `HumanMessage.additional_kwargs["attachments"]` のサイドカー方式**。handler は `HumanMessage(content="...", additional_kwargs={"attachments": [{kind, name, path, mime_type?, ...}, ...]})` として送り込む。`ChatCopilot._agenerate` / `_astream` が **最後の HumanMessage** の `additional_kwargs["attachments"]` を読んで `copilot.FileAttachment` / `copilot.BlobAttachment` に変換する。SDK 型は `app/providers/copilot.py` 内に閉じ込める（PROJECT.md "SDK Technical Preview — isolate behind wrapper" 原則、Phase 37 D-17 と同方向）。
- **D-11:** text/code も画像も **attachments で毎 turn eager に送る**。ただし attach するのは **新規添付分のみ**（「このターンでユーザーが送ろうとしている添付」）。過去 turn の添付は再 attach しない（SDK は `create_session` 毎回新規で state を持たないが、token 肥大を避けるため）。過去添付の情報は:
  - 既存 Phase 37 パターン（handler の `langgraph_handler.py` がフォルダ scan → SystemMessage metadata prepend）で LLM に "ファイルの存在" を知らせる
  - LLM が "内容を再度見たい" と判断したら `attachments_extract` MCP ツールを呼ぶ（既存経路）
- **D-12:** attachments_extract MCP ツール（Phase 37 D-14）の責務は **変更しない**:
  - Phase 36 で eager attach するのは **per-turn HumanMessage** 用途のみ
  - `attachments_extract` は execute_python sandbox からの参照（D-16: `sandbox_exposed: true`）と PDF/Office 向けの lazy fetch 用として残す
  - text/code の eager 読み込みと attachments_extract の lazy 読み込みは **並存**（LLM が判断して使い分け）
- **D-13:** `ChatCopilot._messages_to_prompt` は attachments を文字列化しない。attachments は **prompt 文字列とは別路** で SDK に渡す。

### Attachment 標準スキーマ（Area 1 追加決定）

- **D-14:** Request / job payload / `AgentState.attachments` / `HumanMessage.additional_kwargs["attachments"]` / `attachments_list` MCP ツール戻り値 — **全て同一 dict スキーマ** で統一する:
  ```python
  {
      "kind": "file",           # 現状は "file" のみ (BlobAttachment は将来拡張余地)
      "name": "original.png",   # LLM に見せるオリジナル名 (timestamp prefix は剥がす)
      "storage_name": "20260423T120000_original.png",  # folder 内の実ファイル名 (Phase 37 D-02)
      "path": "/shared/thread-files/<github_login>/<thread_id>/20260423T120000_original.png",
      "size": 12345,
      "mime_type": "image/png",
      "ext": "png",
      "modified_at": "2026-04-23T12:00:00Z",
  }
  ```
  - Phase 37 の `attachments_list` 戻り値 `{name, size, modified_at, ext}` を拡張する形（Phase 37 D-14）
  - フィールド追加は Phase 37 の互換性を壊さない（既存テストは 4 キーで assert）
- **D-15:** ラッパー内変換ルール:
  - `kind == "file"` → `copilot.FileAttachment(type="file", path=..., displayName=name)`
  - 将来的に `kind == "blob"` を追加する場合は `copilot.BlobAttachment(type="blob", data=base64, mimeType=..., displayName=...)`（本 phase では未採用）

### vision 判定と fallback（Area 3）

- **D-16:** **vision 対応判定は SDK の `client.list_models()` をソースとする**。hardcoded allowlist は持たない。実装:
  - worker 起動時（または API 起動時）に `list_models()` を呼んで `ModelInfo[]` を **TTL 1 時間** でキャッシュ
  - `GET /api/models` が キャッシュから `[{id, name, vision: bool, vision_limits: {...}?}, ...]` を返す
  - frontend は自分の `selectedModel` に対応する entry を見て 📎 / drop zone の挙動を決める
- **D-17:** vision 非対応モデル選択時の UI 挙動:
  - 📎 ボタンは常に active（text/code 添付は可能なため）
  - **画像を添付した瞬間** に InputBar 上部に **警告バナー** を表示: "現在のモデル (gpt-4.1) は画像非対応です。Claude Sonnet 4.6 などに切り替えると画像が読めます。`[切り替える]`"
  - ワンクリックで `setSelectedModel` が呼ばれ、バナーが消える
- **D-18:** 非対応モデルでそのまま送信した場合の **worker 側 graceful fallback**:
  - 画像は `attachments` から除外して SDK に送る（text/code は通常通り送る）
  - SystemMessage に「以下の画像が添付されましたが、このモデル (`<model_id>`) は画像非対応のため内容を読めません: `foo.png`, `bar.webp`。vision 対応モデル (例: claude-sonnet-4.6) への切替えをユーザーに案内してください」を注入
  - LLM が自然言語でユーザーに説明する（`web_search` の `{error: ...}` 方式と同方向 — 例外を投げずに graceful にする)
  - success criteria 3 の「エラーで止まらず graceful にフォールバック」を満たす
- **D-19:** **ModelVisionLimits を UI 側で pre-validate + worker 側で defense-in-depth 再検証**:
  - UI: 📎 添付時に `selectedModel` の `vision_limits.max_prompt_images` / `max_prompt_image_size` / `supported_media_types` をチェック、超過時は toast / banner で拒否
  - worker: payload を受け取った時点で再度検証、UI が bypass されても超過ファイルは drop + SystemMessage 警告

### チェックポイント保存と履歴 UI（Area 4）

- **D-20:** 履歴上の添付情報の **真実のソースは `HumanMessage.additional_kwargs["attachments"]`**。LangGraph checkpointer が PG の `langgraph_checkpoints.checkpoint` JSONB 列へ自動シリアライズする（LangGraph `add_messages` reducer の既存挙動）。folder scan は "現在の手持ち" の確認用であり、履歴ソースとしては使わない。
- **D-21:** 履歴 UI の表示位置は **メッセージバブル内の末尾にチップ行**:
  ```
  ┌─────────────────────────────┐
  │ (user avatar) これを解析して │
  │ [🖼 sample.png] [📄 data.csv]│  ← 添付チップ行
  └─────────────────────────────┘
  ```
  - 画像は 48×48 サムネ（`<img src="/api/threads/{id}/attachments/{name}">`）
  - text/code は `[📄 name size]` pill
  - クリック時のアクション（modal / ダウンロード / preview）は Claude's Discretion
- **D-22:** `GET /api/chat/history` の返り値 design: **`BaseMessage.additional_kwargs` をそのまま JSON で返す**。別エンドポイントは作らない。frontend は既存の `MessageArea` レンダリング枠内で `additional_kwargs.attachments` を見てチップを描画。既存の message シリアライズ（`app/api/routes/chat.py::get_thread_messages`）に `additional_kwargs` フィールドを足すだけで済む。
- **D-23:** 画像サムネ配信: **`GET /api/threads/{id}/attachments/{name}` で raw bytes を JWT 認証付きで返す**（D-07 の route を兼ねる）。専用サムネ生成（Pillow 64×64 キャッシュ等）は **しない** — browser の `<img>` resize で十分、ADR-0048 のフォルダ規約にサムネディレクトリを追加しない方針。パフォーマンス問題が出たら Phase 39 polish で再検討。

### Claude's Discretion

以下は research / plan / 実装段階で判断:

- upload progress UX（percent bar / spinner / 完了 toast の有無・位置）
- DELETE endpoint の返り値設計（204 / 200 + JSON）
- エラー表示 UI パーツの選択（既存 `ConfirmModal` 流用 / 新規 toast / inline banner — Phase 35 既存の dialog 系パターンに合わせる）
- SystemMessage 注入文言（日本語 / 英語・hint 記述の粒度 — ADR-0025 の既存パターン踏襲）
- `/api/models` キャッシュ TTL の具体値（目安 1 時間、SDK 呼び出しコストに応じて調整）
- サムネのピクセルサイズ（48 vs 64 vs 96）、クリック時の modal 有無
- upload 中のキャンセル UX（upload 進捗バーに × / ESC キー / 個別 cancel AbortController）
- 複数タブから同時アップロードした際の挙動（楽観更新 / `modified_at` 見ての競合検知は Phase 36 では扱わない想定、v6.1+）
- Gem / SuperChat / Canvas / DebateChat などの **他アプリからの添付サポート範囲** — Phase 36 は **ChatApp 中心**、他アプリは InputBar を既に使っている範囲で自動的に継承する方針。個別対応が必要になれば planner 判断で wave 追加
- モバイル幅 (≤767px) での drop zone / paste 挙動 — Phase 35 D-05 の "破綻ゼロ" 保証内で最低限動けば良い
- EXIF / メタデータサニタイズ — 社内 200 名利用では優先度低。判断は planner に委ねる（削除推奨・v6.1+ でも可）
- MIME sniff（ファイル末尾の magic byte 確認）— client-side の `File.type` で足りる想定、サーバー側 sniff は planner 判断
- multipart upload のサイズ制限実装方式（`fastapi.UploadFile.spool_max_size` / chunked streaming）
- `ChatCopilot._astream` での attachments 対応の足並み（`_agenerate` と同じ変換を重複させるか共通ヘルパー化するか）

### Folded Todos

以下は `.planning/todos/` 内の pending todo から本 phase の scope に fold 済み:

- `2026-04-14-file-input-upload-worker-output-download.md`（"チャット入力欄からファイルアップロード + Worker 生成ファイルのダウンロード"）の **入力側部分**。出力側は Phase 38 に残す。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 直接の要件と scope

- `.planning/ROADMAP.md` §Phase 36 — Goal / Depends on / Success Criteria 1–4
- `.planning/REQUIREMENTS.md` §FIN-01 / §FIN-02 — 要件定義

### パターンカタログ / ADR 索引（必須参照 — CLAUDE.md 運用ルール）

- `.planning/patterns.md` — ADR 由来のパターンカタログ
- `docs/adr/INDEX.md` — ADR カテゴリ別索引
- `.planning/adr-categories.yaml` — カテゴリマッピング（新規 ADR 追加時に記載）
- `CLAUDE.md` §"MCP Tool Catalog (Phase 30)" — MCP ツール追加時の SSoT ルール（本 phase では新規 MCP ツール追加予定なし、だが万一必要になった場合の参照）

### 隣接 Phase の確定 context（決定済みは再議論しない）

- `.planning/phases/37-pdf-office-mcp/37-CONTEXT.md` — フォルダ規約・attachments_list/extract・AgentState.attachments・SystemMessage prepend・delete hook・realpath guard の全決定
- `.planning/phases/35-dashboard-design-system/35-CONTEXT.md` — InputBar toolbarSlot / previewSlot 予約、CSS 変数、タブレット breakpoint、mobile policy
- `docs/adr/0048-thread-files-folder-convention.md` — `/shared/thread-files/<login>/<thread_id>/` 規約（書き込み側は本 phase で実装）

### Copilot SDK 0.2.0 multimodal API（Phase 36 の核）

- SDK 型参照（`.venv/lib/python3.12/site-packages/copilot/` 内の以下）:
  - `copilot.FileAttachment` — `{type: "file", path, displayName}`
  - `copilot.BlobAttachment` — `{type: "blob", data: base64, mimeType, displayName}`（本 phase では未採用・将来拡張）
  - `copilot.DirectoryAttachment` / `copilot.SelectionAttachment` — 非採用（ディレクトリ添付 / エディタ選択テキストは scope 外）
  - `copilot.ModelInfo` / `copilot.ModelCapabilities` / `copilot.ModelSupports.vision` / `copilot.ModelLimits.vision` / `copilot.ModelVisionLimits.{supported_media_types, max_prompt_images, max_prompt_image_size}`
  - `copilot.CopilotClient.list_models()` — モデルカタログ取得
  - `copilot.CopilotSession.send_and_wait(prompt, *, attachments=[...], timeout=...)` — attach 付き送信
- `docs/adr/0021-langgraph-bind-tools-toolnode-via-prompt-engineering.md` — Copilot SDK が native tool-calling 未対応だった経緯（multimodal 対応は native）
- `docs/adr/0031-copilot-sdk-token-streaming-three-layer-plumbing.md` — _astream の既存配線（attachments も同じ層に載せる想定）

### SystemMessage 注入・AgentState 関連 ADR

- `docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md` — SystemMessage prepend の既存パターン（D-18 のモデル非対応警告注入で踏襲）
- `docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md` — AIMessage/SystemMessage の checkpoint 保持時の注意（additional_kwargs 永続化の挙動確認に）
- `docs/adr/0042-user-model-override-propagation-to-subagents.md` — `model_override` 伝播経路（vision 判定は `selectedModel` 基準で行うため、SuperChat 等 SubAgent からの経路で `selectedModel` が何になるかを把握）
- `docs/adr/0026-thread-deletion-also-removes-threads-table-row.md` — thread 削除時の原子削除思想（attachment folder rm hook との整合、Phase 37 D-03 踏襲）

### MCP ツール / sandbox 連携（Phase 37 から引き継ぎ）

- `docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md` — YAML SSoT（新規 MCP ツール追加予定はないが、判断基準として参照）
- `docs/adr/0049-per-job-mcp-client-lifecycle-and-cancel-safe-exceptions.md` — per-job MCP client の現行ライフサイクル（Phase 36 で attach 経路が変わるが、attachments_extract は引き続きこの契約）
- `docs/adr/0041-codeact-direct-execution-over-react.md` — execute_python sandbox（`attachments_extract` が `sandbox_exposed: true` である前提）

### Web / DB / 認証の既存パターン

- `docs/adr/0001-nginx-prefix-strip-for-url-routing.md` — `/orochi` prefix（新規 route もこの prefix 下で動く）
- `docs/adr/0014-phase17-security-hardening-jwt-blocklist-redis-and-endpoint-auth.md` — JWT blocklist、未認証 endpoint の扱い（新規 attachment route は **必ず** JWT 認証を付ける）
- `docs/adr/0043-chat-history-content-normalization-defense-in-depth.md` — BaseMessage.content 正規化 + ReactMarkdown ガード（history 返り値に additional_kwargs を足す際も壊さないこと）

### コード参照点（scout_codebase で特定）

- `app/providers/copilot.py` — D-09/10/11/13 で `_agenerate` / `_astream` / `_messages_to_prompt` を変更。SDK 型変換はここに閉じる
- `app/orchestrator/state.py` — `AgentState.attachments` は Phase 37 で追加済み。D-20 で HumanMessage 側に寄せるので state 側の役割は "現在の folder scan 結果" のみに縮退（変更不要）
- `app/jobs/handlers/langgraph_handler.py` — Phase 37 の SystemMessage prepend（folder scan → metadata）。Phase 36 で画像を含めた際に prepend 文言の微修正が必要になる可能性
- `app/jobs/worker.py` — job payload から attachments を取り出し HumanMessage.additional_kwargs に注入する responsibility を追加
- `app/api/routes/chat.py` — `send_message` (POST /api/chat) 入口、JWT 認証フロー、`get_thread_messages` (D-22 の additional_kwargs 返却)
- `app/api/routes/` — 新規 route ファイル追加候補（e.g. `attachments.py`, `models.py`）。ルーティング登録は `app/api/main.py`
- `frontend/src/components/InputBar.tsx` — toolbarSlot / previewSlot 予約（Phase 35 D-08/D-09）。D-04/D-05 の 📎 / Drop / Paste / チップ描画はここへ差し込む
- `frontend/src/components/MessageArea.tsx` — bubble レンダリング。D-21 のチップ行をここへ追加
- `frontend/src/hooks/useChat.ts` — send 時に attachments staging を payload に乗せる改修
- `frontend/src/api/client.ts` — `apiFetch` に multipart 対応追加（D-03）
- `frontend/src/components/Header.tsx` — model selector と connected（D-17 のバナー切替ワンクリック）
- `docker-compose.yml` — `api` サービスの volume mount を **RW のまま**（Phase 37 D-04 で既に RW、追加変更なし）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`/shared/thread-files/<login>/<thread_id>/` フォルダ規約**（ADR-0048、Phase 37）— 書き込み側を本 phase で実装。パス階層・命名・ライフサイクル hook は全て既存
- **`InputBar.tsx` の toolbarSlot / previewSlot**（Phase 35 D-08）— `<AttachmentButton />` / `<AttachmentChips />` を差し込むだけ。既に予約済み
- **`AgentState.attachments` フィールド**（Phase 37 D-12）— D-20 で真実のソースは HumanMessage.additional_kwargs に寄せるが、handler 側の scan 結果の置き場所としては引き続き有用
- **`langgraph_handler.py` の folder scan + SystemMessage prepend**（Phase 37 D-11）— 画像対応の文言追記だけで再利用可
- **`attachments_list` / `attachments_extract` MCP ツール**（Phase 37 D-14）— execute_python sandbox と過去 turn の lazy fetch 用途でそのまま利用
- **`delete_thread` folder rm hook**（Phase 37 D-03, `app/api/routes/chat.py::delete_thread`）— 変更不要。単一ファイル削除は別 route（D-07）
- **JWT 認証 `get_jwt_payload` / `get_github_token` Dependency**（`app/api/routes/chat.py`）— 新規 attachment route にもそのまま適用
- **`apiFetch` wrapper**（`frontend/src/api/client.ts`）— multipart 対応追加のみ
- **`useChat` hook + SSE job ポーリング経路**（Phase 04）— payload に attachments を載せるだけで既存ジョブ経路を流用
- **`web_search` の `{error: ...}` 戻り値パターン**（`mcp_server/tools/web_search.py`）— D-18 の graceful fallback 設計の手本
- **realpath prefix guard**（Phase 37 D-18, `mcp_server/tools/attachments_extract` 実装）— 新規 DELETE / GET raw route でも踏襲
- **CSS 変数 + タブレット breakpoint + dark mode**（Phase 35）— バナー / チップ / モーダルのスタイルは token 経由で書けば自動で dark 対応
- **`ConfirmModal.tsx`**（既存）— 削除確認等の dialog UI を流用可能

### Established Patterns

- **RPCContext による thread_id / github_login 伝搬**（ADR 未番・Phase 11）— 新規 attachment route も JWT → RPCContext → folder path 解決で統一
- **SystemMessage metadata prepend**（ADR-0025、Phase 37）— D-18 の警告注入はこの既存パターンの同じ箇所に追加
- **error を例外ではなく structured response で返す**（web_search / attachments_extract）— D-18 の multimodal 非対応時もこの方向
- **Per-job MCP client ライフサイクル**（ADR-0049）— Phase 36 の ChatCopilot attach 経路は MCP を通らないが、attachments_extract の lazy 経路は引き続き per-job client で動く
- **`config/mcp_tools.yaml` SSoT**（ADR-0044）— 本 phase では **新規 MCP ツール追加なし**（attachments_list/extract で足りる）
- **LangGraph `add_messages` reducer + checkpointer**（Phase 06）— `additional_kwargs` を含む message オブジェクト全体が自動シリアライズされる。D-20 の前提
- **Integration check gate**（ADR-0046）— unit test green でも surface しない silent failure 対策。Phase 36 は `POST /api/chat` → worker → ChatCopilot → SDK → folder read の end-to-end が動くか必ず E2E で確認する
- **Phase 35 mobile policy（D-05）**— タブレット primary / スマホ破綻ゼロ保証。Phase 36 の drop zone / paste UX は最低限スマホで壊れないこと

### Integration Points

- **`app/providers/copilot.py`** — `_agenerate` / `_astream` を attachments 対応に拡張（D-09/10/11）。SDK 型変換はこのファイル内に閉じる
- **`app/jobs/worker.py`** — job payload の `attachments` フィールドを HumanMessage.additional_kwargs に注入
- **`app/jobs/handlers/langgraph_handler.py`** — SystemMessage prepend の画像対応文言追加（"以下の画像が添付: foo.png" 等）
- **`app/api/routes/` 新規ファイル** — `attachments.py` / `models.py` を追加し `app/api/main.py` でルーティング登録
- **`app/api/routes/chat.py::get_thread_messages`** — 返り値に `additional_kwargs` を含める（D-22）
- **`frontend/src/components/InputBar.tsx`** — toolbarSlot に `<AttachmentButton />` / previewSlot に `<AttachmentChips />` を props 経由で差し込む
- **`frontend/src/components/MessageArea.tsx`** — bubble 内チップ行の追加（D-21）
- **`frontend/src/hooks/useChat.ts`** — send 時の payload 構築、staging state 管理
- **`frontend/src/api/client.ts`** — multipart POST 対応追加
- **`frontend/src/components/Header.tsx`** — D-17 のワンクリックモデル切替対応
- **新規 frontend コンポーネント**: `AttachmentButton.tsx` / `AttachmentChips.tsx` / `VisionWarningBanner.tsx`（具体分割は planner 判断）
- **MenuScreen** — Phase 35 D-04 により Phase 36 では **触らない**（最近アップロードしたファイル等のセクション追加なし）

### 既存コードの状態（Phase 36 で活用／補う）

- **SDK 0.2.0 multimodal は native 対応済み**（今回の discovery） — ChatCopilot wrapper の設計ミスなく載せ替えできる
- **multipart upload pattern はプロジェクト初導入** — `fastapi.UploadFile` / `File(...)` が既存コードには皆無。planner 側で新規パターンとして扱う必要あり
- **`/api/models` endpoint は未実装** — 現状 frontend は model 一覧を `Header.tsx` にハードコード（Line 22-41）。D-16 で SDK 由来に切替え（既存 hardcoded は互換性のため fallback として一時保持可、ただし主系路は SDK 由来）
- **frontend 側に file / drag-drop / paste ハンドラ皆無** — 新規 hook / コンポーネントとして追加
- **`HumanMessage.additional_kwargs` に何かを入れる前例は少ない** — `ask_user_question`（Phase 27）で AIMessage.additional_kwargs は使用。message-level 付随情報を checkpointer 経由で永続化した前例は Phase 27 相当

</code_context>

<specifics>
## Specific Ideas

- **SDK 隔離原則**: `copilot.FileAttachment` / `copilot.BlobAttachment` / `copilot.ModelInfo` の import は **`app/providers/copilot.py` の中だけ** に閉じる。他モジュールは全て dict スキーマ (D-14) で扱う。Phase 37 D-17 (RPCContext による thread 解決) と同じく "SDK の変更影響を provider に閉じ込める" 原則の継続
- **per-turn 新規添付 vs 永続ファイル**: frontend は "このターンで送ろうとしている新規添付" のみを InputBar PreviewSlot に表示する。過去 turn の添付（folder に物理的に残っている）は MessageArea bubble 内のチップからのみ見える（D-21）。これにより「InputBar = 送信候補」「MessageArea = 送信済み履歴」の区別が UX に一貫
- **vision 判定 cache 戦略**: `list_models()` は起動時 + 60 分 TTL で十分。Copilot モデル追加はデプロイサイクルに同期するので、runtime でのモデル増減はない前提
- **FIN-02 graceful の二段構造**: UI 層（D-17: 警告バナー）と worker 層（D-18: SystemMessage 注入）の両方で graceful fallback を担保する。UI で気付かずに送信しても技術的失敗にならない
- **画像サムネは browser resize で十分**: 社内 200 名規模 + `<img width="48">` 手法で帯域は問題にならない想定。ADR-0048 のフォルダ規約を汚さない（`.thumb/` サブフォルダを作らない）方針
- **attachments_extract MCP ツールは温存**: Phase 36 で eager attach しても、execute_python sandbox 経由の解析 / 過去 turn の内容再確認 / 大きな text/code の lazy 読み には依然として価値がある。役割分担を明示して ADR 化（本 phase で追加 ADR を起票予定）
- **multipart upload は FastAPI の `UploadFile.spool_max_size`** を活用して 100MB 制限を spooling レベルで enforce する（具体値は planner 判断）
- **staging state のクリアタイミング**: 送信成功 → clear、ユーザー明示キャンセル → 保持、worker エラー → 保持（サーバー側で folder 削除してもチップは残す? → ここは UX として「チップも消える = サーバーと一致」が望ましい、planner で詰める）

## 新規 ADR の見込み

本 phase 完了時に以下の ADR 起票を検討:

- **Phase 36: Copilot SDK 0.2.0 multimodal 添付の採用と隔離原則**（`copilot.FileAttachment` / `BlobAttachment` / `ModelVisionLimits`、additional_kwargs サイドカー envelope、Phase 37 フォルダ規約との接続）
- patterns.md カテゴリ: `LangGraph・Graph` もしくは `Frontend・UI` + `MCP・Tools` secondary

</specifics>

<deferred>
## Deferred Ideas

### 他 phase / 他 milestone 回し

- **外部ストレージ連携**（GitHub / Google Drive / URL import）— 新 phase または v6.1+。OAuth / API Rate / SSRF / Privacy の議論が必要
- **Gem / SuperChat / Canvas / DebateChat 各アプリでの添付 UX 調整** — Phase 36 は ChatApp 中心。InputBar 流用で自動継承する範囲を超える個別対応は planner 判断で wave 追加 or 別 phase
- **専用サムネ生成 (Pillow 64×64 キャッシュ)** — browser resize で帯域問題が出てから Phase 39 polish で再検討
- **EXIF / メタデータサニタイズ** — 社内 200 名では優先度低、必要なら v6.1+
- **複数タブからの同時アップロード競合制御** — `modified_at` 比較 / optimistic concurrency は v6.1+
- **`attachments_read_bytes` のような MCP tool** — execute_python sandbox から volume mount 経由で直接 open() できるので不要（Phase 37 deferred 継承）

### v6.1+

- **OCR（画像テキスト抽出）** — vision 非対応モデル時の代替として MarkItDown + tesseract 系を検討（Phase 37 D-08 と同じく defer）
- **過去 turn 添付の一括管理 UI**（スレッド単位の attachment 一覧パネル）— MessageArea bubble チップで十分な場合はずっと作らない
- **ダウンロード UI / 画像拡大 modal** — Claude's Discretion 範囲で最小対応、本格的な viewer は Phase 38 (FOUT) に寄せる

### 明示的に本 phase 外

- Phase 38: worker 生成ファイルの DL + プレビュー + ユーザー別保持
- Phase 32/33: AI-UI 操作基盤 (data-ai-role 属性)
- Phase 39: UI バグ潰し (chatscope バルーン幅、Mermaid hang 等)

</deferred>

---

*Phase: 36-text-code-image-multimodal*
*Context gathered: 2026-04-23*
