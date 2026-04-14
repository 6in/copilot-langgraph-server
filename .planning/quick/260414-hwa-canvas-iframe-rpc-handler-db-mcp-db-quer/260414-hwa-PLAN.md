---
phase: 260414-hwa
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/jobs/handlers/iframe_rpc_handler.py
  - tests/test_iframe_rpc_handler.py
autonomous: true
requirements:
  - QUICK-260414-HWA
must_haves:
  truths:
    - "Canvas iframe からの QUERY RPC が MCP db_query ツール経由で SELECT を実行し結果を返す"
    - "iframe_rpc_handler.py は psycopg / dict_row を import せず、直接 DB 接続を一切持たない"
    - "MCP db_query ツールが ctx['mcp_tools'] にない (DEGRADED) 場合は明示的なエラーを返す"
    - "既存のテストが新しい実装に追従して全て pass する"
  artifacts:
    - path: "app/jobs/handlers/iframe_rpc_handler.py"
      provides: "MCP db_query 経由の QUERY ハンドラ"
      contains: "ctx[\"mcp_tools\"]"
    - path: "tests/test_iframe_rpc_handler.py"
      provides: "新実装に追従した単体テスト"
  key_links:
    - from: "app/jobs/handlers/iframe_rpc_handler.py::_handle_query"
      to: "ctx['mcp_tools'] の name=='db_query' BaseTool"
      via: "tool.ainvoke({'sql': sql, 'pool_name': pool_name})"
      pattern: "ainvoke.*sql.*pool_name"
---

<objective>
Canvas iframe からの JSON-RPC `QUERY` を、`iframe_rpc_handler._handle_query` の直接 DB アクセス（psycopg_pool）から、Phase 23 で実装済みの MCP `db_query` ツール経由に切り替える。

Purpose: DB アクセス経路を MCP ツール 1 本に集約し、二重実装と二重メンテナンスを排除する。SQL 安全性ガードの正となる実装を MCP 側に統一する。

Output:
- `app/jobs/handlers/iframe_rpc_handler.py` から psycopg 直接アクセスと `is_select_only` を削除し、MCP `db_query` ツールを呼ぶ実装に置換
- `tests/test_iframe_rpc_handler.py` を新実装に合わせて更新（`is_select_only` のテストは削除、`_handle_query` のテストは MCP ツール mock に切替）
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/jobs/handlers/iframe_rpc_handler.py
@app/jobs/worker.py
@mcp_server/tools/db_query.py
@tests/test_iframe_rpc_handler.py

<interfaces>
<!-- ctx に格納されている MCP ツールのインターフェース。
     worker.startup() で MultiServerMCPClient.get_tools() の戻り値が ctx["mcp_tools"] に入る。
     LangChain BaseTool として扱われ、name 属性で識別、ainvoke() で呼び出す。 -->

ctx["mcp_tools"]: list[langchain_core.tools.BaseTool]
  - 各要素は MCP ツール由来の BaseTool
  - name 属性で識別: "db_query", "web_search", など
  - DEGRADED 時は [] (worker.py L72-103)

db_query ツール (mcp_server/tools/db_query.py L119-151):
  入力: {"sql": str, "pool_name": str = "default"}
  戻り値:
    成功: {"rows": [...]}   ← JSON シリアライズ済み (datetime/Decimal/UUID は文字列化済み)
    失敗: {"error": "..."}  ← is_select_only 違反 / unknown pool / 例外

呼び出し例:
  tool = next((t for t in ctx["mcp_tools"] if t.name == "db_query"), None)
  if tool is None:
      return {"result": False, "error": "db_query tool unavailable (MCP DEGRADED)"}
  out = await tool.ainvoke({"sql": sql, "pool_name": pool_name})
  if "error" in out:
      return {"result": False, "error": out["error"]}
  return {"result": True, "rows": out["rows"]}
</interfaces>

<usage_audit>
<!-- is_select_only の参照箇所監査結果 (作業開始時に再確認すること) -->
- app/jobs/handlers/iframe_rpc_handler.py: 定義 + _handle_query での使用 (削除対象)
- mcp_server/tools/db_query.py: 独自に再実装済み (Phase 23, D-03 の方針で重複 OK)
- tests/test_iframe_rpc_handler.py: import + parametrized test (削除対象)
- app/ 配下の他ファイルからの参照: なし (worker.py も含めて参照なし)
→ iframe_rpc_handler.py から削除しても worker / api 側の動作には影響しない
</usage_audit>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: _handle_query を MCP db_query ツール経由に差し替え</name>
  <files>app/jobs/handlers/iframe_rpc_handler.py, tests/test_iframe_rpc_handler.py</files>
  <behavior>
    - Test 1 (success): ctx["mcp_tools"] に name=="db_query" の AsyncMock BaseTool を入れ、`_handle_query` が `tool.ainvoke({"sql": "SELECT 1", "pool_name": "main"})` を呼び、{"result": True, "rows": [...]} を返す
    - Test 2 (tool error passthrough): mock の ainvoke が {"error": "Only SELECT queries are allowed"} を返したとき、`_handle_query` は {"result": False, "error": "Only SELECT queries are allowed"} を返す
    - Test 3 (unknown pool passthrough): mock の ainvoke が {"error": "Unknown pool: nonexistent"} を返したとき、`_handle_query` は {"result": False, "error": "Unknown pool: nonexistent"} を返す
    - Test 4 (DEGRADED): ctx["mcp_tools"] が空リストのとき、`_handle_query` は {"result": False, "error": ...} を返し、エラー文字列に "db_query" と "unavailable" を含む
    - Test 5 (handle dispatch): top-level `handle()` の QUERY 経路でも上記成功パスが job_store.save_result に正しい JSON を保存する
    - 既存テスト `test_is_select_only` は削除する（実装が MCP 側に集約されたため、本ファイルでは責務外）
  </behavior>
  <action>
    実装変更（app/jobs/handlers/iframe_rpc_handler.py）:

    1. `from psycopg.rows import dict_row` を削除
    2. `_COMMENT_RE`, `_ALLOWED_PREFIXES`, `is_select_only(sql)` 関数を削除
       - 監査結果より worker.py / app/ 配下の他コードからの参照はない
       - mcp_server/tools/db_query.py に同等実装が存在する（Phase 23 で複製済み）
    3. モジュール docstring の "is_select_only strips SQL comments..." の記述を MCP db_query 経由に書き換える
    4. `_handle_query(self, ctx, params)` を以下に差し替える:
       ```python
       async def _handle_query(self, ctx: dict, params: dict) -> dict:
           pool_name = params.get("pool_name", "")
           sql = params.get("sql", "")
           user = params.get("user", "")  # D-08: log for future RLS support
           logger.info("iframe-rpc QUERY user=%s pool=%s", user, pool_name)

           mcp_tools = ctx.get("mcp_tools") or []
           tool = next((t for t in mcp_tools if getattr(t, "name", None) == "db_query"), None)
           if tool is None:
               return {"result": False, "error": "db_query tool unavailable (MCP DEGRADED)"}

           try:
               out = await tool.ainvoke({"sql": sql, "pool_name": pool_name})
           except Exception as e:
               return {"result": False, "error": f"db_query invocation failed: {e}"}

           if not isinstance(out, dict):
               return {"result": False, "error": f"db_query returned unexpected type: {type(out).__name__}"}
           if "error" in out:
               return {"result": False, "error": out["error"]}
           return {"result": True, "rows": out.get("rows", [])}
       ```
    5. `_json_default` 関数は AI 経路でも使わなくなるので削除しても良い。ただし他で使われていなければ削除、確認できなければ残す（datetime/decimal import も合わせて評価）。`json.dumps(..., default=_json_default)` は handle() の save_result で使っており、MCP 戻り値は既に JSON シリアライズ済みだが、保険として残してよい。**結論: `_json_default` と datetime/decimal import は残す**（handle() の save_result 互換のため）。

    psycopg, psycopg_pool, dict_row への参照は完全になくなることをファイル全体検索で確認すること。

    テスト変更（tests/test_iframe_rpc_handler.py）:

    1. `from app.jobs.handlers.iframe_rpc_handler import IframeRpcHandler, is_select_only` を `from app.jobs.handlers.iframe_rpc_handler import IframeRpcHandler` に変更
    2. `test_is_select_only` パラメトリックテストブロック全体（L13-28）を削除
    3. `_make_ctx` ヘルパーを書き換える: db_pools の psycopg mock の代わりに、`ctx["mcp_tools"]` に AsyncMock(name="db_query") を入れる版にする。AsyncMock の `name` は属性として明示的に setattr する（コンストラクタ引数の name は別の意味を持つので注意）:
       ```python
       def _make_ctx(*, rows=None, error=None, no_tool=False):
           job_store = AsyncMock()
           job_store.save_result = AsyncMock()
           job_store.get = AsyncMock()

           if no_tool:
               return {"job_store": job_store, "mcp_tools": []}

           tool = AsyncMock()
           tool.name = "db_query"  # 属性として明示設定（コンストラクタの name は別物）
           if error is not None:
               tool.ainvoke = AsyncMock(return_value={"error": error})
           else:
               tool.ainvoke = AsyncMock(return_value={"rows": rows or [{"id": 1, "name": "test"}]})
           return {"job_store": job_store, "mcp_tools": [tool]}
       ```
    4. 既存の `_handle_query` テストを behavior 節の Test 1〜4 に対応する形で書き換える:
       - `test_handle_query_success`: rows=[{"id": 1, "name": "test"}]、`tool.ainvoke.assert_awaited_once_with({"sql": "SELECT * FROM users", "pool_name": "main"})` を含めて呼び出し検証
       - `test_handle_query_tool_error`: error="Only SELECT queries are allowed" → result False / error 文字列含む
       - `test_handle_query_unknown_pool`: error="Unknown pool: nonexistent" → result False / error 文字列含む
       - `test_handle_query_degraded`: no_tool=True → result False / error に "db_query" と "unavailable" を含む
    5. `test_handle_query_dispatch` (top-level handle()) を新 ctx ヘルパーに合わせて修正。`patch("app.jobs.handlers.iframe_rpc_handler.build_notifier", ...)` のパッチパスは変更不要。
    6. `test_handle_ai_*` 系テストはまったく触らない（DB 移行の対象外）
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph &amp;&amp; docker compose run --rm -T worker uv run pytest tests/test_iframe_rpc_handler.py -x -q</automated>
  </verify>
  <done>
    - tests/test_iframe_rpc_handler.py の全テストが pass する
    - `grep -n "psycopg\|dict_row\|is_select_only" app/jobs/handlers/iframe_rpc_handler.py` が 0 件
    - `grep -rn "from app.jobs.handlers.iframe_rpc_handler import.*is_select_only" app/ tests/` が 0 件
    - `_handle_query` が ctx["mcp_tools"] から db_query ツールを取得して `ainvoke({"sql":..., "pool_name":...})` を呼ぶ
    - DEGRADED ケース（mcp_tools 空）で明示的なエラー文字列を返す
  </done>
</task>

<task type="auto">
  <name>Task 2: 実機 smoke test — Canvas QUERY が MCP 経由で動作することを確認</name>
  <files></files>
  <action>
    Docker Compose 環境で iframe RPC QUERY が end-to-end で動くことを確認する。

    1. `docker compose up -d` で全サービス起動（既に起動中なら `docker compose restart worker mcp-server`）
    2. worker ログで MCP tools のロード成功を確認:
       ```bash
       docker compose logs worker --tail 200 | grep -E "MCP tools loaded|MCP client init"
       ```
       期待: `MCP tools loaded: ['...', 'db_query', '...']` のような行（DEGRADED でないこと）
    3. テストプール `default` が `mcp_server/config/db_pools.yaml`（または環境のもの）に存在することを確認:
       ```bash
       docker compose exec mcp-server cat /mcp_server/config/db_pools.yaml 2>/dev/null || docker compose exec mcp-server ls /mcp_server/config/
       ```
       存在しなければ smoke test step 4 はスキップしてよい（ユニットテスト pass で完了とみなす）
    4. （プールがある場合）curl で iframe RPC をエンキュー:
       - 既存の Canvas アプリ経由でブラウザ確認するか、もしくは worker のジョブを直接エンキューする方法は本クイックタスクの範囲外
       - 最低限の確認として、worker ログに "iframe-rpc QUERY" が以前と同様に出力され、エラーが出ていないことを確認する
    5. worker / mcp-server に新規エラーログが出ていないことを確認:
       ```bash
       docker compose logs worker mcp-server --tail 100 | grep -iE "error|exception|traceback" | grep -v "MCP client init failed"
       ```
       既知の DEGRADED 警告以外のエラーがないことを確認
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph &amp;&amp; docker compose logs worker --tail 200 2>/dev/null | grep -E "MCP tools loaded.*db_query" || echo "WARN: db_query not in MCP tools — verify manually"</automated>
  </verify>
  <done>
    - Worker 起動ログに `db_query` が MCP tools として含まれている（DEGRADED でない）
    - worker / mcp-server ログに新規エラーが出ていない
    - （プール設定が存在する場合）iframe-rpc QUERY ログ行が新実装でも出力される
  </done>
</task>

</tasks>

<verification>
- ユニットテスト: `tests/test_iframe_rpc_handler.py` 全 pass
- 静的検査: `iframe_rpc_handler.py` から psycopg / dict_row / is_select_only 参照が完全に消えている
- 結合: Docker Compose で worker が `db_query` を含む MCP tools をロード
- 既存挙動互換: `_handle_query` の戻り値スキーマ `{"result": bool, "rows"|"error": ...}` は不変
</verification>

<success_criteria>
- Canvas iframe からの QUERY が MCP db_query ツール経由で実行される
- iframe_rpc_handler.py に直接 DB アクセスコードが残っていない
- 既存テストが新実装に追従して全て pass
- worker.startup の db_pools 初期化コードはそのまま残っている（今回スコープ外）
- 既存の Canvas アプリ動作にデグレなし
</success_criteria>

<output>
After completion, create `.planning/quick/260414-hwa-canvas-iframe-rpc-handler-db-mcp-db-quer/260414-hwa-SUMMARY.md`
</output>
