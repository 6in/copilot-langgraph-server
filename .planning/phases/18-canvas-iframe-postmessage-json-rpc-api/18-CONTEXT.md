# Phase 18: Canvas iframe postMessage JSON-RPC API ブリッジ - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

デプロイ済み Canvas アプリ（HTML）の中の JavaScript から、postMessage 経由で親フレームの API を呼び出せる仕組みを実装する。
親フレームが JSON-RPC リクエストを受け取り、arq ワーカーに委譲して処理し、結果を iframe に返す。
今回サポートするメソッドは **QUERY**（SELECT 専用 DB クエリ）と **AI**（ワンショット Copilot 呼び出し）の 2 つ。

</domain>

<decisions>
## Implementation Decisions

### postMessage 受信レイヤー
- **D-01:** `CanvasPane.tsx` の `useEffect` 内で `window.addEventListener('message', handler)` — React コンポーネントが受信を担当
- **D-02:** 受信時に `e.origin !== window.location.origin` の場合は即座に無視（origin 検証必須）
- **D-03:** Web Worker は使用しない。React 管理下で実装し、複雑性を避ける

### レスポンス返却方式
- **D-04:** 既存の SSE フローをそのまま流用する
  - `CanvasPane` が `POST /api/iframe-rpc` を呼び → `job_id` を受け取る
  - `GET /api/job/{id}/stream`（SSE）で完了を待つ
  - 完了後、CanvasPane が `iframe.contentWindow.postMessage(result, '*')` で iframe に返す
- **D-05:** JSON-RPC の `id` フィールドでリクエストとレスポンスを対応付ける（iframe 側は Promise + id マップで管理）

### arq ワーカー側のルーティング
- **D-06:** タスク識別子は `iframe_app_api`（既存 `process_chat` と同じ arq キューを使用）
- **D-07:** JSON-RPC `method` フィールドでハンドラを分岐: `QUERY` → DB 処理、`AI` → Copilot 処理

### QUERY メソッド（DB アクセス）
- **D-08:** パラメータ: `pool_name`（文字列）、`sql`（SELECT のみ）、`user`（実行ユーザー）
- **D-09:** SELECT 以外（INSERT/UPDATE/DELETE/DROP 等）は拒否してエラー返却
- **D-10:** 結果フォーマット: `{"result": true, "rows": [{...}, ...]}`
- **D-11:** エラー時: `{"result": false, "error": "メッセージ"}`

### AI メソッド（Copilot 呼び出し）
- **D-12:** パラメータ: `model`（文字列）、`prompt`（文字列）
- **D-13:** 結果フォーマット: `{"result": true, "responseText": "..."}`
- **D-14:** ワンショット（会話履歴なし）。LangGraph グラフは使用せず `ChatCopilot` を直接呼び出す

### DB プール設定
- **D-15:** `config/db_pools.yaml` に DSN のみ記述。pool_name → DSN のマッピング
- **D-16:** フォーマット:
  ```yaml
  pools:
    main:
      dsn: postgresql://user:pass@postgres:5432/app
    analytics:
      dsn: postgresql://user:pass@analytics-db:5432/data
  ```
- **D-17:** Docker Compose でホストの `./config/` を `/app/config/` にマウント
- **D-18:** psycopg_pool の `AsyncConnectionPool` を使用。ワーカー起動時に初期化

### 既存デプロイ済みアプリへの適用
- **D-19:** 今回実装する CanvasPane（postMessage リスナー付き）で表示するアプリのみ有効
- **D-20:** 既存デプロイ済み HTML は変更しない。新規作成/更新されたアプリから自動的に API が利用可能

### Claude's Discretion
- JSON-RPC id の生成方式（UUID4 など）
- iframe 側の JavaScript ヘルパーライブラリの設計（Promise ラッパー）
- SQL SELECT 判定の実装方法（先頭キーワード判定 or sqlparse）
- psycopg_pool の最小/最大接続数デフォルト値

</decisions>

<specifics>
## Specific Ideas

- 「iframe で動作する HTML の JavaScript から親フレームへ message を post して、様々な API として呼び出せる機能」（docs/pre/iframe_app_enhanced.md より）
- 現在の AI 呼び出しフロー（Redis キュー → arq ワーカー）と同じパターンで実装する
- iframe 側は `postMessage` + Promise でシンプルに使えるようにする（Canvas アプリを作る AI が書きやすい API を意識）

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 事前設計ドキュメント
- `docs/pre/iframe_app_enhanced.md` — Phase 18 の原案。API 仕様・パラメータ・レスポンス形式の出発点

### 既存 Canvas 実装
- `app/api/routes/canvas.py` — Canvas CRUD API（upload/get/patch/deploy）。iframe-rpc エンドポイントを追加する際の参考
- `frontend/src/components/CanvasPane.tsx` — postMessage リスナーを追加するファイル（iframe sandbox 設定含む）
- `frontend/src/hooks/useCanvas.ts` — Canvas 状態管理 Hook

### 既存ジョブ/SSE パターン
- `app/jobs/worker.py` — arq ワーカー実装。`TASK_HANDLERS` dict へ `iframe_app_api` を追加するパターン
- `app/jobs/job_store.py` — JobStore パターン（Redis + asyncio.Queue）。SSE 通知フロー
- `app/api/routes/jobs.py` — `GET /api/job/{id}/stream` SSE エンドポイント（流用対象）
- `app/api/routes/chat.py` — `POST /api/chat` の enqueue パターン（iframe-rpc エンドポイントの参考）

### AI プロバイダー
- `app/providers/copilot.py` — `ChatCopilot`。AI メソッド実装で直接インスタンス化して使用

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/jobs/worker.py` の `TASK_HANDLERS` dict: `iframe_app_api` キーを追加するだけでルーティング可能
- `app/jobs/job_store.py` の `JobStore`: 変更なしで流用可能
- `app/api/routes/jobs.py` の SSE エンドポイント: 変更なしで流用可能
- `app/providers/copilot.py` の `ChatCopilot`: AI メソッドで直接使用可能

### Established Patterns
- arq ジョブ: `POST /api/xxx` → job_id 返却 → SSE で完了待ち → `GET /api/job/{id}` で結果取得
- CanvasPane の iframe sandbox: `allow-scripts allow-forms` のみ（`allow-same-origin` は禁止）
- psycopg 非同期: `AsyncConnection.connect(db_uri)` コンテキスト管理パターン

### Integration Points
- `CanvasPane.tsx`: postMessage listener 追加 + iframe への返信
- `app/api/routes/canvas.py`（または新規 `iframe_rpc.py`）: `POST /api/iframe-rpc` エンドポイント追加
- `app/jobs/worker.py`: `iframe_app_api` ハンドラ追加
- `docker-compose.yml`: `./config/` → `/app/config/` ボリュームマウント追加（api・worker サービス）

</code_context>

<deferred>
## Deferred Ideas

- Web API プロキシ（3番目のメソッド）— 仕様で言及されているが今回は QUERY と AI のみ実装。Web API 呼び出しは次フェーズ
- iframe 側ヘルパーライブラリの npm パッケージ化 — 今回はインライン JS のみ
- アクセス制御（allowed_users 等）— db_pools.yaml に接続情報のみ。ユーザー単位の制御は将来フェーズ

</deferred>

---

*Phase: 18-canvas-iframe-postmessage-json-rpc-api*
*Context gathered: 2026-04-08*
