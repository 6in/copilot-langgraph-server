---
created: 2026-04-17T14:41:35.635Z
title: チャット入力欄からファイルアップロード + Worker 生成ファイルのダウンロード
area: ui
files:
  - frontend/src/components/MessageArea.tsx
  - frontend/src/hooks/useChat.ts
  - app/api/routes/chat.py
  - app/jobs/worker.py
---

## Problem

現状のチャット UI はテキストのみの入出力で、ファイルの送受信ができない。

1. **アップロード**: ユーザーがチャット入力欄からファイル（CSV, 画像, テキスト等）を添付して送信できない。CodeAct エージェントでデータ分析をしたい場合にファイルを直接渡せると便利。

2. **ダウンロード**: Worker（execute_python 等）が生成したファイル（グラフ画像, 処理結果 CSV 等）をチャット画面からダウンロードできない。現状は stdout テキストでしか結果を返せない。

## Solution

- アップロード: MessageArea にファイル添付 UI を追加。ファイルを API 経由で一時領域に保存し、Worker がアクセスできるようにする（shared volume or Redis）
- ダウンロード: Worker が生成したファイルを共有ボリュームに書き出し、API からダウンロードエンドポイントを提供。チャットメッセージ内にダウンロードリンクを表示
- execute_python の出力に画像等のバイナリ結果を含められるようにする（base64 or ファイルパス参照）
