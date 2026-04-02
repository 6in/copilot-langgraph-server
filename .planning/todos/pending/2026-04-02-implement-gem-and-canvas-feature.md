---
created: 2026-04-02T03:38:30.023Z
title: Implement Gem and Canvas feature
area: api
files:
  - docs/pre/canvas_design.md
  - db/canvas_apps.py
  - worker.py
  - main.py
  - static/apps/
---

## Problem

チャットで AI にシングルファイル HTML を生成させ、エディタでプレビュー・修正しながらそのままデプロイできる Canvas 機能がない。Gemini の Canvas 相当の機能を Gem の一種として実装したい。

## Solution

設計書 `docs/pre/canvas_design.md` に基づいて実装する。主な作業:

### データモデル
- `gems` テーブルに `type` カラム追加（`default` | `canvas`）
- `canvas_apps` テーブル新規作成（id, thread_id, user_id, name, html, source, deployed, deployed_at, created_at）

### バックエンド
- `db/canvas_apps.py` — CRUD 実装
- `worker.py` — Canvas Gem 判定・HTML 抽出（```html ブロック）・canvas_apps への upsert
- `main.py` に API エンドポイント追加:
  - `POST /canvas/apps/upload` — HTML ファイルアップロード登録
  - `GET /canvas/apps/{id}` — アプリ取得
  - `GET /canvas/apps?thread_id={id}` — スレッドの最新アプリ取得
  - `PATCH /canvas/apps/{id}` — HTML 編集保存
  - `POST /canvas/apps/{id}/deploy` — デプロイ（static/apps/{id}/index.html に書き出し）
  - `GET /apps/{app_id}/` — デプロイ済みアプリ配信
  - `GET /canvas/apps/{id}/source` — 元スレッドへ戻る

### フロントエンド（React版）
- サイドバーに Gem 一覧・アプリ一覧を追加
- Canvas 画面: 左ペイン=チャット、右ペイン=エディタ/プレビュー切り替え + [デプロイ] ボタン
- アップロード登録フロー

### Canvas Gem システムプロンプト
- シングルファイル HTML のみ出力させるシステムプロンプトを設定

### スコープ外（拡張フェーズ）
- DB アクセス連携、AI プロンプト連携、バージョン管理、アプリ一覧管理画面
