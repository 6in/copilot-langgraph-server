---
quick_id: 260514-e0g
slug: build-prod-restart
date: 2026-05-14
branch: quick/260514-e0g-build-prod-restart
---

# Quick: build-prod.sh に restart オプションを追加

## Trigger

PROD で code 変更を反映するために `docker compose -f docker-compose.prod.yml restart worker api` を直接叩くケースが頻繁にある (直前の quick-260514-djz 適用時もこれを実行)。
`docker-compose.prod.override.yml` 自動連結ロジックは `build-prod.sh` に集約済みなので、restart も同スクリプト経由で叩けると一貫性が出る。

## Scope

`build-prod.sh` のみ。

### Change

`case "${1}"` に `restart)` 分岐を追加。`logs)` と同じく `shift` + `"$@"` で追加引数を pass-through。

```bash
restart)
  shift
  if [ $# -eq 0 ]; then
    echo ">>> 本番コンテナを再起動します (全サービス)..."
  else
    echo ">>> 本番コンテナを再起動します ($*)..."
  fi
  $COMPOSE restart "$@"
  ;;
```

ヘッダーコメントの使い方一覧にも追記:

```
#   ./build-prod.sh restart            # 全サービス再起動
#   ./build-prod.sh restart api worker # 指定サービスのみ再起動
```

### Out of scope

- service 名のバリデーション (typo は docker 側のエラーに任せる)
- ヘルスチェック待ち / log tail 自動表示
- `--build` 込みの「再ビルド→再起動」モード (既存 `-d` で代替可)

## Tasks

| ID | Task | File |
|----|------|------|
| T1 | ヘッダーコメントに restart の使い方 2 行を追記 | `build-prod.sh` |
| T2 | case 分岐に `restart)` を追加 | `build-prod.sh` |

## Verification

- `bash -n build-prod.sh` で syntax error なし
- `./build-prod.sh ps` が既存どおり動作 (regression なし)
- `./build-prod.sh restart api worker` で実際に worker / api が再起動することを確認

## Commit Plan

```
chore(quick-260514-e0g): build-prod.sh に restart サブコマンドを追加

- ./build-prod.sh restart            # 全サービス再起動
- ./build-prod.sh restart api worker # 指定サービスのみ再起動

PROD で code 変更を反映するために `docker compose -f docker-compose.prod.yml
restart ...` を直接叩いていたが、override.yml 自動連結ロジックは build-prod.sh
に集約済みなので restart も同経路で叩けるようにする。
```
