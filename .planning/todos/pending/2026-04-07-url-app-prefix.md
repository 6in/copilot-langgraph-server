---
created: 2026-04-07T01:16:09.931Z
title: デプロイ URL に APP_PREFIX を付与する
area: api
files:
  - app/api/routes/canvas.py
  - frontend/src/components/CanvasPane.tsx
---

## Problem

Canvas App をデプロイすると `/apps/{uuid}/` という URL が生成されるが、nginx 経由で `/orochi` などのプレフィックス付きで運用している場合、実際の URL は `/orochi/apps/{uuid}/` になる必要がある。

現状は APP_PREFIX（FastAPI の `root_path` / `VITE_APP_BASE`）が考慮されておらず、プレフィックスなしの URL が発行されてしまう。

例:
- 現在: `http://localhost:5173/apps/7b99a5e4-0230-4f20-946f-917317411aba/`
- 期待: `http://localhost:5173/orochi/apps/7b99a5e4-0230-4f20-946f-917317411aba/`

## Solution

デプロイ URL 生成時に `APP_PREFIX`（環境変数）または FastAPI の `request.app.root_path` を参照してプレフィックスを付与する。

- バックエンド: `canvas.py` の deploy エンドポイントで `request.scope.get("root_path", "")` を使って URL を組み立てる
- フロントエンド: `CanvasPane.tsx` でデプロイ後に表示する URL に `import.meta.env.VITE_APP_BASE` を付与する
- 参考: `docs/nginx.md` の APP_PREFIX / VITE_APP_BASE の設定方針
