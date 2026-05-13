#!/usr/bin/env bash
# scripts/db-backup-prune.sh — 古いバックアップを retention ポリシーで削除
# 使用方法: ./scripts/db-backup-prune.sh [--keep <N>] [--out <dir>] [--dry-run] [-y]
set -euo pipefail

# ─── 共通ライブラリ ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/backup-common.sh
source "${SCRIPT_DIR}/lib/backup-common.sh"

# ─── デフォルト値 ─────────────────────────────────────────────────────────────
KEEP=14
OUT_DIR="./backups"
DRY_RUN=0
ASSUME_YES=0

# ─── 引数パース ───────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --keep)
      KEEP="$2"; shift 2 ;;
    --out)
      OUT_DIR="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    -y|--yes)
      ASSUME_YES=1; shift ;;
    *)
      err "Unknown argument: $1" ;;
  esac
done

export ASSUME_YES

# ─── out-dir 存在確認 ────────────────────────────────────────────────────────
if [ ! -d "${OUT_DIR}" ]; then
  log "Backup directory does not exist: ${OUT_DIR} — nothing to prune"
  exit 0
fi

# ─── YYYYMMDD-HHMMSS 形式のサブディレクトリ一覧取得 ──────────────────────────
# sort で古い順に並べる (辞書順 = 時系列順)
ALL_DIRS=()
while IFS= read -r d; do
  ALL_DIRS+=("${d}")
done < <(find "${OUT_DIR}" -mindepth 1 -maxdepth 1 -type d -name '????????-??????' | sort)

TOTAL=${#ALL_DIRS[@]}
log "Found ${TOTAL} backup snapshot(s) in ${OUT_DIR}"

if [ "${TOTAL}" -le "${KEEP}" ]; then
  log "Nothing to prune: ${TOTAL} snapshot(s) <= keep=${KEEP}"
  exit 0
fi

# 削除対象 = 先頭 (TOTAL - KEEP) 個
DELETE_COUNT=$((TOTAL - KEEP))
DELETE_DIRS=("${ALL_DIRS[@]:0:${DELETE_COUNT}}")

if [ "${DRY_RUN}" = "1" ]; then
  log "[DRY-RUN] Would delete ${DELETE_COUNT} snapshot(s) (keeping ${KEEP} most recent):"
  for d in "${DELETE_DIRS[@]}"; do
    log "  DELETE: ${d}"
  done
  log "[DRY-RUN] Remaining: ${KEEP} snapshot(s) would be kept."
  exit 0
fi

# ─── 確認プロンプト ───────────────────────────────────────────────────────────
confirm "Prune will DELETE ${DELETE_COUNT} backup snapshot(s) from ${OUT_DIR} (keeping ${KEEP} most recent). Continue?"

# ─── 削除 ────────────────────────────────────────────────────────────────────
DELETED=0
for d in "${DELETE_DIRS[@]}"; do
  log "Deleting: ${d}"
  rm -rf "${d}"
  DELETED=$((DELETED + 1))
done

REMAINING=$((TOTAL - DELETED))
log "Pruned ${DELETED} snapshot(s). ${REMAINING} snapshot(s) remaining."
