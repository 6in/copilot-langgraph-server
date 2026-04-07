---
phase: 16-canvas-app
plan: "01"
subsystem: api
tags: [fastapi, postgres, psycopg, canvas, gems, jwt]

requires:
  - phase: 15-gem-canvas
    provides: canvas_apps table, gems table, canvas.py route skeleton

provides:
  - "GET /api/canvas/apps?deployed=true — deployed フィルタ付きアプリ一覧"
  - "GET /api/canvas/gem — Canvas 専用 Gem の gem_id を返す JWT 保護エンドポイント"
  - "lifespan 自動登録 — Canvas Gem (type=canvas, github_login=_canvas_system_) の冪等 INSERT"
  - "app.state.canvas_gem_id — 起動後に UUID 文字列として設定"

affects:
  - 16-canvas-app
  - frontend CanvasScreen (gem_id 取得で使用)
  - frontend CanvasChatApp (deployed=true フィルタで一覧表示)

tech-stack:
  added: []
  patterns:
    - "SELECT → INSERT 冪等パターン (gems テーブルに UNIQUE 制約なし)"
    - "bool | None クエリパラメータによるオプション DB フィルタ"
    - "app.state への lifespan 設定値注入"

key-files:
  created:
    - tests/test_canvas_gem.py
    - tests/test_canvas_api.py
  modified:
    - app/api/routes/canvas.py
    - app/api/main.py

key-decisions:
  - "SELECT → INSERT 冪等パターン採用 — gems テーブルに UNIQUE 制約がないため ON CONFLICT 不可"
  - "GET /api/canvas/gem に JWT Depends(get_jwt_payload) を付与 — T-16-01 脅威対策、gem_id は秘密ではないが一貫性のため保護"
  - "test_canvas_gem_auto_register は lifespan を経由せずロジックを直接ユニットテスト — ASGITransport では lifespan が動かないため"
  - "app.state.canvas_gem_id を commit 後・app.state.graph 設定前に配置 — lifespan の他の state と同一スコープ内"

patterns-established:
  - "Canvas Gem 登録パターン: lifespan 内で SELECT → INSERT (冪等)、結果を app.state に格納"
  - "デプロイ済みフィルタパターン: query += AND deployed = %s with params list"

requirements-completed:
  - D-12
  - D-13
  - D-14

duration: 7min
completed: "2026-04-07"
---

# Phase 16 Plan 01: バックエンド API 拡張 Summary

**Canvas 専用 Gem 自動登録（SELECT→INSERT 冪等）+ GET /api/canvas/gem エンドポイント + deployed フィルタ付き GET /api/canvas/apps**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-07T00:22:40Z
- **Completed:** 2026-04-07T00:29:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `GET /api/canvas/apps?deployed=true` — `deployed: bool | None` パラメータを追加し、deployed フィルタを安全なパラメータ化クエリで実装
- Canvas 専用 Gem（type='canvas', github_login='_canvas_system_'）の lifespan 自動登録: SELECT → INSERT 冪等パターン、`app.state.canvas_gem_id` に格納
- `GET /api/canvas/gem` — JWT 保護付きで `{"gem_id": "uuid"}` を返す新エンドポイント（T-16-01 対応）
- TDD: 7テスト作成（canvas gem ロジック 4 + canvas API 3）、全件 GREEN

## Task Commits

1. **Task 1: テストスキャフォールド作成** - `eef1ddf` (test — RED フェーズ)
2. **Task 2: バックエンド実装** - `d7fad84` (feat — GREEN フェーズ)

## Files Created/Modified

- `app/api/routes/canvas.py` — `deployed: bool | None` フィルタ追加、`GET /api/canvas/gem` エンドポイント追加
- `app/api/main.py` — lifespan に Canvas Gem 自動登録（SELECT → INSERT 冪等）＋ `app.state.canvas_gem_id` 設定
- `tests/test_canvas_gem.py` — Canvas Gem 登録ロジックの直接ユニットテスト（4テスト）
- `tests/test_canvas_api.py` — deployed フィルタ・認証テスト（3テスト）

## Decisions Made

- **SELECT → INSERT 冪等パターン**: gems テーブルに UNIQUE 制約がないため `ON CONFLICT DO NOTHING` は使えない。`SELECT LIMIT 1` → 結果なしなら `INSERT ... RETURNING gem_id` のパターンを採用。
- **JWT 保護**: `GET /api/canvas/gem` に `Depends(get_jwt_payload)` を付与（T-16-01）。gem_id は UUID であり秘密情報ではないが、他エンドポイントとの一貫性とデータ分離のため保護する。
- **ユニットテスト戦略**: lifespan は ASGITransport では起動しないため、`test_canvas_gem_auto_register` と `test_canvas_gem_idempotent` は lifespan ロジックを直接呼び出すユニットテスト形式に変更。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `AsyncContextManager` は `unittest.mock` に存在しない**
- **Found during:** Task 2 検証（テスト収集エラー）
- **Issue:** `test_canvas_api.py` に `from unittest.mock import AsyncContextManager` を記述したが、Python 3.12 の `unittest.mock` にはこのクラスが存在しない
- **Fix:** 使用していないインポートを削除
- **Files modified:** `tests/test_canvas_api.py`
- **Verification:** `pytest --collect-only` でエラーなし
- **Committed in:** `d7fad84`

**2. [Rule 1 - Bug] `test_canvas_gem_auto_register` の lifespan 前提が不正**
- **Found during:** Task 2 検証（テスト失敗 — `app.state.canvas_gem_id` が存在しない）
- **Issue:** 元のテストは ASGITransport で lifespan が動くと仮定していたが実際は動かない。`app.state.canvas_gem_id` は lifespan 内でしか設定されない
- **Fix:** テストを「SELECT → INSERT ロジックを直接呼び出す」ユニットテスト形式に書き直し、lifespan 経由の検証は endpoint テストに委譲
- **Files modified:** `tests/test_canvas_gem.py`
- **Verification:** 7テスト全件 GREEN
- **Committed in:** `d7fad84`

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** 両方ともテストコードの誤り。実装コード（canvas.py / main.py）は計画通りに実装完了。スコープの逸脱なし。

## Issues Encountered

- `test_new_thread_returns_uuid`（`tests/test_api_chat.py`）が変更前から失敗していることを確認（今回の変更とは無関係の既存問題）。今回の変更ではリグレッションなし。

## Known Stubs

なし — すべてのエンドポイントは実データを返す（`app.state.canvas_gem_id` は lifespan で DB から取得した実 UUID）。

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-16-01 mitigated | `app/api/routes/canvas.py` | `GET /api/canvas/gem` に `Depends(get_jwt_payload)` を付与 — 認証済みユーザーのみ gem_id を取得可能 |
| T-16-04 mitigated | `app/api/routes/canvas.py` | `deployed: bool | None` は FastAPI の型検証により任意文字列を排除、パラメータ化クエリで SQL インジェクション不可 |

## Next Phase Readiness

- フロントエンドの `CanvasScreen` が `GET /api/canvas/apps?deployed=true` を使ってデプロイ済みアプリを取得できる
- フロントエンドの `CanvasChatApp` が `GET /api/canvas/gem` を使って Canvas 専用 Gem ID を取得できる
- Canvas Gem は再起動後も同一 gem_id を返す（冪等登録）

## Self-Check: PASSED

- SUMMARY.md: FOUND
- tests/test_canvas_gem.py: FOUND
- tests/test_canvas_api.py: FOUND
- commit eef1ddf: FOUND (Task 1 — test RED)
- commit d7fad84: FOUND (Task 2 — feat GREEN)

---
*Phase: 16-canvas-app*
*Completed: 2026-04-07*
