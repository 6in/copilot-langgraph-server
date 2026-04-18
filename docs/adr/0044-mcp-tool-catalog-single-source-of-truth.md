# 0044. MCP ツールカタログ single-source-of-truth 化（YAML + 決定論ジェネレータ + drift 検知）

**Date:** 2026-04-18
**Status:** Accepted

## Context

Phase 20〜24 で MCP ツールを本番投入した結果、**MCP ツール 1 個を追加するのに複数ファイルを手で同期する必要が発生**した:

- `config/mcp_tools.yaml` — ToolRegistry 用の宣言（ADR 0024）
- `mcp_server/tools/mcp_helper.py` — sandbox から MCP を呼ぶ Python ラッパー（CodeAct 用）
- `static/js/iframe-rpc.js` 内の `AVAILABLE_TOOLS` 定数 — Canvas iframe RPC ブリッジ用のカタログ
- `scripts/sync-tool-list-to-js.py` — iframe-rpc.js 内定数と YAML を突き合わせる独立スクリプト
- ドキュメント側では手書きで `docs/mcp-tools.md` 相当の仕様を維持する必要

これらは論理的には同じ情報（ツール名・引数・返り値・権限フラグ）を別々のフォーマットで書き直したものであり、**片方だけ更新して他方を忘れる drift が構造的に発生**していた。特に `mcp_helper.py` の wrapper docstring と `docs/mcp-tools.md` の仕様は独立に書かれており、乖離していても CI で検知できなかった。

Phase 30 直前には、`db_query` の引数名が Python 側で `pool`、MCP 側で `pool_name` と二重管理されていたり、`iframe-rpc.js` 内の `AVAILABLE_TOOLS` に `web_search` が追加されないまま残っていたりと、実運用で drift が顕在化していた。

さらに社内 200 名規模の利用が始まり、「ツールを 1 個追加する」という作業がオンボーディング直後のメンバーでも実行できる必要が出てきた。現行の分散構造ではどこに何を書くかの知識がドキュメントに書き切れず、経験者頼みになっていた。

## Decision

**YAML を唯一の真実源にし、派生物は決定論的ジェネレータで自動生成する。**

1. **Single source of truth は `config/mcp_tools.yaml`**
   既存の `name` / `privileged` / `description` フィールドに加え、拡張スキーマとして以下を追加:
   - `sandbox_exposed: bool` — `mcp_helper.py` に Python wrapper を生成するか
   - `python_wrapper:` ブロック — `function_name` / `args[{name,type,default?,description}]` / `return_type` / `docstring` / `mcp_args_mapping` / `result_transform{mode,key?}`
   既存フィールドは破壊しない。ToolRegistry（ADR 0024）は `entry["name"]` と `entry.get("privileged")` しか見ないため、拡張フィールドは透過的に無視される。

2. **決定論ジェネレータ `scripts/generate_mcp_artifacts.py`**
   `--target {helper|js|docs|all}` で 3 成果物を生成、`--check` で drift 検知。
   - `mcp_server/tools/mcp_helper.py` — sandbox 用 Python ラッパー
   - `static/js/tool-catalog-generated.js` — iframe-rpc.js が import する ES module
   - `docs/mcp-tools.md` — 人間向けツール仕様カタログ
   同じ YAML 入力に対してバイト単位で同じ出力を返す（キー順固定・末尾単一 `\n`・全成果物に `DO NOT EDIT` ヘッダー）。

3. **手書きと自動生成をファイル単位で分離**
   手書き基盤（`_call_tool` / `_clean_content` / `_INTERNAL_URL` / `_TIMEOUT`）は `mcp_server/tools/mcp_helper_utils.py` に分離。生成版 `mcp_helper.py` はこれを import するだけ。これにより「ファイル全体を書き換えても壊れない箇所」と「1 文字も書き換えてはいけない箇所」が物理的に分かれた。

4. **pre-commit hook で drift をブロック**
   `scripts/install-hooks.sh` を ADR INDEX 生成 + MCP drift 検知の両方を担うように拡張。`config/mcp_tools.yaml` が staged に含まれるコミットは `generate_mcp_artifacts.py --check` を自動実行し、生成物との乖離があれば commit を exit 非 0 でブロックする。

5. **新規ツール追加の標準化**
   `/add-mcp-tool <name>` スラッシュコマンド（`.claude/commands/add-mcp-tool.md`）を追加し、7 ステップ（YAML 追加 → tool .py 実装 → 再生成 → 検証 → 回帰テスト → 単体テスト → commit）を 1 コマンドで完遂できるようにした。手動手順は `docs/mcp-tool-add-manual.md`。CLAUDE.md からこの 2 ファイルへリンクする。

## Alternatives Considered

**A. Runtime reflection（実行時にツールを MCP サーバから取ってきて wrapper を動的生成）**
却下。静的解析（IDE の補完・type check）が効かなくなる。sandbox 側は pyright/pyflakes で壊れる。さらに runtime 依存を増やすと Canvas iframe の起動時に MCP サーバ接続を待つ必要があり、起動遅延が許容できなかった。

**B. ビルド時コード生成のみ（pre-commit なし）**
却下。ローカル開発では Docker build をスキップして `docker compose exec -T api uv run` で直接動かすことが多く、ビルド時 hook に頼ると dev 環境で drift が放置される。Phase 20 以前の `sync-tool-list-to-js.py` が実質これで、結果として drift が発生していた。

**C. 手書き継続 + CI lint 検査**
却下。lint で検知できても PR 上で失敗してから修正する流れになり、レビュー文脈でのノイズが増える。ADR 0006 のローカル防御思想（「CI が落ちる前にローカルで止める」）に反する。

**D. OpenAPI 的な独立スキーマ言語を採用**
却下。スキーマ言語の学習コストが追加発生し、YAML 1 ファイルで完結する現在のシンプルさを失う。社内 200 名規模・ツール 10 個程度の想定にはオーバーエンジニアリング。

**E. python_wrapper を書かず sandbox 用 helper は手書き維持**
却下。wrapper の記述量が少ないとはいえ、docstring 含めると 1 ツールあたり 15〜25 行。6 ツールで 120 行超の重複情報が YAML と Python に分散することになり、drift リスクが残る。

## Consequences

### Positive

- **開発者が触る場所が 3 つに収束**: `config/mcp_tools.yaml` + `mcp_server/tools/<name>.py` + `tests/test_*.py`。それ以外は生成物または不変基盤。
- **drift が構造的に不可能になった**: pre-commit がブロック → 生成物と YAML のズレは git に入らない。
- **オンボーディング時間が減った**: `/add-mcp-tool <name>` が 7 ステップを案内、`docs/mcp-tool-add-manual.md` で背景も理解できる。
- **バイト単位の決定論が drift 検知の前提として成立**: キー順固定・末尾単一 `\n` により、同じ YAML から生成すれば必ず同じバイト列。generator の出力が揺れないので偽陽性がない。
- **ADR 0024 との後方互換が保たれた**: ToolRegistry のテスト 6 件は 1 行も修正せず pass。拡張スキーマは ToolRegistry から見えない。

### Negative / Gotchas

- **YAML のスキーマ理解が必須**: 特に `mcp_args_mapping` と `result_transform.mode` は既存ツールを読まないと意味が分かりにくい。
  - `mcp_args_mapping`: Python 関数引数名と MCP 側引数名が異なる時に使う。例: `db_query` は Python 側 `pool`、MCP 側 `pool_name`。
  - `result_transform.mode`: `passthrough` / `extract_key` / `web_search_results` の 3 種。`web_search` だけ特殊扱い（`_clean_content()` 呼び出し）なので将来ツール追加時に類似パターンが発生したら mode を拡張する必要がある。
- **生成ファイルに `DO NOT EDIT` ヘッダーがあるが、初見のエンジニアは警戒せず編集しがち**: pre-commit が止めてくれるが、ブランチローカルで作業してから初めて気づくと手戻りになる。CLAUDE.md の MCP Tool Catalog セクションに境界を明記して緩和した。
- **ジェネレータ自体の保守コストが増えた**: `scripts/generate_mcp_artifacts.py` は 483 行・pytest 18 件。新フィールドを YAML に足すときはジェネレータ側の rendering も追従が必要。
- **`mcp_helper_utils.py` は wrapper が全滅すると import されなくなる**: Python は未使用 import を検知しないので、全ツールが `sandbox_exposed: false` になった場合 helper.py が `_call_tool` を import しない生成物になる可能性がある。現在は 4/6 ツールが wrapper を持つので顕在化していない。
- **新規クローン時に `bash scripts/install-hooks.sh` を忘れると drift 検知が働かない**: CLAUDE.md に明記済みだが、hook がない環境で作業した場合は commit 時のガードが効かない。

### Follow-ups / 今後の注意点

- 新規 MCP ツールを追加する時は `docs/mcp-tool-add-manual.md` → `/add-mcp-tool` の順で参照。既存 6 ツールをコピペ改変するのが最速。
- `result_transform.mode` を増やすときはジェネレータ側に rendering ロジックを追加し、pytest にケースを足す。
- `config/mcp_tools.yaml` のコメントは drift 検知対象ではない（YAML parse 後の dict を比較するため）。運用ルールや参照先の更新はコメントで積極的に書いてよい。

## Related

- ADR 0020 — FastMCP Docker 基盤
- ADR 0022 — MCP ツールスキーマ検証（初期版）
- ADR 0023 — db_query / claude_code 本番実装
- ADR 0024 — ToolRegistry によるツール名検証
- ADR 0040 — UI 改善バッチ（iframe-rpc カタログ移行の素地）
- ADR 0041 — CodeAct 直接実行方式
- `.planning/phases/30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-/` — Phase 30 全 6 プランの SUMMARY と VERIFICATION
