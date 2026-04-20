# Phase 31: エージェント実行・MCP ツール利用の observability 基盤 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 31-agent-mcp-observability
**Areas discussed:** 観測基盤アーキ (OTEL or PG), トレース粒度・スキーマ, 可視化 UI 配置, 秘匿情報・reasoning token

---

## 観測基盤アーキテクチャ

### Q: Phase 31 の主ストアは何にしますか？
| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL audit_log (Recommended) | 既存テーブル拡張 + docker logs を 2 次的 raw source に | |
| OTEL Collector + Jaeger/Tempo | OTEL SDK + Collector + Jaeger/Tempo/Grafana | |
| 両方 (PG first, OTEL 並行出力) | PG を主にしつつ OTLP exporter で Jaeger 同期 | |
| JSONL file + jq (Minimal) | docker logs / JSONL に JSON line、jq/grep クエリ | ✓ |

**User's choice:** JSONL file + jq (Minimal)
**Notes:** 200 名規模の社内システムなので、DB や集約インフラを入れない最小構成を選択。

### Q: docker logs (stdout) の長期保存はどこまでするか？
| Option | Description | Selected |
|--------|-------------|----------|
| 現状維持 (rotation 済み) (Recommended) | quick 260418-tin の max-size/max-file 設定で十分 | ✓ |
| Loki + Grafana | Loki コンテナ追加 + Grafana UI | |
| file log rotation 強化 | 外部ボリューム + logrotate で 30-90 日保持 | |
| OpenSearch / Elasticsearch | Fluent Bit/Vector 転送 + 全文検索 | |

**User's choice:** 現状維持 (rotation 済み)
**Notes:** ログローテーション設定を行った (quick 260418-tin) ため、追加インフラは不要。

### Q: Phase 31 のスコープはどこまで完成させますか？
| Option | Description | Selected |
|--------|-------------|----------|
| MVP: 書き込み + クエリ API まで (Recommended) | audit_log 拡張 + 3 経路の writer + 基本 API | ✓ |
| Full: UI + ダッシュボードまで | 管理 UI + 統計グラフまで Phase 31 に含める | |
| Observability-only: 書き込みのみ | SQL 直クエリ運用、UI/API は次フェーズ | |

**User's choice:** MVP: 書き込み + クエリ API まで (ただし後続の決定で API は CLI + jq に縮小)
**Notes:** —

### Q: OTEL 導入を次期ににずらす場合の「未来の移行しやすさ」はどの程度確保しますか？
| Option | Description | Selected |
|--------|-------------|----------|
| 技術選択の自由度を維持 (Recommended) | span dict 生成 + writer 抽象で差し替え可に | ✓ |
| 所有権は考えず PG 全力実装 | 直接 insert、移行は将来 refactor | |
| opentelemetry-sdk だけインストールしておく | SDK 同梱 + Console exporter | |

**User's choice:** 技術選択の自由度を維持
**Notes:** writer を抽象化 → 将来 OTLP / PG への切替余地。Phase 31 では OTEL SDK 依存を入れない。

### Q (follow-up): 既存の PostgreSQL audit_log テーブル (write ロジック無し) はどうしますか？
| Option | Description | Selected |
|--------|-------------|----------|
| 削除 (JSONL 一本化) | Phase 31 で CREATE TABLE 行を除去 | ✓ |
| スキーマは残すが無視 (Recommended) | CREATE TABLE は維持、書き込みだけしない | |
| JSONL + PG 両方書き | 重要イベントだけ PG にもサマリ | |

**User's choice:** 削除 (JSONL 一本化)
**Notes:** 将来 DB 化する場合はそのとき改めて設計する。

### Q (follow-up): JSONL ファイルの出力先とロテーションはどうしますか？
| Option | Description | Selected |
|--------|-------------|----------|
| ホスト bind mount + RotatingFileHandler (Recommended) | ./logs/trace/ に出力 | |
| Docker named volume + logrotate | named volume + サイドカー | |
| docker logs stdout と同一 (新規ファイルなし) | python logger → stdout → docker driver rotation | ✓ |

**User's choice:** docker logs stdout と同一 (新規ファイルなし)
**Notes:** 新規インフラ追加ゼロの方針を徹底。

### Q (follow-up): クエリ API はどう実装しますか？
| Option | Description | Selected |
|--------|-------------|----------|
| GET /api/traces で JSONL 読み取り (Recommended) | FastAPI エンドポイントで tail + filter | |
| CLI スクリプト + jq 例提供 | scripts/trace_query.py + docs の jq 例 | ✓ |
| 両方 | API + CLI 両建て | |

**User's choice:** CLI スクリプト + jq 例提供
**Notes:** REST API は作らない。運用者が docker シェル経由で jq を叩く前提。

### Q (follow-up): JSONL 1 行スキーマはどの程度 OTEL span 互換にしますか？
| Option | Description | Selected |
|--------|-------------|----------|
| OTEL span-like (Recommended) | trace_id / span_id / parent_span_id / operation_name / times / attributes | ✓ |
| フラット event JSON | event / timestamp / user_id / thread_id / action / data | |
| 二層 (parent span + event rows) | 親 span + 子 event rows | |

**User's choice:** OTEL span-like
**Notes:** 将来 OTLP への変換を容易にする。

---

## トレース粒度・スキーマ

### Q: トレースの span 分割粒度はどのぐらいにしますか？
| Option | Description | Selected |
|--------|-------------|----------|
| SubAgent + ツール呼び出しまで (Recommended) | routing / SubAgent / tool_call の 3 層 | ✓ |
| ReAct 各 turn まで 全 span | LLM 1 回呼び出しごとに span | |
| ジョブレベルのみ | 1 ジョブ = 1 span、内訳は attribute 配列 | |
| 設定で切り替え | env var で TRACE/INFO/SUMMARY 切替 | |

**User's choice:** SubAgent + ツール呼び出しまで
**Notes:** ReAct 各 turn は SubAgent span の attribute (`turn_count`) で表現。

### Q: span の共通 attributes はどれですか？(複数選択)
| Option | Description | Selected |
|--------|-------------|----------|
| user_id (github_login) | 誰が呼んだか | ✓ |
| app_id (chat/superchat/canvas 等) | どのアプリから | ✓ |
| agent_name (SubAgent / CodeAct/ iframe) | 実行主体 | ✓ |
| model_name (ユーザー override 含む) | どの Copilot モデル | ✓ |

**User's choice:** 全 4 つ
**Notes:** Phase 11 の context 伝播と Phase 29 の model_override を流用。

### Q: ツール呼び出しの span attributes に tool args / result はどの程度含めますか？
| Option | Description | Selected |
|--------|-------------|----------|
| tool_name + args size のみ (Recommended) | サイズのみ、内容は非記録 | |
| args と result を truncate して格納 | 200-500 文字 prefix を attribute に | ✓ |
| 全文格納 (redact ルール適用後) | tool 個別 redact ルールを経て全文 | |

**User's choice:** args と result を truncate して格納
**Notes:** デバッグ用に prefix が見えたほうが便利。truncate 閾値は env で一律制御 (area 4 の決定で確定)。

### Q: span の trace_id / correlation_id の統一方針は？
| Option | Description | Selected |
|--------|-------------|----------|
| trace_id = correlation_id として統一 (Recommended) | RPCContext.correlation_id をそのまま流用 | ✓ |
| W3C Trace Context 形式に切替 | 32hex trace_id / 16hex span_id | |
| 両方保持 | correlation_id + 新規 trace_id の 2 軸 | |

**User's choice:** trace_id = correlation_id として統一
**Notes:** Phase 11 の correlation 連鎖がそのまま span に乗る。

---

## 可視化 UI 配置

### Q: 将来的に UI (admin 画面) を追加する予定はありますか？
| Option | Description | Selected |
|--------|-------------|----------|
| 将来 admin 画面を作る予定 (Recommended) | UI フォワードコンパチな span スキーマにする | |
| CLI で完結。UI 作らない | 200 名規模では CLI で十分 | ✓ |
| まだ未定 | 必要になったら考える | |

**User's choice:** CLI で完結。UI 作らない
**Notes:** 今後も管理画面追加は予定なし。

### Q: trace 参照のアクセス権限はどうしますか？
| Option | Description | Selected |
|--------|-------------|----------|
| docker / サーバ・シェル前提 (Recommended) | SSH/docker exec で参照、アプリ層の認証なし | ✓ |
| 将来 UI まで見越して admin ロール設定 | GET /api/traces を admin-only で用意 | |
| 特権 user_id 対応 | env / config の特権リスト | |

**User's choice:** docker / サーバ・シェル前提
**Notes:** —

### Q: トレース量が増えたときのサンプリング / フィルタはどうしますか？
| Option | Description | Selected |
|--------|-------------|----------|
| 全件記録 (Recommended) | 200 名規模は十分なスケール | ✓ |
| env var で sample rate 制御 | TRACE_SAMPLING_RATE | |
| 失敗時のみ full trace | 正常 path は summary 粒度 | |

**User's choice:** 全件記録
**Notes:** 将来負荷問題が出たら env で sampling を追加する余地は残す。

---

## 秘匿情報・reasoning token

### Q: ツール args の redact / truncate ポリシーは？
| Option | Description | Selected |
|--------|-------------|----------|
| ツールごとに config/mcp_tools.yaml で指定 (Recommended) | trace_redact / trace_args_max_chars をツール個別に | |
| 全ツール一律の max_chars だけ | env (TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS) | ✓ |
| 完全に args 非出力、サイズのみ | args_bytes / result_bytes だけ | |

**User's choice:** 全ツール一律の max_chars だけ
**Notes:** config/mcp_tools.yaml にツール個別設定は入れない。シンプル維持。

### Q: ユーザーメッセージ本文 / LLM 出力は span に記録しますか？
| Option | Description | Selected |
|--------|-------------|----------|
| 記録しない (Recommended) | checkpointer に全文あるので token 数のみ | |
| prefix のみ記録 | user/LLM 双方 200 文字 prefix | ✓ |
| 全文記録 | message 全体を attribute に | |

**User's choice:** prefix のみ記録
**Notes:** 全文は LangGraph checkpointer (PostgreSQL) に残るので thread_id で JOIN 運用。

### Q: Copilot SDK の reasoning / thinking token はどう扱いますか？
| Option | Description | Selected |
|--------|-------------|----------|
| 調査後、SDK が提供すれば記録 (Recommended) | ChatCopilot._agenerate で露出調査 → span 追加 | |
| 当面見送る | usage.total_tokens のみ、reasoning は将来 | |
| スパイクを先に実行 | Phase 31 最初にスパイクで露出確認 | ✓ |

**User's choice:** スパイクを先に実行
**Notes:** Phase 31 の最初のタスクとして Copilot SDK レスポンスを調査、取れる場合のみ span に追加、取れなければスコープ外。

### Q: privileged ツール (sandbox_exposed=false, claude_code 等) の使用は特別扱いしますか？
| Option | Description | Selected |
|--------|-------------|----------|
| span attribute に privileged=true を記録するのみ (Recommended) | アラート等はスコープ外 | ✓ |
| アラートまで入れる | stderr WARN + 将来通知連携しやすく | |
| 特別扱いなし | 通常 span と同様 | |

**User's choice:** span attribute に privileged=true を記録するのみ
**Notes:** Slack 通知やアラートは Phase 31 スコープ外 (Deferred Ideas)。

---

## Claude's Discretion

- writer 抽象の具体 I/F 設計 (emit_span ヘルパー or context manager or dataclass + emit)
- span start_time / end_time の取得手段 (perf_counter vs datetime)
- Copilot SDK reasoning token spike の具体範囲 (1-2h 目安)
- scripts/trace_query.py の CLI 仕様
- docs/ の jq クエリ例集の構成
- TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS のデフォルト値 (500 / 1000 は目安)
- writer 設置先ディレクトリ (app/observability/ or app/orchestrator/trace.py)

## Deferred Ideas

- 管理 UI / admin 画面
- Loki / OpenSearch / Jaeger / Tempo 等の集約基盤
- OpenTelemetry SDK / OTLP exporter 導入
- PostgreSQL audit_log 書き込み (Phase 31 で削除)
- privileged ツール使用時の Slack / メール通知連携
- サンプリング機構 (TRACE_SAMPLING_RATE 等)
- トークン使用量集計 API / 統計ダッシュボード
- GET /api/traces 等の REST 参照エンドポイント
