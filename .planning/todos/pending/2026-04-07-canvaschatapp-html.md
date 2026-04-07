---
created: 2026-04-07T01:16:09.931Z
title: CanvasChatApp チャット復元時に最後のHTMLをプレビュー表示
area: ui
files:
  - frontend/src/components/CanvasChatApp.tsx
  - frontend/src/hooks/useChat.ts
  - app/api/routes/canvas.py
---

## Problem

CanvasChatApp でチャット履歴を復元したとき（既存スレッドを開いたとき）、右パネルには「アプリがここに表示されます」のプレースホルダーが表示される。

ユーザーは以前そのチャットでデプロイした HTML を作成しているにもかかわらず、右パネルが空のまま再スタートになってしまう。

期待する動作: チャット履歴を復元したら、そのスレッドで最後にデプロイ（または生成）した HTML を自動的に右パネルのプレビューに表示する。

## Solution

チャット内でデプロイした HTML を `canvas_apps` テーブルに `thread_id` と紐付けて保存しておき、CanvasChatApp がスレッドを復元する際にそのスレッドの最新 `canvas_app` を取得してプレビューに反映する。

実装方針:
1. **バックエンド**: `GET /api/canvas/apps?thread_id={thread_id}&limit=1&order=desc` で最新アプリを取得するか、`GET /api/canvas/apps/{thread_id}/latest` を追加
2. **フロントエンド**: `CanvasChatApp.tsx` でスレッド選択時に上記 API を呼び出し、取得した `html_content` を `canvasApp` state にセットして CanvasPane に渡す
3. `canvas_apps` テーブルに `thread_id` カラムが既にある場合はそれを利用。なければ追加が必要
