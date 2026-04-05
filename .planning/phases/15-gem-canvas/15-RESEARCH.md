# Phase 15: gem/canvas 機能実装 - Research

**Researched:** 2026-04-05
**Domain:** PostgreSQL スキーマ拡張 / FastAPI ルート追加 / arq Worker 拡張 / React 19 フロントエンド拡張
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### データモデル — gems テーブル
- `gems` テーブルを PostgreSQL に追加（`app/api/main.py` の lifespan でマイグレーション）
- スキーマ: `gem_id UUID PK`, `github_login TEXT`, `name TEXT`, `system_prompt TEXT DEFAULT ''`, `type TEXT DEFAULT 'default'`（`'default'` | `'canvas'`）, `created_at/updated_at TIMESTAMPTZ`
- `threads` テーブルに `gem_id UUID REFERENCES gems(gem_id) ON DELETE SET NULL` を追加

#### データモデル — canvas_apps テーブル
- `app_id UUID PK`, `thread_id TEXT` (既存 threads.thread_id が TEXT 型), `github_login TEXT`, `name TEXT`, `html TEXT`, `source TEXT DEFAULT 'canvas'`（`'canvas'` | `'upload'` | `'builtin'`）, `deployed BOOLEAN DEFAULT FALSE`, `deployed_at TIMESTAMPTZ`, `created_at TIMESTAMPTZ`
- `thread_id` は TEXT 型（既存 `threads.thread_id` が TEXT PRIMARY KEY のため）

#### マイグレーション方針
- `app/api/main.py` の lifespan 内に `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` を追記するのみ
- 既存テーブルを壊さない

#### Gems API
- `app/api/routes/gems.py` 新規作成
- エンドポイント: `POST /api/gems`, `GET /api/gems`, `GET /api/gems/{gem_id}`, `PATCH /api/gems/{gem_id}`, `DELETE /api/gems/{gem_id}`
- すべて `Depends(get_jwt_payload)` で JWT 必須

#### threads テーブルとの接続
- `POST /api/threads` に `gem_id: str | None = None` を追加
- スレッド作成時に `gem_id` を `threads` テーブルに保存

#### Canvas Apps API
- `app/api/routes/canvas.py` 新規作成
- `POST /api/canvas/apps/upload`, `GET /api/canvas/apps/{app_id}`, `GET /api/canvas/apps?thread_id={id}`, `PATCH /api/canvas/apps/{app_id}`, `POST /api/canvas/apps/{app_id}/deploy`, `GET /api/canvas/apps/{app_id}/source`
- `/apps/{app_id}/` は `StaticFiles(directory="./static/apps")` でサーブ

#### Worker 拡張
- `app/jobs/handlers/langgraph_handler.py` の `LangGraphHandler.handle()` を拡張
- Canvas Gem 検出 → HTML 抽出 → `canvas_apps` upsert
- `result_payload` に `{"type": "canvas", "app_id": ..., "html": ...}` を含める

#### HTML 抽出ロジック（固定）
```python
def extract_html(text: str) -> str:
    import re
    m = re.search(r"```html\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text
```

#### Deploy 実装
- デプロイ先: `./static/apps/{app_id}/index.html`（pathlib.Path で書き出し）
- `/apps/{app_id}/` は `app/api/main.py` で `StaticFiles(directory="./static/apps")` として mount

#### Pydantic モデル（`app/api/models.py` に追加）
- `GemCreate(name, system_prompt, type)` — type は `Literal['default', 'canvas']`, default='default'
- `GemInfo(gem_id, name, system_prompt, type, created_at, updated_at)`
- `CanvasAppInfo(app_id, thread_id, name, html, source, deployed, deployed_at, created_at)`
- `CanvasDeployResponse(url: str)`

#### フロントエンド — Gem 管理
- `frontend/src/components/GemSelector.tsx` 新規作成
- Gem の作成・一覧・選択 UI
- 選択中の Gem は `useChat` hook 経由でスレッド作成時に `gem_id` として送信

#### フロントエンド — Canvas ペイン
- AI 応答 `type == 'canvas'` の場合、右側 or 下側に Canvas ペインを表示
- エディタ（`<textarea>`）+ プレビュー（`<iframe srcDoc={html}>`）タブ切り替え
- デプロイボタン → `POST /api/canvas/apps/{app_id}/deploy` → URL 表示

### Claude's Discretion
- 既存 `app/api/routes/apps.py` の route prefix が `/api` であることと衝突しないよう注意（canvas apps は `/api/canvas/apps/...`）
- フロントエンドの Canvas ペインのレイアウト詳細（幅比率、モバイル対応等）は実装者判断
- Gem の icon フィールドは v1 では実装しない（拡張フェーズ）
- `builtin` アプリの事前登録は v1 スコープ外

### Deferred Ideas (OUT OF SCOPE)
- 生成アプリからの社内 DB アクセス API
- 生成アプリ内から AI へのプロンプト連携 API
- バージョン管理・ロールバック
- デプロイ済みアプリの管理画面
- Gem の icon フィールド
- builtin アプリの事前登録
- multipart upload の大容量対応
</user_constraints>

---

## Summary

Phase 15 は既存の FastAPI + PostgreSQL + arq Worker + React 19 アーキテクチャに対して、Gem（AIペルソナ）と Canvas（シングルファイル HTML 生成・デプロイ）機能を追加するフェーズである。

**バックエンド側**は `gems` / `canvas_apps` テーブルを `lifespan` 内のマイグレーションで追加し、`app/api/routes/gems.py` と `app/api/routes/canvas.py` を新規作成する。既存の JWT 認証パターン（`Depends(get_jwt_payload)`）をそのまま踏襲できる。Worker 側は `LangGraphHandler.handle()` で Canvas Gem を検出した場合に HTML を抽出して `canvas_apps` upsert するロジックを追加する。

**フロントエンド側**は `GemSelector.tsx` コンポーネントと Canvas ペインを追加する。Canvas ペインは `type == 'canvas'` のレスポンスを受けたときだけ表示される条件付きレンダリングで実装し、`ChatApp.tsx` の既存レイアウトを大きく壊さないように右側に挿入する。

**Primary recommendation:** 既存のコードパターン（JWT依存、psycopg直接接続、arqジョブディスパッチ）を最大限踏襲し、新しい依存ライブラリを追加せずに実装する。

---

## Standard Stack

### Core（既存 — 追加不要）
| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| `fastapi` | >=0.135.2 | HTTP API | routes/gems.py, routes/canvas.py 追加先 |
| `psycopg[binary]` | >=3.2.0 | PostgreSQL 直接接続 | lifespan マイグレーション + ルート内 DB アクセス |
| `python-multipart` | >=0.0.22 | ファイルアップロード | `UploadFile` 対応（既インストール済み） |
| `PyJWT` | >=2.9.0 | JWT 認証 | `get_jwt_payload` 依存関係 |

[VERIFIED: pyproject.toml — 上記すべて既インストール済み]

### 追加不要な理由
Canvas のデプロイは `pathlib.Path.write_text()` のみで完結する。HTML 抽出は標準 `re` モジュールで完結する。新規ライブラリの追加は不要。[VERIFIED: docs/pre/canvas_design.md, 15-CONTEXT.md]

---

## Architecture Patterns

### 既存コードの重要パターン（調査済み）

#### マイグレーションパターン（`app/api/main.py` lifespan）
[VERIFIED: app/api/main.py L49-124]

```python
# 既存パターン — lifespan 内で psycopg.AsyncConnection を使って DDL を実行
async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
    await conn.execute("CREATE TABLE IF NOT EXISTS ...")
    await conn.execute("ALTER TABLE threads ADD COLUMN IF NOT EXISTS gem_id UUID ...")
    await conn.commit()
```

**重要な落とし穴:** `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` は PostgreSQL 9.6+ でサポートされているが、`threads` テーブルは lifespan 内でも `CREATE TABLE IF NOT EXISTS` で宣言されている。FK 追加順序に注意が必要:
1. `gems` テーブルを先に作成
2. `threads` テーブルに `gem_id` カラムを追加（`threads` テーブルは既存の `CREATE TABLE IF NOT EXISTS` 宣言の後）
3. `canvas_apps` テーブルは `threads.thread_id` を TEXT で参照するため順序依存あり

[VERIFIED: app/api/main.py — 既存テーブル作成順序を確認]

#### JWT 認証パターン
[VERIFIED: app/api/routes/chat.py L29-55]

```python
from app.api.routes.chat import get_jwt_payload  # gems.py, canvas.py で import

@router.post("/api/gems")
async def create_gem(body: GemCreate, payload: dict = Depends(get_jwt_payload)):
    github_login = payload.get("github_login", "unknown")
    ...
```

`get_jwt_payload` は `app/api/routes/chat.py` に定義されている。既存の `apps.py` も同じパターンで import している。[VERIFIED: app/api/routes/apps.py L18]

#### ルート登録パターン
[VERIFIED: app/api/main.py L191-197]

```python
# main.py — include_router の追加場所
app.include_router(gems.router)    # 新規追加
app.include_router(canvas.router)  # 新規追加
```

StaticFiles mount は既存の `/` catch-all の前に追加する必要がある（ルート登録順序の制約）。

#### StaticFiles mount パターン
[VERIFIED: app/api/main.py L202-206]

```python
# 既存パターン（参照）
if os.path.isdir("frontend/dist"):
    app.mount("/react", StaticFiles(directory="frontend/dist", html=True), name="react")

# 追加するパターン（Canvas apps 用）
import os
os.makedirs("./static/apps", exist_ok=True)  # ディレクトリ不在でも起動クラッシュを防ぐ
app.mount("/apps", StaticFiles(directory="./static/apps", html=True), name="canvas_apps")
```

**注意:** `static/apps/` ディレクトリが存在しない場合、`StaticFiles()` は起動時にクラッシュする。[VERIFIED: app/api/main.py L202 のガードパターンを参照]

#### Worker ジョブディスパッチパターン
[VERIFIED: app/jobs/worker.py, app/jobs/handlers/langgraph_handler.py]

```python
# LangGraphHandler.handle() 内の拡張ポイント
# 現状: result = await graph.ainvoke(...) → final_text = result["messages"][-1].content
# 拡張: gem_type を取得 → 'canvas' なら HTML 抽出 → canvas_apps upsert
```

Worker は `job["github_login"]` と `job["thread_id"]` を受け取れる（既に `process_chat` で渡されている）。[VERIFIED: app/jobs/worker.py L81-93]

#### フロントエンド — job レスポンスの型拡張
[VERIFIED: frontend/src/hooks/useChat.ts L80-86]

現在 `getJob(job_id)` は `{ status, result: string }` を返す。Canvas の場合は `result_payload` が `{"type": "canvas", "app_id": ..., "html": ...}` になるため、フロントが `result` の中身を解析して Canvas ペインを表示するか、通常テキストとして表示するかを判定する必要がある。

`job_store.save_result()` が文字列のみ受け付ける場合は `JSON.stringify(result_payload)` で文字列化してから保存し、フロントで `JSON.parse(result)` して判定する。

### 推奨プロジェクト構造（追加分のみ）

```
app/
  api/
    routes/
      gems.py          # 新規作成 — Gem CRUD
      canvas.py        # 新規作成 — Canvas Apps CRUD + Deploy
    models.py          # 既存 — GemCreate/GemInfo/CanvasAppInfo/CanvasDeployResponse 追加
  main.py              # 既存 — lifespan に DDL 追加, include_router 追加, /apps mount 追加

frontend/
  src/
    components/
      GemSelector.tsx  # 新規作成 — Gem 一覧・作成・選択 UI
      CanvasPane.tsx   # 新規作成 — エディタ/プレビュー/デプロイ UI
    hooks/
      useGems.ts       # 新規作成 — Gem CRUD state management
      useCanvas.ts     # 新規作成 — Canvas App state management
    api/
      client.ts        # 既存 — Gem/Canvas API 呼び出し関数を追加
    types.ts           # 既存 — GemInfo/CanvasAppInfo 型を追加

static/
  apps/                # 新規作成（空ディレクトリ） — デプロイ済みアプリの配置先
    .gitkeep
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML ファイルのサーブ | カスタム静的サーバー | `FastAPI.mount(StaticFiles(...))` | 既存の StaticFiles パターンが完全に適合する |
| JWT 認証チェック | カスタム認証ミドルウェア | `Depends(get_jwt_payload)` | 既存依存関係をそのまま再利用 |
| HTML 抽出 | html.parser / BeautifulSoup | `re.search(r"```html\n(.*?)```", ...)` | CONTEXT.md で固定済み |
| ファイルアップロード | カスタム multipart パーサー | `fastapi.UploadFile` | python-multipart は既インストール済み |
| DB upsert | 手動 SELECT + INSERT/UPDATE | PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` | 既存 chat.py のパターンと同じ |
| iframe サンドボックス | カスタム HTML レンダラー | `<iframe srcDoc={html} sandbox="...">` | ブラウザネイティブ、XSS 境界を自動的に提供 |

---

## Common Pitfalls

### Pitfall 1: StaticFiles が起動時にクラッシュする
**What goes wrong:** `./static/apps/` ディレクトリが存在しない状態で `StaticFiles(directory="./static/apps")` を mount しようとすると `RuntimeError` が発生する
**Why it happens:** FastAPI の StaticFiles は mount 時にディレクトリの存在を検証する
**How to avoid:** `os.makedirs("./static/apps", exist_ok=True)` を mount 前に実行するか、既存の `os.path.isdir()` ガードを使う
**Warning signs:** `RuntimeError: Directory './static/apps' does not exist`
[VERIFIED: app/api/main.py L202 のガードパターンを参照]

### Pitfall 2: threads.gem_id カラム追加の順序依存
**What goes wrong:** `gems` テーブルが存在しない状態で `ALTER TABLE threads ADD COLUMN IF NOT EXISTS gem_id UUID REFERENCES gems(gem_id)` を実行すると FK エラーになる
**Why it happens:** PostgreSQL は FK の参照先テーブルが存在しないと `ALTER TABLE` を拒否する
**How to avoid:** lifespan の DDL 実行順序を必ず `gems` → `canvas_apps` → `threads ALTER` の順にする
**Warning signs:** `psycopg.errors.UndefinedTable: relation "gems" does not exist`

### Pitfall 3: `/api/canvas/apps` と既存 `/api/apps` の衝突
**What goes wrong:** FastAPI の URL マッチングは先にマウントしたルートが優先される。`/api/apps` （AppRegistry）が `/api/canvas/apps` より先に登録されていると、誤ってマッチする可能性がある
**Why it happens:** FastAPI は prefix の長さでなく登録順でマッチングする
**How to avoid:** Canvas ルートのプレフィックスは `/api/canvas` にして `apps.py` の `/api/apps` と明確に分離する。main.py での include_router 順序は変更不要
**Warning signs:** `GET /api/canvas/apps/{id}` が 404 を返す場合

### Pitfall 4: job_store.save_result() が文字列のみ受け付ける
**What goes wrong:** Canvas モードでは `result_payload` が dict（`{"type": "canvas", "app_id": ..., "html": ...}`）だが、現在の `job_store.save_result()` は文字列を想定している
**Why it happens:** `JobStore.save_result()` の型が `str` のみ
**How to avoid:** Worker 側で `json.dumps(result_payload)` して保存し、フロントで `JSON.parse(result)` して判定する
**Warning signs:** フロントエンドが Canvas ペインを表示せず生の JSON 文字列をチャットに表示する

### Pitfall 5: Canvas Gem のシステムプロンプトが LangGraph グラフに渡されない
**What goes wrong:** 現在の `LangGraphHandler.handle()` は `graph.ainvoke({"messages": [HumanMessage(content=prompt)]})` を呼ぶだけで、システムプロンプトを注入していない
**Why it happens:** `build_graph()` は `system_prompt` パラメータを受け取らない設計になっている
**How to avoid:** Canvas Gem のシステムプロンプトは `HumanMessage` の前に `SystemMessage` として追加するのが LangChain の標準的な方法。`graph.ainvoke({"messages": [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]})` のように渡す
**Warning signs:** Canvas Gem を使っても AI が HTML を出力しない（システムプロンプトが無視されている）

### Pitfall 6: iframe の XSS リスク
**What goes wrong:** `<iframe srcDoc={html}>` で任意の HTML を描画すると、スクリプト実行が可能
**Why it happens:** `srcDoc` は HTML をそのまま描画する
**How to avoid:** `sandbox="allow-scripts allow-forms"` 属性を付ける（外部ナビゲーションをブロック、ローカルスクリプトは許可）。デプロイ済みアプリは CDN 利用を想定しているので `allow-same-origin` は不要
**Warning signs:** プレビュー内のリンクが親ページのナビゲーションを変更する

### Pitfall 7: canvas_apps upsert の識別キー
**What goes wrong:** upsert を `thread_id` + `github_login` で行う場合、同じスレッドで異なるユーザーが同じ HTML を更新できてしまう
**Why it happens:** threads テーブルに `github_login` はあるが、canvas_apps の upsert は worker 側で行われる
**How to avoid:** upsert の WHERE 条件は `thread_id = %s AND github_login = %s` にして所有権を確認する。`ON CONFLICT` は `(thread_id, github_login)` の unique constraint が必要（または明示的な SELECT + UPDATE）
**Warning signs:** 別ユーザーがスレッドの HTML を上書きする

---

## Code Examples

### lifespan への DDL 追加
[VERIFIED: app/api/main.py — 既存パターンから導出]

```python
# app/api/main.py lifespan 内（既存の applications/threads DDL の後に追加）

# gems テーブル（Gem ペルソナ管理）
await conn.execute(
    """CREATE TABLE IF NOT EXISTS gems (
           gem_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
           github_login  TEXT NOT NULL,
           name          TEXT NOT NULL,
           system_prompt TEXT NOT NULL DEFAULT '',
           type          TEXT NOT NULL DEFAULT 'default',
           created_at    TIMESTAMPTZ DEFAULT now(),
           updated_at    TIMESTAMPTZ DEFAULT now()
       )"""
)
await conn.execute(
    "CREATE INDEX IF NOT EXISTS gems_github_login_idx ON gems(github_login)"
)

# threads テーブルへの gem_id カラム追加（gems テーブル作成後に実行）
await conn.execute(
    "ALTER TABLE threads ADD COLUMN IF NOT EXISTS gem_id UUID REFERENCES gems(gem_id) ON DELETE SET NULL"
)

# canvas_apps テーブル（生成 HTML の保存）
await conn.execute(
    """CREATE TABLE IF NOT EXISTS canvas_apps (
           app_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
           thread_id    TEXT REFERENCES threads(thread_id) ON DELETE SET NULL,
           github_login TEXT NOT NULL,
           name         TEXT NOT NULL,
           html         TEXT NOT NULL,
           source       TEXT NOT NULL DEFAULT 'canvas',
           deployed     BOOLEAN NOT NULL DEFAULT FALSE,
           deployed_at  TIMESTAMPTZ,
           created_at   TIMESTAMPTZ DEFAULT now()
       )"""
)
await conn.execute(
    "CREATE INDEX IF NOT EXISTS canvas_apps_thread_id_idx ON canvas_apps(thread_id)"
)
await conn.execute(
    "CREATE INDEX IF NOT EXISTS canvas_apps_github_login_idx ON canvas_apps(github_login)"
)
```

### Worker 拡張（Canvas HTML 抽出）
[VERIFIED: app/jobs/handlers/langgraph_handler.py + 15-CONTEXT.md]

```python
# app/jobs/handlers/langgraph_handler.py — handle() 拡張部分
import json
import re
import psycopg

DB_URI = os.getenv("DATABASE_URL", ...)

def extract_html(text: str) -> str:
    m = re.search(r"```html\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text

async def _get_gem_type(thread_id: str, db_uri: str) -> tuple[str | None, str | None, str | None]:
    """thread_id から gem_id, gem_type, gem_name を取得する。"""
    async with await psycopg.AsyncConnection.connect(db_uri) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT g.gem_id, g.type, g.name, g.system_prompt
                   FROM threads t
                   LEFT JOIN gems g ON t.gem_id = g.gem_id
                   WHERE t.thread_id = %s""",
                (thread_id,)
            )
            row = await cur.fetchone()
            if row:
                return row[0], row[1], row[2], row[3]
            return None, None, None, None

# handle() 内 — graph.ainvoke() の前後に追加
gem_id, gem_type, gem_name, system_prompt = await _get_gem_type(thread_id, DB_URI)

# SystemMessage 追加（Canvas Gem の場合）
from langchain_core.messages import SystemMessage
messages_input = []
if system_prompt:
    messages_input.append(SystemMessage(content=system_prompt))
messages_input.append(HumanMessage(content=prompt))

result = await graph.ainvoke({"messages": messages_input}, config=config)
final_text = result["messages"][-1].content

# Canvas Gem の場合は HTML 抽出 + upsert
if gem_type == 'canvas':
    html = extract_html(final_text)
    async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
        row = await conn.execute(
            """INSERT INTO canvas_apps (thread_id, github_login, name, html, source)
               VALUES (%s, %s, %s, %s, 'canvas')
               ON CONFLICT DO NOTHING
               RETURNING app_id""",
            (thread_id, job.get("github_login", "unknown"), gem_name or "Canvas App", html)
        )
        # upsert: 既存レコードがあれば UPDATE
        # 注: ON CONFLICT には UNIQUE 制約が必要 → (thread_id, github_login) UNIQUE
        ...
    result_payload = json.dumps({"type": "canvas", "app_id": str(app_id), "html": html})
else:
    result_payload = final_text

await job_store.save_result(job_id, result_payload)
```

**注意:** `canvas_apps` の upsert には `(thread_id, github_login)` の UNIQUE 制約を追加するか、明示的な SELECT → UPDATE の2ステップを使う必要がある。CONTEXT.md では `ON CONFLICT` 方式を示唆しているため、DDL に `UNIQUE (thread_id, github_login)` を追加することを推奨する。

### FastAPI ルート — Gem CRUD パターン
[VERIFIED: app/api/routes/apps.py + chat.py のパターンから導出]

```python
# app/api/routes/gems.py
from fastapi import APIRouter, Depends, HTTPException, Request
import psycopg
from psycopg.rows import dict_row
from app.api.models import GemCreate, GemInfo
from app.api.routes.chat import get_jwt_payload

router = APIRouter(prefix="/api", tags=["gems"])

@router.get("/gems", response_model=list[GemInfo])
async def list_gems(request: Request, payload: dict = Depends(get_jwt_payload)):
    github_login = payload.get("github_login", "")
    db_uri = request.app.state.db_uri
    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT gem_id, name, system_prompt, type, created_at, updated_at FROM gems WHERE github_login = %s ORDER BY created_at DESC",
                (github_login,)
            )
            rows = await cur.fetchall()
    return [GemInfo(**row) for row in rows]
```

### フロントエンド — Canvas ペイン表示ロジック
[VERIFIED: frontend/src/hooks/useChat.ts + types.ts から導出]

```typescript
// frontend/src/types.ts に追加
export interface CanvasResult {
  type: 'canvas';
  app_id: string;
  html: string;
}

// useChat.ts 内 — result を解析して Canvas か Text かを判定
const rawResult = result.result ?? '';
let parsedResult: CanvasResult | string = rawResult;
try {
  const parsed = JSON.parse(rawResult);
  if (parsed.type === 'canvas') {
    parsedResult = parsed as CanvasResult;
  }
} catch {
  // plain text — そのまま使用
}
```

---

## Runtime State Inventory

> Phase 15 は新機能追加であり、既存データを保持したまま拡張する。

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `threads` テーブル（既存レコードあり） — `gem_id` カラムを追加 | `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` で NULL 許容カラム追加（既存データは NULL） |
| Stored data | `canvas_apps` テーブル | 新規作成 — 既存データなし |
| Stored data | `gems` テーブル | 新規作成 — 既存データなし |
| Live service config | Docker Compose — `api` / `worker` サービス | コード変更のみ、設定変更不要 |
| OS-registered state | なし | なし |
| Secrets/env vars | `DATABASE_URL`（既存）を新テーブルのマイグレーションにも使用 | 変更不要 |
| Build artifacts | `static/apps/` ディレクトリが存在しない | `os.makedirs("./static/apps", exist_ok=True)` または Dockerfile に追加 |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | gems/canvas_apps テーブル | ✓ | Docker Compose postgres サービス | — |
| Redis | arq Worker | ✓ | Docker Compose redis サービス | — |
| python-multipart | UploadFile (canvas upload) | ✓ | >=0.0.22（pyproject.toml） | — |
| `static/apps/` ディレクトリ | StaticFiles mount | ✗（未作成） | — | `os.makedirs()` で自動作成 |

[VERIFIED: pyproject.toml — python-multipart は既インストール済み]

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` — `asyncio_mode = "auto"`, `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

[VERIFIED: pyproject.toml L30-35, pytest --version 出力]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GEM-01 | `POST /api/gems` が認証済みユーザーで Gem を作成できる | unit | `uv run pytest tests/test_api_gems.py::test_create_gem -x` | ❌ Wave 0 |
| GEM-02 | `GET /api/gems` が自分の Gem のみ返す | unit | `uv run pytest tests/test_api_gems.py::test_list_gems -x` | ❌ Wave 0 |
| GEM-03 | `DELETE /api/gems/{id}` が他ユーザーの Gem を削除できない（404） | unit | `uv run pytest tests/test_api_gems.py::test_delete_gem_ownership -x` | ❌ Wave 0 |
| CANVAS-01 | `POST /api/canvas/apps/upload` が HTML を保存できる | unit | `uv run pytest tests/test_api_canvas.py::test_upload_app -x` | ❌ Wave 0 |
| CANVAS-02 | `GET /api/canvas/apps/{app_id}` が正しい HTML を返す | unit | `uv run pytest tests/test_api_canvas.py::test_get_app -x` | ❌ Wave 0 |
| CANVAS-03 | `POST /api/canvas/apps/{app_id}/deploy` が HTML ファイルを書き出す | unit | `uv run pytest tests/test_api_canvas.py::test_deploy_app -x` | ❌ Wave 0 |
| WORKER-01 | LangGraphHandler が Canvas Gem のスレッドで HTML を抽出して canvas_apps に保存する | unit | `uv run pytest tests/test_langgraph_handler.py::test_canvas_gem_extraction -x` | ❌ Wave 0 |
| WORKER-02 | `extract_html()` が正しく HTML ブロックを抽出できる | unit | `uv run pytest tests/test_langgraph_handler.py::test_extract_html -x` | ❌ Wave 0 |
| THREAD-01 | `POST /api/threads` が `gem_id` を受け取って保存できる | unit | `uv run pytest tests/test_api_chat.py::test_create_thread_with_gem -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_gems.py` — GEM-01, GEM-02, GEM-03 をカバー
- [ ] `tests/test_api_canvas.py` — CANVAS-01, CANVAS-02, CANVAS-03 をカバー
- [ ] `tests/test_langgraph_handler.py` に Canvas テストを追加（または新ファイル）— WORKER-01, WORKER-02 をカバー

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | 既存 JWT HS256 (`Depends(get_jwt_payload)`) — すべての Gem/Canvas エンドポイントに適用 |
| V3 Session Management | yes | 既存 JWT httpOnly cookie — 変更不要 |
| V4 Access Control | yes | `github_login` 照合による所有権チェック — Gem/Canvas 両方に必須 |
| V5 Input Validation | yes | Pydantic v2 モデル（`GemCreate`, `CanvasAppInfo`）でリクエスト検証 |
| V6 Cryptography | no | HTML 保存は平文ファイル — 要件なし |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 他ユーザーの Gem/Canvas App へのアクセス | Elevation of Privilege | `github_login` 照合（WHERE github_login = %s）で所有権確認 |
| Canvas プレビューの XSS | Spoofing | `<iframe sandbox="allow-scripts">` でスクリプトをサンドボックス化 |
| デプロイ済み HTML のパストラバーサル | Tampering | `app_id` は UUID 形式（`gen_random_uuid()`）— ディレクトリトラバーサル不可 |
| 大容量 HTML アップロード | Denial of Service | FastAPI の `UploadFile` は通常メモリに展開 — 必要なら `MAX_UPLOAD_SIZE` チェックを追加（CONTEXT.md では大容量対応はスコープ外） |

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| iframe に `src=URL` でサーバー経由 | `srcDoc={html}` でインラインレンダリング | ネットワーク往復なし、プレビューが即時表示 |
| デプロイにファイルサーバー別途起動 | FastAPI `StaticFiles` mount | インフラ追加なし |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ~~`job_store.save_result()` は文字列を受け付ける~~ **解決済み** — `save_result(job_id, result: str)` は文字列のみ受け付ける。Canvas の場合は `json.dumps()` して保存し、フロントで `JSON.parse()` して判定する | Worker 拡張 | [VERIFIED: app/jobs/job_store.py L25] |
| A2 | `LangGraph StateGraph` は `SystemMessage` をメッセージリストの先頭に追加することでシステムプロンプトとして扱う | Worker 拡張 | Canvas Gem がシステムプロンプトを無視する — build_graph() の拡張が必要になる可能性 [ASSUMED] |
| A3 | ~~`static/apps/` の永続化が不明~~ **解決済み** — `api` / `worker` サービスはどちらも `- .:/app` バインドマウントを使用。`static/apps/` への書き込みはホストに永続化される | Deploy 実装 | [VERIFIED: docker-compose.yml — volumes: .:/app] |

**未解決の仮定は A2 のみ。** A1 と A3 は直接コード確認で検証済み。

---

## Open Questions (RESOLVED)

1. **`build_graph()` への SystemMessage 注入**
   - What we know: `graph.ainvoke({"messages": [HumanMessage(...)]})` は `messages` リストを直接受け取る。LangChain の `MessagesState` は `add_messages` reducer を使うため、リスト内の順序がそのまま LLM に渡される
   - What's unclear: Copilot SDK が `SystemMessage` を正しくシステムプロンプトとして処理するか（SDK は JSON-RPC ベースの独自実装）
   - RESOLVED: Worker で `[SystemMessage(content=sp), HumanMessage(content=prompt)]` として渡し、Phase 実装時に動作確認する。問題があれば ChatCopilot の `_agenerate()` でシステムプロンプトを別処理する

2. **canvas_apps upsert の UNIQUE 制約**
   - What we know: CONTEXT.md は `thread_id + github_login` で既存レコードを探してデータを更新するよう指定
   - What's unclear: `ON CONFLICT DO UPDATE` には UNIQUE 制約が必要。DDL に `UNIQUE (thread_id, github_login)` を追加するか、明示的な SELECT + UPDATE を使うか
   - RESOLVED: `UNIQUE (thread_id, github_login)` 制約を DDL に追加し、`INSERT ... ON CONFLICT (thread_id, github_login) DO UPDATE SET html = EXCLUDED.html` の形式を使う

---

## Sources

### Primary (HIGH confidence)
- `app/api/main.py` — lifespan マイグレーションパターン、StaticFiles mount パターン [VERIFIED: 直接読み込み]
- `app/api/routes/chat.py` — JWT 認証パターン (`get_jwt_payload`), スレッド CRUD [VERIFIED: 直接読み込み]
- `app/api/routes/apps.py` — FastAPI ルートパターン参照実装 [VERIFIED: 直接読み込み]
- `app/jobs/handlers/langgraph_handler.py` — Worker 拡張対象 [VERIFIED: 直接読み込み]
- `app/jobs/worker.py` — process_chat ジョブディスパッチ [VERIFIED: 直接読み込み]
- `app/api/models.py` — 既存 Pydantic モデル [VERIFIED: 直接読み込み]
- `frontend/src/hooks/useChat.ts` — チャット状態管理 [VERIFIED: 直接読み込み]
- `frontend/src/hooks/useThreads.ts` — スレッド CRUD [VERIFIED: 直接読み込み]
- `frontend/src/api/client.ts` — apiFetch ラッパー [VERIFIED: 直接読み込み]
- `pyproject.toml` — 依存関係とテスト設定 [VERIFIED: 直接読み込み]

### Secondary (MEDIUM confidence)
- `docs/pre/canvas_design.md` — 元の設計仕様（PRD）[VERIFIED: 直接読み込み]
- `.planning/phases/15-gem-canvas/15-CONTEXT.md` — ユーザー決定事項 [VERIFIED: 直接読み込み]

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 15 |
|-----------|-------------------|
| Python 3.12 | すべての Python コードは 3.12 構文（`str | None` 等） |
| `langchain-core` のみ（`langchain` フルパッケージ不使用） | `SystemMessage` は `langchain_core.messages` から import |
| `pyproject.toml` + `uv` | 新しいパッケージは `uv add` で追加（この Phase では不要） |
| `async def` ルート必須 | `gems.py`, `canvas.py` のすべてのルートは `async def` |
| `BaseChatModel` ラッパーパターン | Copilot SDK 直接参照は `app/providers/copilot.py` のみ |
| Docker Compose 起動 | `docker compose up` が主要起動方法 — `static/apps/` の永続化を確認 |
| 応答は日本語 | コード以外のすべての出力（コメント含む）は日本語 |

[VERIFIED: CLAUDE.md — 直接読み込み]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — すべて既存 pyproject.toml で確認済み
- Architecture: HIGH — 既存コードを直接読み込んで確認
- Pitfalls: HIGH — 既存コードパターンから導出（Pitfall 5 のみ MEDIUM — LangGraph の SystemMessage 動作は ASSUMED）
- フロントエンドパターン: HIGH — useChat.ts / ChatApp.tsx を直接確認

**Research date:** 2026-04-05
**Valid until:** 2026-05-05（PostgreSQL/FastAPI/React 19 は安定版のため30日）
