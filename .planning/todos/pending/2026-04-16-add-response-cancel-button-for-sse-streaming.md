---
created: 2026-04-16T03:55:00.000Z
title: AI 応答のキャンセルボタンを追加（SSE 受信中断）
area: ui
files:
  - frontend/src/components/MessageArea.tsx
  - frontend/src/hooks/useChat.ts
  - app/api/routes/jobs.py
  - app/jobs/job_store.py
---

## Problem

AI の応答待ち中（バウンシングドット表示中）にリクエストをキャンセルする手段がない。長時間のツール実行やタイムアウト間際のジョブを中断できず、ユーザーは応答が返るまで待つしかない。

## Solution

バウンシングドット + 経過秒数カウンターの横にキャンセルボタンを追加:

### フロントエンド

1. **MessageArea.tsx**: ドットアニメーション横に `✕` ボタンを追加
   ```
   ● ● ●  12s  [✕ キャンセル]
   ```
2. **useChat.ts**: `onCancel` コールバックを追加
   - SSE の `EventSource` を `.close()` して受信を中断
   - `isThinking` を `false` にリセット
   - 部分的に受信したストリーミングテキストがあればメッセージとして確定（「(中断されました)」付記）

### バックエンド（検討）

フロントで SSE を切るだけでは、バックエンドのジョブは走り続ける。完全なキャンセルには:

- `POST /api/job/{id}/cancel` エンドポイントを追加
- `job_store` にキャンセルフラグを立てる
- worker 側で定期的にフラグをチェックし、`GraphRecursionError` 相当の中断を行う
- ただし Copilot SDK のセッションは途中キャンセル不可（`send_and_wait` はブロッキング）なので、実際には「次のステップに進まない」レベルの中断になる

### 段階的実装

- **Phase 1**: フロントのみ（SSE 切断 + UI リセット）— バックエンドは走り続けるが UX は改善
- **Phase 2**: バックエンドキャンセル（`/api/job/{id}/cancel` + worker フラグチェック）

Phase 1 だけでも十分実用的。
