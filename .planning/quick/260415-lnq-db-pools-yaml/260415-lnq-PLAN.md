---
phase: quick-260415-lnq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - config/db_pools.yaml
  - mcp_server/tools/db_query.py
autonomous: true
requirements:
  - QUICK-260415-lnq
must_haves:
  truths:
    - "config/db_pools.yaml のプールエントリで min_size / max_size / max_idle / reconnect_timeout を指定できる"
    - "init_pools() は YAML で指定された値を AsyncConnectionPool にそのまま渡す"
    - "YAML でチューニングパラメータを省略したプール定義は psycopg_pool のデフォルト値で動作する（後方互換）"
    - "DSN は従来どおりログに出力されない（T-23-03 維持）"
  artifacts:
    - path: "config/db_pools.yaml"
      provides: "チューニングパラメータ付き YAML サンプル"
      contains: "min_size"
    - path: "mcp_server/tools/db_query.py"
      provides: "init_pools() の YAML 駆動パラメータ読込"
      contains: "AsyncConnectionPool"
  key_links:
    - from: "config/db_pools.yaml"
      to: "mcp_server/tools/db_query.py::init_pools"
      via: "yaml.safe_load -> pool_cfg -> AsyncConnectionPool(**kwargs)"
      pattern: "AsyncConnectionPool\\("
---

<objective>
`mcp_server/tools/db_query.py` の `init_pools()` にハードコードされている `min_size=1` / `max_size=5` を廃止し、`config/db_pools.yaml` のプールごとの設定から接続プールパラメータ（`min_size` / `max_size` / `max_idle` / `reconnect_timeout`）を読み込めるようにする。

Purpose: 環境（開発/本番）やプール単位で接続数・タイムアウトを調整できるようにし、運用チューニングの選択肢を確保する。
Output:
- `config/db_pools.yaml`: チューニングパラメータ付きのサンプル設定
- `mcp_server/tools/db_query.py`: YAML 値を `AsyncConnectionPool` に渡すように修正した `init_pools()`
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/todos/pending/2026-04-14-db-pools-yaml-tuning-params.md
@config/db_pools.yaml
@mcp_server/tools/db_query.py

<interfaces>
<!-- 現状の init_pools() の該当箇所（行 88-97）: -->

```python
pools_config = config.get("pools", {})
for name, pool_cfg in pools_config.items():
    dsn = pool_cfg.get("dsn", "")
    try:
        pool = AsyncConnectionPool(dsn, open=False, min_size=1, max_size=5)
        await pool.open()
        _pools[name] = pool
        logger.info("db_query: pool '%s' opened", name)
    except Exception as e:
        logger.error("db_query: failed to open pool '%s' — %s", name, e)
```

<!-- psycopg_pool.AsyncConnectionPool の関連キーワード引数（psycopg_pool 3.x API）: -->
<!-- - min_size: int  （デフォルト 4） -->
<!-- - max_size: int | None  （デフォルト None = min_size と同じ） -->
<!-- - max_idle: float  （秒, デフォルト 600） -->
<!-- - reconnect_timeout: float  （秒, デフォルト 300） -->
<!-- いずれも AsyncConnectionPool コンストラクタの kwargs としてそのまま渡せる。 -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: init_pools() を YAML 駆動のチューニングパラメータに対応させる</name>
  <files>mcp_server/tools/db_query.py</files>
  <action>
`init_pools()` の `AsyncConnectionPool` 生成部分（現状 `pool = AsyncConnectionPool(dsn, open=False, min_size=1, max_size=5)`）を書き換え、`pool_cfg` から `min_size` / `max_size` / `max_idle` / `reconnect_timeout` を読み取って `AsyncConnectionPool` のキーワード引数に渡す。

実装方針:

1. ループ内で DSN を取得した後、空の `pool_kwargs: dict = {}` を用意する。
2. 次の 4 パラメータについて、`pool_cfg` にキーが存在する場合のみ `pool_kwargs` に追加する（存在しない場合は psycopg_pool のデフォルトを使わせるため一切セットしない）:
   - `min_size` (int)
   - `max_size` (int)
   - `max_idle` (float/int、秒)
   - `reconnect_timeout` (float/int、秒)
   - 読み取りは `if "min_size" in pool_cfg: pool_kwargs["min_size"] = pool_cfg["min_size"]` のように `in` チェックで判定する（`get()` デフォルトで埋めない）。
3. `AsyncConnectionPool(dsn, open=False, **pool_kwargs)` で生成する。`open=False` + `await pool.open()` の既存パターンは維持する。
4. ログ出力は既存の `logger.info("db_query: pool '%s' opened", name)` をそのまま維持しつつ、直後に `logger.debug("db_query: pool '%s' kwargs=%s", name, pool_kwargs)` を追加する（DSN は含めない — T-23-03）。
5. 既存の try/except、エラーログ、`_pools[name] = pool` 代入順序は変更しない。

後方互換性:
- `pool_cfg` に 4 パラメータがいずれも無い場合、`pool_kwargs` は `{}` となり、`AsyncConnectionPool(dsn, open=False)` と等価 → psycopg_pool のデフォルト値が適用される。
- 既存の `config/db_pools.yaml`（dsn のみのプール定義）は無変更で動作する。

注意:
- `pool_cfg.get("min_size", 1)` のようにコード側でデフォルト値を埋めてはいけない。ハードコードが残り、psycopg_pool のデフォルトを使う選択肢が失われる。必ず「キーが存在する時だけ渡す」実装にする。
- `dsn` の読み取りは既存の `pool_cfg.get("dsn", "")` を維持。
- import 文（`yaml`, `AsyncConnectionPool`）は既存位置を変更しない。
  </action>
  <verify>
    <automated>python -c "
import ast
tree = ast.parse(open('mcp_server/tools/db_query.py').read())
src = open('mcp_server/tools/db_query.py').read()
assert 'min_size=1, max_size=5' not in src, 'ハードコードが残っている'
assert 'pool_kwargs' in src, 'pool_kwargs が導入されていない'
for key in ('min_size', 'max_size', 'max_idle', 'reconnect_timeout'):
    assert key in src, f'{key} の読み取りが無い'
print('OK')
"</automated>
  </verify>
  <done>
- `init_pools()` から `min_size=1, max_size=5` のハードコードが消えている。
- `pool_kwargs` dict に `min_size` / `max_size` / `max_idle` / `reconnect_timeout` が「キー存在時のみ」追加されている。
- `AsyncConnectionPool(dsn, open=False, **pool_kwargs)` で生成されている。
- 既存の dsn のみ指定された YAML で `init_pools()` を実行した場合も例外にならず動作する（構文・ロジック上）。
  </done>
</task>

<task type="auto">
  <name>Task 2: config/db_pools.yaml にチューニングパラメータのサンプルとコメントを追加する</name>
  <files>config/db_pools.yaml</files>
  <action>
既存の `config/db_pools.yaml` を更新し、`default` プールにチューニングパラメータのサンプル値とコメントを追加する。開発環境向けの控えめな値を設定し、各パラメータの意味をコメントで明示する。

更新後の内容（全体を置き換え）:

```yaml
# Local development DB pool config.
# Uses the same postgres instance as the main app.
#
# 接続プールのチューニングパラメータ（すべて任意 — 省略時は psycopg_pool のデフォルト値が適用される）:
#   min_size:          プール内の最小接続数（psycopg_pool デフォルト: 4）
#   max_size:          プール内の最大接続数（デフォルト: min_size と同じ）
#   max_idle:          アイドル接続を保持する最大秒数（デフォルト: 600 秒）
#   reconnect_timeout: 接続失敗時に再接続を試み続ける最大秒数（デフォルト: 300 秒）
pools:
  default:
    dsn: postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable
    min_size: 1
    max_size: 5
    max_idle: 300
    reconnect_timeout: 30
```

注意:
- インデントは半角スペース 2。
- `dsn` は既存の値を変更しない。
- 後方互換確認: このパラメータを省略した既存の最小 YAML（`default: { dsn: ... }` のみ）でも Task 1 の `init_pools()` が動作することが前提。
  </action>
  <verify>
    <automated>python -c "
import yaml
with open('config/db_pools.yaml') as f:
    cfg = yaml.safe_load(f)
d = cfg['pools']['default']
assert d['dsn'].startswith('postgresql://'), 'dsn が失われている'
for key in ('min_size', 'max_size', 'max_idle', 'reconnect_timeout'):
    assert key in d, f'{key} が YAML に無い'
assert isinstance(d['min_size'], int)
assert isinstance(d['max_size'], int)
print('OK')
"</automated>
  </verify>
  <done>
- `config/db_pools.yaml` がパース可能で、`default` プールに `min_size` / `max_size` / `max_idle` / `reconnect_timeout` が含まれている。
- 各パラメータの意味を説明するコメントが冒頭に付与されている。
- `dsn` の値が保持されている。
  </done>
</task>

<task type="auto">
  <name>Task 3: init_pools() の YAML 読み込み結合テストをインラインで実行する</name>
  <files></files>
  <action>
Task 1 + Task 2 が整合していることを軽量な結合テストで確認する。Python を直接起動し、以下 2 シナリオを YAML 文字列から `yaml.safe_load` → `pool_kwargs` 構築ロジックを模擬実行して確認する（実 DB 接続はしない）。

1. **フル指定 YAML:** `min_size=1`, `max_size=5`, `max_idle=300`, `reconnect_timeout=30` が `pool_kwargs` dict にそのまま反映されることを確認。
2. **最小 YAML（後方互換）:** `dsn` のみのプール定義から生成された `pool_kwargs` が `{}`（空 dict）であることを確認。

この検証は一時的な Python ワンライナーで良く、コードをリポジトリに残す必要はない。`mcp_server/tools/db_query.py` を直接 import して `init_pools()` を呼ぶ必要はない（実 DB 接続を試みる）。代わりに、`init_pools()` 内のパラメータ抽出ロジックを手動でなぞるだけで十分。

さらに、`mcp_server/tools/db_query.py` を静的 import して構文エラーが無いことを確認する:

```
python -c "import importlib, sys; sys.path.insert(0, '.'); importlib.import_module('mcp_server.tools.db_query'); print('import OK')"
```

エラーが出た場合は Task 1 に戻って修正する。
  </action>
  <verify>
    <automated>python -c "
import sys, yaml
sys.path.insert(0, '.')
import importlib
importlib.import_module('mcp_server.tools.db_query')

# Simulated pool_kwargs extraction matching Task 1 logic
def extract(pool_cfg):
    kwargs = {}
    for key in ('min_size', 'max_size', 'max_idle', 'reconnect_timeout'):
        if key in pool_cfg:
            kwargs[key] = pool_cfg[key]
    return kwargs

# Scenario 1: full YAML from config/db_pools.yaml
with open('config/db_pools.yaml') as f:
    cfg = yaml.safe_load(f)
full = extract(cfg['pools']['default'])
assert full == {'min_size': 1, 'max_size': 5, 'max_idle': 300, 'reconnect_timeout': 30}, full

# Scenario 2: minimal YAML (backward compat)
minimal_yaml = 'pools:\n  default:\n    dsn: postgresql://x\n'
mcfg = yaml.safe_load(minimal_yaml)
mkwargs = extract(mcfg['pools']['default'])
assert mkwargs == {}, mkwargs
print('integration OK')
"</automated>
  </verify>
  <done>
- `mcp_server.tools.db_query` が import エラー無くロードできる。
- 現在の `config/db_pools.yaml` から抽出した `pool_kwargs` が 4 キー全て含む dict になる。
- `dsn` のみの最小 YAML から抽出した `pool_kwargs` が空 dict（後方互換）。
  </done>
</task>

</tasks>

<verification>
- `config/db_pools.yaml` が有効な YAML で、`default` プールにチューニングパラメータ 4 種が含まれる。
- `mcp_server/tools/db_query.py` の `init_pools()` がハードコードされた `min_size=1, max_size=5` を持たず、`pool_cfg` からキー存在時のみ kwargs を抽出して `AsyncConnectionPool` に渡す。
- Task 3 の結合チェックが通る（import OK + パラメータ抽出 OK）。
- T-23-03（DSN ログ非公開）が維持されている: `logger.info` は pool 名のみ、追加の debug ログも `pool_kwargs` のみで DSN を含まない。
</verification>

<success_criteria>
- [ ] `config/db_pools.yaml` で `min_size` / `max_size` / `max_idle` / `reconnect_timeout` を指定でき、コメントで意味が説明されている
- [ ] `init_pools()` のハードコード `min_size=1, max_size=5` が撤去され、YAML 値が `AsyncConnectionPool` に渡る
- [ ] 4 パラメータ全て省略した YAML プール定義で `init_pools()` が psycopg_pool のデフォルトで動作する（後方互換）
- [ ] Task 3 の軽量結合テストが成功する
- [ ] DSN が info/debug いずれのログにも出現しない
</success_criteria>

<output>
After completion, create `.planning/quick/260415-lnq-db-pools-yaml/260415-lnq-SUMMARY.md`
</output>
