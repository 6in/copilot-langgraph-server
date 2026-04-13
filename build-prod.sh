#!/bin/bash
# 本番モードのビルド＆起動スクリプト
# 使い方:
#   ./build-prod.sh          # ビルドして起動（フォアグラウンド）
#   ./build-prod.sh -d       # ビルドして起動（バックグラウンド）
#   ./build-prod.sh --down   # 停止＆ボリューム削除なしで終了

set -e

COMPOSE="docker compose -f docker-compose.prod.yml"

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
    echo "起動完了: http://localhost/orochi/"
    echo "ログ確認: docker compose -f docker-compose.prod.yml logs -f"
    echo "停止:     ./build-prod.sh --down"
    ;;
  *)
    echo ">>> 本番モードでビルド＆起動..."
    $COMPOSE up --build
    ;;
esac
