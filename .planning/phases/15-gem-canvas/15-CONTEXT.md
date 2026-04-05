# Phase 15: gem/canvas 機能実装 - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning
**Source:** PRD Express Path (docs/pre/canvas_design.md) — 現在のアーキテクチャへの適合済み

<domain>
## Phase Boundary

### このフェーズで実装すること

1. **Gems テーブル + CRUD API** — ユーザーが作成できる AI ペルソナ（システムプロンプト）。`type` フィールドで `'default'` / `'canvas'` を区別する
2. **Canvas Apps テーブル + CRUD API** — チャットで生成したシングルファイル HTML の保存・取得・編集・デプロイ
3. **Worker 拡張** — Canvas Gem のスレッドでは HTML を抽出して `canvas_apps` に upsert するロジックを追加
4. **Deploy エンドポイント** — HTML を `static/apps/{app_id}/index.html` に書き出して `/apps/{app_id}/` で公開
5. **アップロード登録** — 外部で作った HTML をアップロードして canvas_apps に保存
6. **React フロントエンド拡張** — Gem 管理 UI（一覧・作成・選択）+ Canvas ペイン（エディタ/プレビュー切り替え + デプロイボタン）

### スコープ外（拡張フェーズ）

- 生成アプリからの社内 DB アクセス API
- 生成アプリ内から AI へのプロンプト連携 API
- バージョン管理・ロールバック
- デプロイ済みアプリの管理画面

</domain>

<decisions>
## Implementation Decisions

### データモデル — gems テーブル

- `gems` テーブルを PostgreSQL に追加（`app/api/main.py` の lifespan でマイグレーション）
- スキーマ:

```sql
CREATE TABLE IF NOT EXISTS gems (
    gem_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_login TEXT NOT NULL,
    name       TEXT NOT NULL,
    system_prompt TEXT NOT NULL DEFAULT '',
    type       TEXT NOT NULL DEFAULT 'default',  -- 'default' | 'canvas'
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS gems_github_login_idx ON gems(github_login);
```

- `threads` テーブルに `gem_id UUID REFERENCES gems(gem_id) ON DELETE SET NULL` カラムを追加（既存スレッドは NULL — gem なし = 通常チャット）

### データモデル — canvas_apps テーブル

```sql
CREATE TABLE IF NOT EXISTS canvas_apps (
    app_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id  TEXT REFERENCES threads(thread_id) ON DELETE SET NULL,
    github_login TEXT NOT NULL,
    name       TEXT NOT NULL,
    html       TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT 'canvas',  -- 'canvas' | 'upload' | 'builtin'
    deployed   BOOLEAN NOT NULL DEFAULT FALSE,
    deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS canvas_apps_thread_id_idx ON canvas_apps(thread_id);
CREATE INDEX IF NOT EXISTS canvas_apps_github_login_idx ON canvas_apps(github_login);
```

- `thread_id` は `TEXT` 型（既存 `threads.thread_id` が TEXT PRIMARY KEY のため）
- `upload` / `builtin` は `thread_id = NULL`

### マイグレーション方針

- `app/api/main.py` の lifespan 内に `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` を追記するのみ
- 既存テーブルを壊さない。既存スレッドの `gem_id` は NULL で問題なし

### Gems API — 認証

- すべての Gem エンドポイントは `Depends(get_jwt_payload)` で JWT 必須
- 自分の gem のみ操作可能（github_login 照合）

### Gems API エンドポイント（`app/api/routes/gems.py` 新規作成）

```
POST   /api/gems                  # Gem 作成
GET    /api/gems                  # 自分の Gem 一覧
GET    /api/gems/{gem_id}         # Gem 取得
PATCH  /api/gems/{gem_id}         # Gem 更新
DELETE /api/gems/{gem_id}         # Gem 削除
```

### threads テーブルとの接続

- `POST /api/threads` に `gem_id: str | None = None` を追加
- スレッド作成時に `gem_id` を `threads` テーブルに保存

### Canvas Apps API エンドポイント（`app/api/routes/canvas.py` 新規作成）

```
POST   /api/canvas/apps/upload           # HTML アップロード登録
GET    /api/canvas/apps/{app_id}         # アプリ取得（エディタ用）
GET    /api/canvas/apps?thread_id={id}   # スレッドの最新アプリ取得
PATCH  /api/canvas/apps/{app_id}         # HTML 編集・保存
POST   /api/canvas/apps/{app_id}/deploy  # デプロイ実行
GET    /api/canvas/apps/{app_id}/source  # デプロイ済みから元スレッドへ
```

- `/apps/{app_id}/` は FastAPI StaticFiles (`./static/apps/`) でサーブ

### Worker 拡張方針

- `app/jobs/handlers/langgraph_handler.py` の `LangGraphHandler.handle()` を拡張
- DB から `thread_id` → `gem_id` → `gems.type` を取得
- `gem.type == 'canvas'` の場合は AI 出力から HTML を抽出して `canvas_apps` に upsert
- `result_payload` に `{"type": "canvas", "app_id": ..., "html": ...}` を含める
- Canvas Gem のシステムプロンプト: 下記固定値を `gems.system_prompt` のデフォルトとして使用

```python
CANVAS_SYSTEM_PROMPT = """
あなたはシンプルな Web アプリを生成するアシスタントです。
以下のルールに従って出力してください。

- 必ずシングルファイルの HTML で出力する
- 出力は ```html から始まるコードブロックのみとする（説明文は不要）
- 外部 CDN は利用可能（Tailwind CSS・Chart.js・Alpine.js 等）
- スタイルは HTML 内の <style> タグに記述する
- スクリプトは HTML 内の <script> タグに記述する
"""
```

### HTML 抽出ロジック

```python
def extract_html(text: str) -> str:
    import re
    m = re.search(r"```html\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text
```

### Deploy 実装

- デプロイ先: `./static/apps/{app_id}/index.html`（`pathlib.Path` で書き出し）
- `canvas_apps.deployed = TRUE`, `deployed_at = now()` に更新
- `/apps/{app_id}/` は `app/api/main.py` で `StaticFiles(directory="./static/apps")` として mount（既存 StaticFiles の `/static/` とは別に `/apps/` を追加）
- nginx では `/apps/` → `./static/apps/` へ alias（既存 docs/nginx.md のパターンに倣う）

### Pydantic モデル

`app/api/models.py` に追加:
- `GemCreate(name, system_prompt, type)` — type は Literal['default', 'canvas'], default='default'
- `GemInfo(gem_id, name, system_prompt, type, created_at, updated_at)`
- `CanvasAppInfo(app_id, thread_id, name, html, source, deployed, deployed_at, created_at)`
- `CanvasDeployResponse(url: str)`

### フロントエンド — Gem 管理

- `frontend/src/components/GemSelector.tsx` 新規作成
  - ChatApp.tsx のスレッドサイドバー上部または入力エリアに「Gem 選択」UI を追加
  - Gem の作成・一覧・選択ができる
  - 選択中の Gem は `useChat` hook 経由でスレッド作成時に `gem_id` として送信

### フロントエンド — Canvas ペイン

- スレッドの AI 応答 `type == 'canvas'` の場合、チャットの右側 or 下側に Canvas ペインを表示
- Canvas ペインは「エディタ」「プレビュー」タブ切り替え
  - エディタ: `<textarea>` で HTML 編集 → `PATCH /api/canvas/apps/{app_id}` で保存
  - プレビュー: `<iframe srcDoc={html}>` でレンダリング
- 「デプロイ」ボタン: `POST /api/canvas/apps/{app_id}/deploy` → 完了後に `/apps/{app_id}/` の URL を表示

### Claude's Discretion

- 既存 `app/api/routes/apps.py` の route prefix が `/api` であることと衝突しないよう注意（canvas apps は `/api/canvas/apps/...`）
- フロントエンドの Canvas ペインのレイアウト詳細（幅比率、モバイル対応等）は実装者判断
- Gem の icon フィールドは v1 では実装しない（拡張フェーズ）
- `builtin` アプリの事前登録は v1 スコープ外

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### アーキテクチャ概要
- `CLAUDE.md` — プロジェクト全体のアーキテクチャ、技術スタック、規約
- `.planning/STATE.md` — フェーズ間の決定事項（Decisions セクション）

### 既存コード（拡張対象）
- `app/api/main.py` — lifespan でのマイグレーション追加パターン（gems/canvas_apps テーブル追加先）
- `app/api/routes/chat.py` — JWT auth パターン (`get_jwt_payload`, `get_github_token`)
- `app/api/routes/apps.py` — FastAPI route パターン（参照実装）
- `app/api/models.py` — Pydantic モデル追加先
- `app/jobs/handlers/langgraph_handler.py` — Worker 拡張対象（Canvas HTML 抽出ロジック追加先）
- `app/jobs/worker.py` — process_chat エントリポイント（拡張不要の可能性大）

### フロントエンド
- `frontend/src/components/ChatApp.tsx` — メインチャット UI（Canvas ペイン挿入先）
- `frontend/src/hooks/useChat.ts` — チャット状態管理（gem_id 送信対応先）
- `frontend/src/hooks/useThreads.ts` — スレッド CRUD（gem_id 追加先）
- `frontend/src/api/client.ts` — apiFetch ラッパー（Canvas/Gem API 呼び出しに使用）

### 設計仕様（PRD）
- `docs/pre/canvas_design.md` — 元の設計仕様（このフェーズの原点）

</canonical_refs>

<specifics>
## Specific Ideas

- `thread_id` の型は既存コードが TEXT を使っているため UUID 型ではなく TEXT 型で統一する
- `canvas_apps.upsert` の動作: `thread_id` + `github_login` で既存レコードを探し、あれば HTML を更新、なければ新規挿入（反復修正のたびに上書き）
- Deploy 済みアプリは `<iframe>` や別タブで確認できる URL として `/apps/{app_id}/` を返す
- デプロイ済みアプリの「修正する」リンク: `GET /api/canvas/apps/{app_id}/source` → `thread_id` を返す → フロントがそのスレッドを開く

</specifics>

<deferred>
## Deferred Ideas

- DB アクセス API（生成アプリから社内 DB を参照）
- AI プロンプト連携 API（生成アプリ内からプロンプトを投げる）
- バージョン管理・ロールバック
- アプリ一覧管理画面（デプロイ済みアプリの公開設定）
- Gem の icon フィールド
- builtin アプリの事前登録
- multipart upload の大容量対応

</deferred>

---

*Phase: 15-gem-canvas*
*Context gathered: 2026-04-05 via PRD Express Path (docs/pre/canvas_design.md)*
