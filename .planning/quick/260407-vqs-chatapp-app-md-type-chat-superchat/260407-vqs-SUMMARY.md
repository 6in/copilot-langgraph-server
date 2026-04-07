---
phase: quick
plan: "260407-vqs"
subsystem: routing
tags: [frontend, backend, routing, chat, superchat]
dependency_graph:
  requires: []
  provides: [chat-app-type-routing]
  affects: [frontend/src/App.tsx, app/api/routes/apps.py]
tech_stack:
  added: []
  patterns: [frontmatter-type-field, screen-type-branching]
key_files:
  created: []
  modified:
    - apps/chat/APP.md
    - app/api/models.py
    - app/api/routes/apps.py
    - frontend/src/types.ts
    - frontend/src/App.tsx
decisions:
  - "APP.md の type フィールドのデフォルト値を superchat とし、既存アプリへの影響をゼロにした"
  - "handleNavigate で app.type === 'chat' のみ分岐し、未知の type は superchat にフォールバック"
metrics:
  duration: "~10min"
  completed_at: "2026-04-07T13:54:50Z"
  tasks_completed: 2
  files_modified: 5
---

# Quick 260407-vqs: ChatApp ルーティング修正 Summary

APP.md の `type` フィールドで Chat と SuperChat を分岐し、Chat アプリ選択時に ChatApp コンポーネントをレンダリングして GemSelector が表示されないようにした。

## What Was Built

メニューから Chat を選択すると `SuperChatApp`（GemSelector 付き）にルーティングされていたバグを修正。`APP.md` に `type` フロントマターフィールドを追加し、バックエンドがそれを API で返すことで、フロントエンドが `ChatApp` / `SuperChatApp` を正しく分岐できるようにした。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend: APP.md type フィールド追加・AppInfo 拡張・apps.py 読み取り | 6c6d678 | apps/chat/APP.md, app/api/models.py, app/api/routes/apps.py |
| 2 | Frontend: AppDefinition 型拡張・App.tsx chat 画面追加 | 6d2f90b | frontend/src/types.ts, frontend/src/App.tsx |

## Key Changes

### Backend
- `apps/chat/APP.md`: フロントマターに `type: chat` を追加
- `app/api/models.py`: `AppInfo` に `type: str = "superchat"` フィールド追加（デフォルト `"superchat"` で既存 APP.md への影響なし）
- `app/api/routes/apps.py`: `post.metadata.get("type", "superchat")` で読み取り `AppInfo` に渡す

### Frontend
- `frontend/src/types.ts`: `AppDefinition` に `type?: string` 追加
- `frontend/src/App.tsx`:
  - Screen 型に `'chat'` 追加（8-screen に拡張）
  - `ChatApp` を import
  - `handleNavigate`: `app.type === 'chat'` なら `'chat'` 画面、それ以外は `'superchat'`
  - `currentScreen === 'chat'` レンダリングブロック追加（Header + ChatApp）

## Verification

- `python -c "import frontmatter; ..."` で APP.md type=chat と AppInfo デフォルト値を確認: PASS
- `docker compose exec frontend npx tsc --noEmit`: エラーなし

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `apps/chat/APP.md` 修正: FOUND
- `app/api/models.py` AppInfo.type: FOUND
- `app/api/routes/apps.py` type 読み取り: FOUND
- `frontend/src/types.ts` AppDefinition.type: FOUND
- `frontend/src/App.tsx` chat screen: FOUND
- commit 6c6d678: FOUND
- commit 6d2f90b: FOUND
