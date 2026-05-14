---
quick_id: 260514-ecs
slug: prod-default-port-18080
date: 2026-05-14
branch: quick/260514-ecs-prod-default-port-18080
---

# Quick: PROD のデフォルトポートを 127.0.0.1:18080 に変更

## Trigger

前段の quick-260514-e0g (restart オプション追加) で `docker-compose.prod.override.yml` 自動連結ロジックの話題に派生。
ローカル開発機で port 80 を取る理由は無く (server-side nginx forwarding 前提のみが理由)、cookie はポートでスコープされない (RFC 6265)、Device Flow はリダイレクト URL を持たない、`secure` flag も未設定 — ということで、`127.0.0.1:18080:80` を最初からデフォルトにする方が合理的という結論に至った。

## Scope

### Change 1 — `docker-compose.prod.yml`

`nginx` サービスの ports:

```yaml
    ports:
      - "80:80"
```

を:

```yaml
    ports:
      - "127.0.0.1:18080:80"
```

に変更。これで override.yml 無しでもローカル / 本番両方で `127.0.0.1:18080` バインドが効く。

### Change 2 — `build-prod.sh`

- `ACCESS_HINT="http://localhost/orochi/"` を `ACCESS_HINT="http://127.0.0.1:18080/orochi/"` に変更
- override.yml 検出時の port 抽出ロジック (現存) は **そのまま** — ユーザーが別 port にしたい場合の挙動を維持

### Change 3 — `README.prod.md`

セクションごとの変更:

- **§1 公開ポート table** (line 52): 「本書では port を変更する手順を含む」を「デフォルトで 127.0.0.1:18080 にバインド済み (別 port にしたい場合は §4)」に修正
- **§4 ポート設定の変更**: 「override.yml で 127.0.0.1:18080:80 にする」手順 → 「デフォルトで 127.0.0.1:18080:80 になっているので追加設定不要。**別 port を使いたい場合のみ** override.yml で上書き」という構造に書き換え
- **§5 起動の直接コマンド例** (line 203): `-f docker-compose.prod.override.yml` の必須扱いを「(override.yml がある場合のみ)」と緩める
- **§1 ASCII 構成図**: 既に 18080 を仮定して書かれているので変更不要
- **その他の `127.0.0.1:18080` 言及**: 既存どおり (curl コマンド例など) — 動作変更なし

### Out of scope

- 旧 override.yml ユーザーへの migration ドキュメント (override.yml が無ければ新デフォルトが効くだけ、override.yml ありの環境はそのまま動く — 二重 bind とはならない、override が override.yml の同 port で衝突するわけでもない)
- nginx コンテナ内部 (port 80 listen) の変更
- README.md (dev 用) の変更

## Tasks

| ID | Task | File |
|----|------|------|
| T1 | nginx ports を `127.0.0.1:18080:80` に変更 | `docker-compose.prod.yml` |
| T2 | `ACCESS_HINT` を `http://127.0.0.1:18080/orochi/` に変更 | `build-prod.sh` |
| T3 | §1 公開ポート table の説明文を修正 | `README.prod.md` |
| T4 | §4 ポート設定の変更セクションを書き換え (デフォルト → override は escape hatch) | `README.prod.md` |
| T5 | §5 起動の直接コマンド例から override 必須を外す | `README.prod.md` |

## Verification

- `bash -n build-prod.sh` syntax OK
- `docker compose -f docker-compose.prod.yml config | grep -A2 "nginx:" | head` で ports が `127.0.0.1:18080:80` になっていることを確認
- `grep -n "localhost/orochi\|localhost:80" README.prod.md build-prod.sh docker-compose.prod.yml` で取り残しが無いか確認
- ライブ反映: `./build-prod.sh -d` で再起動して `./build-prod.sh ps` の nginx PORTS が `127.0.0.1:18080->80/tcp` になることを確認 (オプション — user 操作)

## Commit Plan

```
chore(quick-260514-ecs): PROD のデフォルトポートを 127.0.0.1:18080 に変更

- docker-compose.prod.yml: nginx ports を 80:80 から 127.0.0.1:18080:80 へ
- build-prod.sh: ACCESS_HINT を http://127.0.0.1:18080/orochi/ に更新
- README.prod.md: §1 公開ポート表、§4 ポート設定の変更、§5 起動例を
  「デフォルト 18080、override.yml は別 port 用の escape hatch」という
  構造に書き換え

cookie はポートでスコープされない (RFC 6265)、Device Flow はリダイレクト
URL を持たない、secure flag 未設定 — の 3 点から port 80 固定の必然性が
無いため、最初から server-side nginx forwarding を想定した 127.0.0.1:18080
をデフォルトにする。override.yml で別 port にする経路は引き続き有効。
```
