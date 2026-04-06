---
created: 2026-04-03T09:30:01.620Z
title: チャットのコンテキストにてユーザー情報も入れるようにする
area: api
files:
  - app/api/routes/chat.py
  - app/jobs/worker.py
  - app/graph/builder.py
---

## Problem

現在 LangGraph に渡す会話コンテキスト（MessagesState）にはユーザー情報が含まれていない。
マルチユーザー対応を進めた結果、JWT から `github_login` が取得できるようになったが、グラフ実行時にその情報がシステムプロンプトや state に渡されていない。
将来的にエージェントがユーザー固有の応答（例：「○○さん、こんにちは」）や権限制御を行う際に必要になる。

## Solution

`POST /api/chat` で JWT から取得した `github_login`（および必要なら `github_token`）を LangGraph の invoke に渡す。
方法の候補：

1. `config["configurable"]` に `github_login` を追加して graph 内で参照できるようにする
2. MessagesState にシステムメッセージとして先頭に `github_login` を注入する
3. StateGraph の State 型に `user` フィールドを追加して明示的に持たせる

最小対応は (1) の configurable 渡し。(3) は State スキーマ変更を伴うため大きめの変更。
