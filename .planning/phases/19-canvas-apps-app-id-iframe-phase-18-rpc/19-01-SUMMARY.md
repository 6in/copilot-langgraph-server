---
phase: 19-canvas-apps-app-id-iframe-phase-18-rpc
plan: "01"
subsystem: canvas-hosting
tags: [canvas, iframe, postmessage, json-rpc, hosting, fastapi]
dependency_graph:
  requires:
    - phase-18 iframe_rpc.py
    - phase-15 canvas_apps DB table
    - static/js/iframe-rpc.js
  provides:
    - GET /apps/{app_id} dynamic hosting shell
    - static/js/parent-bridge.js
    - JWT-free POST /api/iframe-rpc
  affects:
    - CanvasPane.tsx (postMessage relay delegation)
    - app/api/main.py (router registration order)
tech_stack:
  added: []
  patterns:
    - e.source for postMessage reply (no iframeRef needed)
    - window.__parentBridgeInstalled idempotency guard
    - srcdoc HTML escaping (" -> &quot;, & -> &amp;)
    - FastAPI dynamic route before StaticFiles mount
key_files:
  created:
    - static/js/parent-bridge.js
    - app/api/routes/hosted_apps.py
  modified:
    - app/api/routes/iframe_rpc.py
    - app/api/main.py
    - frontend/src/components/CanvasPane.tsx
decisions:
  - "parent-bridge.js uses e.source (not iframeRef) to reply to iframe — enables shared logic between Shell and CanvasPane"
  - "iframe_rpc.py JWT auth removed (D-07): github_token fetched from auth_manager.load_token()"
  - "hosted_apps.router registered before /apps StaticFiles (D-02) — dynamic route takes priority"
  - "sandbox=allow-scripts+allow-forms only — allow-same-origin excluded (D-06, T-19-03)"
  - "srcdoc escaping: & -> &amp;, quote -> &quot; to prevent attribute injection (T-19-02)"
metrics:
  duration: "~15 min"
  completed: "2026-04-09"
  tasks: 4
  files: 5
---

# Phase 19 Plan 01: Canvas アプリホスティングシェル実装 Summary

Canvas アプリを `/apps/{app_id}` URL でスタンドアロンホスティングし、Phase 18 の iframe postMessage JSON-RPC ブリッジ（parent-bridge.js）を共通化した。

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | parent-bridge.js 作成 | 6f255f8 | static/js/parent-bridge.js |
| 2 | hosted_apps.py 実装 | ead25e7 | app/api/routes/hosted_apps.py |
| 3 | CanvasPane.tsx リファクタ | e10b637 | frontend/src/components/CanvasPane.tsx |
| 4 | iframe_rpc JWT削除 + main.py登録 | b6fec71 | app/api/routes/iframe_rpc.py, app/api/main.py |

## What Was Built

### static/js/parent-bridge.js
- 親フレーム（Shell HTML または CanvasPane）で動作する postMessage リレースクリプト
- `e.source` を使って返信先 iframe を特定（`iframeRef` 不要）
- `window.__parentBridgeInstalled` による二重登録防止
- `/api/iframe-rpc` へ fetch（`credentials: 'include'`）→ SSE 待機 → 返信
- 60 秒タイムアウト
- Origin 検証: `window.location.origin` または `'null'`（srcdoc iframe 対応）

### app/api/routes/hosted_apps.py
- `GET /apps/{app_id}` — DB から Canvas アプリ HTML を取得してシェルに埋め込む
- 認証不要（D-08）。`github_login` フィルターなしで `app_id` のみ検索
- `sandbox="allow-scripts allow-forms"` のみ（`allow-same-origin` 除外、D-06）
- `<script src="/js/parent-bridge.js">` でリレーを有効化（D-13 更新版）
- HTML が存在しない場合は 404（D-12）
- srcdoc エスケープ実装済み（T-19-02）

### app/api/routes/iframe_rpc.py (修正)
- `Depends(get_jwt_payload)` および `Depends(get_github_token)` を削除（D-07）
- `github_login` を `"anonymous"` に固定（ログ用）
- `github_token` を `auth_manager.load_token()` で取得

### app/api/main.py (修正)
- `hosted_apps` を import に追加
- `app.include_router(hosted_apps.router)` を `/apps` StaticFiles マウントより前に登録（D-02）

### frontend/src/components/CanvasPane.tsx (修正)
- `useRef`, `useCallback`, `iframeRef` を削除
- `handleIframeMessage` インライン実装と関連 `useEffect` を削除
- `postIframeRpc`, `streamJob`, `getJob` の import を削除
- `/js/parent-bridge.js` を `document.head` にスクリプト注入する `useEffect` を追加（一度だけ）

## Decisions Made

1. **parent-bridge.js を新規作成して共通化**: Shell HTML と CanvasPane.tsx の両方が同じリレーロジックを使う設計。プランナー再設計による変更（当初は CanvasPane のロジックをそのまま使う想定だった）。
2. **JWT auth 削除 (D-07)**: `/api/iframe-rpc` を公開エンドポイント化。github_token はサーバー側 auth_manager から取得することで Copilot 呼び出しを維持。
3. **router 登録順序 (D-02)**: FastAPI のルート優先順位により、動的ルート `GET /apps/{app_id}` が先にマッチし、StaticFiles がフォールバックとして機能する。

## Deviations from Plan

### Auto-fixed Issues

なし。プランに記載された内容をそのまま実装。

### Notes

- CONTEXT.md の D-13 は `iframe-rpc.js` を読み込む設計だったが、PLAN.md の再設計により `parent-bridge.js` を読み込む形に更新済み。実装は PLAN.md に従った。

## Known Stubs

なし。

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: auth_bypass | app/api/routes/iframe_rpc.py | JWT auth removed — any request can enqueue iframe_app_api jobs (D-07 accepted risk) |
| threat_flag: public_access | app/api/routes/hosted_apps.py | GET /apps/{app_id} requires no auth — URL知る者は誰でもアクセス可能 (T-19-01 accepted) |

## Self-Check: PASSED

- `static/js/parent-bridge.js` — FOUND
- `app/api/routes/hosted_apps.py` — FOUND
- `app/api/routes/iframe_rpc.py` — JWT Depends removed VERIFIED
- `app/api/main.py` — hosted_apps imported and registered VERIFIED
- `frontend/src/components/CanvasPane.tsx` — iframeRef removed, parent-bridge.js injected VERIFIED
- Commits: 6f255f8, ead25e7, e10b637, b6fec71 — all present in git log
