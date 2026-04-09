# Phase 19: Canvas アプリのデプロイ＆ホスティング機能 - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

デプロイ済み Canvas アプリ（HTML）を `/apps/{app_id}/` URL で独立してホスティングする。
Phase 18 で実装した iframe postMessage JSON-RPC ブリッジ（AI/DB 呼び出し）が動作するホスティングシェルを FastAPI 動的ルートで配信する。
Canvas チャットエディタ（CanvasPane）は対象外 — あくまでデプロイ済みアプリのスタンドアロン配信に絞る。

</domain>

<decisions>
## Implementation Decisions

### ホスティングシェルの配信方式
- **D-01:** FastAPI 動的ルート `GET /apps/{app_id}` で shell HTML を動的生成して返す
- **D-02:** `main.py` で `StaticFiles("/apps")` より前に動的ルートを登録する（FastAPI のルート優先順位ルール）
- **D-03:** 動的ルートは新規モジュール（例: `app/api/routes/hosted_apps.py`）に切り出す

### Canvas app HTML の iframe 注入方式
- **D-04:** DB から HTML を取得して `srcdoc` に埋め込む — CanvasPane.tsx と同じパターン
- **D-05:** 既存の `GET /api/canvas/apps/{app_id}` エンドポイントの DB アクセスパターンを参考にする（JWT 保護なしで読む形に調整）
- **D-06:** iframe の sandbox 属性は Phase 18 の設定を踏襲: `sandbox="allow-scripts allow-forms"` （`allow-same-origin` は除外）

### RPC の認証戦略
- **D-07:** 暫定として `/api/iframe-rpc` の JWT 認証を不要にする（`Depends(get_jwt_payload)` を外す）
- **D-08:** shell HTML 自体は認証なしで誰でも URL を知ればアクセス可能
- **D-09:** iframe-rpc.js の fetch 呼び出しは `credentials: 'include'` のまま（将来の認証復活に備えて）

### 既存デプロイ済みアプリの互換性
- **D-10:** `static/apps/{app_id}/index.html` の静的ファイルはそのまま残す
- **D-11:** DB に HTML が存在するアプリ → 動的ルートで shell 付き配信
- **D-12:** DB に HTML がないアプリ（静的ファイルのみ）→ 404 または StaticFiles フォールバック（Claude の裁量）

### iframe-rpc.js の読み込み
- **D-13:** shell HTML から `<script type="module" src="/js/iframe-rpc.js"></script>` で読み込む（Phase 18 で `/js/` ルートが整備済み）

### Claude's Discretion
- shell HTML のスタイリング（シンプルなフルスクリーン iframe でよい）
- DB から app が見つからない場合のエラーページ
- `GET /apps/{app_id}` のレスポンスに `Cache-Control` ヘッダーを付けるか否か

</decisions>

<specifics>
## Specific Ideas

- CanvasPane で行っているように DB から HTML を取得して iframe に設定する、というのがユーザーの意図
- `/apps/{app_id}/` は社内向けの共有 URL として機能させたい（認証は将来フェーズで追加）
- 将来フェーズ（Deferred）: shell HTML で Copilot JWT チェック → 未ログインならログイン画面にリダイレクト（メニューアプリからのみアクセス可にする想定）

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 18 — RPC ブリッジ（流用対象）
- `app/api/routes/iframe_rpc.py` — `POST /api/iframe-rpc` エンドポイント。JWT 依存を外す変更対象
- `static/js/iframe-rpc.js` — ESM クライアントライブラリ。shell から `src="/js/iframe-rpc.js"` で読み込む
- `.planning/phases/18-canvas-iframe-postmessage-json-rpc-api/18-CONTEXT.md` — Phase 18 の全設計決定（D-01〜D-20）

### 既存 Canvas 実装
- `app/api/routes/canvas.py` — `GET /api/canvas/apps/{app_id}` の DB アクセスパターンを参考にする（HTML 取得ロジック）
- `frontend/src/components/CanvasPane.tsx` — `srcdoc` 注入パターンの実装参考

### エントリポイント
- `app/api/main.py` — StaticFiles マウント順序。動的ルートを `/apps` StaticFiles より前に登録する必要あり（L357 付近）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/api/routes/canvas.py` の `GET /api/canvas/apps/{app_id}`: DB から app の HTML を取得するクエリが実装済み。ただし JWT 保護あり — hosted_apps ルートでは直接 DB を叩くか、認証なしで呼び出せる形に調整
- `static/js/iframe-rpc.js`: Phase 18 で整備済みの ESM ライブラリ。shell HTML に `<script type="module" src="/js/iframe-rpc.js">` で読み込み可能
- `app/jobs/job_store.py` / `app/api/routes/jobs.py`: RPC の SSE フローは変更なし

### Established Patterns
- FastAPI ルート登録順: API ルーターは StaticFiles より前（`main.py` Pitfall 3）
- iframe sandbox: `allow-scripts allow-forms` のみ（`allow-same-origin` は禁止 — Phase 15 決定）
- psycopg 非同期アクセス: `AsyncConnection` / `pool` パターン（Phase 18 D-18 参照）

### Integration Points
- `app/api/main.py`: `hosted_apps.router` を `app.mount("/apps", ...)` より前に `include_router` する
- `app/api/routes/iframe_rpc.py`: `Depends(get_jwt_payload)` を削除して認証不要化（D-07）
- `static/apps/{app_id}/index.html`: 既存ファイルは触らない（D-10）

</code_context>

<deferred>
## Deferred Ideas

- shell HTML に Copilot JWT チェック＋ログインリダイレクト — メニューアプリからのみアクセス可にする認証フロー（将来フェーズ）
- `static/apps/{app_id}/index.html` の静的ファイルを DB 移行後に削除するクリーンアップ

</deferred>

---

*Phase: 19-canvas-apps-app-id-iframe-phase-18-rpc*
*Context gathered: 2026-04-09*
