#!/usr/bin/env bash
# scripts/db-restore.sh — バックアップディレクトリから 4 系統を復元
# 使用方法: ./scripts/db-restore.sh <backup-dir> [--env dev|prod] [-y] [--no-canvas-rebuild]
# 警告: 破壊的操作 — 既存の volume および ./static/apps/ を全削除して再構築します
set -euo pipefail

# ─── 共通ライブラリ ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/backup-common.sh
source "${SCRIPT_DIR}/lib/backup-common.sh"

# ─── デフォルト値 ─────────────────────────────────────────────────────────────
BACKUP_DIR=""
ENV_NAME=""
ASSUME_YES=0
NO_CANVAS_REBUILD=0

# ─── 引数パース ───────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --env)
      ENV_NAME="$2"; shift 2 ;;
    -y|--yes)
      ASSUME_YES=1; shift ;;
    --no-canvas-rebuild)
      NO_CANVAS_REBUILD=1; shift ;;
    -*)
      err "Unknown option: $1" ;;
    *)
      if [ -z "${BACKUP_DIR}" ]; then
        BACKUP_DIR="$1"; shift
      else
        err "Unexpected positional argument: $1"
      fi
      ;;
  esac
done

export ASSUME_YES

# ─── 依存コマンド確認 ─────────────────────────────────────────────────────────
require_cmd docker
require_cmd jq

# ─── backup-dir 確認 ─────────────────────────────────────────────────────────
if [ -z "${BACKUP_DIR}" ]; then
  err "Usage: $0 <backup-dir> [--env dev|prod] [-y] [--no-canvas-rebuild]"
fi

if [ ! -d "${BACKUP_DIR}" ]; then
  err "Backup directory not found: ${BACKUP_DIR}"
fi

MANIFEST="${BACKUP_DIR}/MANIFEST.json"

# ─── MANIFEST.json 読み込み ───────────────────────────────────────────────────
if [ -f "${MANIFEST}" ]; then
  log "Reading MANIFEST.json from: ${MANIFEST}"
  MANIFEST_ENV=$(jq -r '.env // empty' "${MANIFEST}" 2>/dev/null || true)
  if [ -z "${ENV_NAME}" ] && [ -n "${MANIFEST_ENV}" ]; then
    ENV_NAME="${MANIFEST_ENV}"
    log "env auto-detected from MANIFEST.json: ${ENV_NAME}"
  fi
else
  warn "MANIFEST.json not found in ${BACKUP_DIR}"
fi

# env が未解決の場合はエラー
if [ -z "${ENV_NAME}" ]; then
  err "Cannot determine env. Pass --env dev|prod explicitly, or ensure MANIFEST.json contains 'env' field."
fi

# ─── env 解決 ────────────────────────────────────────────────────────────────
resolve_env "${ENV_NAME}"

# ─── 確認プロンプト ───────────────────────────────────────────────────────────
confirm "Restore will WIPE current data in env=${ENV_NAME} (volumes: ${VOL_POSTGRES}, ${VOL_THREAD_FILES}, ${VOL_CLAUDE_OUT} and host ./static/apps/). Continue?"

# ─── SQL ダンプファイル確認 ───────────────────────────────────────────────────
if [ -f "${BACKUP_DIR}/postgres.sql.gz" ]; then
  PG_FILE="${BACKUP_DIR}/postgres.sql.gz"
  PG_COMPRESSED=1
elif [ -f "${BACKUP_DIR}/postgres.sql" ]; then
  PG_FILE="${BACKUP_DIR}/postgres.sql"
  PG_COMPRESSED=0
else
  err "PostgreSQL dump not found in ${BACKUP_DIR} (expected postgres.sql.gz or postgres.sql)"
fi

# ─── 全サービス停止 ───────────────────────────────────────────────────────────
log "Stopping all services (compose down)..."
compose down || warn "compose down returned non-zero (continuing)"

# ─── volume 削除 ─────────────────────────────────────────────────────────────
log "Removing volumes: ${VOL_POSTGRES} ${VOL_THREAD_FILES} ${VOL_CLAUDE_OUT}..."
docker volume rm "${VOL_POSTGRES}" "${VOL_THREAD_FILES}" "${VOL_CLAUDE_OUT}" 2>/dev/null \
  || warn "Some volumes did not exist — proceeding"

# ─── postgres だけ起動 (initdb 実行) ─────────────────────────────────────────
log "Starting postgres service (initdb will run)..."
compose up -d postgres

# ─── postgres healthcheck 待機 ───────────────────────────────────────────────
log "Waiting for postgres to be ready..."
RETRY=0
MAX_RETRY=30
until compose exec -T postgres pg_isready -U postgres -q 2>/dev/null; do
  RETRY=$((RETRY + 1))
  if [ "${RETRY}" -ge "${MAX_RETRY}" ]; then
    err "postgres did not become ready after ${MAX_RETRY} seconds. Aborting."
  fi
  sleep 1
done
log "postgres is ready."

# ─── PostgreSQL リストア ──────────────────────────────────────────────────────
log "Restoring PostgreSQL from ${PG_FILE}..."
if [ "${PG_COMPRESSED}" = "1" ]; then
  gunzip -c "${PG_FILE}" | compose exec -T postgres psql -U postgres -d postgres
else
  compose exec -T postgres psql -U postgres -d postgres < "${PG_FILE}"
fi
log "PostgreSQL restore complete."

# ─── thread-files volume 展開 ─────────────────────────────────────────────────
if [ -f "${BACKUP_DIR}/thread-files.tar.gz" ]; then
  log "Restoring volume: ${VOL_THREAD_FILES}..."
  docker run --rm \
    -v "${VOL_THREAD_FILES}:/data" \
    -v "$(realpath "${BACKUP_DIR}"):/backup" \
    busybox sh -c 'cd /data && tar xzf /backup/thread-files.tar.gz'
  log "thread-files restored."
else
  warn "thread-files.tar.gz not found — skipping"
fi

# ─── claude-code-outputs volume 展開 ─────────────────────────────────────────
if [ -f "${BACKUP_DIR}/claude-code-outputs.tar.gz" ]; then
  log "Restoring volume: ${VOL_CLAUDE_OUT}..."
  docker run --rm \
    -v "${VOL_CLAUDE_OUT}:/data" \
    -v "$(realpath "${BACKUP_DIR}"):/backup" \
    busybox sh -c 'cd /data && tar xzf /backup/claude-code-outputs.tar.gz'
  log "claude-code-outputs restored."
else
  warn "claude-code-outputs.tar.gz not found — skipping"
fi

# ─── Canvas 静的ファイル復元 ──────────────────────────────────────────────────
if [ -f "${BACKUP_DIR}/canvas-static.tar.gz" ]; then
  log "Restoring Canvas static files to ./static/..."
  mkdir -p ./static
  tar xzf "${BACKUP_DIR}/canvas-static.tar.gz" -C ./static/
  log "Canvas static files restored."
else
  warn "canvas-static.tar.gz not found — skipping"
fi

# ─── Canvas dual-source rebuild ───────────────────────────────────────────────
CANVAS_REBUILD_COUNT=0
if [ "${NO_CANVAS_REBUILD}" = "1" ]; then
  warn "--no-canvas-rebuild specified — skipping Canvas dual-source rebuild"
else
  log "Running Canvas dual-source rebuild (canvas_apps.deployed = true)..."

  APP_PREFIX="${APP_PREFIX:-}"

  # deployed=true の app_id と HTML を base64 エンコードで取得
  # COPY ... TO STDOUT は psql interactive mode では動作しないため SELECT を使用
  # psql -tAc で行を読み込み、jq で処理できるよう JSON 形式で出力
  ROWS=$(compose exec -T postgres psql -U postgres -d postgres \
    -tAc "SELECT app_id || E'\t' || encode(convert_to(html, 'UTF8'), 'base64') FROM canvas_apps WHERE deployed = true;" \
    2>/dev/null || true)

  if [ -n "${ROWS}" ]; then
    while IFS=$'\t' read -r app_id html_b64; do
      [ -z "${app_id}" ] && continue
      APP_DIR="./static/apps/${app_id}"
      mkdir -p "${APP_DIR}"
      # base64 デコード → $URL_PREFIX を APP_PREFIX で置換 → ファイル書き出し
      echo "${html_b64}" | tr -d '\n' | base64 -d | \
        sed "s|\$URL_PREFIX|${APP_PREFIX}|g" > "${APP_DIR}/index.html"
      log "  Rebuilt: ${APP_DIR}/index.html"
      CANVAS_REBUILD_COUNT=$((CANVAS_REBUILD_COUNT + 1))
    done <<< "${ROWS}"
    log "Canvas dual-source rebuild complete: ${CANVAS_REBUILD_COUNT} app(s) rebuilt."
  else
    log "No deployed canvas apps found (canvas_apps WHERE deployed = true returned 0 rows)."
  fi
fi

# ─── 全サービス再開 ───────────────────────────────────────────────────────────
log "Starting all services..."
compose up -d

# ─── 完了サマリ ───────────────────────────────────────────────────────────────
TOTAL_SIZE=0
for f in "${BACKUP_DIR}"/*.gz "${BACKUP_DIR}"/*.sql; do
  [ -f "${f}" ] || continue
  SIZE=$(stat -c '%s' "${f}")
  TOTAL_SIZE=$((TOTAL_SIZE + SIZE))
done

log "Restore complete!"
log "  env: ${ENV_NAME}"
log "  backup: ${BACKUP_DIR}"
log "  total restored size: $(( TOTAL_SIZE / 1024 )) KB"
log "  canvas apps rebuilt: ${CANVAS_REBUILD_COUNT}"
