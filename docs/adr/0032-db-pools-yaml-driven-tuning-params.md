# 0032. db_pools.yaml 駆動の接続プールチューニングパラメータ

**Date:** 2026-04-15
**Status:** Accepted

## Context

`mcp_server/tools/db_query.py::init_pools()` では `AsyncConnectionPool` 初期化時に `min_size=1, max_size=5` がハードコードされていた。プールごとにパラメータを調整することができず、開発/本番での接続数チューニングや、アイドル接続のライフサイクル調整 (`max_idle`)、障害時の再接続タイムアウト (`reconnect_timeout`) を変更するには Python コードを書き換える必要があった。

v5.0 milestone 完了後の運用フェーズに入り、接続プールを環境・用途ごとに調整したい需要が出てきたため、`config/db_pools.yaml` を単一の設定源として活用する方針に整理する。

## Decision

`config/db_pools.yaml` の各プール定義に以下 4 つの任意キーを追加できるようにし、`init_pools()` が YAML からそのまま `AsyncConnectionPool(**kwargs)` に引き渡す:

- `min_size`
- `max_size`
- `max_idle` (秒)
- `reconnect_timeout` (秒)

`pool_kwargs` の組み立ては `if key in pool_cfg` 方式で行い、**キーが存在する場合のみ** kwargs に含める。コード側でデフォルト値を持たないことで、未指定時は psycopg_pool ライブラリ本来のデフォルトにフォールバックさせる。

`config/db_pools.yaml` の `default` プールにはサンプル値とヘッダーコメントを追加し、運用者がキー名と単位を参照できるようにした。

## Alternatives Considered

- **`pool_cfg.get("min_size", 1)` 方式:** コード側にデフォルト値を埋める案。パラメータを追加するたびに Python 側にもデフォルト値を書く必要があり、psycopg_pool のアップストリームデフォルト変更を吸収できない。後方互換性の観点でも、今回は「YAML に書かれていないものは一切渡さない」方がライブラリ挙動と整合する。却下。
- **Pydantic モデルでスキーマ化:** YAML → PoolConfig モデル → kwargs 展開の経路。型安全だが、Quick タスクの粒度に対して over-engineering。現在プール定義は 1-2 件であり、将来プール数やパラメータが増えた時点で検討する。
- **環境変数でオーバーライド:** 12-factor 的アプローチ。しかしプール名ごとに異なる値を渡したい要件が強く、環境変数空間が肥大化するため不採用。

## Consequences

### Positive
- 運用者が Python コードを触らずに接続プールをチューニングできる。
- `if key in pool_cfg` 方式により、psycopg_pool のバージョンアップでデフォルト値が変わっても追従しやすい。
- 既存の `db_pools.yaml` (パラメータ未指定) はそのまま動作し、後方互換を壊さない。
- T-23-03 (DSN をログに出さない) を維持しつつ、`pool_kwargs` のみ debug ログで出力することで運用時の確認手段を確保。

### Gotchas / 注意点
- YAML に書いたキー名のタイプミスはエラーではなく**黙って無視される**。`AsyncConnectionPool` に存在しないキーを追加した場合のみ `TypeError` で起動失敗する。今後パラメータを追加する際はキー名の allowlist を `db_query.py` 側で一元管理している点を忘れないこと (将来キー追加時は `db_query.py::init_pools()` の `for key in (...)` タプルを更新する必要がある)。
- `max_idle` は `min_size > 0` のプールでは意味を持たない (psycopg_pool 仕様)。YAML で両方を指定しても警告は出ないので、運用者向けのコメントで明記した。
- プールごとの設定ができる分、本番と開発で挙動差が出やすくなった。`docker compose` の healthcheck が通っても、プール枯渇は負荷時にしか顕在化しないので、`pool_kwargs` debug ログを本番で有効化しておくことを推奨。
