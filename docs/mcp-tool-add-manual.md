# MCP ツール追加マニュアル

このドキュメントは MCP ツールを新規追加する際の **手順書** です。
自動化されたスラッシュコマンド `/add-mcp-tool` が用意されていますが、その中身で何が
起きているかを理解するため、また個別の事情で手動調整が必要な場合のためにこのマニュアル
を参照してください。

Phase 30 で確立された single-source-of-truth 方針:
`config/mcp_tools.yaml` が MCP ツールカタログの **唯一の宣言**。以下 3 ファイルは全て
そこから自動生成される:

- `mcp_server/tools/mcp_helper.py` — sandbox から MCP を呼ぶ Python ラッパー
- `static/js/tool-catalog-generated.js` — iframe-rpc.js が import する JS カタログ
- `docs/mcp-tools.md` — 人間向けツールカタログ

## 手書き境界（Phase 30 D-02）

| ファイル | 区分 | 編集方法 |
|---------|-----|---------|
| `config/mcp_tools.yaml` | 手書き（SSoT） | 手動編集 |
| `mcp_server/tools/<name>.py` | 手書き（実装） | 手動編集 |
| `mcp_server/tools/mcp_helper_utils.py` | 手書き（基盤） | 手動編集 |
| `mcp_server/tools/mcp_helper.py` | **自動生成** | ジェネレータ再実行 |
| `static/js/tool-catalog-generated.js` | **自動生成** | ジェネレータ再実行 |
| `static/js/iframe-rpc.js` | 手書き（RPC 本体） | 手動編集（カタログは import 経由） |
| `docs/mcp-tools.md` | **自動生成** | ジェネレータ再実行 |
| `docs/mcp-tool-add-manual.md` | 手書き（本ファイル） | 手動編集 |

自動生成ファイルの先頭には `DO NOT EDIT` ヘッダーが付く。手動編集すると pre-commit
hook (`scripts/install-hooks.sh` でインストール) が drift を検知し commit をブロック
する。

## YAML スキーマリファレンス

````yaml
tools:
  - name: <str>                    # 必須。MCP サーバーの @mcp.tool 関数名と完全一致
    description: <str>              # 必須。短文説明（JS カタログ・docs で表示）
    privileged: <bool>              # 任意。true で SubAgentRegistry が WARNING を出す
    sandbox_exposed: <bool>         # 任意。false で mcp_helper.py に wrapper を生成しない
    python_wrapper:                 # sandbox_exposed: true かつ sandbox から呼ぶ場合に必須
      function_name: <str>          # mcp_helper.py 内の関数名
      args:                         # Python 関数の引数リスト
        - name: <str>
          type: <str>               # Python 型注釈文字列（"str", "int", "list[dict]" 等）
          default: <str>            # 任意。引用符込みで書く（例: '"default"'）
          description: <str>
      return_type: <str>            # "list[dict]", "dict" 等
      docstring: |                  # 関数 docstring。Args/Returns/Example ブロックを含める
        ...
      mcp_args_mapping:             # Python 関数引数 → MCP tool 引数へのマッピング
        <py_arg_name>: <mcp_arg_name>
      result_transform:             # _call_tool の戻り値の変換方法
        mode: passthrough | extract_key | web_search_results
        key: <str>                  # extract_key の場合のみ必須
````

### result_transform.mode の 3 種

1. `passthrough` — `_call_tool` の戻り値をそのまま返す（ping / get_current_datetime）
2. `extract_key` — dict から `result.get("<key>", [result])` を取り出す（db_query の `rows`）
3. `web_search_results` — `results` キーを取り出し、各 item の `content` に `_clean_content()` を適用（web_search 専用）

新しい transform パターンが必要になった場合は `scripts/generate_mcp_artifacts.py` の
`_generate_wrapper_body()` に分岐を追加すること。

## 生成コマンド

```bash
# 3 ファイル全て再生成
python3 scripts/generate_mcp_artifacts.py --target all

# 個別ターゲット（stdout に出力）
python3 scripts/generate_mcp_artifacts.py --target helper
python3 scripts/generate_mcp_artifacts.py --target js
python3 scripts/generate_mcp_artifacts.py --target docs

# drift 検知（pre-commit hook が内部で使用）
python3 scripts/generate_mcp_artifacts.py --check
```

## privileged フラグの基準 (ADR 0023 / 0024)

`privileged: true` は以下のいずれかに該当するツールに付与する:

- worker / mcp-server コンテナのファイルシステム全域にアクセスできる (claude_code)
- 任意の Python コードを実行できる (execute_python)
- 外部 API に書き込み操作を行える
- 機密情報（秘密鍵、DSN 等）を読み出せる

`privileged: true` のツールを `agents/<name>/AGENT.md` の `tools:` フィールドに
宣言すると `SubAgentRegistry` が WARNING ログを出す。社内機密を扱うエージェントには
付与しないこと。

## pre-commit hook の挙動

`scripts/install-hooks.sh` を実行すると `.git/hooks/pre-commit` がインストールされる。
hook は以下 2 つの検査を行う:

1. **ADR INDEX 再生成** (Phase 26) — `docs/adr/*.md` が staged なら `generate_adr_index.py`
2. **MCP artifacts drift 検知** (Phase 30) — 以下のいずれかが staged なら `generate_mcp_artifacts.py --check`:
   - `config/mcp_tools.yaml`
   - `mcp_server/tools/mcp_helper.py`
   - `static/js/tool-catalog-generated.js`
   - `docs/mcp-tools.md`

drift が検知されると commit がブロックされ、以下のメッセージが表示される:

    python3 scripts/generate_mcp_artifacts.py --target all
    git add mcp_server/tools/mcp_helper.py static/js/tool-catalog-generated.js docs/mcp-tools.md
    git commit

## 新規ツール追加チェックリスト

### 推奨: スラッシュコマンドを使う

```
/add-mcp-tool <tool_name>
```

これで以下 6 ステップが対話的に実行される。

### 手動手順

1. `config/mcp_tools.yaml` に新エントリを追加（上記スキーマに従う）
2. `mcp_server/tools/<name>.py` を新規作成（既存 `ping.py` / `web_search.py` / `db_query.py` を参考）
3. `mcp_server/server.py` に `register_<name>_tools` import と呼び出しを追加
4. `python3 scripts/generate_mcp_artifacts.py --target all` を実行
5. `tests/test_<name>_tool.py` に最低 1 つの pytest テストを追加
6. `ToolRegistry` が MCP 実ツールリストとの一致を検証するため、`docker compose restart worker` で MCP サーバーとの同期を確認（YAML とコードの両方がコミットされた状態である必要がある）
7. `git add config/mcp_tools.yaml mcp_server/tools/<name>.py mcp_server/server.py mcp_server/tools/mcp_helper.py static/js/tool-catalog-generated.js docs/mcp-tools.md tests/test_<name>_tool.py`
8. `git commit -m "feat(mcp): add <name> tool"`

### 削除手順

1. `config/mcp_tools.yaml` から該当エントリを削除
2. `mcp_server/tools/<name>.py` を削除
3. `mcp_server/server.py` の import と register 呼び出しを削除
4. `python3 scripts/generate_mcp_artifacts.py --target all`
5. 関連テストファイルを削除
6. コミット

## ToolRegistry との関係 (ADR 0024)

`app/orchestrator/tool_registry.py` は `config/mcp_tools.yaml` の `tools[*].name` と
MCP サーバーが実際に公開するツール名の集合が **完全一致** することを worker 起動時に
検証する。不一致時は `RuntimeError` を raise して worker 起動を失敗させる。

Phase 30 で YAML スキーマが拡張された後も、ToolRegistry は `name` と `privileged` の
2 フィールドしか参照しないため、`python_wrapper` / `sandbox_exposed` 等の追加フィールド
は無視される（後方互換）。
