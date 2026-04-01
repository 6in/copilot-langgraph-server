---
created: 2026-04-01T06:24:25.191Z
title: PoC の非同期イベント処理パターンをベースに移行
area: general
files:
  - app/providers/copilot.py
  - app/api/routes/chat.py
  - app/api/main.py
  - /home/parallels/work/copilot-server-poc/src/worker/scripts/code_review.py
  - docs/pre/async_chat_sse_polling.md
---

## Problem

現在の `ChatCopilot._agenerate()` は `send_and_wait()` を使っており、レスポンスが来るまでブロックする同期的なやり取りになっている。また `/api/chat` はリクエスト中に LangGraph を直接実行しており、以下の問題がある:

- サーバー再起動で実行中のタスクが消える
- 重い AI 処理が FastAPI のイベントループを圧迫する
- スケールアウト時に別インスタンスのジョブを追えない
- ストリーミング（部分レスポンスの逐次受信）ができない

## Solution

`docs/pre/async_chat_sse_polling.md` に詳細な設計仕様あり。以下がターゲットアーキテクチャ:

```
POST /chat → job_id 即時返却 → Redis キューにジョブ積む
Worker（別プロセス）→ LangGraph 実行 → JobStore.save_result() → Notifier.done()
GET /chat/{job_id}/stream → SSE（リアルタイム通知）
GET /job/{job_id} → ポーリング API（リカバリ・再接続用）
```

**主要コンポーネント:**
- `JobStore`: 結果の保存（Redis）と SSE キュー管理の分離
- `Notifier`（Strategy パターン）: Web / Slack など通知先ごとに分離
- `Worker`: 別プロセスで LangGraph 実行。`create_llm_for_user()` でユーザー別トークンを使用

**PoC の SDK パターン（code_review.py）との組み合わせ:**
- Worker 内で `session.on()` イベントリスナー方式を使用
- `session.idle` イベントで完了を検知 → `job_store.save_result()` → `notifier.done()`

**注意点:**
- SDK バージョン差異の確認が必要（PoC は 0.1.0、現プロジェクトは 0.2.0）
- Redis の追加が必要（現在は SQLite のみ）
- マルチユーザ対応 todo（JWT 導入）と合わせて実装するのが自然
- Slack Bot 対応も仕様に含まれる（`reply_to` パターン）
