#!/usr/bin/env bash
# scripts/db-backup.sh — PostgreSQL + Docker volumes + Canvas 静的ファイルのバックアップ
# 使用方法: ./scripts/db-backup.sh [--env dev|prod] [--out <dir>] [--stop-services] [--no-compress] [-y]
set -euo pipefail

# ─── 共通ライブラリ ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/backup-common.sh
source "${SCRIPT_DIR}/lib/backup-common.sh"

# ─── デフォルト値 ─────────────────────────────────────────────────────────────
ENV_NAME="dev"
OUT_DIR="./backups"
STOP_SERVICES=0
NO_COMPRESS=0
ASSUME_YES=0

# ─── 引数パース ───────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --env)
      ENV_NAME="$2"; shift 2 ;;
    --out)
      OUT_DIR="$2"; shift 2 ;;
    --stop-services)
      STOP_SERVICES=1; shift ;;
    --no-compress)
      NO_COMPRESS=1; shift ;;
    -y|--yes)
      ASSUME_YES=1; shift ;;
    *)
      err "Unknown argument: $1" ;;
  esac
done

export ASSUME_YES

# ─── 依存コマンド確認 ─────────────────────────────────────────────────────────
require_cmd docker

# ─── env 解決 ────────────────────────────────────────────────────────────────
resolve_env "${ENV_NAME}"

# ─── タイムスタンプ + 出力先ディレクトリ ─────────────────────────────────────
STAMP=$(date -u +"%Y%m%d-%H%M%S")
DEST="${OUT_DIR}/${STAMP}"

# ERR trap: 途中失敗時は中途半端なディレクトリを削除
trap 'RC=$?; if [ $RC -ne 0 ] && [ -d "${DEST}" ]; then warn "Backup failed (rc=${RC}), cleaning up ${DEST}"; rm -rf "${DEST}"; fi' EXIT

mkdir -p "${DEST}"
log "Backup destination: ${DEST}"

# ─── サービス停止 (--stop-services) ──────────────────────────────────────────
if [ "${STOP_SERVICES}" = "1" ]; then
  log "Stopping api and worker services..."
  compose stop api worker
fi

# ─── PostgreSQL ダンプ ────────────────────────────────────────────────────────
log "Dumping PostgreSQL (volume: ${VOL_POSTGRES})..."
if [ "${NO_COMPRESS}" = "1" ]; then
  compose exec -T postgres pg_dump \
    -U postgres \
    --no-owner \
    --no-comments \
    --no-publications \
    --no-subscriptions \
    postgres > "${DEST}/postgres.sql"
  PG_FILE="${DEST}/postgres.sql"
else
  compose exec -T postgres pg_dump \
    -U postgres \
    --no-owner \
    --no-comments \
    --no-publications \
    --no-subscriptions \
    postgres | gzip > "${DEST}/postgres.sql.gz"
  PG_FILE="${DEST}/postgres.sql.gz"
fi
log "PostgreSQL dump: ${PG_FILE}"

# ─── thread-files volume tar ──────────────────────────────────────────────────
log "Archiving volume: ${VOL_THREAD_FILES}..."
docker run --rm \
  -v "${VOL_THREAD_FILES}:/data" \
  -v "${DEST}:/backup" \
  busybox sh -c 'cd /data && tar czf /backup/thread-files.tar.gz . 2>/dev/null || tar czf /backup/thread-files.tar.gz --files-from /dev/null'
log "thread-files archived: ${DEST}/thread-files.tar.gz"

# ─── claude-code-outputs volume tar ──────────────────────────────────────────
log "Archiving volume: ${VOL_CLAUDE_OUT}..."
docker run --rm \
  -v "${VOL_CLAUDE_OUT}:/data" \
  -v "${DEST}:/backup" \
  busybox sh -c 'cd /data && tar czf /backup/claude-code-outputs.tar.gz . 2>/dev/null || tar czf /backup/claude-code-outputs.tar.gz --files-from /dev/null'
log "claude-code-outputs archived: ${DEST}/claude-code-outputs.tar.gz"

# ─── Canvas 静的ファイル ──────────────────────────────────────────────────────
CANVAS_STATIC_EXISTS=0
if [ -d "./static/apps" ]; then
  log "Archiving Canvas static files: ./static/apps/..."
  tar czf "${DEST}/canvas-static.tar.gz" -C ./static apps/
  CANVAS_STATIC_EXISTS=1
  log "Canvas static archived: ${DEST}/canvas-static.tar.gz"
else
  warn "./static/apps/ not found — skipping Canvas static backup"
fi

# ─── サービス再開 (--stop-services) ──────────────────────────────────────────
if [ "${STOP_SERVICES}" = "1" ]; then
  log "Restarting api and worker services..."
  compose start api worker
fi

# ─── MANIFEST.json 生成 ───────────────────────────────────────────────────────
log "Generating MANIFEST.json..."

_fileinfo() {
  local f="$1"
  local size sha256
  size=$(stat -c '%s' "${f}")
  sha256=$(sha256sum "${f}" | awk '{print $1}')
  echo "{\"size\": ${size}, \"sha256\": \"${sha256}\"}"
}

PG_BASENAME=$(basename "${PG_FILE}")
PG_INFO=$(_fileinfo "${PG_FILE}")
TF_INFO=$(_fileinfo "${DEST}/thread-files.tar.gz")
CO_INFO=$(_fileinfo "${DEST}/claude-code-outputs.tar.gz")

ISO_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "${CANVAS_STATIC_EXISTS}" = "1" ]; then
  CS_INFO=$(_fileinfo "${DEST}/canvas-static.tar.gz")
  CANVAS_ENTRY="    \"canvas-static.tar.gz\": ${CS_INFO}"
  FILES_JSON="    \"${PG_BASENAME}\": ${PG_INFO},
    \"thread-files.tar.gz\": ${TF_INFO},
    \"claude-code-outputs.tar.gz\": ${CO_INFO},
${CANVAS_ENTRY}"
else
  FILES_JSON="    \"${PG_BASENAME}\": ${PG_INFO},
    \"thread-files.tar.gz\": ${TF_INFO},
    \"claude-code-outputs.tar.gz\": ${CO_INFO}"
fi

cat > "${DEST}/MANIFEST.json" << EOF
{
  "timestamp": "${ISO_TS}",
  "env": "${ENV_NAME}",
  "compose_project": "${COMPOSE_PROJECT}",
  "volumes": {
    "postgres": "${VOL_POSTGRES}",
    "thread_files": "${VOL_THREAD_FILES}",
    "claude_code_outputs": "${VOL_CLAUDE_OUT}"
  },
  "files": {
${FILES_JSON}
  },
  "restore_cmd": "./scripts/db-restore.sh ${OUT_DIR}/${STAMP} --env ${ENV_NAME}"
}
EOF

log "MANIFEST.json generated."

# ─── 完了サマリ ───────────────────────────────────────────────────────────────
TOTAL=0
for f in "${DEST}"/*.gz "${DEST}"/*.sql; do
  [ -f "${f}" ] || continue
  SIZE=$(stat -c '%s' "${f}")
  TOTAL=$((TOTAL + SIZE))
  log "  $(basename "${f}"): $(( SIZE / 1024 )) KB"
done
log "Backup complete: ${DEST}  (total: $(( TOTAL / 1024 )) KB)"

# 正常終了時は trap の削除処理を無効化
trap - EXIT
