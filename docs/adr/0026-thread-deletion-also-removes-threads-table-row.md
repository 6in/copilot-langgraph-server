# 0026. スレッド削除時に threads テーブルの行も削除する

**Date:** 2026-04-14  
**Status:** Accepted

## Context

`DELETE /api/threads/{thread_id}` エンドポイントは、LangGraph の `AsyncPostgresSaver.adelete_thread()` を呼び出すことでスレッドのチェックポイントデータを削除していた。
しかし `adelete_thread()` が操作するのは `checkpoints` / `checkpoint_blobs` / `checkpoint_writes` の3テーブルのみであり、スレッドのメタデータを保持する `threads` テーブルの行は削除されなかった。

その結果、削除操作後も `GET /api/threads?app_id=...` が `threads` テーブルを直接クエリするため、チェックポイントは消えているにもかかわらず削除済みスレッドが一覧に復活するバグが発生していた。
Chat / SuperChat / Gems / DebateChat / Canvas のすべてのアプリが同一エンドポイントを共有しているため、全アプリで同じ問題が起きていた。

UI 側の確認ダイアログには固定文言 `"このスレッドを削除しますか？"` しか表示されず、どのスレッドを削除しようとしているか判別できないという UX 問題も同時に発見された。

## Decision

1. **`delete_thread()` の DB 操作を1トランザクションに統合する**  
   所有権チェック（`SELECT`）と `threads` テーブルへの `DELETE` を同一 `psycopg.AsyncConnection` 内で実行し、`conn.commit()` で確定させる。`adelete_thread()` はその後に呼び出してチェックポイント系テーブルを削除する。

2. **削除確認ダイアログにスレッド名を表示する**  
   `ThreadSidebar.tsx` の `ConfirmModal` の `message` prop を動的に生成し、`「{thread.label}」を削除しますか？` の形式で表示する。

3. **Copy all のロール表示にエージェント名を反映する**  
   同セッションで `ChatMessage.senderName` が設定されていない問題も発覚。`MessageArea.tsx` の `CopyAllButton` で `senderName ?? 'Assistant'` を使うよう修正し、SuperChat / DebateChat のエージェント名がコピー結果に正しく出力されるようにした。

## Alternatives Considered

- **`adelete_thread()` を拡張して `threads` 行も削除する** — LangGraph の `AsyncPostgresSaver` は外部ライブラリであり改変はメンテナンス負荷が高い。ラッパー側で補う方が安全。
- **`GET /api/threads` 側で orphan フィルタリングを行う** — クエリコストが増加し、根本的な不整合データが残り続けるため不採用。

## Consequences

- **正**: スレッド削除後に再表示しても復活しなくなった。全アプリで一貫した動作となる。
- **正**: 削除確認ダイアログにスレッド名が表示され、誤削除リスクが低下した。
- **正**: Copy all のコピー結果にエージェント名が反映され、SuperChat / DebateChat のログとして意味のある出力になった。
- **注意**: `adelete_thread()` が失敗しても `threads` 行はすでに削除済みになる。チェックポイントデータは残るが UI 上は見えなくなる（孤立レコード）。現状は `except: pass` で無視しているが、将来的には定期クリーンアップを検討する。
