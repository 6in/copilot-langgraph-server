# Phase 31: エージェント実行・MCP ツール利用の observability 基盤 - Research

**Researched:** 2026-04-18
**Domain:** Tracing / 構造化ロギング / OpenTelemetry span-like JSONL 設計 / Python contextvars
**Confidence:** HIGH

## Summary

Phase 31 は「新しいインフラを一切追加せずに」エージェント実行 (routing / SubAgent / tool_call の 3 層) と MCP ツール呼び出し (3 経路) を docker logs stdout に OTEL span-like JSONL として記録する基盤を作る。既存の構造化 JSON ログ (`app/orchestrator/graph.py` の `event: routing`) を踏襲しつつ、`trace_id = RPCContext.correlation_id` を軸に `span_id` / `parent_span_id` / `operation_name` / `start_time` / `end_time` / `attributes` / `status_code` を emit する薄い writer 抽象を追加する。

**最大の発見:** `github-copilot-sdk` 0.2.0 は既に `ASSISTANT_REASONING` / `ASSISTANT_REASONING_DELTA` / `ASSISTANT_USAGE` の 3 イベント種別を emit している。`ASSISTANT_USAGE` には `input_tokens` / `output_tokens` / `cache_read_tokens` / `cache_write_tokens` / `copilot_usage.total_nano_aiu` が含まれ、`ASSISTANT_REASONING` には `reasoning_text` / `reasoning_id` / `reasoning_opaque` が含まれる [VERIFIED: `python3 -c "from copilot.generated.session_events import SessionEventType; print(...)"` で 2026-04-18 確認]。したがって「reasoning token 露出スパイク」は露出**有り**が濃厚で、Phase 31 スコープ内で span attribute として拾える可能性が高い (ただし実際に拾うにはモデルが reasoning-capable である必要あり — 空配列の可能性は残る → スパイクはプローブ形式で残す価値あり)。

**Primary recommendation:** `app/observability/trace.py` に `async with trace_span(operation, attributes, parent_span_id=...) as span:` context manager + `contextvars.ContextVar` ベースの親 span 伝搬を実装。既存 `logger.info(json.dumps(...))` パターンを踏襲して `logger.info(json.dumps(span.to_dict()))` を emit。`app/orchestrator/graph.py` の routing log を一括置換、3 経路の tool_call は (1) `build_react_graph` の ToolNode 前後、(2) `CodeActSubAgent.run` の `execute_python.ainvoke` 前後、(3) `IframeRpcHandler._handle_query` の `tool.ainvoke` 前後、でラップする。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Span writer (emit JSONL to stdout) | API / Worker (Python) | — | Python `logging` に載せて docker logging driver が rotation する既存設計を継承 |
| trace_id 発行 | HTTP intake (`app/api/routes/chat.py`) | — | `RPCContext.correlation_id` が Phase 11 で request 起点に生成済み |
| routing span emit | Worker / LangGraph (`app/orchestrator/graph.py`) | — | Router は Worker 内の arq job 内で動く |
| SubAgent span emit | Worker / LangGraph (ToolEnabledSubAgent / SubAgent / CodeActSubAgent / GemAgent) | — | LangGraph node / agent.run 内 |
| tool_call span (経路 1) | Worker / LangGraph ReAct (`tool_agent.py`) | — | `ToolNode` 前後が最小侵襲ポイント |
| tool_call span (経路 2) | Worker / CodeAct (`codeact_agent.py`) | — | `execute_python.ainvoke` を直接ラップ |
| tool_call span (経路 3) | Worker / iframe RPC (`iframe_rpc_handler.py`) | — | MCP `db_query` tool の `ainvoke` を直接ラップ |
| audit_log テーブル削除 | API (`app/api/main.py`) + DB | — | DDL は lifespan にあり、削除もここで |
| trace query CLI (`scripts/trace_query.py`) | Developer tool (stdin / host) | — | docker logs を pipe 受け取る CLI |

## Standard Stack

### Core (既存、追加なし)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `logging` (stdlib) | - | JSONL emit | [VERIFIED: `app/orchestrator/graph.py:47`] 既存 `logger.info(json.dumps({...}))` パターンと揃える。Phase 31 では `opentelemetry-sdk` を追加しない (D-05) |
| `contextvars` (stdlib) | - | parent_span_id の async 文脈伝搬 | [VERIFIED: `app/orchestrator/tool_context.py:7`] 既に `tool_event_cb: ContextVar[...]` で同じ用途に使用済み。LangGraph の async 実行環境で動作実績あり |
| `time.perf_counter` (stdlib) | - | duration_ms 計測 | 単調増加クロックで wall-clock ジャンプの影響を受けない |
| `datetime.datetime.now(timezone.utc)` | - | ISO-8601 タイムスタンプ | 既存ログで JST を使っているが、トレースは UTC ISO-8601 で一貫させる (OTLP 将来差し替え時に変換不要) |
| `uuid.uuid4().hex[:16]` | - | span_id 生成 | [CITED: CONTEXT.md D-08] |

### Supporting (新規)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `app/observability/trace.py` (新規) | `emit_span()` / `trace_span()` context manager / `SpanDict` dataclass | 全 3 層の span emit に使用 |
| `scripts/trace_query.py` (新規) | CLI フィルタ・親子 tree 表示 | 運用者が docker logs を検索する時 |
| `docs/trace-query-recipes.md` (新規) | jq クエリ例集 | 運用者リファレンス |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 自作 writer 抽象 | `opentelemetry-sdk` + console exporter | SDK 依存・起動コスト・学習コスト増。D-05 で明示的に却下済み。JSONL 自作の方が 200 名規模には合う |
| `structlog` | — | bind 型 API は魅力的だが、既存 `logger.info(json.dumps(...))` パターンと不整合になる。新規依存を増やす価値は Phase 31 時点ではない |
| ISO-8601 タイムスタンプ | Unix nano int | OTEL spec は nano int 推奨だが、jq で人間が読む前提なので ISO-8601 `2026-04-18T12:34:56.789Z` の方が運用者に優しい。OTLP 差し替え時の変換は `datetime.fromisoformat().timestamp() * 1e9` で容易 |
| `@trace_span` デコレータ | context manager | LangGraph node 内で `state` から `correlation_id` を抽出する必要があるので、デコレータではなく `async with` の方が柔軟 |

**Installation:** 追加なし (stdlib のみ)。

**Version verification:** `github-copilot-sdk==0.2.0` は pyproject.toml L7 で pin 済み。Phase 31 スパイクでは `python3 -c "import copilot; print(copilot.__version__)"` と `python3 -c "from copilot.generated.session_events import SessionEventType; print([e for e in dir(SessionEventType) if not e.startswith('_')])"` で version と event set を 2026-04-18 に確認済み。

## User Constraints (from CONTEXT.md)

### Locked Decisions

**観測基盤アーキテクチャ**
- **D-01:** 主ストアは JSONL (docker logs stdout)。PostgreSQL / OTEL Collector / Loki / OpenSearch 等の新規インフラは Phase 31 では導入しない。200 名規模・社内運用では docker logging driver の rotation (quick 260418-tin 設定済み) で十分。
- **D-02:** 既存の PostgreSQL `audit_log` テーブルは Phase 31 で削除する。`app/api/main.py` L105-124 の `CREATE TABLE IF NOT EXISTS audit_log` と `CREATE INDEX` を除去し、Phase 31 の JSONL 一本化方針を明示する。
- **D-03:** 新規ログファイルは作らない。trace 出力は既存の python `logging` (`logger.info(json.dumps({...}))` パターン) で stdout へ流す。docker logging driver の rotation にそのまま乗る。
- **D-04:** Phase 31 のスコープは MVP: 3 経路の writer + CLI スクリプト (`scripts/trace_query.py`) + jq クエリ例 (`docs/`) に限定する。管理 UI / admin API / REST エンドポイントは作らない。
- **D-05:** writer 層は `span dict` を生成して `logger.info` に渡す薄い抽象を作り、将来 OTLP exporter や PG insert に差し替えられる柔軟性を確保する。Phase 31 時点では `opentelemetry-sdk` 依存は追加しない。

**トレース粒度・スキーマ**
- **D-06:** span 粒度は 3 層: `routing` (parent) / `SubAgent` (run) / `tool_call` (child)。ReAct の各 LLM turn は span として切らず、SubAgent span の attribute (`turn_count` / `iterations`) で表現する。
- **D-07:** 1 行スキーマは OTEL span-like: `trace_id` / `span_id` / `parent_span_id` / `operation_name` / `start_time` / `end_time` / `duration_ms` / `attributes` / `status_code` / `status_message`。将来 OTLP への変換をしやすくしておく。
- **D-08:** `trace_id` は既存 `RPCContext.correlation_id` (UUID4、Phase 11 整備済み) と同一にする。`span_id` は span ごとに `uuid4().hex[:16]` 生成。`parent_span_id` で親子関係を表現。
- **D-09:** 全 span 共通の attributes は 4 つ: `user_id` (github_login) / `app_id` (chat / superchat / canvas / gem / debate) / `agent_name` (SubAgent の `name`) / `model_name` (Phase 29 の `model_override` 含む最終モデル)。

**ツール呼び出しイベント (軸 B)**
- **D-10:** 3 経路 (`ToolEnabledSubAgent` / `CodeActSubAgent` / `iframe_rpc_handler`) から統一された `tool_call` span を出す。全 span に `tool_name` / `args_bytes` / `result_bytes` / `duration_ms` / `success` / `privileged` を記録。
- **D-11:** `args` / `result` 本体は truncate して span attribute に格納する (prefix 保存)。truncate 閾値は env var (`TRACE_ARGS_MAX_CHARS` デフォルト 500、`TRACE_RESULT_MAX_CHARS` デフォルト 1000 目安) で**全ツール一律**に制御する。`config/mcp_tools.yaml` にツール個別の redact 指定は入れない。
- **D-12:** `privileged` 判定は `config/mcp_tools.yaml` の `sandbox_exposed=false` を元に span の `attributes.privileged=true` として記録するのみ。アラート / Slack 通知は Phase 31 スコープ外。

**メッセージと LLM 計測**
- **D-13:** ユーザーメッセージ本文 / LLM 出力は prefix 200 字のみ span attribute に記録する (`user_input_prefix` / `llm_output_prefix`)。全文は LangGraph checkpointer (PostgreSQL) に残るため、`thread_id` で JOIN して読む運用。
- **D-14:** トークン使用量 (`usage.total_tokens` / `prompt_tokens` / `completion_tokens`) は SubAgent span の attribute に記録する。Copilot SDK が提供する標準フィールドのみ。
- **D-15:** Copilot SDK の `reasoning` / `thinking` token 露出は Phase 31 の最初のタスクとして小規模スパイクで調査する。SDK から `thinking` / `reasoning_content` / `usage.reasoning_tokens` 相当が取れる場合だけ span attribute に追加し、取れなければ Phase 31 スコープ外に倒す。

**可視化 / 参照手段**
- **D-16:** 可視化 UI は作らない。Phase 31 では CLI + jq 運用で完結し、将来的にも admin 画面は予定しない。
- **D-17:** trace 参照は docker シェル前提 (`docker compose logs api | jq ...` / `docker exec`)。アプリ層の認証・認可は持たない。
- **D-18:** サンプリングは実装しない (全件記録)。将来負荷が問題になったら env var で sample rate を導入する拡張余地を残す。

### Claude's Discretion

- writer 抽象の具体 I/F (`emit_span(operation, attributes)` ヘルパー関数 / `with trace_span(...)` context manager / dataclass + emit 等)
- span `start_time` / `end_time` の取得手段 (`time.perf_counter` 差分 vs ISO-8601 タイムスタンプ)
- Copilot SDK reasoning / thinking spike の規模 (想定 1-2h、成果物は `docs/phase-31-reasoning-token-spike.md` か spike ディレクトリに集約)
- `scripts/trace_query.py` の具体 CLI インターフェース (filter フラグ、pretty 出力、follow モード等)
- `docs/` に置く jq クエリ例集の構成 (例: ユーザー別集計 / 失敗 trace 抽出 / privileged ツール一覧)
- truncate 閾値のデフォルト最終値 (上記 500 / 1000 は目安、実装時に Claude が微調整可)
- writer 設置先ディレクトリ (`app/observability/`、`app/orchestrator/trace.py` 等)
- 既存 `graph.py` の `event: routing` ログを新スキーマに段階的移行するか一括置換するか

### Deferred Ideas (OUT OF SCOPE)

- 管理 UI / admin 画面 (CLI で完結する前提)
- Loki / OpenSearch / Jaeger / Tempo / Grafana 等の集約基盤
- OpenTelemetry SDK / OTLP exporter の導入 (writer 抽象で将来差し替え可に留める)
- PostgreSQL `audit_log` への書き込み復活 (Phase 31 で削除)
- privileged ツール使用時の Slack / メール / 通知連携
- サンプリング機構 (`TRACE_SAMPLING_RATE` 等)
- トークン使用量の集計 API / 統計ダッシュボード
- `GET /api/traces` 等の REST 参照エンドポイント

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PHASE31-D01..D05 | writer 抽象層 + 既存 audit_log 削除 + stdout 一本化 | 本 research の §2 (writer パターン) と §8 (audit_log 削除影響) |
| PHASE31-D06..D09 | 3 層 span (routing / SubAgent / tool_call) + 共通 4 attributes | §1 (OTEL schema) と §4 (parent-child 伝搬) |
| PHASE31-D10..D12 | 3 経路統一 tool_call span + truncate env var + privileged flag | §3 (3 経路 emit ポイント) |
| PHASE31-D13..D15 | message prefix 200 字 / token usage / reasoning spike | §5 (Copilot SDK reasoning / usage 露出 — VERIFIED 済) |
| PHASE31-D16..D18 | CLI + jq + 全件記録 | §6 (CLI 設計) と §7 (jq クエリ例集) |

---

## 1. OTEL span-like JSON スキーマ設計

### 1.1 推奨フィールド命名

OTEL 仕様 [CITED: https://opentelemetry.io/docs/specs/otel/trace/api/] に準拠した snake_case を採用。OTLP/JSON ではなく human-readable JSON を目指す (jq で読む前提)。

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "span_id": "a3f5c9e1b2d4a0f8",
  "parent_span_id": "f1d2c3b4a5968778",
  "operation_name": "tool_call",
  "start_time": "2026-04-18T12:34:56.123456Z",
  "end_time":   "2026-04-18T12:34:57.789012Z",
  "duration_ms": 1666,
  "status_code": "OK",
  "status_message": null,
  "attributes": {
    "user_id": "0hya6in",
    "app_id": "superchat",
    "agent_name": "researcher",
    "model_name": "claude-sonnet-4-6",
    "tool_name": "web_search",
    "args_bytes": 42,
    "result_bytes": 8912,
    "success": true,
    "privileged": false,
    "args_prefix": "{\"query\":\"OpenTelemetry spec 2026\"}",
    "result_prefix": "[{\"title\":\"Tracing API\", ...}]"
  }
}
```

### 1.2 フィールド詳細

| Field | Type | Notes |
|-------|------|-------|
| `trace_id` | UUID4 string | `RPCContext.correlation_id` そのまま。OTEL spec の 32-hex 16-byte 形式ではないが、OTLP 差し替え時に `uuid.hex` へ変換可能 [CITED: OTEL spec] |
| `span_id` | 16-char hex | `uuid4().hex[:16]` (D-08) |
| `parent_span_id` | 16-char hex / null | ルート span は null |
| `operation_name` | enum-like str | `"routing"` / `"sub_agent"` / `"tool_call"` の 3 種 (D-06) |
| `start_time` | ISO-8601 UTC ms 精度 | `datetime.now(timezone.utc).isoformat(timespec='microseconds')` |
| `end_time` | ISO-8601 UTC ms 精度 | 同上。end_time - start_time でも duration_ms は算出可能だが、`time.perf_counter()` 差分の方が単調性が保証される |
| `duration_ms` | int | `perf_counter` 差分 × 1000、int 丸め |
| `status_code` | `"OK"` \| `"ERROR"` \| `"UNSET"` | [CITED: OTEL spec] OK / ERROR / UNSET の 3 種。例外発生時に ERROR |
| `status_message` | str / null | ERROR 時のみ例外メッセージ先頭 200 字 |
| `attributes` | dict | 共通 4 fields (D-09) + operation 固有 fields |

### 1.3 snake_case 採用根拠

- OTEL spec の semantic conventions は dot notation (`http.method` 等) を使う部分もあるが、JSON の key に dot を入れると jq で `.attributes.http.method` の解釈が曖昧になる (`http` object の子か single key か不明)
- Python の dict key としても snake_case が自然
- OTLP/JSON exporter 差し替え時は semconv 変換テーブルを writer 内に閉じ込めれば足りる

### 1.4 タイムスタンプ形式

- **採用:** ISO-8601 UTC microseconds (`2026-04-18T12:34:56.123456Z`)
- **非採用:** Unix nano int (OTLP 標準だが jq で `date -d @...` しないと読めない)
- **理由:** 運用者が `docker compose logs api | jq 'select(.start_time > "2026-04-18T12:00")'` で時刻フィルタできる方が CLI-only 運用 (D-17) と整合
- **OTLP 差し替え:** `int(datetime.fromisoformat(s.replace("Z","+00:00")).timestamp() * 1e9)` で 1 行変換可能

### 1.5 status_code enum

OTEL spec の StatusCode enum [CITED: https://opentelemetry.io/docs/specs/otel/trace/api/] に準拠:

| Value | 意味 | 発火条件 |
|-------|------|----------|
| `"UNSET"` | span 作成直後、明示的な status 未設定 | 通常は emit しないうちに終わる |
| `"OK"` | 正常終了 | `async with` ブロックが例外なく抜けた |
| `"ERROR"` | 異常終了 | `async with` ブロック内で例外発生 (再送前に status を ERROR にセット) |

Phase 31 実装では `__aexit__` で例外の有無を見て自動設定する。明示的に `span.set_status("ERROR", "reason")` を呼べる I/F も用意 (ツール結果が `{"error": "..."}` の場合など)。

---

## 2. Python writer 抽象パターン

### 2.1 採用: `async with trace_span(...)` context manager

```python
# app/observability/trace.py (新規)
from __future__ import annotations
import json, logging, time, uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, AsyncIterator

logger = logging.getLogger("trace")

# parent_span_id の async 文脈伝搬に使う ContextVar
_current_span_id: ContextVar[str | None] = ContextVar("_current_span_id", default=None)
_current_trace_id: ContextVar[str | None] = ContextVar("_current_trace_id", default=None)


@dataclass
class SpanDict:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    operation_name: str
    start_time: str
    end_time: str
    duration_ms: int
    status_code: str
    status_message: str | None
    attributes: dict[str, Any]


@asynccontextmanager
async def trace_span(
    operation_name: str,
    trace_id: str,
    attributes: dict[str, Any] | None = None,
    parent_span_id: str | None = None,
) -> AsyncIterator["_ActiveSpan"]:
    """Emit an OTEL span-like JSON line on exit.

    trace_id は caller が明示 (通常 RPCContext.correlation_id)。
    parent_span_id は (a) 引数で明示、(b) 省略時は ContextVar から取得。

    Usage:
        async with trace_span("tool_call", trace_id=ctx.correlation_id,
                              attributes={"tool_name": "web_search"}) as span:
            result = await tool.ainvoke(args)
            span.set_attribute("result_bytes", len(str(result)))
    """
    span_id = uuid.uuid4().hex[:16]
    # ContextVar から親 span_id を継承 (引数優先)
    parent = parent_span_id if parent_span_id is not None else _current_span_id.get()

    start_wall = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    start_mono = time.perf_counter()

    active = _ActiveSpan(attributes=dict(attributes or {}))

    token_span = _current_span_id.set(span_id)
    token_trace = _current_trace_id.set(trace_id)
    status_code = "OK"
    status_message: str | None = None
    try:
        yield active
    except Exception as e:
        status_code = "ERROR"
        status_message = type(e).__name__ + ": " + str(e)[:200]
        raise
    finally:
        _current_span_id.reset(token_span)
        _current_trace_id.reset(token_trace)

        end_wall = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        duration_ms = int((time.perf_counter() - start_mono) * 1000)

        # active から明示的に設定された status があれば優先 (tool result が error の場合等)
        if active._status_override:
            status_code, status_message = active._status_override

        span_dict = SpanDict(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent,
            operation_name=operation_name,
            start_time=start_wall,
            end_time=end_wall,
            duration_ms=duration_ms,
            status_code=status_code,
            status_message=status_message,
            attributes=active.attributes,
        )
        try:
            logger.info(json.dumps(asdict(span_dict), ensure_ascii=False, default=str))
        except Exception:
            # 絶対に caller の処理を止めない (Landmine 6)
            logger.exception("trace_span emit failed")


class _ActiveSpan:
    """yield で返されるオブジェクト。属性の追加と status override を許可する。"""
    def __init__(self, attributes: dict[str, Any]) -> None:
        self.attributes: dict[str, Any] = attributes
        self._status_override: tuple[str, str | None] | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_attributes(self, mapping: dict[str, Any]) -> None:
        self.attributes.update(mapping)

    def set_status(self, code: str, message: str | None = None) -> None:
        """例外以外の異常 (tool result が error dict 等) に使う。"""
        self._status_override = (code, message)
```

### 2.2 検討した 3 方式の比較

| 方式 | 利点 | 欠点 | 判断 |
|------|------|------|------|
| `emit_span(operation, attrs)` ヘルパー関数 | シンプル、書き手の負担最小 | duration 計測が caller 責務、例外時の status 自動化不可、parent_span_id 伝搬も手動 | ❌ |
| `async with trace_span(...)` context manager | duration 自動、例外時 status 自動、`_current_span_id` の reset も安全 | やや冗長 | **✅ 採用** |
| `@trace_span` デコレータ | 関数全体を span にする用途に最適 | ノード関数は引数が `state` のみで `trace_id` / attributes をそこから抽出する必要があり、デコレータだと柔軟性が落ちる | ❌ |

### 2.3 contextvars での親 span 伝搬

- [CITED: Python docs https://docs.python.org/3/library/contextvars.html] `ContextVar` は `asyncio` タスク間で自動コピーされる。`asyncio.create_task()` は呼び出し時点の Context をコピーする。
- [VERIFIED: `app/orchestrator/tool_context.py:7`] 本プロジェクトでは既に `tool_event_cb: ContextVar` が `ToolEnabledSubAgent` → `ToolNode` 実行中に伝搬する実績あり。同じパターンで `_current_span_id` が伝搬する。
- **Landmine 1:** LangGraph の streaming context は nested graph invocation で leak する issue が報告されている [CITED: https://github.com/langchain-ai/langgraph/issues/4826]。ただし Phase 31 の usage では nested graph をまたがない (routing → SubAgent → tool_call は flat な親子) ため影響なし。

### 2.4 既存 `logger.info(json.dumps(...))` からの移行

- **置換戦略 (D-08 discretion):** 一括置換を採用。CONTEXT.md specifics で「互換 alias は残さない」と明記されており、既存 log line (`{"event": "routing", ...}`) は Phase 31 で OTEL span 形式 (`{"operation_name": "routing", "trace_id": ..., ...}`) に置き換える。
- **影響範囲:** `app/orchestrator/graph.py` の 3 箇所 (L47, L61, L93) と L86 の `routing_fallback` warning。外部向け契約ではないので破壊的変更だが、運用者向け jq クエリは `docs/trace-query-recipes.md` で新形式ベースに書き直す。

### 2.5 差し替え可能性 (OTLP exporter 将来対応)

`logger.info(json.dumps(...))` を `_emit(span_dict)` に閉じ込め、その中で現状は `logger.info` を呼ぶだけにしておけば、将来 `_emit` を OTLP exporter の `span_exporter.export(...)` 呼び出しに差し替えるだけで済む。本 research の実装例では dataclass → asdict → json.dumps → logger.info を直接 context manager 内で行っているが、`_emit(span_dict)` ヘルパーに切り出すのは実装時の微調整範疇。

---

## 3. 3 経路のツール span emit ポイント

### 3.1 経路 1: ToolEnabledSubAgent + build_react_graph (app/orchestrator/tool_agent.py)

**emit ポイント:** `agent_node` 内で LLM 応答を得た直後 (`response` に `tool_calls` があるか確認する箇所、L137-148 と同じ位置) と、ToolNode 実行後の agent_node 再入のタイミング。

**最小侵襲アプローチ:**
- `tool_agent.py` L155 の `graph.add_edge("tools", "agent")` の前後ではなく、**ToolNode 自体をラップする薄い関数で置き換える**のが最も簡潔:

```python
# tool_agent.py (修正案)
from app.observability.trace import trace_span, _current_trace_id

async def instrumented_tool_node(state: MiniReActState) -> dict:
    """ToolNode をラップして tool_call span を emit する。"""
    result = await tool_node.ainvoke(state)
    # ToolNode の内部では tool が個別に呼ばれるが、ToolNode の async I/F は
    # まとめて result を返す。個別 tool_call を span にするには state["messages"]
    # の末尾 AIMessage から tool_calls を取り、呼び出し前に span を開始する必要がある。
    # → ToolNode の invoke 前後を個別にラップする wrapper を書く。
    return result
```

**推奨実装パターン:** `ToolNode` は `BaseTool.ainvoke` をループで呼ぶので、**tools 自体を trace でラップした `BaseTool` サブクラス** (`TracedTool`) に差し替える。`ToolEnabledSubAgent.__init__` で `tools = [TracedTool(t, ctx_provider=...) for t in tools]` としてから `ToolNode(tools)` を構築する。

```python
# app/observability/traced_tool.py (新規検討)
from langchain_core.tools import BaseTool

class TracedTool(BaseTool):
    def __init__(self, wrapped: BaseTool, trace_id: str, common_attrs: dict):
        super().__init__(name=wrapped.name, description=wrapped.description, ...)
        self._wrapped = wrapped
        self._trace_id = trace_id
        self._common_attrs = common_attrs

    async def _arun(self, **kwargs):
        args_json = json.dumps(kwargs, ensure_ascii=False, default=str)
        async with trace_span(
            "tool_call",
            trace_id=self._trace_id,
            attributes={
                **self._common_attrs,
                "tool_name": self._wrapped.name,
                "args_bytes": len(args_json),
                "args_prefix": args_json[:TRACE_ARGS_MAX_CHARS],
                "privileged": self._wrapped.name in PRIVILEGED_TOOL_NAMES,
            },
        ) as span:
            result = await self._wrapped.ainvoke(kwargs)
            result_json = json.dumps(result, ensure_ascii=False, default=str)
            span.set_attribute("result_bytes", len(result_json))
            span.set_attribute("result_prefix", result_json[:TRACE_RESULT_MAX_CHARS])
            # tool 自身がエラー dict を返す場合 (web_search が {"error": ...} 返す等)
            if isinstance(result, dict) and "error" in result:
                span.set_status("ERROR", str(result["error"])[:200])
                span.set_attribute("success", False)
            else:
                span.set_attribute("success", True)
            return result
```

**既に取れている情報:**
- `correlation_id` / `user_id` / `app_id`: `state["context"]` (`RPCContext`) 経由。`ToolEnabledSubAgent.run()` の `context = state.get("context")` で取得可能 (L299)
- `tool_name`: `tool.name` (自明)
- `agent_name`: `self.name`

**追加で必要な情報:**
- `duration_ms`: `trace_span` が自動計測
- `args_bytes` / `result_bytes`: JSON dump 後の byte 数 (truncate 前)
- `success`: result が dict で `error` key を持つかどうか判定 (既存 `mcp_helper_utils._call_tool` のエラー表現と揃える)

### 3.2 経路 2: CodeActSubAgent (app/orchestrator/codeact_agent.py)

**emit ポイント:** `codeact_agent.py` L200 の `result = await execute_python.ainvoke({"code": code})` の前後。

**問題:** CodeAct の **真の** tool_call は、sandbox 内から呼ばれる `mcp_helper._call_tool` (web_search, db_query 等) である。`execute_python` 自体も tool_call として計測する価値はあるが、そこから更に生成される sandbox → MCP サーバーへの HTTP call は別モジュール (`mcp_server/tools/mcp_helper_utils.py:_call_tool`) で発生する。

**2 つのアプローチ:**

1. **CodeAct agent 側で `execute_python` 呼び出しだけを計測** (Phase 31 ミニマム)
   - 対象: `execute_python` 1 個の tool_call span のみ
   - sandbox 内の個別 MCP ツール呼び出し (web_search 等) は可視化されないが、`execute_python` の `result_prefix` に stdout が入るので間接的に分かる
   - 実装コスト: 最小 (agent.run の 5 行程度の追加)

2. **MCP サーバー側の `/internal/call_tool` エンドポイントで span 発行** (拡張案)
   - `mcp_server/server.py:internal_call_tool` に trace_id をクライアント (sandbox) から受け渡す機構が必要
   - sandbox の `mcp_helper_utils._call_tool` が env var 経由で trace_id を拾い HTTP ヘッダー `X-Trace-Id` で送信、MCP サーバー側で受信して span emit
   - Phase 31 スコープ外との線引き判断: **CONTEXT.md D-10 は「3 経路から統一された tool_call span を出す」と明言**しており、CodeAct 経路では **`execute_python` を 1 回の tool_call として扱う** 解釈で十分 (D-06 の 3 層 = 3 層であり、sandbox 内の 4 層目は想定外)。
   - **判断:** Phase 31 はアプローチ 1 (execute_python のみ計測)。アプローチ 2 は `Deferred Ideas` に追加しておく。

**推奨実装 (アプローチ 1):**

```python
# codeact_agent.py:run() の該当箇所に置換
trace_id = context.correlation_id if context else "unknown"
common_attrs = {
    "user_id": getattr(context, "user_id", "unknown") if context else "unknown",
    "app_id": getattr(context, "app_id", "") if context else "",
    "agent_name": self.name,
    "model_name": self._llm.model,
}

# ... 既存コード ...

code = _extract_code(content)
if code:
    args_json = json.dumps({"code": code}, ensure_ascii=False)
    async with trace_span(
        "tool_call",
        trace_id=trace_id,
        attributes={
            **common_attrs,
            "tool_name": "execute_python",
            "args_bytes": len(args_json),
            "args_prefix": args_json[:TRACE_ARGS_MAX_CHARS],
            "privileged": True,  # execute_python は privileged
        },
    ) as span:
        try:
            result = await execute_python.ainvoke({"code": code})
            raw_result = _normalize_tool_result(result)
        except Exception as e:
            raw_result = json.dumps({"stdout": "", "stderr": str(e), "exit_code": -1})
            span.set_status("ERROR", str(e)[:200])
        span.set_attribute("result_bytes", len(raw_result))
        span.set_attribute("result_prefix", raw_result[:TRACE_RESULT_MAX_CHARS])
        stdout, stderr, exit_code = _parse_execute_result(raw_result)
        span.set_attribute("success", exit_code == 0)
        if exit_code != 0:
            span.set_status("ERROR", f"exit_code={exit_code}")
```

### 3.3 経路 3: iframe_rpc_handler (app/jobs/handlers/iframe_rpc_handler.py)

**emit ポイント:** `_handle_query` の `out = await tool.ainvoke({...})` (L128) の前後、および `_handle_ai` の `llm.ainvoke(...)` (L175) の前後。

**既に取れている情報:**
- `correlation_id`: iframe_rpc 経路の `RPCContext` は `app/jobs/handlers/iframe_rpc_handler.py` の `handle` 内の `job` dict から生成する必要あり (現状 `handle` 内に `RPCContext` を組み立てるコードは見当たらない — `job` に `correlation_id` が入っているかは Phase 11 整備の範囲を確認する必要)
- `user`: `params.get("user", "")` (L119) で既に取れている
- `tool_name`: `"db_query"` (固定)

**[ASSUMED] iframe_rpc 経路では RPCContext が完全には組まれていない可能性がある。**`app/api/routes/iframe_rpc.py` を読んで確認し、必要なら Phase 31 で `correlation_id` を `job` dict に追加する小タスクを含める。

**追加タスク:** `job` dict に `correlation_id` / `user_id` / `app_id="canvas"` / `thread_id` を載せる改修を `app/api/routes/iframe_rpc.py` 側で行う必要あり (Phase 11 が iframe_rpc まで波及していない可能性を plan 内で確認)。

**推奨実装:**

```python
async def _handle_query(self, ctx: dict, params: dict, job: dict) -> dict:
    trace_id = job.get("correlation_id", "unknown")
    common_attrs = {
        "user_id": job.get("user_id") or params.get("user", "unknown"),
        "app_id": "canvas",
        "agent_name": "iframe_rpc",  # エージェントではないが operation source として
        "model_name": "",
    }
    args_json = json.dumps({"sql": sql, "pool_name": pool_name}, ensure_ascii=False)
    async with trace_span(
        "tool_call", trace_id=trace_id,
        attributes={
            **common_attrs,
            "tool_name": "db_query",
            "args_bytes": len(args_json),
            "args_prefix": args_json[:TRACE_ARGS_MAX_CHARS],
            "privileged": False,  # db_query は sandbox_exposed: true
        },
    ) as span:
        out = await tool.ainvoke({"sql": sql, "pool_name": pool_name})
        ...
```

### 3.4 3 経路の一覧まとめ

| 経路 | ファイル | 現行 call site | wrap 方式 | 差分の大きさ |
|------|---------|---------------|-----------|--------------|
| 1. ToolEnabledSubAgent | `app/orchestrator/tool_agent.py:252` `ToolNode(tools)` | tools を `TracedTool` で包んでから ToolNode に渡す | 中 (新規 `TracedTool` クラス + agent の `__init__` 修正) |
| 2. CodeActSubAgent | `app/orchestrator/codeact_agent.py:200` `execute_python.ainvoke` | 呼び出し箇所を `async with trace_span(...)` で包む | 小 (1 ファイル 10 行程度) |
| 3. iframe_rpc_handler | `app/jobs/handlers/iframe_rpc_handler.py:128` `tool.ainvoke` | 呼び出し箇所を `async with trace_span(...)` で包む。事前に `job` dict に `correlation_id` / `user_id` を載せる改修が必要 (Phase 11 範囲確認) | 小〜中 |

---

## 4. LangGraph の親子 span 伝搬

### 4.1 設計

`routing` (parent) → `SubAgent` (child) → `tool_call` (grandchild) の 3 層 tree。

```
routing span (operation=routing, parent=null, span_id=A)
└── sub_agent span (operation=sub_agent, parent=A, span_id=B)
    ├── tool_call span (operation=tool_call, parent=B, span_id=C)
    └── tool_call span (operation=tool_call, parent=B, span_id=D)
```

### 4.2 伝搬手段: ContextVar (採用)

- LangGraph の node 関数は async で呼ばれ、同じ asyncio task 内で順次実行される。`_current_span_id` ContextVar は task 境界を越えて自動伝搬するので、`RouterNode.__call__` → SubAgent node → ToolNode の連鎖で `_current_span_id` が自然に親 span_id を指す
- **state['configurable']** への注入は D-06 (`state 追加は最小限`) に反するので採用しない
- [VERIFIED: `app/orchestrator/tool_context.py`] 同じ ContextVar パターンが既に `tool_event_cb` で動作実績あり

### 4.3 CodeAct の扱い

CodeActSubAgent は LangGraph の node **ではなく**、`SubAgent.run` から直接呼ばれるループを持つ (LangGraph の node としては 1 回しか呼ばれない)。したがって:

- `SubAgent` span は CodeActSubAgent の `run()` 全体を包む
- `tool_call` span は `execute_python.ainvoke` の 1 回 1 回に対応
- 親子関係は ContextVar で自動伝搬する (run が async で、同じ task 内なので)

### 4.4 routing → SubAgent の親子関係

OrchestratorGraph の compile 済みグラフでは `router` ノードの後に条件分岐で各 SubAgent ノードに遷移する。両ノードは同じ graph.ainvoke 呼び出し内の同じ task で順次実行されるため、routing span を開始し終えた**後**に SubAgent node が呼ばれると、SubAgent node 側で `_current_span_id.get()` しても routing span は既に抜けていて None が返る。

**解決策:** routing span を **context manager としては短時間**で終わらせず、**ルーティング決定の attribute 記録のためだけに短命 span として emit し、parent としては trace_id 直下** (= 暗黙のリクエスト root) として扱う。

```
[trace_id root (暗黙、root span 未明示)]
├── routing span (parent=null)
└── sub_agent span (parent=null)  ← routing と同じ trace_id の並列兄弟扱い
    └── tool_call span (parent=sub_agent)
```

代案: routing span を「長い」span にして SubAgent の run までカバーする方式もあるが、LangGraph の compile グラフの途中で context manager を明示的に抜ける/入るのは難しい。Phase 31 ではシンプルに routing / sub_agent を**兄弟扱い**で emit し、同じ `trace_id` で検索できれば十分とする。

**Alternative:** RouterNode の前に外側の "request" span を追加する案もあるが、そのためには OrchestratorHandler (worker handler) 側で `async with trace_span("request", trace_id=...)` を追加する必要がある。これは**低コストで有用** — Plan に含めることを推奨:

```python
# app/jobs/handlers/orchestrator_handler.py (修正案)
async with trace_span("request", trace_id=ctx.correlation_id,
                      attributes={"user_id": ctx.user_id, "app_id": ctx.app_id}) as request_span:
    result = await compiled_graph.ainvoke(initial_state, config=config)
```

こうすると `routing` / `sub_agent` / `tool_call` のすべてが request span の子孫になり、trace tree が自然にできる。**D-06 の「3 層」は routing / sub_agent / tool_call を指すが、暗黙の request span を root として追加するのはスコープ内と解釈する** (plan-check で確認推奨)。

### 4.5 結論

| Node | operation_name | parent_span_id |
|------|---------------|----------------|
| OrchestratorHandler 全体 | `request` (optional) | null |
| RouterNode | `routing` | request span の id (または null) |
| SubAgent (run) | `sub_agent` | request span の id (または null) |
| ToolNode 内の tool 呼び出し | `tool_call` | sub_agent span の id |
| CodeAct の execute_python | `tool_call` | sub_agent span の id |
| iframe_rpc の db_query | `tool_call` | request span の id (または null) |

---

## 5. Copilot SDK reasoning / thinking token 露出調査

### 5.1 調査結果 (スパイク前倒し VERIFIED)

**[VERIFIED: 2026-04-18 ローカル Python で直接確認]** `github-copilot-sdk` 0.2.0 は以下のイベント・フィールドを既に emit する。

**Session event types (関連するもの抜粋):**

```python
from copilot.generated.session_events import SessionEventType
# 以下が存在:
SessionEventType.ASSISTANT_REASONING          # reasoning 完了イベント
SessionEventType.ASSISTANT_REASONING_DELTA    # reasoning streaming delta
SessionEventType.ASSISTANT_USAGE              # token usage イベント
SessionEventType.ASSISTANT_MESSAGE            # assistant response
SessionEventType.ASSISTANT_TURN_START / END   # turn boundary
```

**Data クラス (`copilot.generated.session_events.Data`) の reasoning / usage 関連フィールド:**

| フィールド名 | 型 | 意味 |
|-------------|----|------|
| `reasoning_effort` | `str \| None` | reasoning 強度設定値 ("low" / "medium" / "high" 等) |
| `previous_reasoning_effort` | `str \| None` | 前回値 |
| `reasoning_id` | `str \| None` | reasoning 呼び出し ID (cross-reference 用) |
| `reasoning_text` | `str \| None` | reasoning 本文 (thinking のテキスト出力) |
| `reasoning_opaque` | `str \| None` | reasoning の不透明表現 (encrypted/opaque な内部表現) |
| `input_tokens` | `float \| None` | 入力 token 数 |
| `output_tokens` | `float \| None` | 出力 token 数 |
| `cache_read_tokens` | `float \| None` | cache hit で読まれた token 数 |
| `cache_write_tokens` | `float \| None` | cache に書かれた token 数 |
| `conversation_tokens` | `float \| None` | 会話全体 token 数 |
| `system_tokens` | `float \| None` | system prompt token 数 |
| `tool_definitions_tokens` | `float \| None` | ツール定義 token 数 |
| `copilot_usage.total_nano_aiu` | `float` | Copilot AIU (請求単位) |
| `copilot_usage.token_details` | `list[TokenDetail]` | `{batch_size, cost_per_batch, token_count, token_type}` の配列 |

**結論:** D-15 の「取れる場合だけ span attribute に追加」の**取れる**側に確実に該当する。Phase 31 スコープ内で reasoning token 計測を span に載せる価値が高い。

### 5.2 具体的な取得手順

**現状の問題:** `ChatCopilot._agenerate` (L88-132) は `session.send_and_wait(prompt, timeout)` を呼ぶだけで、その戻り値 (`response.data.content`) しか見ていない。usage / reasoning イベントは `session.on(callback)` で個別に配信される streaming API で受け取る必要がある。

**`ChatCopilot._astream`** (L134-207) は既に `session.on(on_event)` を登録して `ASSISTANT_MESSAGE_DELTA` / `ASSISTANT_MESSAGE` / `SESSION_IDLE` を監視している。ここに `ASSISTANT_USAGE` / `ASSISTANT_REASONING` ハンドラを追加すれば reasoning / usage が拾える。

**`_agenerate` 側の改修:** send_and_wait は synchronous API なので、`session.on(handler)` を send_and_wait の**前**に登録しておけば、同じ session 上で emit される usage / reasoning イベントをコールバックで受信できる。

**スパイク手順 (推奨、1-2h で終わる):**

1. ブランチ上で `app/providers/copilot.py:_agenerate` に最小限のイベント捕捉を追加:
    ```python
    # _agenerate の先頭
    captured_usage: dict = {}
    captured_reasoning: list[str] = []
    def on_event(event):
        etype = getattr(event, "type", None)
        data = getattr(event, "data", None)
        if etype == SessionEventType.ASSISTANT_USAGE:
            captured_usage.update({
                "input_tokens": getattr(data, "input_tokens", None),
                "output_tokens": getattr(data, "output_tokens", None),
                "cache_read_tokens": getattr(data, "cache_read_tokens", None),
                "cache_write_tokens": getattr(data, "cache_write_tokens", None),
            })
        elif etype == SessionEventType.ASSISTANT_REASONING:
            rt = getattr(data, "reasoning_text", None)
            if rt: captured_reasoning.append(rt)
    session.on(on_event)
    # ... send_and_wait ...
    logger.info(json.dumps({"event":"spike-usage", "usage":captured_usage,
                            "reasoning_count":len(captured_reasoning),
                            "reasoning_total_chars":sum(len(t) for t in captured_reasoning)}))
    ```
2. docker compose up で各モデルにて Chat で 1 本質問を流す:
   - `claude-sonnet-4-6` (deep think 非対応想定)
   - `claude-haiku-4-5-20251001` (deep think 非対応想定)
   - `gpt-4.1` (reasoning 有無確認)
   - 可能であれば `o1` / `o3` 系や `claude-3.7-sonnet-thought` 等があれば試す (Copilot 側のモデル ID は不明)
3. docker compose logs api | grep spike-usage で各モデルの結果を集計
4. 結果を **docs/phase-31-reasoning-token-spike.md** に記録:
   - モデル別の usage / reasoning 露出可否
   - 露出フォーマット実例 (JSON)
   - Phase 31 span schema に追加する attribute 名を確定

### 5.3 判断基準と分岐

| 結果 | Phase 31 実装 |
|------|--------------|
| `ASSISTANT_USAGE` が全モデルで来る (期待) | SubAgent span attribute に `input_tokens` / `output_tokens` / `cache_read_tokens` / `cache_write_tokens` を追加 |
| `ASSISTANT_USAGE` が一部モデルでしか来ない | SubAgent span に来た分だけ追加 (None チェック必須) |
| `ASSISTANT_REASONING` が deep-think モデルで来る | SubAgent span attribute に `reasoning_chars` (文字数のみ、本文は D-13 の prefix ルールに合わせて 200 字まで `reasoning_prefix`) を追加 |
| `ASSISTANT_REASONING` が全モデルで来ない | Phase 31 スコープ外。将来 deep-think モデル対応時に拡張 |

### 5.4 成果物と配置先

- **`docs/phase-31-reasoning-token-spike.md`** — モデル別露出マトリクス + 実サンプル JSON + span schema への反映判断
- スパイク実装ブランチ: Phase 31 の Plan 01 内で実施し、結果を RESEARCH 反映・PLAN 更新の形でフィードバック
- **[ASSUMED]** スパイク結果が期待通り usage を返せばコード変更は `copilot.py` の `_agenerate` / `_astream` の両方に分散 (小〜中程度)。仮にイベントが来なければ span attribute は追加せず token 関連 attribute は null で emit。

---

## 6. scripts/trace_query.py CLI 設計

### 6.1 推奨インターフェース

```bash
# 基本: stdin から JSONL を読む (docker compose logs api からパイプ)
docker compose logs api 2>&1 | python3 scripts/trace_query.py

# 特定 trace_id のフルトレースを tree 表示
docker compose logs api 2>&1 | python3 scripts/trace_query.py --trace-id 550e8400-e29b-41d4-a716-446655440000 --format tree

# filter + 直近 follow
docker compose logs --follow api | python3 scripts/trace_query.py --user 0hya6in --tool web_search -f

# 直接 docker compose に食わせるショートカット
python3 scripts/trace_query.py --since 1h --status ERROR
```

### 6.2 CLI スペック

```
usage: trace_query.py [options]

入力:
  (default)                  stdin から JSONL を読む
  --docker-compose SERVICE   内部で `docker compose logs {SERVICE}` を subprocess で起動

フィルタ (複数指定 AND):
  --trace-id ID
  --user GITHUB_LOGIN
  --app APP_ID               chat | superchat | canvas | gem | debate
  --agent NAME
  --tool TOOL_NAME
  --status {OK,ERROR,UNSET}
  --operation {routing,sub_agent,tool_call,request}
  --since TIMESTAMP          ISO-8601 or "1h" "5m" "30s"
  --until TIMESTAMP
  --privileged               privileged=true のみ
  --min-duration-ms N        duration_ms >= N の span のみ

出力:
  --format {pretty,tree,tsv,ndjson}
     pretty (default): 1 span 1 行に縦整列、duration と status を色付け
     tree:             --trace-id 指定時に親子関係を tree で表示
     tsv:              スプレッドシート貼り付け用
     ndjson:           生 JSONL を pass-through (他の tool にチェーン可)

動作:
  -f, --follow               stdin が EOF にならない限り待ち続ける (docker compose logs -f 対応)
  --max N                    最大 N span で終了 (default: 全件)
```

### 6.3 argparse ベースの実装スケッチ (stdlib のみ)

```python
# scripts/trace_query.py
import argparse, json, sys, re
from datetime import datetime, timedelta, timezone

def parse_since(v: str):
    m = re.match(r"^(\d+)([smhd])$", v)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        seconds = {"s":1, "m":60, "h":3600, "d":86400}[unit] * n
        return datetime.now(timezone.utc) - timedelta(seconds=seconds)
    return datetime.fromisoformat(v.replace("Z","+00:00"))

def is_trace_line(obj: dict) -> bool:
    return "trace_id" in obj and "span_id" in obj and "operation_name" in obj

def matches(span: dict, args) -> bool:
    a = span.get("attributes") or {}
    if args.trace_id and span.get("trace_id") != args.trace_id: return False
    if args.user and a.get("user_id") != args.user: return False
    if args.app and a.get("app_id") != args.app: return False
    if args.agent and a.get("agent_name") != args.agent: return False
    if args.tool and a.get("tool_name") != args.tool: return False
    if args.status and span.get("status_code") != args.status: return False
    if args.operation and span.get("operation_name") != args.operation: return False
    if args.privileged and not a.get("privileged"): return False
    if args.min_duration_ms is not None and span.get("duration_ms",0) < args.min_duration_ms: return False
    # since / until は span.start_time で判定
    return True

def main():
    parser = argparse.ArgumentParser(...)
    # ... フラグ追加 ...
    args = parser.parse_args()

    spans: list[dict] = []
    for line in sys.stdin:
        # docker compose logs は "api-1  | <log line>" 形式なので prefix を剥がす
        if " | " in line:
            line = line.split(" | ", 1)[1]
        line = line.strip()
        # JSON でない行 (uvicorn 起動ログ等) をスキップ
        if not line.startswith("{"): continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not is_trace_line(obj): continue
        if not matches(obj, args): continue
        spans.append(obj)
        if args.format in ("pretty","tsv","ndjson"):
            emit_single(obj, args.format)
        if args.max and len(spans) >= args.max: break

    if args.format == "tree":
        emit_tree(spans, args.trace_id)
```

### 6.4 tree 出力 (--trace-id + --format tree)

```
trace_id: 550e8400-e29b-41d4-a716-446655440000
├── [OK]   request       duration=4521ms  user=0hya6in app=superchat
│   ├── [OK]   routing       duration=89ms    agent=researcher  stage=keyword
│   └── [OK]   sub_agent     duration=4100ms  agent=researcher  model=claude-sonnet-4-6  tokens_in=1250 tokens_out=430
│       ├── [OK]   tool_call     duration=1200ms  tool=web_search  args_bytes=42  result_bytes=8912
│       └── [ERR]  tool_call     duration=950ms   tool=db_query    status=permission denied
```

---

## 7. jq クエリ例集の構成 (`docs/trace-query-recipes.md`)

以下 7 セクションを含む Markdown ドキュメントを作成。各クエリは docker シェルで**コピペ実行**できる完全な形 (D-17)。

### 7.1 基本

```bash
# 生の JSONL を見る (api サービスのログから trace 行のみ抽出)
docker compose logs api 2>&1 | jq -cC 'select(.trace_id and .span_id)'
```

### 7.2 特定ユーザーの直近トレース

```bash
docker compose logs --since 1h api 2>&1 | jq -c 'select(.attributes.user_id == "0hya6in")'
```

### 7.3 失敗 trace 一覧

```bash
docker compose logs api 2>&1 | jq -c 'select(.status_code == "ERROR") | {trace_id, op:.operation_name, tool:.attributes.tool_name, msg:.status_message}'
```

### 7.4 privileged ツール使用履歴

```bash
docker compose logs api 2>&1 | jq -c 'select(.attributes.privileged == true) | {time:.start_time, user:.attributes.user_id, tool:.attributes.tool_name}'
```

### 7.5 特定 tool_name の duration 分布 (p50/p95/max)

```bash
docker compose logs api 2>&1 \
  | jq -c 'select(.attributes.tool_name == "web_search") | .duration_ms' \
  | sort -n \
  | awk 'BEGIN{c=0} {a[c++]=$1} END {print "count=",c,"p50=",a[int(c*0.5)],"p95=",a[int(c*0.95)],"max=",a[c-1]}'
```

### 7.6 trace_id でフルトレース再構築 (scripts/trace_query.py 推奨)

```bash
TRACE_ID=$(docker compose logs api 2>&1 | jq -r 'select(.attributes.user_id=="0hya6in") | .trace_id' | tail -1)
docker compose logs api 2>&1 | python3 scripts/trace_query.py --trace-id "$TRACE_ID" --format tree
```

### 7.7 Token 使用量集計 (spike 結果次第)

**[ASSUMED — §5 の結果に依存]** reasoning token が露出するなら:

```bash
docker compose logs api 2>&1 \
  | jq -c 'select(.operation_name == "sub_agent" and .attributes.user_id == "0hya6in")
           | {time:.start_time, model:.attributes.model_name,
              input:.attributes.input_tokens, output:.attributes.output_tokens}'
```

---

## 8. 既存 audit_log 削除の影響範囲

### 8.1 grep 調査結果 [VERIFIED: 2026-04-18]

`app/` 下の `audit_log` 参照は以下のみ:

| File | Line | 種別 |
|------|------|------|
| `app/api/main.py` | 52 | コメント (スキーマ説明) |
| `app/api/main.py` | 107-117 | `CREATE TABLE IF NOT EXISTS audit_log (...)` |
| `app/api/main.py` | 118-124 | `CREATE INDEX ... ON audit_log(...)` × 2 |

`app/` 下に **`INSERT INTO audit_log` / `SELECT ... FROM audit_log`** は**ゼロ**。audit_log は Phase 10 で DDL を敷いただけで書き込み・読み取り実装は一度もされていないことが確認できた。

テストでも唯一の参照:
- `tests/test_api_chat.py:100` コメント `# Phase 10: Tests for normalized schema (applications/threads/audit_log)`  → コメントのみ、テーブル直接参照なし

### 8.2 LangGraph checkpointer との独立性 [VERIFIED]

- LangGraph checkpointer は `langgraph-checkpoint-postgres` 提供のテーブル (`checkpoints`, `checkpoint_writes` 等) を `checkpointer.setup()` で独立管理 [CITED: `app/api/main.py:50`]
- `audit_log` テーブルは **lifespan 内の `conn.execute(...)` で独自作成**されたもので checkpointer とは無関係
- 削除時に checkpointer への影響は**ゼロ**

### 8.3 マイグレーション方針 (推奨)

`audit_log` 削除は以下 3 アプローチのいずれかを選ぶ。**推奨: アプローチ C**

| アプローチ | 内容 | 判断 |
|----------|------|------|
| A. `DROP TABLE audit_log` を lifespan に追加 | 次回起動で即削除 | 既存環境に副作用が出る。200 名規模で全員が同時に使うわけではないので回避 |
| B. 新規インストール時のみ DROP、既存は無視 | 実装が複雑 | テーブルが残り続ける — 退役テーブルとして気持ち悪い |
| **C. lifespan から CREATE TABLE / INDEX 文のみ削除、既存テーブルは手動 DROP 指示** | 現行運用環境への破壊的影響ゼロ、Phase 31 の PR message に「本番 DB で `DROP TABLE audit_log CASCADE;` を手動実行すること」と明記 | **採用** — `docs/phase-31-audit-log-removal.md` (または SUMMARY) に手動手順を残す |

**`applications(app_id)` の FK 考慮:** `audit_log` テーブルには `app_id TEXT REFERENCES applications(app_id)` FK がある (L110)。DROP 時に CASCADE 不要 (applications 側が削除されなければ audit_log 削除は単独で OK)。

**SQL 実行コマンド (運用者向け):**

```bash
docker compose exec postgres psql -U postgres -d postgres -c \
  "DROP TABLE IF EXISTS audit_log CASCADE;"
```

### 8.4 アプリ起動時の確認

- DDL 削除後、`app/api/main.py` を再起動してエラーが出ないことを確認 (lifespan が CREATE TABLE を呼ばないだけなので静かに成功するはず)
- `grep -r "audit_log" app/ tests/` で 0 件になることを確認 (main.py の削除されたコメントと DDL 以外は残らない)

---

## 9. 既存構造化 log 置換戦略

### 9.1 方針 (CONTEXT.md specifics 明示: 「互換 alias は残さない」)

**一括置換**を採用。`app/orchestrator/graph.py` の `event: routing` ログを新 OTEL span スキーマで完全置換する。

### 9.2 現行ログ → 新 span への対応表

| 現行ログ (graph.py) | 新 span (Phase 31) |
|---------------------|--------------------|
| L47 `{"event":"routing","stage":"keyword",...}` | `operation_name="routing"`, `attributes.stage="keyword"` |
| L61 `{"event":"routing","stage":"single",...}` | `operation_name="routing"`, `attributes.stage="single"` |
| L86 `{"event":"routing_fallback",...}` (warning) | `operation_name="routing"`, `status_code="ERROR"`, `status_message="unknown_agent=<chosen>"`, `attributes.stage="llm"`, `attributes.fallback=true` |
| L93 `{"event":"routing","stage":"llm",...}` | `operation_name="routing"`, `attributes.stage="llm"` |

### 9.3 実装タスク粒度 (plan 向け)

- Task A: `app/observability/trace.py` を新規作成 (writer 抽象、§2 のコード)
- Task B: `app/orchestrator/graph.py` の `RouterNode.__call__` を `async with trace_span("routing", ...)` でラップし、3 箇所の `logger.info(json.dumps(...))` を 1 箇所に統合。`routing_fallback` は status_code=ERROR + `stage=llm_fallback` で表現
- Task C: orchestrator_handler / langgraph_handler / debate_handler の最上位に `async with trace_span("request", ...)` を追加 (§4.4)
- Task D: SubAgent / ToolEnabledSubAgent / CodeActSubAgent / GemAgent の `run()` 先頭に `async with trace_span("sub_agent", ...)` 追加
- Task E: `TracedTool` クラス新規 + ToolEnabledSubAgent の `__init__` で tools を wrap
- Task F: CodeActSubAgent.run の execute_python 呼び出し箇所に tool_call span 追加
- Task G: iframe_rpc_handler の db_query / AI 呼び出しに tool_call span 追加 (+ 必要なら RPCContext 組み立て)
- Task H: `scripts/trace_query.py` 新規
- Task I: `docs/trace-query-recipes.md` 新規
- Task J: `app/api/main.py` から audit_log DDL 削除 + 手動 DROP 手順ドキュメント
- Task K: Copilot reasoning spike (§5.2) → span attribute 追加判断

**段階的 rollout はしない** (CONTEXT.md specifics)。

---

## 10. Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 + pytest-asyncio >= 0.25 [VERIFIED: pyproject.toml L30-31] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode=auto`, `testpaths=["tests"]`) |
| Quick run command | `uv run pytest tests/test_trace.py -x` (新規テストファイル) |
| Full suite command | `docker compose exec -T api uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-05 | writer 抽象が span dict を生成して logger.info に渡す | unit | `uv run pytest tests/test_trace.py::test_emit_basic_span -x` | ❌ Wave 0 |
| D-07 | OTEL span スキーマ (全 9 フィールド + attributes) が揃う | unit | `uv run pytest tests/test_trace.py::test_span_schema_complete -x` | ❌ Wave 0 |
| D-07 | status_code が例外時に ERROR、正常時に OK | unit | `uv run pytest tests/test_trace.py::test_status_code_on_exception -x` | ❌ Wave 0 |
| D-08 | trace_id が caller 指定値と一致、span_id が 16 hex | unit | `uv run pytest tests/test_trace.py::test_trace_span_ids -x` | ❌ Wave 0 |
| D-08 | parent_span_id が ContextVar から伝搬 | unit | `uv run pytest tests/test_trace.py::test_parent_span_propagation -x` | ❌ Wave 0 |
| D-09 | 共通 4 attributes (user_id/app_id/agent_name/model_name) 欠落なし | unit | `uv run pytest tests/test_trace.py::test_common_attributes -x` | ❌ Wave 0 |
| D-10 | 3 経路すべて tool_call span を emit | integration | `docker compose up -d && 本文§10.3` | N/A (手順) |
| D-11 | TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS で truncate | unit | `uv run pytest tests/test_trace.py::test_truncate_env_vars -x` | ❌ Wave 0 |
| D-12 | privileged attribute が sandbox_exposed=false で true になる | unit | `uv run pytest tests/test_traced_tool.py::test_privileged_from_yaml -x` | ❌ Wave 0 |
| D-13 | user_input_prefix / llm_output_prefix が 200 字で切られる | unit | `uv run pytest tests/test_trace.py::test_prefix_200 -x` | ❌ Wave 0 |
| D-14 | SubAgent span に token usage attribute が載る | integration | `uv run pytest tests/test_sub_agent_trace.py -x` (mock Copilot SDK) | ❌ Wave 0 |
| D-15 | reasoning spike 成果物が docs/ にある | manual | `ls docs/phase-31-reasoning-token-spike.md` | N/A |
| D-02 | `audit_log` DDL が main.py から消える | grep | `! grep -q audit_log app/api/main.py` | N/A |
| D-02 | audit_log 削除後にアプリ起動成功 | integration | `docker compose up -d api && curl localhost:8000/health` | N/A (手順) |
| D-16/17 | scripts/trace_query.py --trace-id で tree が出る | CLI | `本文§10.4` | N/A |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_trace.py tests/test_traced_tool.py -x` (trace 関連の unit test のみ高速実行)
- **Per wave merge:** `docker compose exec -T api uv run pytest tests/ -x` (全スイート)
- **Phase gate:** 全スイート green + §10.3 integration + §10.4 CLI + §10.5 audit_log 削除 validation 完了

### Wave 0 Gaps

- [ ] `tests/test_trace.py` — writer 抽象の unit test (span schema / status / parent propagation / truncate / prefix)
- [ ] `tests/test_traced_tool.py` — TracedTool wrapper の unit test (privileged / args_bytes / result_bytes / success flag)
- [ ] `tests/test_sub_agent_trace.py` — ChatCopilot mock で usage / reasoning を emit させて SubAgent span に載ることを確認
- [ ] `tests/conftest.py` 追加 fixture: `capture_trace_logs` — pytest caplog + JSONL parser を組み合わせて span dict のリストを返す fixture
- [ ] `pyproject.toml` 変更は不要 (pytest / pytest-asyncio は既にある)

### 10.3 integration validation 手順 (docker compose 必須)

```bash
# 前提: docker compose up -d
# 1. Chat 経路 (軸 A: routing + sub_agent、軸 B 経路 1 に該当しない場合は経路 1 だけ検証できない)
curl -X POST http://localhost:8000/api/chat -H "Cookie: jwt=..." \
  -d '{"message":"東京の天気を教えて","thread_id":"integration-test-1"}'
docker compose logs --since 30s api | \
  jq -c 'select(.trace_id) | select(.attributes.app_id=="chat")' | \
  tee /tmp/trace-chat.jsonl
# 期待: operation_name が request / routing / sub_agent 並ぶ

# 2. SuperChat + web_search (軸 B 経路 1: ToolEnabledSubAgent)
# researcher エージェントに web_search をさせる入力を投げる
# docker compose logs | jq 'select(.operation_name=="tool_call" and .attributes.tool_name=="web_search")'
# 期待: parent_span_id が直前の sub_agent span の span_id を指す

# 3. CodeAct 経路 (軸 B 経路 2)
# execute_python を呼ばせる入力を投げる
# 期待: operation_name=tool_call, tool_name=execute_python, privileged=true

# 4. Canvas iframe RPC (軸 B 経路 3)
# Canvas アプリから query() を叩く (ブラウザ手動 or curl で iframe_rpc endpoint 叩く)
# 期待: operation_name=tool_call, tool_name=db_query, app_id=canvas
```

### 10.4 CLI validation 手順

```bash
# trace_id を 1 つ抽出
TRACE_ID=$(docker compose logs --since 5m api 2>&1 | \
  jq -r 'select(.trace_id) | .trace_id' | head -1)
# tree 表示
docker compose logs --since 5m api 2>&1 | \
  python3 scripts/trace_query.py --trace-id "$TRACE_ID" --format tree
# 期待: ツリー構造で request > routing / sub_agent > tool_call の階層が表示される
```

### 10.5 audit_log 削除 validation 手順

```bash
# 1. コード側から audit_log が完全消去されていることを確認
! grep -rn "audit_log" app/ scripts/ tests/ || echo "FAIL: audit_log 残存"
# (test ファイル内のコメント 1 箇所は Phase 31 で削除対象)

# 2. アプリ起動成功
docker compose up -d api
sleep 5
curl -sf http://localhost:8000/health || echo "FAIL: /health 応答しない"

# 3. (運用者ジョブ) 本番 DB で手動 DROP
docker compose exec postgres psql -U postgres -d postgres -c \
  "DROP TABLE IF EXISTS audit_log CASCADE;"
```

---

## 11. Landmines (落とし穴)

### 11.1 LangGraph async 文脈での contextvars 伝搬の罠

- **罠:** `asyncio.create_task(..., context=None)` で新規タスクを作ると **呼び出し時点の Context がコピー**されるが、コピーなので**子 task 内の `_current_span_id.set(...)` は親 task に反映されない**。LangGraph は内部で `create_task` を使う場合があり、node の前後で親 span_id が意図通り見えないケースが出る。
- **検出:** ContextVar の伝搬テストを unit で書き、`asyncio.create_task` を挟んでも親の span_id が見えるか確認する。
- **対策:** 実用上は 1 本の request/trace は同じ task 内で完結 (LangGraph compile graph の ainvoke は単一 task) するので問題は起きにくいが、**`astream_events` を使うパスでは nested task が増える**。iframe_rpc_handler や orchestrator_handler で nested task が生成されるかは Plan の verify 段階で確認する。

### 11.2 docker logs の JSON パース破壊

- **罠:** `logger.info(json.dumps(x))` が多行 (例: reasoning_text に改行含む) になると docker logs は 1 行ずつ JSON として読もうとして壊れる。
- **対策:**
  - `json.dumps(x, ensure_ascii=False)` のみで改行は `\n` にエスケープされる (ensure_ascii=False でも改行は `\n` のまま)
  - 生の改行を含む文字列は attribute 側で必ず `\n` エスケープされた 1 行 JSON になるよう `json.dumps` を使う (直接 `logger.info(f"{x}")` はしない)
  - trace_query.py 側で `line.strip()` + 先頭が `{` の行のみ処理
- **検証:** reasoning_text に改行・ダブルクォート・バックスラッシュ込みの文字列を渡した unit test で span JSON が `json.loads(line)` で re-parse できることを assert

### 11.3 Copilot SDK Technical Preview 版のレスポンス破壊的変更

- **罠:** `github-copilot-sdk==0.2.0` は pyproject で pin 済みだが、今後 0.3.x に上げる際に `ASSISTANT_USAGE` の schema が変わる可能性は高い。
- **対策:** 
  - span attribute への落とし込みは `getattr(data, "input_tokens", None)` のように**個別フィールド取得 + None 許容**にする (辞書コピーではない)
  - spike 時点で取れた field 名を `docs/phase-31-reasoning-token-spike.md` に記録し、将来 SDK 更新時の diff 確認ポイントにする
  - `app/providers/copilot.py` が **SDK の唯一の接点** (Phase 1 から厳守) なのでそこで吸収する

### 11.4 audit_log 削除が既存 docker volume に残存

- **罠:** `app/api/main.py` から DDL を消しても、既存の `postgres-data` volume には `audit_log` テーブルが残り続ける。テーブルが残り続けると将来「使われない空テーブル」として混乱の原因。
- **対策:** §8.3 アプローチ C — PR message / SUMMARY に手動 DROP コマンドを明記。`scripts/drop_audit_log.sh` を 1 行で追加してもよい。

### 11.5 trace_query.py の JSON パース堅牢性

- **罠:** docker compose logs の出力には `api-1  | ` のような prefix が先頭に付く。uvicorn や arq の起動メッセージ (非 JSON) も混ざる。FastAPI 自身の INFO 行 (`INFO:     127.0.0.1:...`) も混ざる。
- **対策:** 
  - prefix は ` | ` で split (§6.3)
  - 先頭が `{` でない行はスキップ
  - `json.JSONDecodeError` を握りつぶす (continue)
  - span かどうかは `"trace_id" in obj and "span_id" in obj and "operation_name" in obj` の 3 条件で判定

### 11.6 reasoning token が取れない場合の graceful degrade

- **罠:** Copilot SDK が `ASSISTANT_USAGE` を emit しないモデルで None が attribute に入ると、jq の集計が落ちる (`null + null` 等)
- **対策:** 
  - None の attribute は **dict に入れない** (キーごと omit) 設計にする
  - jq 側で `select(.attributes.input_tokens != null)` を必ず入れる (recipe に明記)

### 11.7 iframe_rpc 経路の RPCContext 未整備の可能性

- **[ASSUMED]** `app/api/routes/iframe_rpc.py` (ルート) は未調査。Phase 11 の `RPCContext` 整備がこの経路まで波及しているか、あるいは iframe_rpc_handler 内で独自に trace_id を抽出する必要があるかは、Plan の task 分割時に確認する (もし未整備なら Phase 31 内の小タスクとして実装する)

### 11.8 ToolNode 内の並行実行時の span 重複/欠落

- **罠:** LangGraph ToolNode は同時に複数 tool を `asyncio.gather` で呼ぶことがある (単一 LLM response で `tool_calls` が複数返る場合)。その場合 `_current_span_id` がどちらの親を指すか曖昧になる。
- **検証:** TracedTool の内側では `trace_span` が毎回新しい span_id を生成し、**parent_span_id は tool_node 実行開始時点の `_current_span_id`** (= sub_agent) を指すので、兄弟 tool_call span として正しく emit される。ContextVar の reset は `finally` ブロックで安全に行われる (§2.1 の実装)。
- **結論:** 問題なし。ただし unit test で `asyncio.gather(traced_tool1.ainvoke(...), traced_tool2.ainvoke(...))` のシナリオを書いておく。

### 11.9 `_normalize_tool_result` との関係

- **罠:** CodeActSubAgent は既に `_normalize_tool_result` で結果を string 化するが、span の `result_bytes` はどの時点の bytes を指すべきか (生の dict か、normalize 後か)
- **決定:** **normalize 後の string の byte 数**を記録 (運用者が見るのは normalize 後の表現なので)

---

## 12. 推奨 writer 設置先

**採用: `app/observability/`**

| 候補 | 利点 | 欠点 | 判断 |
|------|------|------|------|
| `app/observability/` (新規ディレクトリ) | 将来の metrics / logs 抽象の置き場として拡張しやすい。責務が明確 | 新規ディレクトリ 1 つ追加 | **✅ 採用** |
| `app/orchestrator/trace.py` | 既存ディレクトリで済む、ファイル 1 個追加のみ | orchestrator は LangGraph グラフ構築層。observability は横断的関心で tier mismatch。iframe_rpc / worker からも参照するので orchestrator 配下にあると参照の方向性が歪む | ❌ |
| `app/utils/trace.py` | utils は既存 | observability は utils (汎用) というより application concern。テストも utils に混ざる | ❌ |

**配置構成:**

```
app/observability/
├── __init__.py
├── trace.py          — trace_span context manager, SpanDict, ContextVar helpers
├── traced_tool.py    — TracedTool (BaseTool wrapper for 軸 B 経路 1)
└── config.py         — TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS / PRIVILEGED_TOOL_NAMES を env から読む helpers
```

---

## Project Constraints (from CLAUDE.md)

- **応答言語:** すべて日本語 (本 RESEARCH.md も日本語)
- **ブランチ必須:** GSD 実行時は main 上で作業しない (Phase 31 は `gsd/phase-31-agent-mcp-observability` ブランチ上)
- **Merge Safety Rules:** 削除行数 > 追加行数 × 2 なら要精査。audit_log 削除は純粋な削除 + JSONL writer 新規追加なので、追加行数の方が上回る想定
- **MCP Tool Catalog:** `config/mcp_tools.yaml` が唯一のソース。Phase 31 では `sandbox_exposed:false` の読み取りに使うのみで、YAML 自体は変更しない。もし span attribute 用に何か付け足す必要が出ても YAML には入れない (D-11 で明言)
- **生成ファイル変更禁止:** `mcp_server/tools/mcp_helper.py` / `static/js/tool-catalog-generated.js` / `docs/mcp-tools.md` は Phase 31 のスコープでは変更しない
- **ADR INDEX 自動生成 hook:** Phase 31 完了時に ADR 追加するなら `scripts/install-hooks.sh` を有効化してから ADR ファイルを作る
- **squash merge:** Phase 31 の PR は squash merge で main に取り込む

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | trace_query.py, writer | ✓ (docker image) | 3.12 | — |
| `logging` stdlib | writer emit | ✓ | - | — |
| `contextvars` stdlib | parent span 伝搬 | ✓ | - | — |
| pytest / pytest-asyncio | Wave 0 unit tests | ✓ | >=8.0 / >=0.25 | — |
| docker compose | integration / logs 取得 | ✓ | - | — |
| `jq` | docs の recipe 実行 | ✓ (host 想定、missing なら apt install) | - | python3 + json.tool |
| `github-copilot-sdk` 0.2.0 | reasoning spike | ✓ (pinned) | 0.2.0 | N/A — spike 前提 |
| `opentelemetry-sdk` | (NOT required) | — | — | D-05 で明示的に不要 |

**Missing dependencies with no fallback:** なし
**Missing dependencies with fallback:** なし

---

## Architecture Patterns

### System Architecture Diagram

```
  HTTP /api/chat (chat.py)
          │   RPCContext(correlation_id=uuid4)
          ▼
  arq enqueue (worker)
          │
          ▼ ─────────────────────── trace_span("request") start ────┐
  TaskHandler (orchestrator_handler.py / langgraph_handler.py /    │
              debate_handler.py / iframe_rpc_handler.py)           │
          │                                                         │
          ▼ ────────── trace_span("routing") [only orchestrator] ─┐ │
    RouterNode (graph.py)                                          │ │
          │  emit routing span with stage=keyword/single/llm       │ │
          ▼                                                         │ │
    chosen SubAgent node                                            │ │
          │                                                         │ │
          ▼ ────────── trace_span("sub_agent") ────────┐            │ │
    SubAgent.run / ToolEnabledSubAgent.run /           │            │ │
    CodeActSubAgent.run / GemAgent.run                 │            │ │
          │                                            │            │ │
          │  ┌──────────────────────────────────────┐  │            │ │
          │  │ 軸 B 経路 1 (ToolEnabledSubAgent)    │  │            │ │
          │  │ build_react_graph → ToolNode         │  │            │ │
          │  │ TracedTool wraps each BaseTool       │  │            │ │
          │  │ trace_span("tool_call") per tool     │  │            │ │
          │  └──────────────────────────────────────┘  │            │ │
          │  ┌──────────────────────────────────────┐  │            │ │
          │  │ 軸 B 経路 2 (CodeActSubAgent)        │  │            │ │
          │  │ execute_python.ainvoke direct call   │  │            │ │
          │  │ trace_span("tool_call") around       │  │            │ │
          │  └──────────────────────────────────────┘  │            │ │
          │                                            │            │ │
          ▼ ────────────────────────────────────────── ┘            │ │
         END                                                         │ │
                                                                     │ │
  iframe-rpc /api/iframe_rpc (separate route)                        │ │
    IframeRpcHandler._handle_query → db_query MCP tool               │ │
    ┌──────────────────────────────────────────────┐                 │ │
    │ 軸 B 経路 3 (iframe_rpc_handler)             │                 │ │
    │ trace_span("tool_call") around tool.ainvoke  │                 │ │
    └──────────────────────────────────────────────┘                 │ │
                                                                     │ │
          ▼                                                           │ │
    Python logging → docker compose logs stdout ─────────────────────┴─┘
          │
          ▼
    docker logging driver (json-file, max-size 50m, max-file 10) — quick 260418-tin
          │
          ▼
    Operator:  docker compose logs api | jq ...
               docker compose logs api | python3 scripts/trace_query.py --trace-id ...
```

### Recommended Project Structure

```
app/
├── observability/            # NEW
│   ├── __init__.py
│   ├── trace.py              — trace_span / ContextVar / SpanDict
│   ├── traced_tool.py        — TracedTool (BaseTool wrapper, 軸 B 経路 1)
│   └── config.py             — env var accessors (TRACE_ARGS_MAX_CHARS etc.)
├── orchestrator/
│   ├── graph.py              — RouterNode 置換 (event:routing → routing span)
│   ├── tool_agent.py         — ToolEnabledSubAgent に TracedTool + sub_agent span 追加
│   ├── codeact_agent.py      — execute_python 呼び出しに tool_call span 追加
│   ├── agent.py              — SubAgent.run に sub_agent span 追加
│   └── gem_agent.py          — GemAgent.run に sub_agent span 追加
├── jobs/handlers/
│   ├── orchestrator_handler.py — request span 追加
│   ├── langgraph_handler.py    — request span 追加
│   ├── debate_handler.py       — request span 追加
│   └── iframe_rpc_handler.py   — request span + tool_call span 追加 + correlation_id 整備確認
├── api/main.py               — audit_log DDL 削除 (L52 コメント + L105-124)
└── providers/copilot.py      — (spike 結果次第) ASSISTANT_USAGE / ASSISTANT_REASONING ハンドラ追加

scripts/
└── trace_query.py            — NEW (argparse ベース stdin JSONL フィルタ)

docs/
├── trace-query-recipes.md    — NEW (jq クエリ例集)
└── phase-31-reasoning-token-spike.md  — NEW (spike 成果物)

tests/
├── test_trace.py             — NEW (writer 抽象 unit)
├── test_traced_tool.py       — NEW (TracedTool unit)
└── test_sub_agent_trace.py   — NEW (Copilot mock で usage 確認)
```

### Pattern 1: trace_span context manager

**What:** async with 内の処理を 1 個の span として記録
**When to use:** 3 層のいずれかのスコープを計測する全箇所
**Example:**
```python
# Source: §2.1 本 research 自作
from app.observability.trace import trace_span

async with trace_span(
    "sub_agent",
    trace_id=ctx.correlation_id,
    attributes={"user_id": ctx.user_id, "app_id": ctx.app_id,
                "agent_name": self.name, "model_name": self._llm.model},
) as span:
    result = await self._run_inner(state)
    span.set_attribute("turn_count", self._turn_count)
    span.set_attribute("input_tokens", captured_usage.get("input_tokens"))
```

### Pattern 2: TracedTool wrapper

**What:** LangChain BaseTool の薄い wrapper で tool_call span を自動 emit
**When to use:** `ToolEnabledSubAgent` (軸 B 経路 1) の tools 構築時
**Example:**
```python
# Source: §3.1 本 research 自作
from app.observability.traced_tool import TracedTool

tools = [t for t in mcp_tools if t.name in agent_tool_names]
# wrap with trace
traced = [TracedTool(t, trace_id_getter=lambda s: s["context"].correlation_id,
                     common_attrs_getter=...) for t in tools]
self._tool_node = ToolNode(traced)
```

### Anti-Patterns to Avoid

- **Anti-pattern:** `logger.info(f"tool {name} ran in {duration}ms")` のようなフリーテキストログ。jq で抽出できない → span dict JSONL のみ使用
- **Anti-pattern:** `trace_span` の外で `logger.info(json.dumps({"event":"legacy"...}))` を残す (互換 alias)。CONTEXT.md specifics で明示禁止
- **Anti-pattern:** span attribute に生メッセージ本文を全量入れる。D-13 で 200 字 prefix 限定
- **Anti-pattern:** config/mcp_tools.yaml に redact 指定を追加する。D-11 で全ツール一律 env var 方式固定

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON 構造化ログ | カスタムログフォーマッタ | `json.dumps(asdict(span), ensure_ascii=False, default=str)` | stdlib で十分、default=str で datetime/Decimal 対応 |
| 親 span 伝搬 | thread-local + async 互換レイヤー | `contextvars.ContextVar` | 既に `tool_context.py` で実績あり [VERIFIED] |
| monotonic 時間計測 | `time.time()` 差分 | `time.perf_counter()` | wall-clock のジャンプ影響を受けない |
| span dataclass | dict 手書き | `@dataclass SpanDict` + `asdict` | 型補完 + mypy で schema drift 検知 |
| truncate 閾値 | ハードコード | `os.environ.get("TRACE_ARGS_MAX_CHARS", "500")` | D-11 で env var 固定 |
| OTLP exporter | 自作 | (Phase 31 は追加しない) | D-05 |

**Key insight:** Phase 31 のコア価値は「writer 抽象 + 3 経路への適用」であり、writer 実装そのものは約 100 行程度の薄いコードで済む。OpenTelemetry SDK を導入しない判断 (D-05) は**運用簡便性を優先**した正解で、同等の機能を stdlib + 100 行で実現できる。

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PostgreSQL audit_log (未使用) | JSONL on stdout | Phase 31 (2026-04-18) | 書き込みコード追加せずに済んでいたため副作用なし、DDL 削除のみ |
| `{"event":"routing",...}` ad-hoc JSON log | OTEL span-like `{"operation_name":"routing","trace_id":...}` | Phase 31 | 既存 docs の jq recipe は書き換えが必要 |
| ツール呼び出しは何も記録されない | 3 経路統一 tool_call span | Phase 31 | 全ツール使用が可視化 |

**Deprecated/outdated:**
- `app/api/main.py:105-124` audit_log DDL + INDEX → Phase 31 で削除
- `app/orchestrator/graph.py:47-101` 旧 routing ログ → Phase 31 で OTEL span に置換 (互換 alias 残さない)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | iframe_rpc 経路で RPCContext の correlation_id が job dict に現状載っているかは未確認 | §3.3, §11.7 | Phase 11 の整備が iframe_rpc まで波及していなければ、Plan に correlation_id 伝搬の小タスクを追加する必要がある。最大でもコード変更 5-10 行 |
| A2 | reasoning token が実際にアプリ経由の質問で出るかは未検証 (SDK field は存在するが、モデル次第で null の可能性) | §5, §7.7 | 全モデルで null なら token usage のみ span に載る。Phase 31 は MVP として可用な分だけ載せる設計なので problem なし |
| A3 | ContextVar が LangGraph の全 async パスで伝搬する (`astream_events`, `ainvoke` 両方) | §4.2, §11.1 | 伝搬しない場合は `state["configurable"]` 経由に切り替える bail-out プランが必要 (D-06 は「state 追加は最小限」なのでやむなし) |
| A4 | audit_log テーブルを削除しても既存 PostgreSQL volume に副作用なし | §8 | grep で書き込み 0 件確認済みなので risk 低 |
| A5 | Copilot SDK 0.2.0 で spike した reasoning/usage イベントが 0.3.x でも互換 | §11.3 | 破壊的変更は `app/providers/copilot.py` 内で吸収、影響範囲は 1 ファイル |

---

## Open Questions (RESOLVED)

> すべての Open Questions は planning 時点で decision を確定済み。Phase 31 実装中は以下の解決方針で進める。

1. **iframe_rpc 経路の RPCContext 整備状況**
   - **What we know:** `app/jobs/handlers/iframe_rpc_handler.py` 内では `params.get("user",...)` を直接読む実装 (Phase 11 の RPCContext 導入以前の可能性)
   - **What's unclear:** `iframe_rpc` ルート → job enqueue 時に `correlation_id` が job dict に載るか、それとも不在か
   - **Recommendation:** Plan Task G (iframe_rpc 経路 tool_call span) の冒頭で `app/api/routes/iframe_rpc.py` を読んで確認。もし未整備なら 5-10 行の correlation_id 追加タスクを Plan に含める
   - **RESOLVED:** Plan 31-05 Task 1 で調査・必要なら job dict に `correlation_id` 追加を明示。実装時に対応する。

2. **request span を追加するかどうか**
   - **What we know:** D-06 は「3 層」と明言 (routing / sub_agent / tool_call)
   - **What's unclear:** その 3 層の**外側** (request root) は追加してよいか
   - **Recommendation:** 追加を推奨 (§4.4)。trace tree が明確になり、orchestrator 以外の経路 (langgraph_handler / debate_handler / iframe_rpc_handler) で routing が存在しない場合のトップレベル span として機能する。plan-check で user confirm 取る
   - **RESOLVED:** 追加する方針で plan 31-04 Task 3 / 31-05 Task 3 に `request` span emit を組み込み済み。

3. **CodeAct 内の sandbox → MCP call の個別 span 化**
   - **What we know:** §3.2 アプローチ 2 (MCP サーバー側で span emit) は実装コストが大きい
   - **Recommendation:** Phase 31 スコープ外。execute_python の stdout に含まれる mcp_helper 実行結果で間接的に把握可能。Deferred Ideas に追加
   - **RESOLVED:** Phase 31 スコープ外 (Deferred)。CodeAct agent レベルの tool_call span で十分とし、mcp_helper_utils._call_tool 側の子 span は将来拡張。

4. **reasoning_text / reasoning_opaque を span に載せるか**
   - **What we know:** D-13 は user_input/llm_output を 200 字 prefix に限定。reasoning は別扱い
   - **Recommendation:** スパイク結果を見てから判断。本文全量 (`reasoning_text` まるごと) を span attribute に入れると 1 span が巨大化するリスク。`reasoning_chars` (int) + `reasoning_prefix` (200 字) で妥協案
   - **RESOLVED:** Plan 31-01 spike 結果次第で決定。spike で `ASSISTANT_REASONING` が露出すれば `reasoning_chars` (int) + `reasoning_prefix` (200 字) を追加。露出しなければ Phase 31 スコープ外。

---

## Sources

### Primary (HIGH confidence)

- **[VERIFIED: 直接 Python 実行]** `github-copilot-sdk==0.2.0` の `copilot.generated.session_events.SessionEventType` と `Data` dataclass フィールド一覧 (2026-04-18)
- **[VERIFIED: grep]** `app/` 配下の audit_log 参照は `app/api/main.py` L52, 107-124 のみ、書き込み・読み取り 0 件 (2026-04-18)
- **[VERIFIED: コード読み]** `app/orchestrator/tool_context.py` の ContextVar 実績、`app/orchestrator/graph.py:47-101` の既存 routing log パターン、`app/orchestrator/context.py` の `RPCContext.correlation_id` (Phase 11)
- **[VERIFIED: pyproject.toml]** pytest>=8.0 / pytest-asyncio>=0.25 / github-copilot-sdk==0.2.0 / langgraph>=1.1.4 の version pin

### Secondary (MEDIUM confidence)

- **[CITED: OpenTelemetry spec]** https://opentelemetry.io/docs/specs/otel/trace/api/ — Span field 名 / StatusCode enum / timestamp format
- **[CITED: Python docs]** https://docs.python.org/3/library/contextvars.html — ContextVar の asyncio Task 間伝搬挙動

### Tertiary (LOW confidence)

- **[ASSUMED — spike 未実施]** Copilot SDK が **実際に** ASSISTANT_USAGE / ASSISTANT_REASONING を emit するかは、フィールドが schema に存在することは確認済みだが、アプリで実際に呼んで confirmation は未実施。§5.2 のスパイクで確定する

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib のみ、すべて VERIFIED
- Architecture (writer + 3 経路 + 親子伝搬): HIGH — 既存パターン踏襲、schema は OTEL 公式を citation
- Copilot SDK reasoning/usage 露出: HIGH — SDK schema を直接確認済 (actual emission はスパイクで confirmation)
- audit_log 削除影響範囲: HIGH — grep で確認済
- iframe_rpc correlation_id 整備状況: MEDIUM — Plan 実行時に個別確認

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (1 month — Copilot SDK Technical Preview のため version 更新に注意)

---

## RESEARCH COMPLETE

**Phase:** 31 - エージェント実行・MCP ツール利用の observability 基盤
**Confidence:** HIGH

### Key Findings

1. **Copilot SDK 0.2.0 で reasoning / usage token は既に露出している** — `ASSISTANT_USAGE` / `ASSISTANT_REASONING` / `ASSISTANT_REASONING_DELTA` イベントと `input_tokens` / `output_tokens` / `reasoning_text` / `reasoning_id` フィールドが schema に存在 (VERIFIED)。Phase 31 スコープ内で token 計測を span attribute に載せる価値が高い。
2. **既存 ContextVar パターン (`app/orchestrator/tool_context.py`) が Phase 31 の親 span_id 伝搬にそのまま使える** — LangGraph async 文脈で動作実績あり。`state["configurable"]` に何も追加せず D-06 の「state 追加は最小限」要件を満たせる。
3. **audit_log 削除は完全に安全** — grep で書き込み・読み取りコード 0 件確認。DDL/INDEX の削除のみで副作用なし。ただし既存 volume のテーブルは手動 DROP 必要 (運用者向け SQL を SUMMARY に残す)。
4. **writer 抽象は `app/observability/trace.py` の 100 行程度 + `TracedTool` wrapper クラスで完結** — stdlib (`logging` / `contextvars` / `uuid` / `dataclasses` / `datetime` / `time.perf_counter`) のみ。`opentelemetry-sdk` は不要 (D-05)。
5. **3 経路の wrap 方式は (1) TracedTool で tools を包む + ToolNode で使う / (2) CodeAct の execute_python 呼び出しを直接 async with / (3) iframe_rpc の tool.ainvoke を直接 async with、で統一済み。**

### File Created

`.planning/phases/31-agent-mcp-observability/31-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | stdlib のみ、すべて VERIFIED |
| Architecture (writer / 3 層 span / 3 経路) | HIGH | 既存 ContextVar パターン踏襲、OTEL spec を citation |
| Copilot SDK reasoning/usage 露出 | HIGH | SDK schema 直接確認済 (実 emission スパイクで更に confirmation) |
| audit_log 削除影響 | HIGH | grep で 0 件 |
| Pitfalls | HIGH | LangGraph async / docker logs / Tech Preview / volume 残存の 8 項目を列挙 |
| iframe_rpc 経路 correlation_id 整備状況 | MEDIUM | 未確認 (Plan Task G 冒頭で確認予定) |

### Open Questions (to be decided at plan time)

1. iframe_rpc 経路の RPCContext 整備が未完なら小タスク追加
2. request span (3 層の外側) を追加してよいか (推奨: YES)
3. reasoning_text をどれだけ span に載せるか (推奨: chars のみ + prefix 200)

### Ready for Planning

Research complete. Planner は以下を前提に PLAN.md を構成できる:

- 11 個の実装タスク (A〜K) が §9.3 に列挙済み
- Validation Architecture (§10) に Wave 0 テストファイル 3 個 + integration 手順が定義済み
- Landmines (§11) に 9 個の具体的な罠と回避策
- Copilot reasoning spike は Plan 01 の最初に配置し、結果を以降のタスクに反映する流れを推奨
