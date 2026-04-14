---
created: 2026-04-14T06:34:12.920Z
title: db_pools.yaml に接続プールのチューニングパラメータを追加する
area: api
files:
  - config/db_pools.yaml
  - mcp_server/tools/db_query.py
---

## Problem

`mcp_server/tools/db_query.py` の `init_pools()` で `AsyncConnectionPool` を初期化する際、`min_size=1`・`max_size=5` がハードコードされている。`keepalives`・`reconnect_timeout`・`max_idle` などのチューニングパラメータも psycopg_pool のデフォルト任せ。

環境（開発/本番）やプールごとに接続数・タイムアウトを調整したい場合に対応できない。

## Solution

`config/db_pools.yaml` でプールごとにパラメータを指定できるよう拡張する:

```yaml
pools:
  default:
    dsn: postgresql://...
    min_size: 1
    max_size: 5
    max_idle: 300        # 秒: アイドル接続の最大保持時間
    reconnect_timeout: 30
```

`init_pools()` で `pool_cfg.get("min_size", 1)` のように YAML 値を読み込み、`AsyncConnectionPool` に渡す。未指定のパラメータは psycopg_pool のデフォルト値を使う。
