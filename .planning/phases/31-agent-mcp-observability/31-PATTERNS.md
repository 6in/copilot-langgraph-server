# Phase 31: agent-mcp-observability - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 13 (新規 9 + 修正 6、部分重複除き)
**Analogs found:** 12 / 13

## File Classification

### 新規作成ファイル

| 新規ファイル | Role | Data flow | 最近接アナログ | Match |
|--------------|------|-----------|---------------|-------|
| `app/observability/__init__.py` | package-init | — | `app/auth/__init__.py` (空に近い pkg init) | exact |
| `app/observability/trace.py` | writer (core infra) | event-driven emit + ContextVar 伝搬 | `app/orchestrator/tool_context.py` (ContextVar) + `app/orchestrator/graph.py:47-101` (JSON line emit) | role-match (複合) |
| `app/observability/traced_tool.py` | wrapper (BaseTool delegate) | request-response around tool.ainvoke | `app/orchestrator/tool_agent.py` 内の `_build_rich_output` + LangChain `BaseTool` 継承一般 | partial (プロジェクト内に BaseTool サブクラスはなし) |
| `scripts/trace_query.py` | CLI | file-I/O (stdin JSONL filter) | `scripts/generate_adr_index.py` (stdlib argparse-less) / `scripts/generate_mcp_artifacts.py` (argparse full) | role-match |
| `docs/trace-query-recipes.md` | docs (recipe collection) | static | `docs/mcp-tool-add-manual.md` (手書き手順書) / `docs/nginx.md` (操作レシピ) | exact |
| `docs/phase-31-reasoning-token-spike.md` | docs (spike writeup) | static | `docs/phase-14.md` (phase-specific writeup 過去事例) | role-match |
| `tests/test_trace.py` | test (unit, pure) | assertion | `tests/test_generate_adr_index.py` (stdlib のみ unit test) / `tests/test_rpc_context.py` (dataclass + ContextVar 近縁) | role-match |
| `tests/test_traced_tool.py` | test (unit, async) | assertion | `tests/test_copilot_bind_tools.py` (tool 関連 async unit) | role-match |
| `tests/test_sub_agent_trace.py` | test (integration, async) | assertion w/ Copilot mock | `tests/test_react_e2e.py` (ReAct + Copilot mock end-to-end) | role-match |

### 修正ファイル

| 修正ファイル | Role | Data flow | Integration point | Match |
|--------------|------|-----------|-------------------|-------|
| `app/orchestrator/graph.py` | integration (router) | event-driven span | 既存 `logger.info(json.dumps({...}))` L47/61/86/93 → `trace_span("routing")` に置換 | **exact (self-analog)** |
| `app/orchestrator/tool_agent.py` | integration (sub_agent + ToolNode wrap) | request-response | `ToolEnabledSubAgent.__init__` L252 で `ToolNode(tools)` → `ToolNode([TracedTool(t) for t in tools])`。`run()` L285-339 全体を `trace_span("sub_agent")` で囲む | exact |
| `app/orchestrator/codeact_agent.py` | integration (sub_agent + execute_python) | request-response | `run()` L152-256 を `trace_span("sub_agent")` で囲む + L200 `execute_python.ainvoke` 周囲に `trace_span("tool_call")` | exact |
| `app/jobs/handlers/iframe_rpc_handler.py` | integration (tool_call emit) | request-response | `_handle_query` L128 `tool.ainvoke` + `_handle_ai` L175 `llm.ainvoke` 周囲を `trace_span("tool_call")` で囲む。RPCContext 整備の有無を確認 | exact |
| `mcp_server/tools/mcp_helper_utils.py` | integration (sandbox → MCP HTTP call) | request-response | `_call_tool` L24-43 の urllib 呼び出し周囲に薄い trace (アプローチ 2 保留枠) | partial (Research §3.2 で deferred 判断) |
| `app/api/main.py` | integration (DDL 削除) | startup schema | lifespan L105-124 の `CREATE TABLE audit_log` + INDEX 除去。L52 のコメント修正 | exact |
| `tests/conftest.py` | fixture 追加 | pytest fixture | 既存 fixtures (L8-55) と同じ書式で `capture_trace_logs` 追加 | exact |

## Pattern Assignments

### `app/observability/trace.py` (writer, event-driven)

**Primary analog 1:** `app/orchestrator/tool_context.py` — ContextVar 定義パターン
**Primary analog 2:** `app/orchestrator/graph.py` L47-101 — structured JSON log line emit
**Primary analog 3:** `app/orchestrator/context.py` — `@dataclass(frozen=True)` + `field(default_factory=...)` パターン

**ContextVar 定義パターン** (analog: `tool_context.py:1-8`):

```python
"""ツール実行イベントを非同期コンテキスト経由で伝播させる ContextVar ヘルパー。"""
from contextvars import ContextVar
from typing import Awaitable, Callable, Optional

ToolEventCallback = Callable[[str, str], Awaitable[None]]
# args: (tool_name, query)
tool_event_cb: ContextVar[Optional[ToolEventCallback]] = ContextVar('tool_event_cb', default=None)
```

**流用方針:**
- 同じ宣言形式で `_current_span_id: ContextVar[str | None] = ContextVar("_current_span_id", default=None)` を module-level に置く
- `_current_trace_id` も並列に定義
- 1 ファイルに閉じ込めるのは同じだが、context manager との組み合わせは `trace.py` で新規追加（`tool_context.py` の domain knowledge は「ContextVar が async 文脈で確実に伝搬する」という [VERIFIED] の事実のみ流用）

**既存 JSON 構造化ログパターン** (analog: `graph.py:47-55`):

```python
logger.info(json.dumps({
    "event": "routing",
    "input": state["input"][:80],
    "chosen": chosen,
    "candidates": [a.name for a in agents],
    "stage": "keyword",
    "thread_id": context.thread_id if context else "",
    "correlation_id": context.correlation_id if context else "",
}))
```

**流用方針:**
- `logger.info(json.dumps(...))` の **1 行 1 JSON の形は維持する**（docker logs stdout → jq パイプを破壊しない）
- `ensure_ascii=False` を追加（日本語 user_input_prefix のため、既存は未指定だが span schema では明示）
- `default=str` を追加（`datetime` / `Decimal` を安全にシリアライズ — `iframe_rpc_handler.py:67-73 _json_default` と同等の役割を stdlib に寄せる）
- 旧 `"event"` キーは残さず、新 schema の `"operation_name"` / `"trace_id"` / `"span_id"` / `"parent_span_id"` / `"start_time"` / `"end_time"` / `"duration_ms"` / `"attributes"` / `"status_code"` / `"status_message"` に全置換（CONTEXT.md specifics で互換 alias 禁止）

**dataclass + default_factory パターン** (analog: `context.py:20-34`):

```python
@dataclass(frozen=True)
class RPCContext:
    user_id: str
    app_id: str = ""
    thread_id: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

**流用方針:**
- `SpanDict` は **frozen にはしない**（context manager 内で `attributes` を set_attribute で成長させるため）
- `uuid4().hex[:16]` (16-char) を span_id 用ジェネレータとして使う（OTEL spec 準拠、`correlation_id` の full UUID4 と区別）
- `@dataclass` + `asdict()` → `json.dumps(default=str)` のチェーンは stdlib のみで完結（`opentelemetry-sdk` 不要、D-05）

**Error handling パターン** (context manager 内の finally):
- `try/except Exception as e: status_code="ERROR"; raise` で「例外は飲まず、status だけ記録して再送出」
- `finally:` で `_current_span_id.reset(token)` と `logger.info` emit を必ず実行
- 外側の `try/except Exception: logger.exception("trace_span emit failed")` で emit 自体が失敗しても caller を止めない（Landmine 6）

---

### `app/observability/traced_tool.py` (wrapper, request-response)

**Primary analog:** `app/orchestrator/tool_agent.py` — ToolEnabledSubAgent による `ToolNode(tools)` 構築パターン
**Secondary analog:** LangChain `BaseTool` (`langchain_core.tools.BaseTool`) は外部ライブラリ定義 — 本プロジェクト内に BaseTool サブクラスは**なし**。`langchain-mcp-adapters` 由来の BaseTool インスタンスを wrap する形が Phase 31 の新規パターン

**参考すべき既存 wrapping パターン** (analog: `graph.py:112-128` `_wrap_agent_run`):

```python
def _wrap_agent_run(agent):
    """Wrap agent.run to ensure AIMessage.name is set after SubAgent returns."""
    async def wrapped(state: AgentState) -> AgentState:
        result = await agent.run(state)
        raw_messages = result.get("messages", [])
        fixed = [
            AIMessage(content=m.content, name=agent.name)
            if isinstance(m, AIMessage) and not m.name else m
            for m in raw_messages
        ]
        return {**result, "messages": fixed}
    return wrapped
```

**流用方針:**
- **デコレータ関数ではなくクラス wrapping を選ぶ**: `_wrap_agent_run` は async 関数の wrapping だが、`TracedTool` は `BaseTool` のインターフェース (`name`, `description`, `args_schema`, `_arun`, `_run`) すべてを持つ必要があるためクラス継承の方が素直
- **wrap 対象の属性を素通しにする**: `self.name = wrapped.name` / `self.description = wrapped.description` / `self.args_schema = wrapped.args_schema` を `__init__` で転送（`graph.py:123` の `name=agent.name` 転送と同発想）
- **エラー時は raise し、status だけ記録**: `_wrap_agent_run` は例外を飲まないので `TracedTool._arun` も同じ。`trace_span` の `finally` で status が記録される

**既存 tool 実行位置** (analog: `tool_agent.py:252`):

```python
self._tool_node = ToolNode(tools)
self._llm_with_tools = self._llm.bind_tools(tools)
```

**流用方針:**
- **`__init__` の `ToolNode(tools)` 構築前に tools を wrap**: `wrapped = [TracedTool(t, ...) for t in tools]; self._tool_node = ToolNode(wrapped)` とする
- `self._llm_with_tools = self._llm.bind_tools(tools)` は**元の tools のまま**使う（LLM に渡す tool schema は wrap 不要、`TracedTool` の .name / .description が wrapped.* を返すのでどちらでも良いが、schema 生成が `args_schema` 経由なら wrap 前の方が安全）
- `trace_id` と `common_attrs` は agent の `run()` 実行時に state から取れるので、**`TracedTool` には state-aware な getter を渡す** (例: `trace_id_getter=lambda state: state["context"].correlation_id`) か、ContextVar 経由で参照する設計を選ぶ。後者の方が ToolNode 内で `state` が一度 split される罠（Landmine 8）を回避できる

**result error 判定パターン** (analog: `iframe_rpc_handler.py:146-149`):

```python
if not isinstance(out, dict):
    return {"result": False, "error": f"db_query returned unexpected type: {type(out).__name__}"}
if "error" in out:
    return {"result": False, "error": out["error"]}
```

**流用方針:**
- **`isinstance(result, dict) and "error" in result` で tool の error を判定する**: Phase 31 の span.success / span.status_code の自動判定ロジックとして同じ条件を使う（プロジェクト規約として既に `_call_tool` / iframe_rpc で採用されている）

---

### `app/observability/__init__.py`

**Analog:** `app/auth/__init__.py` (既存、おそらく空 or ごく短い)

**流用方針:**
- 外部から使うエクスポートを `__all__` で限定: `trace_span`, `SpanDict`, `emit_span` (もし補助関数を提供するなら) / `TracedTool`
- `from app.observability.trace import trace_span` のように module path で直接参照することを許容し、`__init__.py` は空寄りにする（既存 `app/orchestrator/__init__.py` の方針に合わせる）

---

### `app/orchestrator/graph.py` 修正 (integration point, routing)

**Self-analog:** 自身の既存 `logger.info(json.dumps({...}))` ブロック 4 箇所 (L47, L61, L86, L93)

**現行実装** (`graph.py:45-102`):

```python
if len(keyword_matches) == 1:
    chosen = keyword_matches[0].name
    logger.info(json.dumps({
        "event": "routing",
        "input": state["input"][:80],
        "chosen": chosen,
        "candidates": [a.name for a in agents],
        "stage": "keyword",
        "thread_id": context.thread_id if context else "",
        "correlation_id": context.correlation_id if context else "",
    }))
    return {"next": chosen}
```

**流用方針 (新 schema への置換):**

- `logger.info(json.dumps({"event": "routing", ...}))` の代わりに `async with trace_span("routing", trace_id=context.correlation_id, attributes={...}) as span:` で囲む
- `stage` / `chosen` / `candidates` は `attributes` dict に入れる（span schema の attributes フィールド直下）
- `input` 先頭 80 文字は `attributes.user_input_prefix` に rename（D-13 の 200 字 prefix ルールと整合 — 80 → 200 に拡大するのは plan 時判断）
- `thread_id` は `attributes.thread_id`、`user_id` / `app_id` / `agent_name` も context から取れる 4 共通 attribute を `attributes` に載せる (D-09)
- `routing_fallback` の warning (L86-90) は `status_code="ERROR"` + `status_message=f"unknown_agent={chosen}"` + `attributes.stage="llm"` + `attributes.fallback=True` で表現 (RESEARCH §9.2)
- **互換 alias は残さない** (CONTEXT.md specifics 明示)

**3 箇所の routing log を 1 箇所に統合するリファクタ:**

```python
# 修正イメージ (RESEARCH §9.3 Task B)
async def __call__(self, state: AgentState) -> AgentState:
    context = state.get("context")
    trace_id = context.correlation_id if context else ""
    common_attrs = {
        "user_id": context.user_id if context else "unknown",
        "app_id": context.app_id if context else "",
        "thread_id": context.thread_id if context else "",
        "user_input_prefix": state["input"][:200],
        "candidates": [a.name for a in agents],
    }
    async with trace_span("routing", trace_id=trace_id, attributes=common_attrs) as span:
        # stage 判定ロジックで chosen を決定し、span.set_attribute("stage", ...) / ("chosen", ...)
        ...
        span.set_attribute("stage", "keyword")
        span.set_attribute("chosen", chosen)
        return {"next": chosen}
```

**流用時の注意:**
- 現行コードは `context` が None (legacy thread) の場合にも動く設計 (`context.thread_id if context else ""`) — Phase 31 でも同じ defensive pattern を維持する
- `state["input"][:80]` の 80 字は現行値。D-13 の 200 字ルールに合わせるなら plan 時に 200 へ拡張するか、operations attribute としてどちらを採用するか決める

---

### `app/orchestrator/tool_agent.py` 修正 (integration, sub_agent + tool_call)

**Self-analog:** 自身の `ToolEnabledSubAgent.run()` L285-339 + `__init__` L229-253

**現行の tools 構築** (`tool_agent.py:246-253`):

```python
self._tools = tools
if not tools:
    logger.warning("[tool-agent] '%s' initialized with empty tools list", name,)
self._tool_node = ToolNode(tools)
self._llm_with_tools = self._llm.bind_tools(tools)
```

**流用方針:**
- **`ToolNode(tools)` の引数を wrap 済みに差し替え**: `wrapped_tools = [TracedTool(t, common_attrs_getter=lambda s: {...}) for t in tools]; self._tool_node = ToolNode(wrapped_tools)`
- `self._llm.bind_tools(tools)` は **wrap 前の tools を渡す**（LLM に見せる schema は元ツールのもの、TracedTool は実行時 only）
- `__init__` の段階では state/ctx にアクセスできないので、TracedTool は **ContextVar 参照型** にする or **run() 実行時に毎回 TracedTool を再生成する** の 2 択。ContextVar 経由の方がオーバーヘッドがなく推奨

**現行の run() 先頭** (`tool_agent.py:285-314`):

```python
async def run(self, state: AgentState) -> AgentState:
    mini_graph = build_react_graph(...)
    context = state.get("context")
    user_id = context.user_id if context and getattr(context, "user_id", None) not in (None, "unknown") else None
    system_prompt = build_system_prompt_prefix(user_id) + "\n\n" + self._system_prompt
    ...
    try:
        result = await mini_graph.ainvoke(...)
        all_messages: list[BaseMessage] = result["messages"]
    except GraphRecursionError:
        ...
```

**流用方針:**
- **`run()` 全体を `async with trace_span("sub_agent", ...)` で囲む**: 先頭で `trace_id = context.correlation_id if context else ""` を取得し、attributes に `agent_name=self.name`, `model_name=self._llm.model`, `user_id`, `app_id` を入れる
- **`GraphRecursionError` 捕捉時は span.set_status("ERROR", "recursion_limit_reached")** + `span.set_attribute("recursion_limit_reached", True)` を記録する（既存の `logger.warning` もそのまま残すか、新 span で統合するか plan 時判断）
- **turn_count / iterations** を記録する場合は、`build_react_graph` の agent_node が呼ばれた回数を数える必要がある。最小侵襲で `len(all_messages)` を代理指標として `span.set_attribute("message_count", ...)` に載せる手もある (D-06: 各 turn は独立 span にしない)

**流用時の注意:**
- `context.user_id not in (None, "unknown")` の 3 値判定 (None / "unknown" / その他) は既存パターン — span attribute でも同じ値に倒す
- 既存 tool_event_cb コールバック (L138-148) は UI 進捗通知なので**残す**。trace_span とは独立の責務

---

### `app/orchestrator/codeact_agent.py` 修正 (integration, sub_agent + tool_call)

**Self-analog:** 自身の `run()` L152-256、特に L199-205 の `execute_python.ainvoke` 呼び出し

**現行の execute_python 呼び出し** (`codeact_agent.py:199-205`):

```python
try:
    result = await execute_python.ainvoke({"code": code})
    raw_result = _normalize_tool_result(result)
except Exception as e:
    raw_result = json.dumps({"stdout": "", "stderr": str(e), "exit_code": -1})

stdout, stderr, exit_code = _parse_execute_result(raw_result)
```

**流用方針:**
- **run() 全体を `trace_span("sub_agent")` で囲む** (tool_agent と同じ)
- **L200 の `execute_python.ainvoke({"code": code})` を `trace_span("tool_call", tool_name="execute_python", privileged=True)` で囲む**
- **`try/except Exception as e:` の中は現行維持**: 例外時は `raw_result = json.dumps({"stderr": str(e), "exit_code": -1})` で継続するので、span 側は `span.set_status("ERROR", str(e)[:200])` を try の except 節で明示呼び出す（`trace_span` の自動 except 検出は `raise` する場合のみ動くため、飲まれる例外は手動で set_status する必要がある）
- **`exit_code != 0` なら `span.set_status("ERROR", f"exit_code={exit_code}")` + `span.set_attribute("success", False)`**: `_parse_execute_result(raw_result)` の結果を見て判定
- **result_bytes / result_prefix は `raw_result` (normalize 後) の byte 数で記録** (Research §11.9 判断)

**流用時の注意:**
- `execute_python` は `tools = {t.name: t for t in tools}` (L124) で dict 管理されている — `self._tools.get("execute_python")` は L159 で既に実装されている defensive pattern を維持
- `iteration` ループ (L180) が複数回回ると複数の `tool_call` span が emit される (正しい挙動、ReAct の 1 ターン = 1 span は D-06 と整合)
- 現行の `logger.info("[codeact] %s: iteration %d", ...)` (L181) はフリーテキストログ — **残すか span attribute に吸収するか plan 時判断**（recipe で検索しやすいので残す寄り）

---

### `app/jobs/handlers/iframe_rpc_handler.py` 修正 (integration, tool_call)

**Self-analog:** 自身の `_handle_query` L103-150、`_handle_ai` L152-178

**現行の _handle_query** (`iframe_rpc_handler.py:117-128`):

```python
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
```

**流用方針:**
- **`_handle_query` の `tool.ainvoke` 周囲に `trace_span("tool_call", tool_name="db_query")` を追加**
- **handle() 最上位に `trace_span("request", trace_id=ctx.correlation_id)` を追加** (RESEARCH §4.4 推奨)
- `handle()` の `job` dict から `correlation_id` / `user_id` / `app_id="canvas"` / `thread_id` を抽出 — **Research §11.7/3.3 で「iframe_rpc 経路の RPCContext が job に載っているか未確認」と警告されているので plan Task G 冒頭で `app/api/routes/iframe_rpc.py` を読んで確認必要**。未整備なら job 構築側 (route) で `correlation_id = str(uuid.uuid4())` を付与する小タスクを同 plan 内に含める
- `privileged=False` を span attribute に (db_query は `sandbox_exposed: true` なので非特権)
- 既存の fre text `logger.info("iframe-rpc QUERY user=%s pool=%s", ...)` (L120) は**残すか span に統合するか plan 時判断**。Research のアンチパターンに「フリーテキストログは残さない」とあるが、現行は情報量が少ないので span に吸収して削除して良い

**_handle_ai の方針:**
- L175 `result = await llm.ainvoke([HumanMessage(content=prompt)])` 周囲を `trace_span("tool_call", tool_name="ai", model_name=model)` で囲む（または `trace_span("sub_agent")` の 1 層扱いでも良い — plan 時判断）

**流用時の注意:**
- `_handle_query` は dict を return する形式 (`{"result": False, "error": ...}`)、tool のエラー状態 (`if "error" in out:` L148) を span.set_status("ERROR", ...) に反映する。ここは既存 error-dict 判定パターンをそのまま流用

---

### `mcp_server/tools/mcp_helper_utils.py` 修正 (integration, partial)

**Self-analog:** `_call_tool` L24-43

**現行実装:**

```python
def _call_tool(name: str, args: dict | None = None) -> dict:
    payload = json.dumps({"tool": name, "args": args or {}}).encode("utf-8")
    req = urllib.request.Request(_INTERNAL_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("result", body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {"error": str(e)}
```

**流用方針 (Phase 31 での扱い):**
- **Research §3.2 で「sandbox → MCP 内部呼び出しの個別 span 化は deferred」と判断されている** (Deferred Ideas に追加)
- Phase 31 では `_call_tool` は**変更しない**可能性が高い。ただし plan Task F (CodeAct の execute_python 周りの span) で sandbox 内部ログを取りたいなら、ここに薄い trace 足跡を残す選択肢もある
- 注意: `mcp_helper_utils.py` は sandbox 内 (subprocess) で実行される → `app.observability.trace` は import できない (sandbox は app 依存を持たない、`mcp_helper.py` は自動生成)。span emit は **CodeActSubAgent 側からまとめて 1 span** に寄せる設計が妥当

**流用時の注意:**
- このファイルは **sandbox 実行環境** (execute_python の subprocess) で動くため、`app.observability` module を import 不可
- span 発行を強行するなら、結果 dict に `_trace` key を潜ませて CodeActSubAgent 側で展開する「out-of-band channel」方式が必要 — これは Phase 31 のスコープ外に倒す

---

### `app/api/main.py` 修正 (DDL 削除)

**Self-analog:** 自身の lifespan L105-124 (audit_log DDL + INDEX)

**削除対象** (`app/api/main.py:52, 105-124`):

```python
# L52 コメント: # (applications, threads, audit_log).
# L105-116 CREATE TABLE
await conn.execute(
    """CREATE TABLE IF NOT EXISTS audit_log (
           id           BIGSERIAL PRIMARY KEY,
           github_login TEXT NOT NULL,
           app_id       TEXT REFERENCES applications(app_id),
           thread_id    TEXT,
           action       TEXT NOT NULL,
           metadata     JSONB,
           created_at   TIMESTAMPTZ DEFAULT now()
       )"""
)
# L118-124 INDEX
await conn.execute(
    "CREATE INDEX IF NOT EXISTS audit_log_github_login_idx ON audit_log(github_login)"
)
await conn.execute(
    "CREATE INDEX IF NOT EXISTS audit_log_created_at_idx ON audit_log(created_at)"
)
```

**流用方針:**
- **純粋削除のみ**: `await conn.execute(...)` ブロックを削除し、L52 コメントから `, audit_log` 部を削除 (`(applications, threads)` に変更)
- 他の DDL (applications / threads / gems / canvas_apps) は**保持**
- 既存 volume の DROP TABLE は別途 SQL 実行を運用者に委ねる (CONTEXT.md D-02、Research §8.3 Approach C)
- `tests/test_api_chat.py:100` のコメント `# Phase 10: ... applications/threads/audit_log` もコメントからの audit_log 言及を消す対応は任意 (実コードには影響なし)

**流用時の注意:**
- `audit_log` の FK `REFERENCES applications(app_id)` は**純削除で問題なし**（applications 側には影響ゼロ、CASCADE 不要、Research §8.3）
- docs/SUMMARY に運用者向け SQL `DROP TABLE IF EXISTS audit_log CASCADE;` を明記する Plan Task を含める

---

### `tests/conftest.py` 修正 (fixture 追加)

**Self-analog:** 既存 fixtures L8-64

**現行の fixture パターン** (`conftest.py:21-28`):

```python
@pytest.fixture
def mock_graph():
    """Mock compiled LangGraph graph that returns a fixed AI reply."""
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(return_value={
        "messages": [MagicMock(content="Hello from AI")]
    })
    return graph
```

**流用方針 (capture_trace_logs fixture 追加):**

```python
@pytest.fixture
def capture_trace_logs(caplog):
    """Capture 'trace' logger JSON lines as parsed dicts.

    Usage:
        async def test_foo(capture_trace_logs):
            ...
            spans = capture_trace_logs()
            assert any(s["operation_name"] == "tool_call" for s in spans)
    """
    import json, logging
    caplog.set_level(logging.INFO, logger="trace")

    def _get_spans() -> list[dict]:
        spans = []
        for record in caplog.records:
            if record.name != "trace":
                continue
            try:
                spans.append(json.loads(record.getMessage()))
            except (json.JSONDecodeError, TypeError):
                continue
        return spans

    return _get_spans
```

**流用方針の詳細:**
- **既存の `caplog.at_level(logging.INFO, logger="app.orchestrator.graph")` + `json.loads(record.getMessage())` パターン** (`tests/test_routing_keyword.py:57-61, 65-70`) をそのまま基盤にする
- **closure で spans を返す callable として返す** (fixture の遅延評価): test 本体で span 発行処理を呼んだ**後**に `capture_trace_logs()` で拾える。これにより setup-teardown 順序に悩まない
- **logger 名は `"trace"` で固定** (RESEARCH §2.1 の `logger = logging.getLogger("trace")` と一致させる)

---

### `scripts/trace_query.py` (CLI)

**Primary analog:** `scripts/generate_mcp_artifacts.py` (argparse + sub-target パターン、200 行超の CLI)
**Secondary analog:** `scripts/generate_adr_index.py` (stdlib のみ、shebang + main() return int パターン)

**shebang + sys.exit(main()) パターン** (analog: `generate_adr_index.py:1-3, 99-108`):

```python
#!/usr/bin/env python3
"""docs/adr/INDEX.md を .planning/adr-categories.yaml に基づいて自動生成する。"""
from __future__ import annotations
...
def main() -> int:
    ...
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**argparse + 複数フラグパターン** (analog: `generate_mcp_artifacts.py:1-20` の module docstring + argparse 後半):

```python
"""MCP ツールカタログ用アーティファクト決定論ジェネレータ。

実行例:
    python3 scripts/generate_mcp_artifacts.py --target helper
    python3 scripts/generate_mcp_artifacts.py --target all
    python3 scripts/generate_mcp_artifacts.py --check
"""
...
import argparse
```

**流用方針:**
- **shebang + module docstring に実行例** の形を踏襲 (RESEARCH §6.1 の CLI 使用例を docstring にコピーする)
- **`argparse.ArgumentParser` で複数フラグを定義**: `--trace-id`, `--user`, `--app`, `--agent`, `--tool`, `--status`, `--operation`, `--since`, `--until`, `--privileged`, `--min-duration-ms`, `--format`, `-f/--follow`, `--max`
- **stdin から JSONL を読む**: `for line in sys.stdin: ...` (RESEARCH §6.3 の実装スケッチをそのまま採用)
- **docker logs prefix (`"api-1  | "`) を剥がす前処理**: `if " | " in line: line = line.split(" | ", 1)[1]` (Landmine 2/5 対策)
- **JSON parse 失敗は silent skip** (uvicorn 起動ログが混ざる — Landmine 5)
- **exit code**: 正常 0, 入力なし 0, パースエラー continue (exit 1 にはしない — pipeline を止めないため)

**流用時の注意:**
- `generate_mcp_artifacts.py` は複数 target の分岐 (`--target helper/js/docs/all`) が複雑 — `trace_query.py` は filter が中心なので、もう少し素朴な構成で良い
- `generate_adr_index.py` は YAML パースが主役 — `trace_query.py` は JSONL 1 行ずつなので逆に軽量

---

### `docs/trace-query-recipes.md` (docs)

**Primary analog:** `docs/mcp-tool-add-manual.md` (手書き手順書、セクション立て、コードブロック実例)
**Secondary analog:** `docs/nginx.md` (コピペ可能な shell / config 実例集)

**structure パターン** (analog: `mcp-tool-add-manual.md:1-32`):

```markdown
# MCP ツール追加マニュアル

このドキュメントは MCP ツールを新規追加する際の **手順書** です。
...

## 手書き境界（Phase 30 D-02）

| ファイル | 区分 | 編集方法 |
|---------|-----|---------|
| ...
```

**流用方針:**
- **タイトル + 目的説明 1-2 段落 + セクション箇条書き** の H1/H2 階層を踏襲
- 冒頭に「このドキュメントは trace 検索レシピ集です。運用者は docker シェルから直接コピペで実行できます」と明示
- 以降は RESEARCH §7.1-7.7 の 7 レシピをそれぞれ `## 7.X タイトル` + shell ブロック形式で記載
- shell ブロックは **copy-paste で動く完全形** (D-17) — `docker compose logs api 2>&1 | jq ...` のフルコマンドを書く（abbreviation なし）

**コピペ可能 shell ブロック例** (analog: `nginx.md:17-32`):

```markdown
```bash
docker compose logs api 2>&1 | jq -cC 'select(.trace_id and .span_id)'
```
```

**流用方針:**
- code fence は ` ```bash ` を使う (`docs/nginx.md` 踏襲)
- 表形式 (RESEARCH §7 末尾の推奨レシピ一覧など) は `docs/mcp-tool-add-manual.md:17-32` の markdown table を踏襲

---

### `docs/phase-31-reasoning-token-spike.md` (docs, spike report)

**Analog:** `docs/phase-14.md` (phase 別 writeup、過去事例 — ただし Phase 14 の内容詳細は未読)
**Alternative analog pattern:** RESEARCH §5.1 の表形式 (モデル別マトリクス) をそのまま成果物に展開できる

**流用方針:**
- タイトル: `# Phase 31 Spike: Copilot SDK reasoning / thinking token 露出調査`
- セクション:
  1. `## 目的` — D-15 と §5.1 の要約
  2. `## 実施手順` — `scripts/probe_sdk_events.py` (既存、docker exec 実行パターン) を template にした調査スクリプト
  3. `## 結果` — モデル別の露出マトリクス (RESEARCH §5.3 の判断基準テーブルを実測値で埋めたもの)
  4. `## span schema への反映判断` — どの attribute を追加するか (`input_tokens` / `output_tokens` / `reasoning_chars` / `reasoning_prefix`)
- docker exec 実行コマンドを冒頭に: `docker exec copilot-langgraph-worker-1 uv run python /app/scripts/probe_sdk_events.py` (analog: `scripts/probe_sdk_events.py:3-4` ヘッダコメント)

---

### テストファイル 3 本

**`tests/test_trace.py`** (writer unit):

**Analog:** `tests/test_generate_adr_index.py` (stdlib のみ unit test) + `tests/test_rpc_context.py` (dataclass unit)

**流用方針:**
- **pytest-asyncio の `@pytest.mark.asyncio` 装飾** (analog: `tests/test_routing_keyword.py:49`)
- **`caplog.at_level(logging.INFO, logger="trace")` + `json.loads(record.getMessage())` で span を assert** (analog: `tests/test_routing_keyword.py:57-70`)
- テストケース:
  - trace_span が 1 span を emit する
  - parent_span_id が ContextVar で nested 伝搬する (親 / 子 2 span を emit、`assert spans[1].parent_span_id == spans[0].span_id`)
  - 例外時に status_code=ERROR + status_message が記録され、例外は再送出される
  - `set_attribute` / `set_status` の override が反映される
  - `emit` が例外を投げても caller の `yield` 済みの処理を止めない

---

**`tests/test_traced_tool.py`** (TracedTool unit):

**Analog:** `tests/test_copilot_bind_tools.py` (tool wrap 系 async unit) + `tests/test_react_e2e.py` (ReAct + tool mock)

**流用方針:**
- **mock BaseTool の作り方**: `MagicMock(spec=BaseTool)` or 小さな dummy `class DummyTool(BaseTool): name = "dummy"; ...` で代替
- test ケース:
  - TracedTool._arun が wrapped.ainvoke を呼ぶ (pass-through 確認)
  - tool_call span が emit される (args_bytes / result_bytes / tool_name / success / privileged 属性を assert)
  - `result = {"error": "..."}` で success=False + status_code="ERROR"
  - 例外発生時に status_code=ERROR + 例外は再送出
  - `asyncio.gather(traced_tool.ainvoke(...), traced_tool.ainvoke(...))` で 2 span が兄弟として emit される (Landmine 8 の検証)

---

**`tests/test_sub_agent_trace.py`** (integration):

**Analog:** `tests/test_react_e2e.py` — ReAct + Copilot mock で tool_call 系 end-to-end
**Supporting analog:** `tests/test_orchestrator_graph.py` — RouterNode + context (RPCContext) のテスト

**流用方針:**
- **ChatCopilot mock パターン**: 既存 `test_react_e2e.py` の mock ChatCopilot を踏襲 (send_and_wait の戻り値を固定、ASSISTANT_USAGE イベントを callback でシミュレート)
- **RPCContext 使用**: `RPCContext(user_id="test", app_id="superchat", thread_id="t1", correlation_id="trace-001")` を state に入れて run() を呼ぶ
- **spans 階層の assert**: routing span → sub_agent span → tool_call span (× N) が同 trace_id 下に出る。parent_span_id で親子関係が正しい

---

## Shared Patterns

### A. JSON 構造化ログ emit (writer 内共通)

**Source:** `app/orchestrator/graph.py:47-55` + `json.dumps(default=str)`
**Apply to:** `app/observability/trace.py` の emit ロジック、全 span 発行箇所

```python
logger.info(json.dumps(asdict(span_dict), ensure_ascii=False, default=str))
```

**Why:** 日本語プロンプト (user_input_prefix 等) と datetime/Decimal を同時に JSON 化するには `ensure_ascii=False` + `default=str` が必須。既存の `iframe_rpc_handler.py:67-73 _json_default` と同じ発想を stdlib default で簡潔に表現。

---

### B. correlation_id / trace_id の参照パターン

**Source:** `app/orchestrator/graph.py:54` の `context.correlation_id if context else ""`
**Apply to:** 全 integration point (graph.py / tool_agent.py / codeact_agent.py / iframe_rpc_handler.py / orchestrator_handler.py)

```python
context = state.get("context")
trace_id = context.correlation_id if context else ""
```

**Why:** legacy thread (context 未設定) でも crash しないための既存 defensive pattern。Phase 31 の trace_id 取得も同じ 3 値フォールバックで統一。

---

### C. privileged 判定パターン

**Source:** `config/mcp_tools.yaml` の `sandbox_exposed` フィールド (ADR 0024)
**Apply to:** TracedTool 内の privileged attribute 判定、および CodeAct `execute_python` の privileged=True 固定

- privileged の source: worker 起動時に `ctx["mcp_privileged_tool_names"]` (既存、`orchestrator_handler.py:43` 参照) で frozenset が組み立てられているので、それを TracedTool の common_attrs getter から参照する
- `execute_python` はカタログ外 (sandbox 内 tool) なので特別扱い: CodeActSubAgent 側で hardcode `privileged=True`

---

### D. エラー result dict 判定

**Source:** `app/jobs/handlers/iframe_rpc_handler.py:146-149` + `mcp_server/tools/mcp_helper_utils.py:39-43`
**Apply to:** TracedTool の result 後処理 / CodeActSubAgent の exit_code 判定

```python
if isinstance(result, dict) and "error" in result:
    span.set_status("ERROR", str(result["error"])[:200])
    span.set_attribute("success", False)
else:
    span.set_attribute("success", True)
```

**Why:** プロジェクト全体で「エラーは例外ではなく `{"error": "..."}` dict で返す」規約が浸透している。span の success 判定も同じ pivot を使うことで既存コードとの整合性を保つ。

---

### E. pytest fixture + caplog で構造化ログ検証

**Source:** `tests/test_routing_keyword.py:57-70` + `tests/conftest.py:8-28` の fixture 形式
**Apply to:** `test_trace.py` / `test_traced_tool.py` / `test_sub_agent_trace.py` すべて

- fixture 名は既存 fixture (`mock_graph`, `mock_auth_manager`) の命名規則に合わせ `capture_trace_logs` とする (動詞より名詞、スネークケース)
- `caplog.set_level(logging.INFO, logger="trace")` + `json.loads(record.getMessage())` の 2 段コンボが既にプロジェクト内で複数箇所で機能している VERIFIED パターン

---

### F. `from __future__ import annotations` 先頭パターン

**Source:** 全モジュールで統一されている (例: `tool_agent.py:21`, `codeact_agent.py:16`, `mcp_helper_utils.py:15`)
**Apply to:** `app/observability/trace.py` / `app/observability/traced_tool.py` / `scripts/trace_query.py`

**Why:** Python 3.12 を pin しているのでもはや必須ではないが、プロジェクト規約として徹底されている。Phase 31 の新規ファイルも従う。

---

## No Analog Found

| File | Role | Data flow | Reason |
|------|------|-----------|--------|
| `app/observability/traced_tool.py` (の `BaseTool` 継承部分) | wrapper | request-response | プロジェクト内で `langchain_core.tools.BaseTool` を**サブクラス化している既存コードはない** (すべて `langchain-mcp-adapters` 由来のインスタンスを dict / list で保持するだけ)。LangChain 公式ドキュメントの `BaseTool` インターフェース (`name`, `description`, `args_schema`, `_run`, `_arun`) を参照して Phase 31 で新規パターンを作る必要がある |

**代替参照先:**
- LangChain 公式 `BaseTool` API: https://api.python.langchain.com/en/latest/tools/langchain_core.tools.BaseTool.html
- RESEARCH §3.1 に TracedTool の最小コード例が既に提示されている — 実装時はその snippet を起点にする

---

## Metadata

**Analog search scope:** `app/`, `tests/`, `scripts/`, `docs/`, `mcp_server/tools/`
**Files scanned (主要):** 16 ファイル
  - `app/orchestrator/{graph,tool_agent,codeact_agent,context,tool_context,agent,gem_agent}.py`
  - `app/jobs/handlers/{iframe_rpc_handler,orchestrator_handler}.py`
  - `app/api/main.py`
  - `mcp_server/tools/mcp_helper_utils.py`
  - `scripts/{generate_adr_index,generate_mcp_artifacts,probe_sdk_events}.py`
  - `tests/{conftest,test_routing_keyword,test_orchestrator_graph}.py`
  - `docs/{nginx,mcp-tool-add-manual}.md`

**Pattern extraction date:** 2026-04-18

## PATTERN MAPPING COMPLETE
