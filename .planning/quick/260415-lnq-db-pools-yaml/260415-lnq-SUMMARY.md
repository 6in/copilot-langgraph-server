---
quick_id: 260415-lnq
description: db_pools.yaml に接続プールのチューニングパラメータを追加する
date: 2026-04-15
status: completed
---

# Quick Task 260415-lnq: db_pools.yaml チューニングパラメータ追加

## 概要

`mcp_server/tools/db_query.py::init_pools()` の `min_size=1, max_size=5` ハードコードを撤去し、
`config/db_pools.yaml` でプールごとにチューニングパラメータを指定できるよう拡張した。

## 変更内容

### 1. `mcp_server/tools/db_query.py` — YAML 駆動パラメータ抽出

`init_pools()` で `pool_cfg` から 4 つのチューニングパラメータを `if key in pool_cfg` 方式で抽出し、
`AsyncConnectionPool(**pool_kwargs)` に渡すように変更:

- `min_size`
- `max_size`
- `max_idle`（アイドル接続の最大保持時間、秒）
- `reconnect_timeout`

**後方互換性:** キーが存在する場合のみ kwargs に含めるため、省略時は psycopg_pool のデフォルト値に
フォールバックする（コード側にデフォルトを埋めない）。

**T-23-03 維持:** DSN はログに出さず、追加 debug ログも `pool_kwargs` のみ出力。

### 2. `config/db_pools.yaml` — サンプル値とコメント追加

`default` プールにチューニングパラメータのサンプル値とヘッダーコメントを追加。他プール定義は変更なし
（省略時フォールバックで引き続き動作する）。

### 3. 結合テスト（検証のみ、ファイル変更なし）

- YAML パース
- `psycopg_pool.AsyncConnectionPool` の kwargs 互換確認
- パラメータ抽出ロジックの単体検証
- 後方互換性（キー省略時の挙動）確認

すべて合格。ファイル変更を伴わないためコミットなし。

## コミット

- `a51e594` — feat(quick-260415-lnq): init_pools() を YAML 駆動のチューニングパラメータ対応に変更
- `859bae7` — chore(quick-260415-lnq): db_pools.yaml にチューニングパラメータのサンプルとコメント追加
- `cabaff6` — chore: merge quick task worktree (worktree-agent-a80fe246)

## 関連ファイル

- `mcp_server/tools/db_query.py`
- `config/db_pools.yaml`
