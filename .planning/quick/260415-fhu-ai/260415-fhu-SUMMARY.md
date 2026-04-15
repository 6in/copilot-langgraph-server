---
phase: quick-260415-fhu
plan: "01"
subsystem: streaming
tags: [streaming, sse, copilot-sdk, langgraph, react]
dependency_graph:
  requires: []
  provides: [token-streaming-preview]
  affects: [app/providers/copilot.py, app/jobs/notifier.py, app/jobs/handlers/langgraph_handler.py, frontend/src/hooks/useChat.ts, frontend/src/components/MessageArea.tsx, frontend/src/components/ChatApp.tsx]
tech_stack:
  added: [asyncio.Queue for delta buffering, astream_events(version="v2"), ChatGenerationChunk, AIMessageChunk]
  patterns: [Copilot SDK event-driven streaming → asyncio.Queue → LangGraph astream_events → SSE token events → React streamPreview state]
key_files:
  created: []
  modified:
    - app/providers/copilot.py
    - app/jobs/notifier.py
    - app/jobs/handlers/langgraph_handler.py
    - frontend/src/hooks/useChat.ts
    - frontend/src/components/MessageArea.tsx
    - frontend/src/components/ChatApp.tsx
decisions:
  - "_astream は asyncio.Queue を使って session.on() コールバックから async generator に橋渡しする — call_soon_threadsafe でスレッドセーフに put_nowait"
  - "astream_events on_chain_end / LangGraph イベントで最終状態を取得、ainvoke フォールバックで堅牢性確保"
  - "streamPreview は末尾 200 文字のみ保持 — DOM/React reconciliation 負荷対策"
  - "streamPreview は plain text 表示のみ（Markdown レンダリングなし）— 完成時に MarkdownMessage で描画"
metrics:
  duration: "3 min"
  completed_date: "2026-04-15"
  tasks_completed: 3
  files_modified: 6
---

# Quick 260415-fhu Plan 01: AI 応答ストリーミングプレビュー実装 Summary

**One-liner:** Copilot SDK ASSISTANT_MESSAGE_DELTA → ChatCopilot._astream → LangGraph astream_events(on_chat_model_stream) → Notifier.send_token → SSE token イベント → useChat streamPreview → 3 ドット下プレビュー表示、という一貫したトークンストリームパス実装。

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | ChatCopilot._astream + Notifier.send_token | 92b6ddf | copilot.py, notifier.py |
| 2 | langgraph_handler astream_events 配管 | 9e4ba2b | langgraph_handler.py |
| 3 | フロント streamPreview 表示 | ebffa6a | useChat.ts, MessageArea.tsx, ChatApp.tsx |

## What Was Built

### Task 1: Backend Streaming Foundation

`app/providers/copilot.py` に `ChatCopilot._astream` async generator を実装:
- `asyncio.Queue[str | None]` を作成（None = 完了シグナル）
- `session.on(handler)` で ASSISTANT_MESSAGE_DELTA / SESSION_IDLE ハンドラを登録（send() の前）
- `call_soon_threadsafe(queue.put_nowait, token)` でスレッドセーフに queue に投入
- `session.send(prompt)` 非ブロッキング呼び出し
- queue から ChatGenerationChunk を yield し、None を受け取ったらループ終了

`app/jobs/notifier.py` に `send_token(token: str)` メソッドを追加:
- `BaseNotifier`: no-op デフォルト実装
- `WebNotifier`: `job_store.notify(job_id, "token", token=token)` を呼び出す

### Task 2: LangGraph Handler Migration

`app/jobs/handlers/langgraph_handler.py` の `graph.ainvoke()` を `graph.astream_events(version="v2")` に移行:
- `on_chat_model_stream` イベントで `chunk.content` を取得し `notifier.send_token(token)` を呼ぶ
- `on_chain_end` / LangGraph イベントから最終状態を取得
- `final_state is None` の場合は `ainvoke` フォールバック

### Task 3: Frontend Preview Display

`frontend/src/hooks/useChat.ts`:
- `streamPreview` state 追加（初期値 `""`）
- SSE `token` イベントハンドラ: 末尾 200 文字保持で累積
- `done` / 新規送信時に `setStreamPreview("")` でクリア
- 戻り値に `streamPreview` 追加

`frontend/src/components/MessageArea.tsx`:
- `streamPreview?: string` prop 追加
- 3 ドットアニメーションの下に plain text プレビュー表示（`white-space: pre-wrap`, `max-height: 3em`）

`frontend/src/components/ChatApp.tsx`:
- `useChat` から `streamPreview` を受け取り `<MessageArea streamPreview={streamPreview} />` に渡す

## Deviations from Plan

None - プランの指示通りに実装しました。

## Known Stubs

なし。全ての変更は実際の機能として実装されています。

## Self-Check

- [x] app/providers/copilot.py 修正済み (92b6ddf)
- [x] app/jobs/notifier.py 修正済み (92b6ddf)
- [x] app/jobs/handlers/langgraph_handler.py 修正済み (9e4ba2b)
- [x] frontend/src/hooks/useChat.ts 修正済み (ebffa6a)
- [x] frontend/src/components/MessageArea.tsx 修正済み (ebffa6a)
- [x] frontend/src/components/ChatApp.tsx 修正済み (ebffa6a)

## Self-Check: PASSED
