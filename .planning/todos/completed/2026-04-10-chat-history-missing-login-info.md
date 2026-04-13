---
created: 2026-04-10T03:12:48.416Z
title: チャット履歴にログイン情報（ユーザー名）が含まれない問題を調査する
area: auth
files: []
---

## Problem

チャット会話の履歴にログイン情報（ユーザー名など）が追加されていない。
以下のやり取りで確認：

- User: 「ハロー」→ Assistant: 通常応答
- User: 「私の名前ってわかる？」→ Assistant: 「いいえ、まだ伺っていません」

会話コンテキストに認証済みユーザーの情報（GitHubユーザー名など）が渡されていない可能性がある。
LangGraph の StateGraph に認証情報が inject されていないか、フロントエンドが `/api/me` の情報をチャットリクエストに含めていない可能性。

## Solution

1. `GET /api/me` のレスポンス（GitHub ユーザー名）がフロントエンドで取得できているか確認
2. `POST /api/chat` のリクエストボディにユーザー名が含まれているか確認
3. LangGraph StateGraph の MessagesState にシステムプロンプトとしてユーザー名を注入する仕組みを検討
4. 必要であれば `app/graph/builder.py` のシステムメッセージ設定を追加
