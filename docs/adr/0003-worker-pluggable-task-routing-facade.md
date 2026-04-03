# 0003. Worker Pluggable Task Routing Facade

**Date:** 2026-04-03  
**Status:** Accepted

## Context

`app/jobs/worker.py` の `process_chat` 関数は LangGraph チャット処理をベタ書きしていた。将来的に ClaudeCode 実行・OpenCode 実行・汎用サーバー処理など、多様な非同期タスクを同じ arq ワーカー基盤で動かしたいが、処理タイプを区別する仕組みがなかった。

またフロントエンドから HTTP リクエスト経由で処理タイプを指定する手段もなく、拡張のたびに `worker.py` 本体を直接修正する必要があった。

## Decision

`task_type` フィールドによるディスパッチ方式を採用し、以下の構造に整理した。

**ハンドラー層の導入:**
```
app/jobs/handlers/
  base.py                — TaskHandler 抽象基底クラス (handle(ctx, job) → dict)
  langgraph_handler.py   — 既存の LangGraph 処理を移植
  __init__.py
```

**worker.py をファサードに変更:**
```python
TASK_HANDLERS: dict[str, TaskHandler] = {
    "langgraph": LangGraphHandler(),
}

async def process_chat(..., task_type: str = "langgraph") -> dict:
    handler = TASK_HANDLERS.get(task_type)
    return await handler.handle(ctx, job)
```

**エンドツーエンドの配線:**
- `ChatRequest`（Pydantic モデル）に `task_type: str = "langgraph"` を追加
- `chat.py` が `body.task_type` を arq enqueue_job に渡す
- フロントエンドの `ChatRequest` 型と `useChat` フックに `task_type` を追加（省略時は `"langgraph"` デフォルト）

## Alternatives Considered

**`if/elif` 分岐を worker.py に直書き** — シンプルだが、タスクタイプが増えるたびに `worker.py` を修正することになり、関心の分離ができない。新しいハンドラーの追加が既存ロジックへの変更を伴うため却下。

**別の arq job 関数として登録** — `process_chat` / `process_claude_code` など job 関数を複数用意する方法。arq の `WorkerSettings.functions` が増えていくが、共通の初期化処理（JobStore、notifier）が重複する。統一エントリポイントの方が管理しやすいと判断。

## Consequences

**ポジティブ:**
- 新しいタスクタイプの追加は `handlers/` にクラスを置いて `TASK_HANDLERS` に登録するだけ。`worker.py` 本体は触らない。
- `task_type` のデフォルト値が `"langgraph"` なので、既存の呼び出し元はすべて後方互換。

**ネガティブ・注意点:**
- worker コンテナはボリュームマウント（`. :/app`）なので、コードを変更した後は `docker compose restart worker` が必要。`--build` では反映されない（Dockerfile を変えていない限り）。コンテナが古いコードで動き続けると `TypeError: unexpected keyword argument 'task_type'` で全ジョブが即失敗する。
- フロントエンドに `task_type` のセレクター UI はまだない。`useChat` の `selectedTaskType` オプション経由で渡せる状態だが、`ChatApp.tsx` 側には未接続。
- 未知の `task_type` が来た場合はエラーメッセージを `job_store` に保存して graceful に失敗する（例外を投げない）。
