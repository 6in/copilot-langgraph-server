# プロセス構成図 — Copilot LangGraph Chat

このドキュメントは、`docker-compose.yml` で定義されたサービス構成をMermaidフローチャートで表現したものです。

5つのサービス（frontend, api, worker, redis, postgres）の依存関係、公開ポート、ボリューム、データフローを示します。

---

## Docker Compose サービストポロジー

```mermaid
graph TD
    subgraph compose["Docker Compose ネットワーク"]
        Frontend["**frontend**\nnode:22-alpine\n(./frontend/Dockerfile)\nport: 5173:5173\nenv: API_TARGET=http://api:8000"]
        API["**api**\nghcr.io/astral-sh/uv:python3.12-bookworm-slim\nport: 8000:8000\ncmd: uvicorn app.api.main:app\nvol: .:/app, ~/.copilot_sdk"]
        Worker["**worker**\nghcr.io/astral-sh/uv:python3.12-bookworm-slim\n(no host port)\ncmd: arq app.jobs.worker.WorkerSettings\nvol: .:/app, ~/.copilot_sdk"]
        Redis["**redis**\nredis:7-alpine\n(no host port)\nvol: redis-data"]
        Postgres["**postgres**\npgvector/pgvector:pg17\nhealthcheck: pg_isready\nvol: postgres-data"]
    end

    GitHub["GitHub\n(github.com)\nDevice Flow OAuth\nCopilot API"]

    %% depends_on edges（起動依存）
    Frontend -->|depends_on| API
    API -->|depends_on\nservice_healthy| Postgres
    API -->|depends_on\nservice_started| Redis
    Worker -->|depends_on\nservice_healthy| Postgres
    Worker -->|depends_on\nservice_started| Redis

    %% データフロー（実行時通信）
    Frontend -.->|"HTTP proxy /api"| API
    API -.->|"arq enqueue_job\n+ JobStore (GET result)"| Redis
    Worker -.->|"arq dequeue job\n+ JobStore (save_result + notifier.done)"| Redis
    API -.->|"checkpoints + thread_labels\n(AsyncPostgresSaver)"| Postgres
    Worker -.->|"checkpoints\n(LangGraph AsyncPostgresSaver)"| Postgres

    %% 外部接続
    Worker -.->|"JSON-RPC\n(CopilotClient subprocess)"| GitHub
    API -.->|"Device Flow OAuth\n(httpx POST)"| GitHub

    %% ボリューム
    Postgres --- pgvol[("postgres-data\n(named volume)")]
    Redis --- rvol[("redis-data\n(named volume)")]
```

---

## サービス詳細

| サービス | イメージ | ホストポート | 主な役割 |
|---------|---------|------------|---------|
| `frontend` | `node:22-alpine` (Dockerfile build) | 5173 | Vite dev server、`/api` を api コンテナへプロキシ |
| `api` | `uv:python3.12-bookworm-slim` | 8000 | FastAPI: chat/auth/job/me エンドポイント、arqジョブエンキュー、SSE |
| `worker` | `uv:python3.12-bookworm-slim` | なし | arq ワーカー: LangGraph実行、ChatCopilot呼び出し、結果保存 |
| `redis` | `redis:7-alpine` | なし(内部のみ) | arqジョブキュー + JobStore（ジョブ結果・done通知） |
| `postgres` | `pgvector/pgvector:pg17` | なし(内部のみ) | LangGraphチェックポイント + thread_labelsテーブル |
