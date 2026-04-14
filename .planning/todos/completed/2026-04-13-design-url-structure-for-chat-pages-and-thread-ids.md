---
created: 2026-04-13T14:52:07.735Z
title: チャット各ページのURL・チャットID設計
area: ui
files:
  - frontend/src/App.tsx
  - frontend/src/components/ChatApp.tsx
  - frontend/src/components/SuperChatApp.tsx
---

## Problem

各チャットアプリ（Chat / SuperChat / GemChat / Canvas / DebateChat）やスレッドに対して、
直接アクセスできる URL が存在しない。現状はすべて SPA のクライアントサイドルーティングのみで、
特定のスレッドや会話へのパーマリンクがない。

具体的な課題:
- スレッドを共有・ブックマークできない
- ブラウザの戻る/進むボタンが機能しない
- アプリ・スレッドの状態が URL に反映されない（ページリロードで状態がリセット）
- チャット ID（thread_id）が URL に含まれていない

## Solution

URL 設計の検討と実装:
- `/orochi/chat/{thread_id}` のような形で各チャットアプリ＋スレッドへのルーティングを設計
- React Router（または現状の条件分岐）に URL パラメータを追加
- スレッド選択時に URL を更新し、ブラウザ履歴を管理
- 直接 URL アクセス時にスレッドを復元する処理

検討事項:
- アプリ種別（chat/superchat/gem/canvas/debate）を URL に含めるか
- スレッド ID は UUID のまま使うか短縮するか
- `APP_PREFIX` (`/orochi`) との整合性
