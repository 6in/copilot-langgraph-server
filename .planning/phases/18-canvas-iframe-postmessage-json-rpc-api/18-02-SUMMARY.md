---
phase: 18-canvas-iframe-postmessage-json-rpc-api
plan: "02"
subsystem: backend
tags: [iframe-rpc, arq, worker, psycopg_pool, config, docker]
dependency_graph:
  requires:
    - app/jobs/handlers/iframe_rpc_handler.py (Plan 01)
    - app/jobs/handlers/base.py
    - app/jobs/worker.py
  provides:
    - Extended worker with IframeRpcHandler registered as iframe_app_api
    - DB pool lifecycle management (startup/shutdown)
    - config/db_pools.yaml + config/db_pools.yaml.example
  affects:
    - app/jobs/worker.py (IframeRpcHandler registration + DB pools + process_chat signature)
    - docker-compose.yml (config/ volume mount for api and worker services)
    - .gitignore (db_pools.yaml excluded from git)
tech_stack:
  added:
    - psycopg_pool.AsyncConnectionPool (DB pool lifecycle in arq worker)
    - yaml (stdlib pyyaml — config file loading)
  patterns:
    - AsyncConnectionPool open=False + await pool.open(wait=True, timeout=30.0) per D-18
    - FileNotFoundError non-fatal — QUERY method gracefully unavailable when no config
    - TASK_HANDLERS dict extension pattern (consistent with Phase 17 DebateHandler)
key_files:
  created:
    - config/db_pools.yaml.example
    - config/db_pools.yaml
  modified:
    - app/jobs/worker.py
    - docker-compose.yml
    - .gitignore
decisions:
  - AsyncConnectionPool open=False, then await pool.open(wait=True) in startup to avoid blocking module import
  - FileNotFoundError in startup is non-fatal — worker runs without QUERY support when no config present
  - config/db_pools.yaml gitignored to protect DSN credentials (T-18-06)
  - config/ volume mounted read-only (:ro) in both api and worker services (D-17)
metrics:
  duration: 12min
  completed: 2026-04-09
  tasks_completed: 3
  files_created: 2
  files_modified: 3
---

# Phase 18 Plan 02: arq ワーカー拡張 + DB プール管理 + config 設定 Summary

**One-liner:** arq worker に IframeRpcHandler を iframe_app_api として登録し、psycopg_pool AsyncConnectionPool の startup/shutdown ライフサイクルと db_pools.yaml 設定ファイルを整備。

## What Was Built

### Task 1: config/db_pools.yaml + .gitignore + example ファイル

- `config/db_pools.yaml.example` — リポジトリにコミットされる設定テンプレート。SECURITY コメントで READ-ONLY ユーザー使用を明記（T-18-07: CTE+write bypass の第2防御）。`pools: { name: { dsn: ... } }` 形式（D-16）。
- `config/db_pools.yaml` — 実際のローカル開発設定（postgres インスタンスへの接続）。`.gitignore` に追加して DSN 認証情報をリポジトリから除外（T-18-06）。
- `.gitignore` に `config/db_pools.yaml` エントリを追加。

### Task 2: worker.py 拡張

`app/jobs/worker.py` に以下を追加:

- **imports:** `import yaml`, `from psycopg_pool import AsyncConnectionPool`, `from app.jobs.handlers.iframe_rpc_handler import IframeRpcHandler`
- **`DB_POOLS_CONFIG`:** `os.getenv("DB_POOLS_CONFIG", "config/db_pools.yaml")` — 設定ファイルパスを環境変数で上書き可能
- **`TASK_HANDLERS`:** `"iframe_app_api": IframeRpcHandler()` を追加（Plan 01 で実装済みのハンドラを接続）
- **`startup()`:** `ctx["db_pools"] = {}` を初期化し、yaml から pool 設定を読み込み、`AsyncConnectionPool(open=False)` + `await pool.open(wait=True, timeout=30.0)` で接続プールを初期化（D-18）。`FileNotFoundError` は非致命的（設定ファイルなしで起動可能）。
- **`shutdown()`:** `ctx.get("db_pools", {}).values()` の全 pool に `await pool.close()` を呼び出してから Redis を閉じる。
- **`process_chat()` シグネチャ:** `rpc_method: str | None = None`, `rpc_params: dict | None = None` を追加（デフォルト None で後方互換）。
- **job dict:** `"rpc_method": rpc_method`, `"rpc_params": rpc_params` を追加して IframeRpcHandler に転送。

### Task 3: docker-compose.yml — config/ ボリュームマウント追加（D-17）

`api` サービスと `worker` サービスの `volumes:` セクションに `./config:/app/config:ro` を追加。`docker compose config` で YAML バリデーション済み。

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. Plan 02 の完了により `iframe_app_api` タスクタイプのフルパスが開通:
- `POST /api/iframe-rpc` → arq enqueue (Plan 01)
- arq worker → `TASK_HANDLERS["iframe_app_api"]` → `IframeRpcHandler.handle()` (Plan 01 + Plan 02)
- DB pool は `ctx["db_pools"]` 経由で `IframeRpcHandler._handle_query()` に渡される

Plan 03（フロントエンド: CanvasPane postMessage リスナー）でエンドツーエンドが完成する。

## Threat Surface Scan

Plan の threat_model にある以下の脅威を実装で緩和:

| Flag | File | Description |
|------|------|-------------|
| T-18-06 mitigated | config/db_pools.yaml | .gitignore に追加し DSN 認証情報をリポジトリから除外 |
| T-18-07 documented | config/db_pools.yaml.example | READ-ONLY ユーザー使用の明示コメントで第2防御を記録 |
| T-18-08 mitigated | app/jobs/worker.py | max_size=5 + timeout=30.0 で接続数上限・タイムアウトを設定 |

## Self-Check: PASSED

| Item | Result |
|------|--------|
| config/db_pools.yaml.example | FOUND |
| config/db_pools.yaml | FOUND |
| .gitignore contains config/db_pools.yaml | FOUND |
| app/jobs/worker.py contains iframe_app_api | FOUND |
| app/jobs/worker.py contains rpc_method | FOUND |
| app/jobs/worker.py contains db_pools | FOUND |
| docker-compose.yml contains ./config:/app/config:ro (×2) | FOUND |
| commit f4f1508 (config files + gitignore) | FOUND |
| commit dec7120 (worker extension) | FOUND |
| commit 2535142 (docker-compose volume mount) | FOUND |
