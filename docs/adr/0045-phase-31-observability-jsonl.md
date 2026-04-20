# 0045. Phase 31 — エージェント実行・MCP ツール利用の observability 基盤 (stdout JSONL + OTEL span-like schema)

**Date:** 2026-04-18
**Status:** Accepted
**Related:** ADR-0024 (sandbox_exposed フラグ), ADR-0041 (CodeAct 直接実行), ADR-0044 (MCP tool catalog single source of truth)

## Context

Phase 31 で「エージェント実行（軸 A: routing / ReAct / LLM）と MCP ツール呼び出し（軸 B: ToolEnabledSubAgent / CodeActSubAgent / iframe_rpc の 3 経路）」を統一的に記録・閲覧できる observability 基盤を構築する必要があった。運用コンテキストは 200 名規模・社内利用。既存の `docker compose logs` + 構造化 JSON ログ（`app/orchestrator/graph.py` の `event: routing` パターン）をベースに、OTEL Collector / Loki / Jaeger / Tempo 等の外部集約基盤を追加せず、stdout の OTEL span-like JSONL に寄せる方針を採用した。既存の未使用 PostgreSQL テーブル `audit_log` (Phase 10 以来読み書きゼロ) は退役させる。

Phase 31 着手前の課題:

- エージェント実行（routing / SubAgent run / tool_call）が個別の `logger.info(json.dumps({...}))` で散在し、`trace_id` による親子関係の紐付けがなかった
- ToolEnabledSubAgent / CodeActSubAgent / iframe_rpc_handler の 3 経路は全て MCP ツール呼び出しを行うが、記録形式がバラバラで統一検索が困難だった
- `config/mcp_tools.yaml` の `sandbox_exposed=false` フラグ（ADR-0024）は ToolRegistry 検証に使われていたが、実行時の privileged 呼び出しの監査には使われていなかった
- Copilot SDK 0.2.0 (Technical Preview) の ASSISTANT_USAGE / ASSISTANT_REASONING イベントが SubAgent run の詳細として露出しているか未調査だった

## Decision

以下を採用する:

1. **Writer 抽象** (`app/observability/trace.py`): `async with trace_span(operation_name, trace_id, attributes)` context manager + `ContextVar` ベースの親 span 伝搬。`logger.info(json.dumps(asdict(span_dict), ensure_ascii=False, default=str))` で stdout に 1 行 1 span を emit。新規インフラ依存ゼロ、stdlib のみ。

2. **Span schema** (OTEL span-like): `trace_id` / `span_id` / `parent_span_id` / `operation_name` / `start_time` / `end_time` / `duration_ms` / `status_code` / `status_message` / `attributes` の 10 フィールド。`trace_id = RPCContext.correlation_id` (Phase 11 の UUID4 を再利用)。`span_id = uuid4().hex[:16]`（OTEL spec 準拠の 16-char）。

3. **3 層 span**: `request` (handler 全体) → `routing` / `sub_agent` (並列兄弟) → `tool_call`。ReAct の各 LLM turn は別 span にせず、SubAgent span の `message_count` attribute で表現する。

4. **3 経路統合 (軸 B)**: `TracedTool` wrapper (ToolEnabledSubAgent) + `execute_python` 直接 wrap (CodeActSubAgent) + `tool.ainvoke` 直接 wrap (iframe_rpc_handler) の 3 経路を同一 `tool_call` span schema で emit。`privileged` attribute は `config/mcp_tools.yaml` の `sandbox_exposed=false` 判定 (ADR-0024 の延長)。

5. **PII / 秘匿情報の保護**: `user_input_prefix` / `llm_output_prefix` は 200 字、`args_prefix` / `result_prefix` は env var `TRACE_ARGS_MAX_CHARS` (default 500) / `TRACE_RESULT_MAX_CHARS` (default 1000) で truncate。全ツール一律制御（ツール個別の redact 設定は `config/mcp_tools.yaml` に入れない）。

6. **既存 PostgreSQL `audit_log` テーブル退役**: `app/api/main.py` の DDL / INDEX を削除。新規 JSONL 一本化方針を明示。既存データベースの `DROP TABLE` は手動運用として SUMMARY に記載。

7. **閲覧手段**: `scripts/trace_query.py` CLI (stdlib のみ、argparse + stdin JSONL) + `docs/trace-query-recipes.md` (jq レシピ集)。管理 UI / admin API は Phase 31 では作らない。

## Consequences

### Positive
- 新規 infra 依存ゼロで即運用開始できる
- 既存 `docker compose logs --follow` + jq / `scripts/trace_query.py` で完結
- 将来 OTLP exporter を追加する際は writer の `_emit` を差し替えるだけで済む（D-05）
- `audit_log` の未使用テーブル削除で DB スキーマが純化される
- ToolEnabledSubAgent / CodeActSubAgent / iframe_rpc_handler の 3 経路すべてが統一 schema でトレースできる
- Copilot SDK の ASSISTANT_USAGE / ASSISTANT_REASONING イベント（spike VERIFIED、Plan 01）を SubAgent span attribute に取り込めるようになった

### Negative
- docker logs rotation (quick 260418-tin で設定済、max-size: 50m × max-file: 10) に依存するため、長期保存は別途 volume / external shipping が必要 (Deferred)
- 可視化は CLI + jq のみで、時系列グラフ等は作れない (Deferred)
- 既存環境の `audit_log` テーブルは手動で `DROP TABLE IF EXISTS audit_log CASCADE;` を運用者が実行する必要がある（コード側では削除しない、運用影響を避けるため）
- 本番 DB で DROP 実行漏れがあると空テーブルが残り続ける（混乱の原因になる可能性）→ Plan 07 SUMMARY.md の運用手順に明記

### Neutral
- `app/orchestrator/graph.py` の旧 `event: routing` / `event: routing_fallback` JSON ログは新 OTEL schema に一括置換。互換 alias は残さない（破壊的変更、docker logs 解析スクリプトを使っている運用者は recipes.md 参照で書き換え）

## Alternatives Considered

- **OTEL SDK + OTLP exporter + Tempo/Jaeger**: 200 名規模に対してオーバーヘッド過大。運用負担増。D-05 で明示的に却下。
- **PostgreSQL audit_log 書き込み復活**: JSON 永続化は stdout で足りる + DB クエリの運用知識が必要になる。D-01 で stdout JSONL に倒した。
- **structlog**: 既存 `logger.info(json.dumps(...))` パターンと不整合。新規依存追加の価値が薄い。
- **`@trace_span` デコレータ**: LangGraph node 関数の引数は `state` のみで `trace_id` を抽出する必要があるためデコレータ不向き。context manager のほうが柔軟。

## Links

- Phase 31 CONTEXT: `.planning/phases/31-agent-mcp-observability/31-CONTEXT.md`
- Phase 31 RESEARCH: `.planning/phases/31-agent-mcp-observability/31-RESEARCH.md`
- Phase 31 PATTERNS: `.planning/phases/31-agent-mcp-observability/31-PATTERNS.md`
- Writer 実装: `app/observability/trace.py`, `app/observability/traced_tool.py`, `app/observability/config.py`
- CLI: `scripts/trace_query.py`
- Docs: `docs/trace-query-recipes.md`, `docs/phase-31-reasoning-token-spike.md`
- 関連 ADR: ADR-0024 (sandbox_exposed), ADR-0041 (CodeAct), ADR-0044 (MCP catalog SoT)
