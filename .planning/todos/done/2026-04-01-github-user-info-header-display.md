---
created: 2026-04-01T08:43:06.804Z
title: GitHubログイン情報からユーザー情報取得＆ヘッダーにユーザー名表示
area: ui
files:
  - app/providers/copilot.py
  - app/static/index.html
---

## Problem

現在のチャット UI にはログイン中のユーザー情報が表示されていない。Device Flow 認証でログインした GitHub アカウントのユーザー名（またはアバター）をヘッダーに表示することで、誰のセッションで動いているかを視覚的に確認できるようにしたい。

## Solution

- GitHub Copilot SDK または GitHub REST API（`/user` エンドポイント）を使って、認証済みトークンからユーザー情報（`login`, `avatar_url` など）を取得
- バックエンドに `/api/me` などのエンドポイントを追加してユーザー情報を返す
- フロントエンドの `index.html` のヘッダー部分にユーザー名（＋任意でアバター画像）を表示
- 認証済みでない場合は「未ログイン」状態のフォールバック表示を用意する
