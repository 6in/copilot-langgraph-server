---
id: 2026-04-09-canvas-app-deploy-hosting
title: Canvas アプリのデプロイ＆ホスティング機能
category: api
created: 2026-04-09
status: pending
---

# Canvas アプリのデプロイ＆ホスティング機能

## 概要

Canvas チャットで生成した HTML アプリを独立した URL にデプロイし、
ブラウザから直接アクセスできるようにする。

## 実装内容

- **デプロイ**: 生成 HTML を DB/ストレージに保存し app-id を付与
- **ルーティング**: `/apps/{app-id}/` → 親 HTML ページを返す FastAPI ルート
- **親 HTML ページ**: iframe + Web Worker を持つホスティングシェル
- **HTML 取得・変換**: デプロイ済み HTML をダウンロードし `$URL_PREFIX` 等を置換して iframe に注入
- **RPC 継続**: デプロイ後も Web Worker 経由で AI/DB ブリッジが動く（Phase 18 の iframe-rpc.js を流用）

## 参考

- Phase 18 で実装した iframe postMessage JSON-RPC API ブリッジを基盤として使う
- アクセス URL 例: `http://localhost:5173/orochi/apps/cfec9804-eca2-49f3-9071-a6f32666c3aa/`
