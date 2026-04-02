---
created: 2026-04-01T08:45:37.319Z
title: React製チャットUIの分離 — chat-ui-kit-react + Vite + Bun
area: ui
files:
  - app/static/index.html
  - app/static/app.js
---

## Problem

現在の UI は Vanilla JS + HTML/CSS のシンプル構成で動いているが、チャット UI としての機能・見た目の拡張に限界がある。`chat-ui-kit-react`（chatscope）を使えばメッセージバブル・タイピングインジケーター・スクロール制御などのリッチな UI コンポーネントが手に入る。

一方、現在のシンプル構成は依存ゼロで動く利点があるため、捨てずに並存させたい。

## Solution

- 新しい React フロントエンドを独立モジュール（例: `frontend/` ディレクトリ）として用意する
- **スタック**: Vite + Bun + React.js + `@chatscope/chat-ui-kit-react`
- 開発時は別ポート（例: `localhost:5173`）で起動し、バックエンド API（FastAPI）に CORS 経由でアクセス
- 既存の Vanilla JS 版（`app/static/`）はそのまま残す
- 将来的には本番ビルド成果物を FastAPI の StaticFiles で配信するか、nginx で振り分けるかを選択

**参考リンク:**
- https://github.com/chatscope/chat-ui-kit-react
- https://qiita.com/Yasushi-Mo/items/29e0a7b158ca8c9a18c3

**実装メモ:**
- `bun create vite frontend --template react-ts` で雛形作成
- FastAPI 側に CORS ミドルウェア追加が必要（開発時 `localhost:5173` を許可）
- SSE（`/chat/{job_id}/stream`）の受信は `EventSource` API または `@microsoft/fetch-event-source` で実装
