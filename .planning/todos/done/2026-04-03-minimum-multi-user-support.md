---
created: 2026-04-03T08:39:05.678Z
title: 最低限のマルチユーザ対応
area: api
files:
  - app/api/routes/chat.py
  - app/api/models.py
---

## Problem

現在のスレッド一覧（GET /api/threads）はログインユーザーに関わらず全スレッドを返す。`checkpoints` テーブルにユーザー情報が紐付いていないため、複数ユーザーが使うと全員のチャット履歴が混在する。また `/api/threads` は JWT 保護もかかっていない（個人ツール前提の意図的設計）。

## Solution

`thread_labels` テーブルに `github_login` カラムを追加し、スレッド作成・取得時にログインユーザーでフィルタする最小対応。

```sql
ALTER TABLE thread_labels ADD COLUMN github_login TEXT;
```

- POST /api/chat 時に JWT から `github_login` を取得して `thread_labels` に保存
- GET /api/threads で `WHERE tl.github_login = ?` フィルタを追加
- `/api/threads` に JWT 保護を追加（任意: 個人ツールなら不要とも言える）

`checkpoints` テーブル自体はユーザー非依存のまま維持し、アクセス制御は `thread_labels` レイヤーで行う。
