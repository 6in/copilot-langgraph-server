---
created: 2026-04-04T02:00:00.000Z
title: SuperChat 履歴保存とモード別スレッド分離
area: api
files:
  - app/jobs/handlers/orchestrator_handler.py
  - app/api/routes/chat.py
  - app/api/models.py
  - app/orchestrator/graph.py
  - frontend/src/hooks/useThreads.ts
  - frontend/src/api/client.ts
---

## Problem

OrchestratorHandler が thread_id も checkpointer も使っていないため、SuperChat の会話が `checkpoints` テーブルに記録されない。
`GET /api/threads` は `INNER JOIN checkpoints` なので SuperChat スレッドが履歴一覧に出てこない。
また `thread_labels` に `mode` カラムがなく、シンプル/スーパーの履歴を分けられない。

根本問題が3層ある:
1. `thread_labels` に `mode` カラムがない → シンプル/スーパーの区別不可
2. `GET /api/threads` が `INNER JOIN checkpoints` → SuperChat スレッドが JOIN で弾かれる
3. OrchestratorHandler が thread_id/checkpointer 未使用 → 会話継続性もない

## Solution

### A: 履歴表示修正 (軽量)
- `thread_labels` に `mode VARCHAR(16) DEFAULT 'simple'` カラム追加 (DB migration)
- `POST /api/threads` と `POST /api/chat` で mode を受け取り保存
- `GET /api/threads?mode=simple|super` フィルタ対応
- `GET /api/threads` を `LEFT JOIN checkpoints` に変更（SuperChat スレッドも出る）
- フロント: `useThreads(mode)` でモード別リスト取得、SuperChatApp は `mode='super'` で呼ぶ

### B: 会話継続性修正 (フル)
- OrchestratorGraph を LangGraph checkpointer 対応にする
  - `MessagesState` ベースに変更 or `AgentState` + `AsyncPostgresSaver`
- OrchestratorHandler で `config = {"configurable": {"thread_id": thread_id}}` を渡す
- フロントで SuperChat スレッド切替時に過去の会話を復元

A + B セットで次フェーズとして実装する。
