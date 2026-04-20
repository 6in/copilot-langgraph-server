# Phase 31: エージェント実行・MCP ツール利用の observability 基盤 - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

エージェント実行 (軸 A: routing / SubAgent / tool call の 3 層 span) と MCP ツール呼び出し (軸 B: ToolEnabledSubAgent / CodeActSubAgent / iframe_rpc_handler の 3 経路) を、docker logs stdout への OTEL span-like JSONL として統一的に記録する observability 基盤を構築する。

**In scope:**
- 3 経路の tool call と routing / SubAgent run の span 発行
- trace_id = RPCContext.correlation_id 統一
- tool_name / user_id / app_id / agent_name / model_name / duration_ms / privileged の attribute 記録
- 既存 `audit_log` PostgreSQL テーブル (未使用スキーマ) の削除
- `scripts/trace_query.py` CLI と jq クエリ例 (`docs/`)
- Copilot SDK reasoning / thinking token 露出の調査スパイク (Phase 31 の最初に実施)

**Out of scope (Deferred Ideas):**
- 管理 UI / admin API / フロントエンド変更
- Loki / OpenSearch / Jaeger / Tempo / OTEL Collector 等の集約インフラ
- PostgreSQL audit_log への書き込み復活
- privileged ツール使用時のアラート通知
- サンプリング機構
- トークン使用量ダッシュボード

</domain>

<decisions>
## Implementation Decisions

### 観測基盤アーキテクチャ
- **D-01:** 主ストアは JSONL (docker logs stdout)。PostgreSQL / OTEL Collector / Loki / OpenSearch 等の新規インフラは Phase 31 では導入しない。200 名規模・社内運用では docker logging driver の rotation (quick 260418-tin 設定済み) で十分。
- **D-02:** 既存の PostgreSQL `audit_log` テーブルは Phase 31 で削除する。`app/api/main.py` L105-124 の `CREATE TABLE IF NOT EXISTS audit_log` と `CREATE INDEX` を除去し、Phase 31 の JSONL 一本化方針を明示する。
- **D-03:** 新規ログファイルは作らない。trace 出力は既存の python `logging` (`logger.info(json.dumps({...}))` パターン) で stdout へ流す。docker logging driver の rotation にそのまま乗る。
- **D-04:** Phase 31 のスコープは MVP: 3 経路の writer + CLI スクリプト (`scripts/trace_query.py`) + jq クエリ例 (`docs/`) に限定する。管理 UI / admin API / REST エンドポイントは作らない。
- **D-05:** writer 層は `span dict` を生成して `logger.info` に渡す薄い抽象を作り、将来 OTLP exporter や PG insert に差し替えられる柔軟性を確保する。Phase 31 時点では `opentelemetry-sdk` 依存は追加しない。

### トレース粒度・スキーマ
- **D-06:** span 粒度は 3 層: `routing` (parent) / `SubAgent` (run) / `tool_call` (child)。ReAct の各 LLM turn は span として切らず、SubAgent span の attribute (`turn_count` / `iterations`) で表現する。
- **D-07:** 1 行スキーマは OTEL span-like: `trace_id` / `span_id` / `parent_span_id` / `operation_name` / `start_time` / `end_time` / `duration_ms` / `attributes` / `status_code` / `status_message`。将来 OTLP への変換をしやすくしておく。
- **D-08:** `trace_id` は既存 `RPCContext.correlation_id` (UUID4、Phase 11 整備済み) と同一にする。`span_id` は span ごとに `uuid4().hex[:16]` 生成。`parent_span_id` で親子関係を表現。
- **D-09:** 全 span 共通の attributes は 4 つ: `user_id` (github_login) / `app_id` (chat / superchat / canvas / gem / debate) / `agent_name` (SubAgent の `name`) / `model_name` (Phase 29 の `model_override` 含む最終モデル)。

### ツール呼び出しイベント (軸 B)
- **D-10:** 3 経路 (`ToolEnabledSubAgent` / `CodeActSubAgent` / `iframe_rpc_handler`) から統一された `tool_call` span を出す。全 span に `tool_name` / `args_bytes` / `result_bytes` / `duration_ms` / `success` / `privileged` を記録。
- **D-11:** `args` / `result` 本体は truncate して span attribute に格納する (prefix 保存)。truncate 閾値は env var (`TRACE_ARGS_MAX_CHARS` デフォルト 500、`TRACE_RESULT_MAX_CHARS` デフォルト 1000 目安) で**全ツール一律**に制御する。`config/mcp_tools.yaml` にツール個別の redact 指定は入れない。
- **D-12:** `privileged` 判定は `config/mcp_tools.yaml` の `sandbox_exposed=false` を元に span の `attributes.privileged=true` として記録するのみ。アラート / Slack 通知は Phase 31 スコープ外 (将来拡張)。

### メッセージと LLM 計測
- **D-13:** ユーザーメッセージ本文 / LLM 出力は prefix 200 字のみ span attribute に記録する (`user_input_prefix` / `llm_output_prefix`)。全文は LangGraph checkpointer (PostgreSQL) に残るため、`thread_id` で JOIN して読む運用。
- **D-14:** トークン使用量 (`usage.total_tokens` / `prompt_tokens` / `completion_tokens`) は SubAgent span の attribute に記録する。Copilot SDK が提供する標準フィールドのみ。
- **D-15:** Copilot SDK の `reasoning` / `thinking` token 露出は Phase 31 の最初のタスクとして小規模スパイクで調査する。SDK から `thinking` / `reasoning_content` / `usage.reasoning_tokens` 相当が取れる場合だけ span attribute に追加し、取れなければ Phase 31 スコープ外に倒す。

### 可視化 / 参照手段
- **D-16:** 可視化 UI は作らない。Phase 31 では CLI + jq 運用で完結し、将来的にも admin 画面は予定しない (200 名規模・社内運用者向け前提)。
- **D-17:** trace 参照は docker シェル前提 (`docker compose logs api | jq ...` / `docker exec`)。アプリ層の認証・認可は持たない。
- **D-18:** サンプリングは実装しない (全件記録)。将来負荷が問題になったら env var で sample rate を導入する拡張余地を残す。

### Claude's Discretion
- writer 抽象の具体 I/F (`emit_span(operation, attributes)` ヘルパー関数 / `with trace_span(...)` context manager / dataclass + emit 等)
- span `start_time` / `end_time` の取得手段 (`time.perf_counter` 差分 vs ISO-8601 タイムスタンプ)
- Copilot SDK reasoning / thinking spike の規模 (想定 1–2h、成果物は `docs/phase-31-reasoning-token-spike.md` か spike ディレクトリに集約)
- `scripts/trace_query.py` の具体 CLI インターフェース (filter フラグ、pretty 出力、follow モード等)
- `docs/` に置く jq クエリ例集の構成 (例: ユーザー別集計 / 失敗 trace 抽出 / privileged ツール一覧)
- truncate 閾値のデフォルト最終値 (上記 500 / 1000 は目安、実装時に Claude が微調整可)
- writer 設置先ディレクトリ (`app/observability/`、`app/orchestrator/trace.py` 等)
- 既存 `graph.py` の `event: routing` ログを新スキーマに段階的移行するか一括置換するか

### Folded Todos
- **`2026-04-18-mcp-tool-usage-impact-visibility.md`** — 「エージェント実行・MCP ツール利用の observability 基盤」— Phase 31 の源泉 todo そのもの。Phase 31 実装完了時に `todos/completed/` へ移動する。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### ADR・パターン
- `.planning/patterns.md` — ADR 由来パターンカタログ (CLAUDE.md 運用ルール)
- `docs/adr/INDEX.md` — ADR カテゴリ別索引 (CLAUDE.md 運用ルール)
- `docs/adr/0024-mcp-tool-catalog-validation.md` — `sandbox_exposed` フラグ (D-12 の privileged 判定根拠)
- `docs/adr/0041-codeact-direct-execution-over-react.md` — CodeAct の `/internal/call_tool` 経路 (軸 B 経路 2)
- `docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md` — `config/mcp_tools.yaml` を唯一のソースとする方針

### エージェント実行 (軸 A)
- `app/orchestrator/graph.py` — Router の既存構造化ログ (`event: routing` / `routing_fallback`、`correlation_id` 埋め込み済み)。Phase 31 で span emit に統合
- `app/orchestrator/tool_agent.py` — ToolEnabledSubAgent + `build_react_graph`。SubAgent span + 内部 tool_call span を仕込む (軸 B 経路 1)
- `app/orchestrator/codeact_agent.py` — CodeActSubAgent (直接実行ループ)。ReAct と独立のループなので別途 span emit
- `app/orchestrator/agent.py` — SubAgentRegistry (load 時 health log パターン)
- `app/orchestrator/context.py` — RPCContext (`correlation_id` = 将来の `trace_id` 源)

### ツール経路 (軸 B)
- `app/jobs/handlers/iframe_rpc_handler.py` — Canvas iframe RPC → MCP ツール呼び出し経路 (軸 B 経路 3)
- `mcp_server/server.py` — FastMCP `/internal/call_tool` エンドポイント (CodeAct が直接叩く経路)
- `mcp_server/tools/mcp_helper_utils.py` — `_call_tool` (CodeAct sandbox → MCP)
- `mcp_server/tools/mcp_helper.py` — 自動生成 Python wrapper (編集禁止。手書きは `mcp_helper_utils.py` 側)
- `config/mcp_tools.yaml` — MCP ツールカタログ (`sandbox_exposed` が D-12 の根拠)

### インフラ基盤
- `docker-compose.yml` — logging driver の `max-size` / `max-file` rotation 設定 (2026-04-18 quick 260418-tin)
- `app/api/main.py` §L105-124 — Phase 31 で削除する `audit_log` テーブル DDL と INDEX (D-02)

### 既存の構造化ログ実装例 (参考パターン)
- `app/orchestrator/graph.py:47-104` — `logger.info(json.dumps({"event": "routing", "correlation_id": ..., "stage": ..., "chosen": ...}))` パターン。新 span スキーマへ移行する際の土台

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RPCContext.correlation_id` (`app/orchestrator/context.py`): 全経路 (HTTP → arq → LangGraph → Tool) に伝播済み。`trace_id` としてそのまま利用可能 (Phase 11 整備)。
- 構造化 JSON ログパターン (`app/orchestrator/graph.py`): `logger.info(json.dumps({"event": ..., "correlation_id": ..., ...}))` を踏襲して OTEL span 形式へ寄せる。
- docker logging driver の rotation (quick 260418-tin): `max-size: 10m-50m` × `max-file: N`。span の永続ストアとして流用。
- `config/mcp_tools.yaml` の `sandbox_exposed`: privileged 判定に流用 (D-12)。
- LangGraph checkpointer (PostgreSQL): 全文メッセージは checkpointer に残るため、span には prefix のみで足りる (D-13)。

### Established Patterns
- 構造化 JSON line 形式 (`logger.info(json.dumps({...}))`): Phase 31 の span emit も同じ形を継承。
- `correlation_id` / `thread_id` / `user_id` / `app_id` の伝播 (Phase 11): span attribute に直接マッピング。
- `tool_name` の命名統一: `config/mcp_tools.yaml` が single source (Phase 30 の ADR 0044)。
- stdout-only の運用方針: 新規インフラ追加を避ける。

### Integration Points
- `app/orchestrator/graph.py` — `routing` span emit (parent)
- `app/orchestrator/tool_agent.py` — `SubAgent` span + `tool_call` span (軸 B 経路 1)
- `app/orchestrator/codeact_agent.py` — `SubAgent` span + `tool_call` span (軸 B 経路 2)
- `app/jobs/handlers/iframe_rpc_handler.py` — `tool_call` span (軸 B 経路 3)
- `mcp_server/tools/mcp_helper_utils.py` — `_call_tool` wrap で CodeAct sandbox 経路の span 統一
- `app/api/main.py` — `audit_log` DDL 削除 (D-02)
- **新規** `app/observability/` (または `app/orchestrator/trace.py`): span writer 抽象

</code_context>

<specifics>
## Specific Ideas

- 「`docker compose logs api | jq '.attributes.user_id == \"foo\"'` で trace が検索できる」が運用者にとっての理想形。
- 既存 `graph.py` の `event: routing` ログは新 OTEL span スキーマに寄せて置き換える (互換 alias は残さない)。
- Copilot SDK reasoning token 対応は**まずスパイク**で露出有無を確認し、取れる場合のみ span に追加 (SDK 0.2.0 は Technical Preview)。
- scope 感: 新規インフラなし・DB なし・UI なし・API なし。logger 文字列の整備と 3 経路の writer 適用が作業の中心。

</specifics>

<deferred>
## Deferred Ideas

- 管理 UI / admin 画面 (CLI で完結する前提)
- Loki / OpenSearch / Jaeger / Tempo / Grafana 等の集約基盤
- OpenTelemetry SDK / OTLP exporter の導入 (writer 抽象で将来差し替え可に留める)
- PostgreSQL `audit_log` への書き込み復活 (Phase 31 で削除)
- privileged ツール使用時の Slack / メール / 通知連携
- サンプリング機構 (`TRACE_SAMPLING_RATE` 等)
- トークン使用量の集計 API / 統計ダッシュボード
- `GET /api/traces` 等の REST 参照エンドポイント

### Reviewed Todos (not folded)
なし (源泉 todo `2026-04-18-mcp-tool-usage-impact-visibility.md` は `<decisions>` の Folded Todos に統合済み)

</deferred>

---

*Phase: 31-agent-mcp-observability*
*Context gathered: 2026-04-18*
