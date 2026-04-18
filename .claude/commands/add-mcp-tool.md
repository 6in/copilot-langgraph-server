新規 MCP ツールを Phase 30 の single-source-of-truth 方針に従って追加する。`$ARGUMENTS` にツール名が入る想定（例: `/add-mcp-tool fetch_url`）。空なら Claude が対話的にユーザーから目的を聞いて命名する。

## Steps

**1. ツール名と概要の確定**

`$ARGUMENTS` を読み取り:
- 非空ならツール名として採用（`snake_case` であることを確認）
- 空ならユーザーに「追加したい MCP ツールの目的は？」と 1 回だけ質問し、結果から `snake_case` のツール名を Claude が命名する

既存ツールとの衝突確認:

```bash
grep -E "^  - name: ${TOOL_NAME}" config/mcp_tools.yaml && echo "衝突: 既存" && exit 1
```

**2. config/mcp_tools.yaml に新エントリを追加**

`docs/mcp-tool-add-manual.md` の YAML スキーマリファレンスに従い、以下をユーザーと対話で決定してから YAML 末尾に追記する:

- `name`: Step 1 で確定
- `description`: 1 行説明（日本語）
- `privileged`: 基準は `docs/mcp-tool-add-manual.md` 参照 — 迷ったら false
- `sandbox_exposed`: sandbox (execute_python) から呼び出したいなら true、そうでなければ false
- `python_wrapper`（sandbox_exposed=true の場合のみ）:
  - `function_name` / `args` / `return_type` / `docstring` / `mcp_args_mapping` / `result_transform`

YAML 編集後、構文チェック:

```bash
python3 -c "import yaml; yaml.safe_load(open('config/mcp_tools.yaml'))"
```

**3. ツール実装ファイルの雛形を作成**

`mcp_server/tools/${TOOL_NAME}.py` を新規作成する。既存の `mcp_server/tools/web_search.py` (簡易 Tavily ラッパー) を雛形として最適。骨格:

```python
"""${TOOL_NAME} MCP ツール (Phase 30 で追加)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_tools(mcp: "FastMCP") -> None:
    """${TOOL_NAME} を FastMCP インスタンスに登録する。"""

    @mcp.tool
    def ${TOOL_NAME}(<args>) -> dict:
        """<description from YAML>

        Args:
            ...

        Returns:
            {...} or {"error": "..."}
        """
        try:
            # 実装をここに書く
            return {"ok": True}
        except Exception as e:
            return {"error": f"${TOOL_NAME} failed: {e}"}
```

実際の引数・戻り値・例外処理はユーザーの要件に応じて Claude が提案する。

**4. mcp_server/server.py に登録を追加**

以下 2 箇所を編集する:

(a) import セクション (L17-22 近辺):
```python
from tools.${TOOL_NAME} import register_tools as register_${TOOL_NAME}_tools
```

(b) register 呼び出しセクション (L49-53 近辺、`register_execute_python_tools(mcp)` の直前か直後):
```python
register_${TOOL_NAME}_tools(mcp)
```

**5. 生成ファイルを再生成**

```bash
python3 scripts/generate_mcp_artifacts.py --target all
```

これで `mcp_server/tools/mcp_helper.py` / `static/js/tool-catalog-generated.js` / `docs/mcp-tools.md` の 3 ファイルが最新化される。

**6. テスト雛形を作成**

`tests/test_${TOOL_NAME}_tool.py` を新規作成する。最低限 1 つの正常系テストを書く。既存 `tests/test_mcp_helper_generated.py` 等のスタイルを踏襲。

**7. pre-commit 互換性確認 + コミット**

```bash
python3 scripts/generate_mcp_artifacts.py --check
uv run pytest tests/test_tool_registry.py tests/test_mcp_helper_generated.py tests/test_tool_catalog_js.py tests/test_${TOOL_NAME}_tool.py -v
git add config/mcp_tools.yaml mcp_server/tools/${TOOL_NAME}.py mcp_server/server.py mcp_server/tools/mcp_helper.py static/js/tool-catalog-generated.js docs/mcp-tools.md tests/test_${TOOL_NAME}_tool.py
git commit -m "feat(mcp): add ${TOOL_NAME} tool"
```

pre-commit hook が走り、drift なしなら commit 成功。

## 関連ドキュメント

- `docs/mcp-tool-add-manual.md` — 手動手順・YAML スキーマ詳細・privileged 基準・pre-commit 挙動
- `config/mcp_tools.yaml` — ツールカタログ (single source of truth)
- `scripts/generate_mcp_artifacts.py` — 3 ファイル生成ジェネレータ

## 完了後の報告

Claude は実行終了時に以下を報告する:

```
Added MCP tool: ${TOOL_NAME}
- YAML entry: config/mcp_tools.yaml
- Implementation: mcp_server/tools/${TOOL_NAME}.py
- Test: tests/test_${TOOL_NAME}_tool.py
- Regenerated: mcp_helper.py / tool-catalog-generated.js / mcp-tools.md

Next: docker compose restart worker mcp-server
```
