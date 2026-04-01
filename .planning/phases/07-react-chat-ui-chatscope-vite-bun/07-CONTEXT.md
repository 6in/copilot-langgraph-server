# Phase 7: React Chat UI (chatscope + Vite + Bun) - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

`frontend/` ディレクトリに独立した React チャットアプリを実装する。
chatscope (`@chatscope/chat-ui-kit-react`) + Vite + Bun をスタックとして使用。
既存の Vanilla JS版 (`static/`) はそのまま残し、FastAPI が `/` と `/react` の両方を配信する形で並存する。

**スコープ外（このフェーズには含めない）:**
- ストリーミング応答（SDK 制約、v2 以降）
- モバイル対応
- nginx での振り分け
- Docker Compose への frontend サービス追加（必要なら後フェーズ）

</domain>

<decisions>
## Implementation Decisions

### Feature Scope

- **D-01:** Phase 7 は Vanilla JS 版と **フル機能パリティ** で実装する。
  - Device Flow 認証（コード表示・ポーリング・完了検知）
  - マルチターン会話表示（Markdown レンダリング）
  - スレッド履歴サイドバー（Thread 一覧 + 切り替え + New Chat）
  - モデル選択ドロップダウン（ハードコード一覧、gpt-4.1 デフォルト）
  - GitHub ユーザー情報表示（アバター + ログイン名）
  - SSE によるリアルタイム完了通知 + ポーリングフォールバック
  - ログアウト機能

### Authentication

- **D-02:** 認証フローは **React 内で完結**。Vanilla JS 側に依存しない。
  React アプリ単体で Device Flow を開始・ポーリング・JWT cookie 取得まで行い、完全独立したアプリとして動く。

### Theming & Design

- **D-03:** **chatscope のデフォルト CSS をそのまま使用**。既存 Vanilla JS の暗色テーマへの視覚的な一致は求めない。
  chatscope の標準スタイルを受け入れ、カスタム CSS の追加は最小限に留める。

### Production Serving

- **D-04:** `bun run build` で生成した `frontend/dist/` を FastAPI が `/react` パスで StaticFiles マウントする。
  - Vanilla JS 版は `/`（`static/`）のまま共存
  - 開発時: Vite dev server (`:5173`) + FastAPI API (`:8000`) の 2 プロセス構成
  - FastAPI に CORS ミドルウェアを追加して `localhost:5173` を許可する

### Layout (from Phase 3)

- **D-05:** メッセージバブルはユーザー右寄せ / AI 左寄せ（chatscope の `MessageList` はこのレイアウトを標準サポート）
- **D-06:** サイドバー（左）にスレッド履歴一覧 + New Chat ボタン
- **D-07:** モデル選択ドロップダウンのデフォルト値は `gpt-4.1`
- **D-08:** AI 応答待ち中は chatscope の typing indicator を使用

### Claude's Discretion

- SSE クライアントの選択（`EventSource` ネイティブ vs `@microsoft/fetch-event-source`）
- Markdown レンダリング（react-markdown など）
- スレッド名の表示方法（メッセージ先頭 or 日時フォーマット）
- エラー表示方法（インライン or トースト）
- `frontend/` のディレクトリ構造・コンポーネント設計
- docker-compose への統合（必要と判断した場合のみ）

### Folded Todos

- **React製チャットUIの分離 — chat-ui-kit-react + Vite + Bun** (area: ui)
  `bun create vite frontend --template react-ts` でスキャフォールド、CORS 追加、SSE 受信実装。このフェーズの本体と同一内容のため折り込み済み。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Project Context
- `.planning/REQUIREMENTS.md` — 受け入れ基準（AUTH, CHAT, SESS 要件）
- `.planning/PROJECT.md` — Core Value, Key Decisions, Out of Scope 一覧

### Existing Frontend (reference for parity)
- `static/app.js` — Vanilla JS 版の全機能実装（640行）。React 版が同等機能を実装する際のリファレンス
- `static/index.html` — 現在配信中の HTML 構造

### Existing Backend (integration points)
- `app/api/main.py` — FastAPI エントリポイント。StaticFiles マウント位置・CORS 追加場所
- `app/api/routes/auth.py` — Device Flow API（`/api/auth/start`, `/api/auth/check`, `/api/auth/logout`）
- `app/api/routes/chat.py` — チャット API（`POST /api/chat`）
- `app/api/routes/jobs.py` — ジョブ結果取得・SSE stream（`GET /api/job/{id}`, `/api/job/{id}/stream`）
- `app/api/routes/me.py` — GitHub ユーザー情報（`GET /api/me`）

### Stack Reference
- `CLAUDE.md` — 技術スタック決定、制約一覧（Bun/Vite/chatscope の採用背景）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `static/app.js` — 全 API 呼び出しパターン（fetch + SSE + ポーリング）の実装例。React 版のロジック実装時に参照する
- `app/api/models.py` — リクエスト/レスポンス型定義。TypeScript 型定義の参考になる

### Established Patterns
- JWT cookie 認証: Device Flow 完了後に `Set-Cookie: session=<jwt>` が発行される。React からは認証状態を `/api/me` の成功/失敗で確認できる
- SSE + ポーリングフォールバック: `POST /api/chat` → `job_id` → `EventSource(/api/job/{id}/stream)` → done → `GET /api/job/{id}` でリザルト取得
- スレッド管理: `GET /api/threads`, `POST /api/threads` などのエンドポイントが存在（`static/app.js` で確認可能）

### Integration Points
- `app/api/main.py` に CORS ミドルウェアを追加（`localhost:5173` を開発時に許可）
- FastAPI に `/react` パスで `frontend/dist/` を StaticFiles マウント（`static/` の `/` マウントより前に定義）
- `frontend/` は Python プロジェクトルートに独立モジュールとして配置

</code_context>

<specifics>
## Specific Ideas

- スキャフォールドコマンド: `bun create vite frontend --template react-ts`
- 開発時の起動: バックエンド `uvicorn app.api.main:app --reload` + フロントエンド `cd frontend && bun dev` を並行実行
- Vite 開発サーバーのプロキシ設定 (`vite.config.ts`) で `/api` を `:8000` にプロキシすると CORS 不要にもできる（Planner が判断）
- `frontend/dist/` は `.gitignore` に追加するか、CI でビルドするかを Planner が決定

</specifics>

<deferred>
## Deferred Ideas

- nginx による `/` と `/react` の振り分け（大規模運用では有効だが個人ツールでは不要）
- Docker Compose への `frontend` ビルドサービス追加
- ストリーミング応答（SDK Technical Preview 対応後）
- モバイル対応

### Reviewed Todos (not folded)

- **今回の仕組みの説明資料をPowerPointで作成する** (area: docs) — Phase 7 スコープ外。別途対応。

</deferred>

---

*Phase: 07-react-chat-ui-chatscope-vite-bun*
*Context gathered: 2026-04-02*
