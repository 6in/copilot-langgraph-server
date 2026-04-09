---
created: 2026-04-09T06:45:36.844Z
title: 本番モード Docker Compose 整備
area: tooling
files:
  - docker-compose.yml
  - frontend/Dockerfile
---

## Problem

現在の Docker Compose は開発モード専用（Vite dev server）のみ。
本番モード（フロントエンドビルド済み + nginx プロキシ）での動作確認ができない。

## Solution

- `docker-compose.prod.yml` を作成
- nginx コンテナを追加（`/orochi` プレフィックスのストリップ、`/api` プロキシ、静的ファイル配信）
- `frontend/Dockerfile` を multi-stage build に変更（`bun run build` → nginx で配信）
- `VITE_APP_BASE=/orochi` を設定した本番ビルドで動作確認
