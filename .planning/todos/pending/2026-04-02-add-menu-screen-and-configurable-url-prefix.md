---
created: 2026-04-02T03:23:51.523Z
title: Add menu screen and configurable URL prefix
area: ui
files: []
---

## Problem

現状、アプリを開くと直接チャット画面が表示される。将来的に複数の機能（チャット以外）を追加することを想定して、メニュー画面（トップ画面）を用意し、そこからチャットを選択して遷移できるようにしたい。

また、FastAPI が配信するすべてのルートに URL プレフィクスを付けたい。デフォルトは `/orochi/` とし、`.env` などの環境変数で変更できるようにする（例: `URL_PREFIX=/orochi/`）。

## Solution

- FastAPI に `root_path` または `APIRouter(prefix=...)` でプレフィクスを設定し、`APP_PREFIX` 環境変数（デフォルト `/orochi/`）で制御できるようにする
- トップページ（メニュー画面）を作成し、チャット（Vanilla JS 版 / React 版）へのリンクを表示する
- 既存の静的ファイルや API エンドポイントのパスがプレフィクスに追従するよう調整する
