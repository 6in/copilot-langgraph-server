#!/usr/bin/env bash
# scripts/lib/backup-common.sh — バックアップ/リストア共通ヘルパー (source 専用)
# shellcheck disable=SC2034  # 変数は呼び出し元スクリプトで使用
set -euo pipefail

# ─── ANSI カラー ─────────────────────────────────────────────────────────────
_CLR_GREEN="\033[0;32m"
_CLR_YELLOW="\033[0;33m"
_CLR_RED="\033[0;31m"
_CLR_RESET="\033[0m"

# ─── ログ関数 ─────────────────────────────────────────────────────────────────
log() {
  local ts
  ts=$(date -u +"%Y-%m-%d %H:%M:%S")
  echo -e "${_CLR_GREEN}[${ts}] $*${_CLR_RESET}" >&2
}

warn() {
  local ts
  ts=$(date -u +"%Y-%m-%d %H:%M:%S")
  echo -e "${_CLR_YELLOW}[${ts}] WARN: $*${_CLR_RESET}" >&2
}

err() {
  local ts
  ts=$(date -u +"%Y-%m-%d %H:%M:%S")
  echo -e "${_CLR_RED}[${ts}] ERROR: $*${_CLR_RESET}" >&2
  exit 1
}

# ─── コマンド存在確認 ─────────────────────────────────────────────────────────
require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" > /dev/null 2>&1; then
    err "Required command not found: ${cmd}. Please install it and retry."
  fi
}

# ─── 確認プロンプト ───────────────────────────────────────────────────────────
# ASSUME_YES=1 が set されているか -y フラグが渡された場合はスキップ
# グローバル変数 ASSUME_YES を呼び出し元で定義しておくこと (デフォルト 0)
ASSUME_YES="${ASSUME_YES:-0}"

confirm() {
  local prompt="$1"
  if [ "${ASSUME_YES}" = "1" ]; then
    log "Auto-confirmed (--yes): ${prompt}"
    return 0
  fi
  echo -e "${_CLR_YELLOW}[CONFIRM] ${prompt} [y/N] ${_CLR_RESET}" >&2
  local answer
  read -r answer
  case "${answer}" in
    [Yy]) return 0 ;;
    *) err "Aborted by user." ;;
  esac
}

# ─── env 解決 ────────────────────────────────────────────────────────────────
# 使用方法: resolve_env "dev" または resolve_env "prod"
# 結果を export:
#   COMPOSE_PROJECT   — docker compose project name
#   COMPOSE_FILES     — -f フラグ文字列
#   VOL_POSTGRES      — postgres-data volume 名
#   VOL_THREAD_FILES  — thread-files volume 名
#   VOL_CLAUDE_OUT    — claude-code-outputs volume 名
resolve_env() {
  local env_name="${1:-dev}"

  case "${env_name}" in
    dev)
      COMPOSE_PROJECT="copilot-langgraph"
      COMPOSE_FILES="-f docker-compose.yml"
      VOL_POSTGRES="${COMPOSE_PROJECT}_postgres-data"
      VOL_THREAD_FILES="${COMPOSE_PROJECT}_thread-files"
      VOL_CLAUDE_OUT="${COMPOSE_PROJECT}_claude-code-outputs"
      ;;
    prod)
      COMPOSE_PROJECT="copilot-langgraph-prod"
      COMPOSE_FILES="-f docker-compose.prod.yml"
      VOL_POSTGRES="${COMPOSE_PROJECT}_postgres-data-prod"
      VOL_THREAD_FILES="${COMPOSE_PROJECT}_thread-files-prod"
      VOL_CLAUDE_OUT="${COMPOSE_PROJECT}_claude-code-outputs-prod"
      ;;
    *)
      err "Unknown env '${env_name}'. Use 'dev' or 'prod'."
      ;;
  esac

  export COMPOSE_PROJECT COMPOSE_FILES VOL_POSTGRES VOL_THREAD_FILES VOL_CLAUDE_OUT

  log "Resolved env=${env_name}: project=${COMPOSE_PROJECT}"

  # volume 実在確認
  local existing_vols
  existing_vols=$(docker volume ls --format '{{.Name}}' 2>/dev/null || true)

  local missing=""
  for vol in "${VOL_POSTGRES}" "${VOL_THREAD_FILES}" "${VOL_CLAUDE_OUT}"; do
    if ! echo "${existing_vols}" | grep -qx "${vol}"; then
      missing="${missing} ${vol}"
    fi
  done

  if [ -n "${missing}" ]; then
    warn "The following volumes do not exist yet (will be created on first 'compose up'):"
    for v in ${missing}; do
      warn "  - ${v}"
    done
  fi
}

# ─── docker compose ラッパー ─────────────────────────────────────────────────
# resolve_env 呼び出し後に使用すること
compose() {
  # shellcheck disable=SC2086
  docker compose -p "${COMPOSE_PROJECT}" ${COMPOSE_FILES} "$@"
}
