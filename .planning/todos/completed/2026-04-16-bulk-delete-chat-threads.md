---
created: 2026-04-16T03:00:00.000Z
title: チャット履歴の一括選択削除機能を追加
area: ui
files:
  - frontend/src/components/ThreadSidebar.tsx
  - frontend/src/hooks/useThreads.ts
  - app/api/routes/chat.py
---

## Problem

ThreadSidebar でスレッドを削除するには 1 件ずつ削除ボタンを押す必要がある。テスト中に大量のスレッドが溜まった場合やまとめて整理したい場合に、1 件ずつ削除するのは非常に手間。

## Solution

ThreadSidebar に一括選択・一括削除モードを追加:

1. **UI**: サイドバーに「選択モード」トグル（チェックボックスアイコン等）を追加
2. **選択モード ON**: 各スレッド行にチェックボックスを表示、ヘッダーに「全選択 / 選択解除」ボタン
3. **一括削除**: 選択中のスレッド数を表示し「N 件削除」ボタンで ConfirmModal → 一括削除実行
4. **API**: `DELETE /api/chat/threads` に `thread_ids: string[]` を受け取るバッチエンドポイントを追加（または既存の単体削除を Promise.all で並列実行）
5. **LangGraph checkpointer**: `adelete_thread` を各 thread_id に対して実行

注意点:
- 全選択時に件数が多い場合のパフォーマンス（API 側でバッチ対応が望ましい）
- 削除後のスレッド選択状態リセット（削除されたスレッドが選択中だった場合）
- ConfirmModal で「N 件のスレッドを削除しますか？」と件数を明示
