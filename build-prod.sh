#!/bin/bash
# 本番モードのビルド＆起動スクリプト
# 使い方:
#   ./build-prod.sh          # ビルドして起動（フォアグラウンド）
#   ./build-prod.sh -d       # ビルドして起動（バックグラウンド）
#   ./build-prod.sh --down   # 停止＆ボリューム削除なしで終了
#   ./build-prod.sh logs     # ログを tail
#   ./build-prod.sh ps       # サービス状態を表示
#
# 補足: 同ディレクトリに `docker-compose.prod.override.yml` があれば
# 自動で `-f` で連結する (README.prod.md §4 の 127.0.0.1:18080 bind パターン用)。

set -e

# Base compose file
COMPOSE="docker compose -f docker-compose.prod.yml"

# Override file (本番 reverse-proxy 配下で port を 127.0.0.1 に bind する設定など)
if [ -f docker-compose.prod.override.yml ]; then
  COMPOSE="${COMPOSE} -f docker-compose.prod.override.yml"
  echo "(override) docker-compose.prod.override.yml を検出 — 自動で連結します"
fi

# 起動完了メッセージで表示する URL を override の bind から推定
ACCESS_HINT="http://localhost/orochi/"
if [ -f docker-compose.prod.override.yml ]; then
  # 127.0.0.1:NNNN:80 形式から port を抽出
  PORT=$(grep -oE '127\.0\.0\.1:[0-9]+:80' docker-compose.prod.override.yml | head -1 | cut -d: -f2)
  if [ -n "$PORT" ]; then
    ACCESS_HINT="http://127.0.0.1:${PORT}/orochi/  (本番では server nginx 経由で HTTPS 公開、README.prod.md §6 参照)"
  fi
fi

case "${1}" in
  --down)
    echo ">>> 本番コンテナを停止します..."
    $COMPOSE down
    exit 0
    ;;
  -d)
    echo ">>> 本番モードでビルド＆起動（バックグラウンド）..."
    $COMPOSE up --build -d
    echo ""
    echo "起動完了: ${ACCESS_HINT}"
    echo "ログ確認: ./build-prod.sh logs"
    echo "状態:     ./build-prod.sh ps"
    echo "停止:     ./build-prod.sh --down"
    ;;
  logs)
    shift
    $COMPOSE logs -f "$@"
    ;;
  ps)
    $COMPOSE ps
    ;;
  *)
    echo ">>> 本番モードでビルド＆起動..."
    $COMPOSE up --build
    ;;
esac
