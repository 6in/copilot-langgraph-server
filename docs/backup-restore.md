# バックアップ/リストア運用ガイド

## 概要

このガイドでは以下の 3 層を一括でバックアップ・リストアする手順を説明します。

1. **PostgreSQL** — 会話スレッド・Gem 定義・Canvas アプリ・監査ログを含む全データ
2. **Worker 生成ファイル** (`thread-files` / `claude-code-outputs` volume) — AI が生成したファイルやアップロード添付
3. **Canvas 静的デプロイファイル** (`./static/apps/`) — デプロイ済み Canvas アプリの HTML

Canvas アプリは **DB の `canvas_apps.html` 列** と **ファイルシステムの `./static/apps/<app_id>/index.html`** の dual-source 構成です。
片方だけ戻すと `deployed = true` なのに物理ファイルが存在しない inconsistent state が発生するため、
リストアスクリプトは両方を同時に復元し、最後に DB → FS の rebuild を自動実行します。

## バックアップ対象

| 層 | dev volume / path | prod volume / path | 保存ファイル名 |
|---|---|---|---|
| PostgreSQL | `copilot-langgraph_postgres-data` | `copilot-langgraph-prod_postgres-data-prod` | `postgres.sql.gz` |
| Worker thread files | `copilot-langgraph_thread-files` | `copilot-langgraph-prod_thread-files-prod` | `thread-files.tar.gz` |
| Worker claude-code outputs | `copilot-langgraph_claude-code-outputs` | `copilot-langgraph-prod_claude-code-outputs-prod` | `claude-code-outputs.tar.gz` |
| Canvas 静的デプロイ | `./static/apps/` (bind mount) | 同左 | `canvas-static.tar.gz` |

**バックアップ対象外:**
- `redis-data` / `redis-data-prod` — ジョブキュー・キャッシュのため再構築可能
- 監査ログ・`agent_traces`・`canvas_apps` テーブルは PostgreSQL ダンプに含まれます

## バックアップ手順

### 基本 (dev)

```bash
./scripts/db-backup.sh
```

`./backups/YYYYMMDD-HHMMSS/` ディレクトリが作成され、以下の 5 ファイルが格納されます:

```
./backups/20260514-051200/
├── postgres.sql.gz
├── thread-files.tar.gz
├── claude-code-outputs.tar.gz
├── canvas-static.tar.gz      # ./static/apps/ が存在する場合のみ
└── MANIFEST.json
```

`MANIFEST.json` のサンプル:

```json
{
  "timestamp": "2026-05-14T05:12:00Z",
  "env": "dev",
  "compose_project": "copilot-langgraph",
  "volumes": {
    "postgres": "copilot-langgraph_postgres-data",
    "thread_files": "copilot-langgraph_thread-files",
    "claude_code_outputs": "copilot-langgraph_claude-code-outputs"
  },
  "files": {
    "postgres.sql.gz": { "size": 102400, "sha256": "abc123..." },
    "thread-files.tar.gz": { "size": 4096, "sha256": "def456..." },
    "claude-code-outputs.tar.gz": { "size": 8192, "sha256": "ghi789..." },
    "canvas-static.tar.gz": { "size": 2048, "sha256": "jkl012..." }
  },
  "restore_cmd": "./scripts/db-restore.sh ./backups/20260514-051200 --env dev"
}
```

### prod 環境

```bash
./scripts/db-backup.sh --env prod
```

### 出力先ディレクトリを変更

```bash
./scripts/db-backup.sh --out /mnt/nas/backups
```

### サービス停止モード (書き込み中の整合性を最大化)

```bash
./scripts/db-backup.sh --stop-services
```

実行中は `api` / `worker` が停止します (`postgres` と `mcp-server` は稼働継続)。
PostgreSQL は MVCC でスナップショットを取るため通常は不要ですが、
大量書き込みが走っている時間帯に実行する場合は推奨します。

### 圧縮なし (デバッグ用)

```bash
./scripts/db-backup.sh --no-compress
```

`postgres.sql.gz` の代わりに `postgres.sql` が生成されます。

### 確認プロンプトをスキップ

```bash
./scripts/db-backup.sh -y
```

> **セキュリティ注意:** `./backups/` には会話履歴・添付ファイル等の機微データが平文で含まれます。
> 別ホストへ転送する際は `scp` や暗号化ストレージを使用してください。
> `./backups/` は `.gitignore` で除外済みのため、誤って git にコミットされることはありません。

## リストア手順

> **必読:** リストアは破壊的操作です。対象 env の volume (`postgres-data`, `thread-files`, `claude-code-outputs`) と
> `./static/apps/` が**全削除されてから再構築**されます。実行前に最新バックアップが手元にあることを確認してください。

### dev

```bash
./scripts/db-restore.sh ./backups/20260514-051200
```

実行すると以下の確認プロンプトが表示されます:

```
[CONFIRM] Restore will WIPE current data in env=dev (volumes: ...). Continue? [y/N]
```

`y` を入力すると復元が開始されます。`-y` を付けると確認をスキップできます。

### prod

```bash
./scripts/db-restore.sh ./backups/20260514-051200 --env prod
```

通常は `MANIFEST.json` から env を自動推定するため `--env` 明示は不要です。
`MANIFEST.json` が存在しない場合のみ明示が必要です。

### 確認スキップ (自動化・CI 向け)

```bash
./scripts/db-restore.sh ./backups/20260514-051200 -y
```

### Canvas dual-source rebuild

リストアの最終ステップで `canvas_apps` テーブルの `deployed = true` 全レコードを
DB から SELECT し、`./static/apps/<app_id>/index.html` を自動で書き戻します。

`$URL_PREFIX` は環境変数 `APP_PREFIX` (例: `/orochi`) で置換されます。
prod を別ホストにリストアする際など APP_PREFIX が変わる場合は、事前に export してください:

```bash
export APP_PREFIX=/my-prefix
./scripts/db-restore.sh ./backups/20260514-051200 --env prod
```

`canvas-static.tar.gz` から展開した内容のみで十分な場合 (DB rebuild を skip したい場合) は:

```bash
./scripts/db-restore.sh ./backups/20260514-051200 --no-canvas-rebuild
```

## 古いバックアップの削除

### 最新 7 個だけ残す

```bash
./scripts/db-backup-prune.sh --keep 7
```

確認プロンプトが表示されます。`y` を入力すると古いスナップショットが削除されます。

### 削除対象の確認のみ (dry-run)

```bash
./scripts/db-backup-prune.sh --keep 7 --dry-run
```

実際には削除せず、削除対象ディレクトリの一覧を表示します。

### デフォルト retention (最新 14 個)

```bash
./scripts/db-backup-prune.sh
```

### 別ディレクトリを指定

```bash
./scripts/db-backup-prune.sh --keep 30 --out /mnt/nas/backups
```

### 確認スキップ

```bash
./scripts/db-backup-prune.sh --keep 7 -y
```

## トラブルシューティング

**`docker volume rm` で "volume in use" エラー:**
`compose down` が正常に完了しなかったケースです。手動で停止してから再実行してください:
```bash
docker compose -p copilot-langgraph down         # dev
docker compose -p copilot-langgraph-prod down    # prod
./scripts/db-restore.sh ./backups/<dir>
```

**`pg_dump` / `psql` で "could not connect to server" エラー:**
postgres コンテナが起動していないか、まだ healthcheck が通っていない可能性があります:
```bash
docker compose ps postgres
# State が "healthy" でない場合は少し待ってから再試行
```

**Canvas rebuild 後にアプリが 404:**
`APP_PREFIX` 環境変数が未設定で `$URL_PREFIX` が空文字に置換されている可能性があります:
```bash
export APP_PREFIX=/orochi
./scripts/db-restore.sh ./backups/<dir>
# または手動で修正:
# sed -i 's|\$URL_PREFIX|/orochi|g' ./static/apps/<app_id>/index.html
```

**バックアップを別ホストへ転送:**
```bash
# 転送元
tar czf backups-snapshot.tar.gz backups/20260514-051200/

# 転送 (scp 推奨)
scp backups-snapshot.tar.gz user@target-host:/path/to/project/

# 転送先
tar xzf backups-snapshot.tar.gz
./scripts/db-restore.sh ./backups/20260514-051200
```

**prune スクリプトが "nothing to prune" を返す:**
`./backups/` ディレクトリが存在しないか、`--keep` の値以下のスナップショットしかありません。正常な動作です。

## 設計メモ

- スクリプトは bash のみ。ホスト側に `pg_dump` / `psql` をインストールする必要はありません (`docker compose exec` 経由)
- Docker named volume の tar は `busybox` イメージを使うパターン — ホスト側ファイルシステムを介さないため OS 非依存
- `set -euo pipefail` + ERR trap により途中失敗時は中途半端なバックアップディレクトリを自動削除
- `--env prod` 指定時は `-p copilot-langgraph-prod` を必ず付ける `compose` ラッパー関数経由のため、dev/prod の取り違えを防止
- `./backups/` は `.gitignore` で除外済み (`/backups/`)
