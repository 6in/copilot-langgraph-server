---
quick_id: 260514-e0g
slug: build-prod-restart
date: 2026-05-14
branch: quick/260514-e0g-build-prod-restart
status: complete
---

# Summary

## What changed

`build-prod.sh` のみ:

1. ヘッダーコメントの使い方一覧に `restart` の 2 行を追記 (引数なし / 引数あり)
2. case 分岐に `restart)` を追加 — `logs)` と同じく `shift` + `"$@"` で追加引数を pass-through
3. 引数なし: 「本番コンテナを再起動します (全サービス)...」を表示して全サービス restart
4. 引数あり: 「本番コンテナを再起動します ($*)...」を表示して指定サービスのみ restart

`docker-compose.prod.override.yml` 自動連結ロジック (上部の `COMPOSE="..."` 構築部) はそのまま流用されるので、override 環境でも正しく動く。

## Verification

| 項目 | 結果 |
|------|------|
| `bash -n build-prod.sh` | syntax OK |
| `./build-prod.sh ps` | 既存どおり 7 サービス表示 (regression なし) |
| `./build-prod.sh restart nonexistent-svc` | 新 echo メッセージ表示後に `no such service` で docker 側からエラー (転送経路正常) |

実サービスの実 restart は実行中の PROD セッションへの影響回避のため smoke test ではスキップ (前段 quick-260514-djz の作業中に直接 docker compose restart で worker/api を再起動済みなので、コマンド到達の正しさは確認済み)。

## Out of scope (未実施)

- service 名のバリデーション (typo は docker 側に任せる)
- ヘルスチェック待ち / log tail 自動表示
- `--build` 込みの「再ビルド→再起動」モード (既存 `-d` で代替可)
