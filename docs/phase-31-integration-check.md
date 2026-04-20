# Phase 31 Integration Check — 4 経路 end-to-end 検証ログ

> **実施日:** 2026-04-20
> **検証者:** Claude Opus 4.7 (1M context) via Claude Code
> **対象:** Phase 31 agent-mcp-observability の 4 経路 (Chat / SuperChat+web_search / CodeAct+execute_python / Canvas iframe_rpc)
> **結論:** **PASS** — must_haves m1–m10 すべて green、Wave 6 で surfaced した silent failure 3 件はいずれも同セッション内で修正・再検証済み。

---

## 目的

Plan 01–07 が実装した observability 基盤 (stdout JSONL + `trace_span` + `TracedTool` wrapper + 3 handler + trace_query CLI + schema cleanup + ADR) が、実 docker 環境で期待通り動作することを end-to-end で確認する。

Phase 31 の unit test (60/60 pass) だけでは Python `logging` の実設定や LangGraph checkpointer の state 永続化、arq worker の enqueue payload shape 整合性を検証できないため、本 integration check が必須。

---

## 環境

- `docker compose up -d` で api / worker / postgres / redis / mcp-server / frontend が Up
- Device Flow 認証済み (`docker compose exec worker ls /root/.copilot_sdk/token.enc` で確認)
- ブラウザで `http://localhost:5173/orochi/` にログイン済み
- VERSION: Phase 31 `f1a41f0`（fresh-trace reducer fix 適用後）→ `d9e0519`（correlation_id 修正後）

---

## 経路 1: Chat (LangGraph handler)

**操作:** Chat タブで任意のプロンプトを投稿。

**観察された trace:**
```
trace_id: ccc8e82e-2053-475c-8483-b23476f6b4ac
└── [OK   ] request    duration=12202ms trace=ccc8e82e user=6in app=chat model=gpt-4.1
```

**確認項目:**
- [x] `request` span が langgraph handler 境界で emit
- [x] `handler="langgraph"` / `agent_type="chatbot"` / `model_name="gpt-4.1"` が attributes に載る
- [x] `trace_id` が UUID4 形式、`span_id` 16-hex、ISO-8601 microseconds timestamp
- [x] `user_id` / `app_id` / `thread_id` 伝搬
- [x] `duration_ms=12202` でレイテンシ計測、`status_code="OK"`

---

## 経路 2: SuperChat + web_search (orchestrator → ToolEnabledSubAgent → TracedTool)

**操作:** SuperChat タブで `general-assistant` を選択し「東京の今日の天気を検索して教えて」を投稿。

**観察された trace:**
```
trace_id: 02fb4e0d-xxxx-xxxx-xxxx-xxxxxxxxxxxx
└── [OK   ] request (handler=orchestrator, app=superchat)          span=d35fa9a2
    ├── [OK   ] routing (chosen=general-assistant, stage=single)     parent=d35fa9a2
    └── [OK   ] sub_agent (agent=general-assistant, model=gpt-4.1)   parent=d35fa9a2  span=0ccbfd79
        └── [OK   ] tool_call (tool=web_search)                       parent=0ccbfd79
                     privileged=false
                     args_prefix='{"query": "東京 明日 天気"}'
                     result_bytes=4212
                     success=true
```

**確認項目:**
- [x] 4 層 span (request → routing → sub_agent → tool_call) が**同一 trace_id** で emit
- [x] `parent_span_id` による親子関係が正しく張られている (tree で ├── └── が正しく表示)
- [x] `tool_name="web_search"`, `privileged=false` (sandbox_exposed=true)
- [x] `args_prefix` / `result_prefix` が truncate 済み (TRACE_*_MAX_CHARS env 尊重)
- [x] `user_input_prefix` が routing span に 200 字以内で記録

---

## 経路 3: SuperChat + CodeAct (execute_python, privileged=true)

**操作:** SuperChat で `codeact` を選択し Python 実行を要するプロンプトを投稿。

**観察された trace:**
```
trace_id: 573ba43d-faa8-4fd6-99bd-1a243dd18516
└── [OK   ] request (handler=orchestrator, app=superchat)              span=883fe0fa
    ├── [OK   ] routing (chosen=codeact, stage=single)                  parent=883fe0fa
    └── [OK   ] sub_agent (agent=codeact, model=gpt-4.1)                parent=883fe0fa  span=9ebbe2ce
         │   usage tokens: input=23358, output=96, cache_read=0, cache_write=0
         ├── [ERROR] tool_call (tool=execute_python, privileged=True) ✗ parent=9ebbe2ce
         ├── [ERROR] tool_call (tool=execute_python, privileged=True) ✗ parent=9ebbe2ce
         ├── [ERROR] tool_call (tool=execute_python, privileged=True) ✗ parent=9ebbe2ce
         ├── [ERROR] tool_call (tool=execute_python, privileged=True) ✗ parent=9ebbe2ce
         └── [ERROR] tool_call (tool=execute_python, privileged=True) ✗ parent=9ebbe2ce
```

**確認項目:**
- [x] `privileged=True` が `execute_python` で記録 (sandbox_exposed=false → privileged 判定、ADR-0024 整合)
- [x] **sub_agent span に token usage 4 フィールド** (input/output/cache_read/cache_write) が載る (Plan 01 spike で決定した採用 attribute)
- [x] ERROR span (`status_code="ERROR"`, `status_message="exit_code=1"`, `success=False`) が記録
- [x] 5 回の retry loop が全部 tool_call span として parent=sub_agent で記録
- [x] すべての span が同一 trace_id を共有 (fresh-trace fix 確認)

**副次的発見 (Phase 31 scope 外):** `execute_python` の sandbox が `import platform` を Blocked imports 扱い。Phase 31 observability が「なぜ 5 回失敗したか」を `"error": "Blocked imports: ['platform']"` として構造化で記録 → 狙い通りの動作。

---

## 経路 4: Canvas iframe_rpc (db_query / ai)

**操作:** Canvas タブでデータ取得系のアプリを開き、`query()` / `ai()` を実行するボタンを押す。

**観察された trace（3 件）:**

### trace 4-1: db_query 成功
```
trace_id: 861c2a90-56e6-45f9-836f-459cca6236dc
└── [OK   ] request (handler=iframe_rpc, app=canvas, rpc_method=QUERY)  span=82f2a9f0
    └── [OK   ] tool_call (tool=db_query, privileged=False)              parent=82f2a9f0
                 args_prefix='{"sql": "SELECT current_timestamp AS now, version() AS pg_version", ...}'
                 result_bytes=201 ('{"rows": [{"now": "2026-04-20T06:57:19...", "pg_version": "PostgreSQL 17.9 ..."}]}')
                 row_count=1, success=true
```

### trace 4-2: ai 呼び出し成功
```
trace_id: b45f170b-4a97-44e7-8e16-fda28b5feb79
└── [OK   ] request (handler=iframe_rpc, app=canvas, rpc_method=AI)       span=c010501265cd44fc
    └── [OK   ] tool_call (tool=ai, model=claude-haiku-4-5-20251001)       parent=c010501265cd44fc
                 args_prefix='{"model": "claude-haiku-4-5-20251001", "prompt": "日本語で「テスト成功」と一言だけ答えてください"}'
                 result_prefix='テスト成功'
                 privileged=false, success=true, duration=9743ms
```

### trace 4-3: db_query security guard で拒否
```
trace_id: d2613930-ad9a-47de-9739-f50c834a5766
└── [OK   ] request (handler=iframe_rpc, app=canvas, rpc_method=QUERY)   span=db14789b657844fd
    └── [ERROR] tool_call (tool=db_query, privileged=False) ✗             parent=db14789b657844fd
                 args_prefix='{"sql": "INSERT INTO test_dummy VALUES (1)", "pool_name": "default"}'
                 result_prefix='{"error": "Only SELECT queries are allowed"}'
                 status_message="Only SELECT queries are allowed"
                 success=false
```

**確認項目:**
- [x] `handler="iframe_rpc"` が request span に記録
- [x] `app_id="canvas"` がすべての span に記録
- [x] `privileged=False` が db_query / ai で記録 (sandbox_exposed=true 経路)
- [x] `rpc_method` (QUERY / AI) が request span の attributes に記録
- [x] SQL injection / DDL 試行のような security guard 違反も構造化で span 化
- [x] 各 trace が独立した UUID4 trace_id を持つ (fresh per request)

---

## must_haves m1–m10 チェックリスト

| ID | 要件 | 結果 | 根拠 |
|----|------|------|------|
| m1 | `app/observability/trace.py` が `trace_span` / `SpanDict` を export | ✅ | `docker compose exec api uv run python3 -c "from app.observability.trace import trace_span, SpanDict"` 成功 |
| m2 | 軸 A の 3 層 span (request/routing → sub_agent → tool_call) が**同一 trace_id**で出力 | ✅ | 経路 2 trace `02fb4e0d` が完全 4 層 chain、parent_span_id / trace_id ともに一致 |
| m3 | 軸 B の 3 経路 (ToolEnabledSubAgent / CodeActSubAgent / iframe_rpc_handler) それぞれで tool_call 発行 | ✅ | 経路 2 (web_search) / 経路 3 (execute_python) / 経路 4 (db_query, ai) すべて捕捉 |
| m4 | `privileged=true` attribute が sandbox_exposed=false のツールで記録 | ✅ | 経路 3 の `execute_python` で `privileged=True`、経路 4 の `db_query` / `ai` で `privileged=False` (ADR-0024 の sandbox_exposed セットと整合) |
| m5 | `TRACE_ARGS_MAX_CHARS` / `TRACE_RESULT_MAX_CHARS` が尊重される | ✅ | unit test (tests/test_trace.py / tests/test_traced_tool.py) で確認、実 env では `args_prefix` / `result_prefix` が truncate される動作を span で観察 |
| m6 | `user_input_prefix` / `llm_output_prefix` が 200 字 prefix で記録 | ✅ | routing span の `user_input_prefix` が 200 字以内 (経路 2 / 3 で確認) |
| m7 | `scripts/trace_query.py --trace-id XXX --format tree` が親子関係を表示 | ✅ | `trace_query.py` が docker logs の `api-1  \| ` prefix を strip して parent_span_id ベースで ASCII tree を描画 |
| m8 | `app/api/main.py` に `audit_log` 文字列が残らない | ✅ | `! grep -q audit_log app/api/main.py` pass (Plan 07 で DDL 純粋削除済み、開発 DB でも DROP 済み) |
| m9 | `docs/trace-query-recipes.md` と `docs/phase-31-reasoning-token-spike.md` が存在 | ✅ | Plan 06 / Plan 01 で生成 |
| m10 | `docs/adr/0045-*.md` が作成され `.planning/patterns.md` に追記 | ✅ | Plan 07 で ADR-0045 新規作成、patterns.md に 2 エントリ追加済み |

**10 / 10 green.**

---

## Wave 6 で surfaced した silent failure 3 件

Phase 31 の unit test はすべて pass していたが、実環境では以下 3 件が**沈黙していた**。integration check で初めて surfaced。

### Bug 1: `trace` logger が silent failure

**症状:** 経路 1 の Chat を実行しても trace span JSON が docker logs に 1 件も出力されない。

**根本原因:** `app/observability/trace.py` が `logging.getLogger("trace")` を取得して `logger.info(json.dumps(...))` で emit する設計だが、Python logging のデフォルト root level は WARNING + handler 空。アプリのどこにも `logging.basicConfig(level=INFO)` / StreamHandler 追加がなく、INFO レベルの trace span log は **root に propagate されても WARNING 未満なので黙って捨てられていた**。

**unit test がすり抜けた理由:** pytest の `caplog` fixture が内部で `caplog.set_level(logging.INFO, logger="trace")` を呼んでおり、テスト文脈でのみ INFO 出力が有効化されていた。本番環境での root logger 設定は未考慮。

**修正:** `app/observability/trace.py` 初回 import 時に `_configure_trace_logger()` で stdout StreamHandler (INFO, `"%(message)s"` formatter) を attach する self-bootstrap を追加。idempotent で trace logger にのみ影響し、root/uvicorn/arq logger は無変更。propagate は True のままで pytest caplog との互換性維持。

**commit:** `1ade308`

### Bug 2: `_keep_first` reducer で trace_id が stale 化

**症状:** 修正 1 の後、経路 2 で `request` span は fresh trace_id を持つが child span (`routing` / `sub_agent` / `tool_call`) が**前リクエストの trace_id**を引き継ぐ。parent_span_id チェーンは正しいが trace_id 伝搬が壊れている。

**根本原因:** `app/orchestrator/state.py` の `AgentState.context` フィールドが `_keep_first` reducer を使用。LangGraph の `AsyncPostgresSaver` が state を thread_id 単位で checkpoint しており、同じ thread で新リクエストを投げると checkpointer が**前回の RPCContext**を復元。reducer `return a if a is not None else b` が「first wins」セマンティックなので、handler が渡す新しい context (`correlation_id=fresh`) が無視されて stale context がノードに流れていた。

**影響:** 軸 A (graph.py の RouterNode / agent.py の SubAgent / traced_tool.py の TracedTool) が `state.context.correlation_id` を trace_id 源として使っていたため、すべての child span が stale trace_id を emit。

**unit test がすり抜けた理由:** `test_context_immutable_via_reducer` が「reducer がノードの context 上書きを拒否する」という invariant をテストしていて、同じ thread_id での再 invoke 時の挙動を未考慮だった。unit test は checkpointer なしで StateGraph を単発実行していたため、checkpointer 経由の state 復元パスを検証していなかった。

**修正:** reducer を `return b if b is not None else a`（= last-wins + None guard）に反転。実コードで `context` を返すノードは handler 初期化時のみ (`orchestrator_handler.py:196`, `debate_graph.py:75`) のため、ノード跨ぎ保護の崩壊はなし。関連 unit test 2 件を新しい semantics に更新 (`test_keep_first_prefers_new_value`, `test_context_fresh_value_wins_over_stale`) + None-guard 用テスト `test_keep_first_none_second_arg_preserves_existing` を新規追加。

**commit:** `f1a41f0`

### Bug 3: `process_chat()` が `correlation_id` kwarg を受け取れず Canvas 完全停止

**症状:** 経路 4 で Canvas アプリの `query()` / `ai()` 呼び出しが 30 秒後に `RPC timeout: QUERY` でエラー。ブラウザ側は応答が返って来ない状態。

**根本原因:** Plan 05 が `app/api/routes/iframe_rpc.py` で `correlation_id=str(uuid.uuid4())` を生成して arq enqueue の kwarg に追加したが、arq job function `process_chat()` (`app/jobs/worker.py`) のシグネチャは未更新。every enqueued job が `TypeError: process_chat() got an unexpected keyword argument 'correlation_id'` で即死し、handler は一度も呼ばれない。結果、JobStore に result が書き込まれず、SSE stream も空のままクライアント側の 30s タイムアウトが発火。

**unit test がすり抜けた理由:** `tests/test_iframe_rpc_trace.py` は handler を直接呼び出して span emit を検証していたため、arq enqueue → worker dispatch の経路を踏んでいなかった。`process_chat` の signature 整合性を検証する契約テストがなかった。

**修正:** `process_chat()` シグネチャに `correlation_id: str | None = None` を追加し、job dict に `"correlation_id": correlation_id` を載せて forward。iframe_rpc_handler は既に `job.get("correlation_id")` を読む実装 (Plan 05)、他の handler は自前で RPCContext を作るので本フィールドを無視。

**commit:** `d9e0519`

---

## 学び (retrospective)

1. **Unit test の green ≠ 実環境で動く**: Python logging / LangGraph checkpointer / arq enqueue payload のような**副作用系**は unit test でカバーされづらい。integration check が「silent に壊れてる機能」を surface する最後の砦。
2. **Observability の仕組み自体の稼働確認が最初のステップ**: logger 設定のような基礎レイヤが壊れていると、その上の全ての trace ロジックが無言で死ぬ。Phase 31 の init 時に `logger.info("phase-31 observability: configured")` のような self-check log を出しておくと 1 分で気づけた。
3. **複数層にわたる contract は接点でテストを書く**: route → arq enqueue → worker → handler の **シグネチャ整合性**を検証するテスト (contract test) がなかったため Bug 3 をすり抜けた。`tests/test_worker_contracts.py` 相当を今後追加する価値あり。
4. **LangGraph checkpointer は state 全体を復元する**: `context` のようなリクエスト毎に fresh であるべきフィールドは、reducer 側で明示的に last-wins にするか、checkpointer の scope から外す (ephemeral field) 設計が必要。

これら 4 点を ADR-0046 に記録 (次タスク)。

---

## 結論: **PASS**

- 4 経路すべてで Phase 31 observability の trace span が期待通り emit される
- must_haves m1–m10 すべて green
- Wave 6 で surfaced した silent failure 3 件はいずれも同セッション内で修正・再検証済み
- unit test 71 / 71 green、Phase 31 focused 60 / 60 green

**Phase 31 は功能的に完了**。残作業は GSD bookkeeping (SUMMARY.md / VALIDATION.md / VERIFICATION.md / ROADMAP completion / ADR-0046) のみ。
