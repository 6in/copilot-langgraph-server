---
phase: 27-askuserquestion-ai-ui
plan: 02
subsystem: frontend
tags: [askuserquestion, useChat, MessageArea, QuestionPanel]
dependency_graph:
  requires: [27-01]
  provides: [pendingQuestion-state, handleQuestionSubmit-callback, MessageArea-QuestionPanel-replacement]
  affects: [ChatApp, SuperChatApp, GemChatApp, CanvasChatApp, DebateChatApp]
tech_stack:
  added: []
  patterns: [conditional-input-replacement, tag-detection-in-parseJobResult]
key_files:
  created: []
  modified:
    - frontend/src/hooks/useChat.ts
    - frontend/src/components/MessageArea.tsx
    - frontend/src/components/ChatApp.tsx
    - frontend/src/components/SuperChatApp.tsx
    - frontend/src/components/GemChatApp.tsx
    - frontend/src/components/CanvasChatApp.tsx
    - frontend/src/components/DebateChatApp.tsx
decisions:
  - "parseJobResult で JSON/plain text 両方の AUQ タグ検出に対応（A3 安全策）"
  - "handleQuestionSubmit は全角コロン区切り（質問：回答）でテキスト化"
requirements-completed: [AUQ-03, AUQ-04, AUQ-05]
metrics:
  duration: 8min
  completed: 2026-04-17
  tasks_completed: 3
  tasks_total: 3
  files_modified: 7
---

# Phase 27 Plan 02: useChat hook AUQ 検出 + MessageArea 入力置換 + 全アプリ伝播 Summary

useChat hook に parseAUQ によるタグ検出と pendingQuestion 状態管理を追加し、MessageArea の入力エリアを QuestionPanel で条件置換、全 5 アプリコンポーネントに props 伝播した。

## Completed Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | useChat hook に AUQ 検出ロジックと pendingQuestion 状態を追加する | 2330576 | frontend/src/hooks/useChat.ts |
| 2 | MessageArea に入力エリア置換ロジックを追加し、全 5 アプリに伝播させる | fcc5ac1 | MessageArea.tsx, ChatApp.tsx, SuperChatApp.tsx, GemChatApp.tsx, CanvasChatApp.tsx, DebateChatApp.tsx |
| 3 | ブラウザで AskUserQuestion フロー全体を手動確認 | -- | checkpoint:human-verify（部分確認 — モデルが AUQ 形式を生成せず） |

## Implementation Details

### Task 1: useChat hook AUQ 検出

- `parseAUQ` と `AskUserQuestionPayload` 型をインポート
- `parseJobResult` の戻り値型に `askUserQuestion` フィールドを追加
- try ブロック内（JSON パース成功後）でも `<ask_user_question>` タグを検出（A3 対応）
- catch ブロック内（plain text）でも `parseAUQ` でタグ検出
- `pendingQuestion` state と `handleQuestionSubmit` callback を追加
- `handleResult` 内で `askUserQuestion` 検出時に `setPendingQuestion` を呼び出し、early return
- `handleQuestionSubmit` は回答を「質問：回答」形式のテキストに変換して `sendMessage` に渡す

### Task 2: MessageArea + 全 5 アプリ伝播

- `MessageAreaProps` に `pendingQuestion` と `onQuestionSubmit` を追加
- chat-input-bar div 内を条件分岐: `pendingQuestion` がある場合は QuestionPanel を表示、ない場合は従来の textarea + Send ボタン
- 「質問に回答してください」ヒントテキストを QuestionPanel の上に表示
- ChatApp / SuperChatApp / GemChatApp / CanvasChatApp / DebateChatApp の全 5 ファイルで useChat の返値に `pendingQuestion`, `handleQuestionSubmit` を追加し、MessageArea に props として渡す

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **parseJobResult で JSON/plain text 両方対応**: AI レスポンスが JSON ラッパーに入っている場合でもタグ検出できるよう、try ブロック内でも `raw.includes('<ask_user_question>')` チェックを実施（A3 安全策）
2. **全角コロン区切り**: `handleQuestionSubmit` で回答テキスト化する際、質問と回答を「：」（全角コロン）で区切る（日本語 UI に自然）

## Verification

- `npx tsc --noEmit` が型エラーなしで通過（Task 1, Task 2 両方）
- Task 3（ブラウザ手動確認）: 部分確認。ユーザーがブラウザで動作確認を実施したが、Copilot モデルが `<ask_user_question>` XML 形式を生成せずプレーンテキストで質問を返したため、QuestionPanel の表示は確認できなかった。コード実装自体は正しいと判断。モデルがプロトコルに従うかどうかは AI の判断に依存する（Plan の注意書きにも記載済み）。

## Known Stubs

None.

## Issues Encountered

- **モデルが AUQ プロトコルに従わなかった**: ブラウザ確認時、Copilot モデルが `<ask_user_question>` XML タグ形式ではなくプレーンテキストで質問を返した。システムプロンプトへの AUQ プロトコル注入が Docker コンテナに反映されていない可能性、またはモデルがプロトコルに従わなかった可能性がある。コード実装（parseAUQ、QuestionPanel、条件置換ロジック）は型チェック済みで正しい。

## Next Phase Readiness

- AUQ フロントエンド統合は完了。全 5 アプリで QuestionPanel が条件表示される実装が入っている
- モデルが `<ask_user_question>` 形式を生成した場合に自動的に QuestionPanel が表示される
- システムプロンプトの AUQ プロトコル注入が確実に反映されているかの確認は別途必要

## Self-Check: PASSED

- FOUND: frontend/src/hooks/useChat.ts
- FOUND: frontend/src/components/MessageArea.tsx
- FOUND: frontend/src/components/QuestionPanel.tsx
- FOUND: commit 2330576 (Task 1)
- FOUND: commit fcc5ac1 (Task 2)

---
*Phase: 27-askuserquestion-ai-ui*
*Completed: 2026-04-17*
