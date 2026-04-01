---
created: 2026-04-01T02:54:06.855Z
title: ログアウト後の再認証で "Waiting For authentication..." が止まる
area: auth
files:
  - app/auth/manager.py
  - app/api/routes/auth.py
---

## Problem

ログアウト後に再ログインを試みたところ、Device Flow による認証コード入力・承認は完了したにもかかわらず、
UI が "Waiting For authentication..." のまま止まり、認証完了を検知できない状態になる。

ログアウト実装（今回追加）では `token.enc` を削除してサーバー再起動を促す設計だったが、
サーバーを再起動せずに再認証を試みた場合のフロー、または Device Flow のポーリングループが
ログアウト後に正しくリセット・再起動されていない可能性がある。

## Solution

TBD — 以下の切り分けが必要:

1. ログアウト後のサーバー状態（`app.state.device_flows` 等）が正しくリセットされているか確認
2. Device Flow のポーリングループがログアウト後に再起動できる構造になっているか確認
3. フロントエンドの polling が中断・再開できているか確認
4. 根本対応: ログアウト後にサーバーを再起動しなくても再認証できるフローを実装するか、
   再起動必須であることを UI で明確に伝えるか、のどちらかを選択する
