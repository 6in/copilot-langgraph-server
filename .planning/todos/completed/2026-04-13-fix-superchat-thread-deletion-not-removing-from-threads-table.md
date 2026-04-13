---
created: 2026-04-13T14:54:04.254Z
title: SuperChat スレッド削除後に再表示すると復活するバグを修正
area: api
files:
  - app/api/routes/chat.py
  - frontend/src/hooks/useThreads.ts
---

## Problem

SuperChat でスレッドを削除ボタンで削除すると、フロントエンド上は即座に消える（楽観的更新）。
しかし SuperChat 画面を離れて戻ると、削除したはずのスレッドが復活している。

**根本原因:**
`DELETE /api/threads/{thread_id}` の実装（`app/api/routes/chat.py:295`）が
`checkpointer.adelete_thread(thread_id)` のみを呼んでいる。
これは `checkpoints` / `checkpoint_blobs` / `checkpoint_writes` テーブルの行を削除するが、
`threads` テーブルの行は削除しない。

再表示時に `GET /api/threads?app_id=superchat` が `threads` テーブルを直接 SQL クエリするため、
チェックポイントは消えていても `threads` 行が残っているスレッドが返ってしまう。

## Solution

`chat.py` の `delete_thread()` エンドポイントに `threads` テーブルの DELETE を追加:

```python
# checkpointer 削除の前後どちらでも可
await conn.execute(
    "DELETE FROM threads WHERE thread_id = %s AND github_login = %s",
    (thread_id, github_login),
)
await conn.commit()
```

所有権チェックは既存のクエリで行っているので、そのまま DELETE に切り替えるか、
`SELECT` + `DELETE` を1回のトランザクションにまとめる形で実装する。
