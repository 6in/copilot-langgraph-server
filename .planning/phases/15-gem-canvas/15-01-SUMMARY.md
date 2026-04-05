---
phase: 15-gem-canvas
plan: "01"
subsystem: backend
tags: [gems, canvas, postgresql, ddl, pydantic, fastapi]
dependency_graph:
  requires: []
  provides: [gems-ddl, canvas-apps-ddl, gem-crud-api, gem-id-in-threads]
  affects: [app/api/main.py, app/api/models.py, app/api/routes/chat.py, app/api/routes/gems.py]
tech_stack:
  added: []
  patterns: [psycopg-dict-row, ownership-filter-via-jwt, partial-update-exclude-unset]
key_files:
  created:
    - app/api/routes/gems.py
    - tests/test_api_gems.py
    - tests/test_api_canvas.py
    - tests/test_langgraph_handler.py
  modified:
    - app/api/main.py
    - app/api/models.py
    - app/api/routes/chat.py
decisions:
  - "DDL 順序: gems → threads ALTER → canvas_apps (FK 依存順序 — Pitfall 2 対応)"
  - "UNIQUE (thread_id, github_login) を canvas_apps に追加 — Worker upsert の ON CONFLICT 用"
  - "gem_id は threads upsert で COALESCE 保護 — 初回セット後は上書きしない"
  - "DELETE/GET/PATCH は 404 返却で gem 存在を漏洩させない (T-15-01)"
metrics:
  duration: "3min"
  completed_date: "2026-04-05"
  tasks_completed: 3
  files_changed: 7
---

# Phase 15 Plan 01: Backend Foundation (Gems + Canvas DDL + CRUD API) Summary

**One-liner:** PostgreSQL に gems/canvas_apps テーブルを追加し、JWT 認証 + 所有権チェック付き Gem CRUD API (5 endpoints) と threads への gem_id 永続化を実装

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 0 | Wave 0 テストスタブ作成 | 05ced79 | tests/test_api_gems.py, test_api_canvas.py, test_langgraph_handler.py |
| 1 | DDL マイグレーション + Pydantic モデル + gem_id 拡張 | ee1001a | app/api/main.py, app/api/models.py, app/api/routes/chat.py |
| 2 | Gem CRUD API エンドポイント実装 | ff6dc4a | app/api/routes/gems.py |

## What Was Built

### DDL マイグレーション (app/api/main.py)

lifespan 内に 3 つの DDL ブロックを追加（順序重要: gems → threads ALTER → canvas_apps）:

1. `gems` テーブル: UUID PK、github_login/name/system_prompt/type フィールド、`gems_github_login_idx` インデックス
2. `threads` テーブルへの `gem_id UUID REFERENCES gems(gem_id) ON DELETE SET NULL` カラム追加
3. `canvas_apps` テーブル: UUID PK、thread_id FK、UNIQUE(thread_id, github_login)、2 インデックス

### Pydantic モデル (app/api/models.py)

- `GemCreate`: POST /api/gems のリクエストボディ (name, system_prompt, type)
- `GemUpdate`: PATCH /api/gems/{gem_id} のリクエストボディ (全フィールド optional)
- `GemInfo`: Gem エンドポイントのレスポンスモデル
- `CanvasAppInfo`: Canvas App エンドポイントのレスポンスモデル
- `CanvasDeployResponse`: デプロイレスポンス (url: str)
- `ChatRequest` に `gem_id: str | None = None` を追加

### threads upsert 修正 (app/api/routes/chat.py)

`body.gem_id` を抽出し、INSERT INTO threads の SQL に gem_id カラムを追加。ON CONFLICT では `COALESCE(threads.gem_id, EXCLUDED.gem_id)` で初回セット後の上書きを防止。

### Gem CRUD API (app/api/routes/gems.py)

5 エンドポイント実装:
- `POST /api/gems` (status 201): Gem 作成
- `GET /api/gems`: ユーザーの全 Gem 一覧 (created_at DESC)
- `GET /api/gems/{gem_id}`: Gem 取得 (404 for not found/other user)
- `PATCH /api/gems/{gem_id}`: 部分更新 (exclude_unset, 動的 SET 句)
- `DELETE /api/gems/{gem_id}` (status 204): Gem 削除

全エンドポイントで `Depends(get_jwt_payload)` + `WHERE github_login = %s` による所有権チェック。

### Wave 0 テストスタブ

8 テストスタブが pytest で収集される:
- `tests/test_api_gems.py`: GEM-01, GEM-02, GEM-03 (3 stubs)
- `tests/test_api_canvas.py`: CANVAS-01, CANVAS-02, CANVAS-03 (3 stubs)
- `tests/test_langgraph_handler.py`: WORKER-01, WORKER-02 (2 stubs)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1/Task 2 の実行順序を調整**
- **Found during:** Task 1 コミット前
- **Issue:** `main.py` が `gems` モジュールをインポートするため、`gems.py` が存在しないと import エラーが発生
- **Fix:** Task 2 (gems.py 作成) を Task 1 コミット前に実行し、Task 1 と Task 2 を別コミットでファイル単位に分けてコミット
- **Files modified:** app/api/routes/gems.py (Task 2 として先行作成)

## Known Stubs

Wave 0 テストスタブが存在する（意図的）:
- `tests/test_api_gems.py`: pytest.skip で実装待ち (Plan 01 verification phase で実装予定)
- `tests/test_api_canvas.py`: pytest.skip で実装待ち (Plan 02 で実装予定)
- `tests/test_langgraph_handler.py`: pytest.skip で実装待ち (Plan 02 で実装予定)

## Threat Flags

脅威モデルはプランで定義済み。新たな surface は検出されなかった。

## Self-Check: PASSED

- [x] `app/api/routes/gems.py` 存在確認 — FOUND
- [x] `tests/test_api_gems.py` 存在確認 — FOUND
- [x] `tests/test_api_canvas.py` 存在確認 — FOUND
- [x] `tests/test_langgraph_handler.py` 存在確認 — FOUND
- [x] commit 05ced79 — FOUND (Wave 0 stubs)
- [x] commit ee1001a — FOUND (DDL + models + chat.py)
- [x] commit ff6dc4a — FOUND (gems.py)
- [x] `python -c "from app.api.routes.gems import router"` — OK (5 routes)
- [x] `python -c "from app.api.models import GemCreate, GemUpdate, GemInfo, CanvasAppInfo, CanvasDeployResponse"` — OK
- [x] `uv run pytest tests/test_api_gems.py tests/test_api_canvas.py tests/test_langgraph_handler.py --co -q` — 8 tests collected
