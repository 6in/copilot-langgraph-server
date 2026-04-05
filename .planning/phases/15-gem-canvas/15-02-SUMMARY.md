---
phase: 15-gem-canvas
plan: "02"
subsystem: backend
tags: [canvas, fastapi, staticfiles, langgraph, html-extraction, psycopg, postgresql]
dependency_graph:
  requires: [gems-ddl, canvas-apps-ddl, gem-crud-api]
  provides: [canvas-apps-api, canvas-deploy, canvas-staticfiles, langgraph-canvas-gem-support]
  affects: [app/api/routes/canvas.py, app/api/main.py, app/jobs/handlers/langgraph_handler.py]
tech_stack:
  added: []
  patterns: [psycopg-dict-row, ownership-filter-via-jwt, staticfiles-mount-order, html-extraction-regex, canvas-upsert-on-conflict]
key_files:
  created:
    - app/api/routes/canvas.py
  modified:
    - app/api/main.py
    - app/jobs/handlers/langgraph_handler.py
decisions:
  - "canvas.py prefix を /api/canvas に設定 — 既存 /api/apps との衝突回避 (Pitfall 3)"
  - "os.makedirs('./static/apps') を StaticFiles mount 前に実行 — 起動クラッシュ防止 (Pitfall 1)"
  - "/apps mount を / catch-all より前に配置 — mount 順序による到達不能を回避"
  - "deploy_app は DB から取得した UUID の app_id を使用 — ユーザー入力パスを直接使わないことでパストラバーサル不可 (T-15-05)"
  - "Canvas upsert は ON CONFLICT (thread_id, github_login) — 反復修正で同じ canvas_apps レコードを上書き"
  - "_get_gem_info の例外は pass で握りつぶし — Gem なしスレッドでも通常動作を継続"
  - "upsert 失敗時は result_payload = final_text にフォールバック — Canvas 生成は致命的エラーにしない"
metrics:
  duration: "8min"
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 3
---

# Phase 15 Plan 02: Canvas Apps API + LangGraphHandler Canvas Gem Extension Summary

**One-liner:** Canvas Apps API 6 エンドポイント (アップロード/取得/編集/デプロイ/ソース) を JWT 認証 + 所有権チェック付きで実装し、LangGraphHandler を拡張して Canvas Gem スレッドで SystemMessage 注入 + HTML 抽出 + canvas_apps upsert を行う

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Canvas Apps API エンドポイント + StaticFiles mount | a0efd70 | app/api/routes/canvas.py (新規), app/api/main.py |
| 2 | LangGraphHandler Canvas Gem 拡張 | 28aaae4 | app/jobs/handlers/langgraph_handler.py |

## What Was Built

### Canvas Apps API (app/api/routes/canvas.py)

6 エンドポイントを `prefix="/api/canvas"` で実装:

- `POST /api/canvas/apps/upload` (status 201): HTML アップロード登録。`source='upload'`、`thread_id=NULL`
- `GET /api/canvas/apps` (クエリパラメータ `?thread_id=`): スレッド別最新 or ユーザー全 20 件取得
- `GET /api/canvas/apps/{app_id}`: エディタ用アプリ取得 (所有権チェック、404 on miss)
- `PATCH /api/canvas/apps/{app_id}`: HTML + 任意の name を更新 (所有権チェック、404 on miss)
- `POST /api/canvas/apps/{app_id}/deploy`: `./static/apps/{app_id}/index.html` に書き出し + `deployed=TRUE` 更新。`CanvasDeployResponse(url=f"/apps/{app_id}/")` を返す
- `GET /api/canvas/apps/{app_id}/source`: デプロイ済みアプリのソース thread_id を返す

全エンドポイントで `Depends(get_jwt_payload)` + `WHERE github_login = %s` による所有権チェック (T-15-06)。

セキュリティ: `deploy_app` の書き出し先は DB から取得した UUID の `app_id` を使用するため、ユーザー入力がパスに入らずパストラバーサル不可 (T-15-05)。

### StaticFiles mount (app/api/main.py)

- `canvas` を import リストに追加
- `app.include_router(canvas.router)` を `gems.router` の後に追加
- `os.makedirs("./static/apps", exist_ok=True)` で事前ディレクトリ作成 (Pitfall 1)
- `app.mount("/apps", StaticFiles(...), name="canvas_apps")` を `/` catch-all の前に追加

### LangGraphHandler Canvas Gem 拡張 (app/jobs/handlers/langgraph_handler.py)

**新規追加関数:**

- `extract_html(text: str) -> str`: ` ```html ... ``` ` コードブロックを正規表現で抽出。マッチなしは元テキストを返す
- `_get_gem_info(thread_id, db_uri)`: threads + gems JOIN で gem_id/type/name/system_prompt を取得。例外は pass で吸収し `(None, None, None, None)` を返す

**handle() メソッドの変更:**

1. `graph.ainvoke` 前に `_get_gem_info` でシステムプロンプトを取得
2. `system_prompt` が存在する場合は `SystemMessage(content=system_prompt)` を先頭に追加してメッセージリストを構築
3. `ainvoke` 後に `gem_type == "canvas"` を確認
4. Canvas の場合: HTML 抽出 → `canvas_apps` に upsert (`ON CONFLICT (thread_id, github_login) DO UPDATE`) → `json.dumps({"type": "canvas", "app_id": ..., "html": ...})` を result_payload に設定
5. 通常の場合: `result_payload = final_text` (既存動作維持)

**後方互換性:** Gem なし / 通常 Gem スレッドでは既存動作が完全に維持される。

## Deviations from Plan

なし — プラン通りに実装した。

## Known Stubs

Wave 0 テストスタブが引き続き存在する（Plan 01 で作成、Plan 03 で実装予定）:
- `tests/test_api_canvas.py`: CANVAS-01, CANVAS-02, CANVAS-03 (pytest.skip)
- `tests/test_langgraph_handler.py`: WORKER-01, WORKER-02 (pytest.skip)

## Threat Flags

脅威モデルはプランで定義済み (T-15-04, T-15-05, T-15-06)。実装は各脅威を軽減:
- T-15-04: フロントエンド iframe sandbox は Plan 04 で実装
- T-15-05: deploy_app は DB 由来の UUID のみを使用 — パストラバーサル不可
- T-15-06: 全エンドポイントで `WHERE github_login = %s` による所有権チェック + 404 返却

## Self-Check: PASSED

- [x] `app/api/routes/canvas.py` 存在確認 — FOUND
- [x] `app/api/main.py` に canvas.router 追加確認 — FOUND
- [x] `app/api/main.py` に `/apps` StaticFiles mount 追加確認 — FOUND
- [x] `app/jobs/handlers/langgraph_handler.py` に extract_html, _get_gem_info 追加確認 — FOUND
- [x] commit a0efd70 — FOUND (canvas.py + main.py)
- [x] commit 28aaae4 — FOUND (langgraph_handler.py)
- [x] `python -c "from app.api.routes.canvas import router"` — OK (6 routes)
- [x] `python -c "from app.jobs.handlers.langgraph_handler import extract_html, _get_gem_info"` — OK
- [x] extract_html 動作確認 — '<h1>Hello</h1>' 正常抽出
