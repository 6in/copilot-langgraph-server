---
phase: 31-agent-mcp-observability
plan: 06
subsystem: observability
tags: [cli, jq, docs, stdlib-only, argparse, trace-query, docker-logs]

# Dependency graph
requires:
  - phase: 31-agent-mcp-observability
    plan: 02
    provides: SpanDict 10-field schema (trace_id / span_id / parent_span_id / operation_name / start_time / end_time / duration_ms / status_code / status_message / attributes)
  - phase: 31-agent-mcp-observability
    plan: 04
    provides: routing / sub_agent / request span emission with 4 common attributes + usage attrs (input/output/cache_read/cache_write tokens)
  - phase: 31-agent-mcp-observability
    plan: 05
    provides: tool_call span emission from iframe_rpc path with pool_name / row_count custom attributes
provides:
  - "scripts/trace_query.py — stdlib-only CLI (argparse + stdin JSONL reader)"
  - "11 filter flags: --trace-id / --user / --app / --agent / --tool / --status / --operation / --since / --until / --privileged / --min-duration-ms / --max"
  - "4 output formats: pretty / tree / tsv / ndjson"
  - "parse_since helper accepting 30s / 5m / 1h / 1d / ISO-8601 UTC with tz fallback"
  - "docker compose logs prefix strip + non-JSON silent skip + span-shape validation (Landmine 11.5)"
  - "docs/trace-query-recipes.md — 10 hands-on recipes + tuning guide (TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS)"
  - "tests/test_trace_query.py — 19 unit tests (filter / robust-parse / format / parse_since)"
affects: [31-07, 31-08]

# Tech tracking
tech-stack:
  added: []  # stdlib-only (argparse / json / sys / re / datetime), no new dependencies
  patterns:
    - "CLI entry: `#!/usr/bin/env python3` + `from __future__ import annotations` + `def main() -> int` + `sys.exit(main())`"
    - "argparse groups: filter (AND) + output。フラグの単一責務化で help 可読性が上がる"
    - "stdin JSONL reader: docker prefix strip → non-JSON skip → JSON decode → span-shape validate の 4 段 pipeline"
    - "tree DFS renderer: parent_span_id → children dict + ASCII connectors (├── / └── / │)"
    - "pretty formatter で trace_id を UUID4 先頭 8 文字に短縮表示 (運用ログの視認性向上)"

key-files:
  created:
    - scripts/trace_query.py
    - docs/trace-query-recipes.md
    - tests/test_trace_query.py

key-decisions:
  - "stdlib のみで実装 (argparse/json/sys/re/datetime) — 外部依存ゼロ + docker compose exec uv run に依存させない → scripts/ 単独で動く"
  - "docker prefix strip は `\" | \"` で split する正規化方式 (sed 前処理を不要にする)。将来の logging driver 変更にも耐える pass-through フォールバックを維持"
  - "span-shape validation は 3 キー (trace_id / span_id / operation_name) の存在確認のみ。余剰フィールドは許容 (forward compat)"
  - "tree 描画は start_time ソートで決定論的にする (unit test の安定性確保)。span_id 不明の parent_span_id は root 扱いにして欠損に耐える"
  - "pretty format は 1 span 1 行の人間可読形式、TSV format は初回のみヘッダを emit (スプレッドシート貼り付け想定)"
  - "--since / --until は span.start_time で判定 (end_time や emit 時刻ではない)。jq で読む時の直感に合わせる"
  - "parse_since は相対形式 + ISO-8601 UTC のどちらも受け付ける。tz 指定なし ISO は UTC とみなして tzaware 化 (Python 3.12 の fromisoformat 拡張に合わせる)"
  - "Recipe 10 (token usage) は Plan 01 spike の 4 フィールド (input/output/cache_read/cache_write tokens) を前提に記載、reasoning 系は T-31-01 の mitigation 通り記載しない"

patterns-established:
  - "Pattern: `docker compose logs api 2>&1 | python3 scripts/trace_query.py [flags]` — 運用者が 1 行で引ける基本形"
  - "Pattern: `scripts/trace_query.py --trace-id $TRACE_ID --format tree` で request → routing → sub_agent → tool_call の親子関係を視覚化"
  - "Pattern: docker prefix strip を sed で代替する場合は `sed -E 's/^[^|]*\\| //'` を先頭に置く (jq パイプ時の最小 boilerplate)"
  - "Pattern: jq で token 集計するときは `.attributes.input_tokens != null` を select に必ず入れる (Landmine 11.6)"
  - "Pattern: TRACE_*_MAX_CHARS は docker-compose.yml の environment: で上書き。invalid 値は writer 側で default fallback するので typo crash なし"

requirements-completed: [D-16, D-17, D-18]

threat-mitigations-applied:
  - T-31-04: "docker logs 改ざんは accept (docker daemon 経由以外の inject 経路なし)。parse_line は JSONDecodeError / JSON だが非 span の両方を silent skip するので malicious 非 JSON 行は無視される"
  - T-31-01: "docs/trace-query-recipes.md の `チューニング: truncate 閾値` セクションで TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS の運用指針 + 推奨値 (通常 500/1000 / インシデント時 2000/4000 / 高頻度時 200/500) を明記"

# Metrics
duration: 4min
completed: 2026-04-19
---

# Phase 31 Plan 06: trace_query CLI + recipe docs Summary

**docker compose logs stdout の OTEL span-like JSONL を運用者が手元で検索・閲覧するための stdlib-only CLI (`scripts/trace_query.py`) と 10 レシピ集 (`docs/trace-query-recipes.md`) を整備した。Plan 04/05 が emit する request / routing / sub_agent / tool_call の 4 operation と 4 共通 attribute + token 4 フィールドを 11 フィルタと 4 出力形式で自在に操作でき、tree モードは親子関係を ASCII tree で描画する。**

## Performance

- **Duration:** 約 4 分
- **Started:** 2026-04-19T09:42:24+09:00
- **Completed:** 2026-04-19T09:46:16+09:00
- **Tasks:** 3 (RED / GREEN / docs)
- **Files created:** 3 / **modified:** 0

## Accomplishments

- `scripts/trace_query.py` (418 行) — shebang + `chmod +x` で直接起動可能。argparse の filter グループ 11 フラグ + output グループ 3 フラグ (`--format` / `--follow` / `--max`)。stdlib のみ。
- `tests/test_trace_query.py` (331 行、19 testcase) — filter (5 件) / robust parse (3 件) / format (4 件) / advanced (3 件) / parse_since (4 件)。すべて 0.03s で green。
- `docs/trace-query-recipes.md` (389 行、12 H2 section) — 10 レシピ + チューニング + 関連リンク。すべての shell ブロックは copy-paste で即実行可能。
- tree format: `└── [OK   ] request  duration=4521ms trace=550e8400 ...` のような pretty line を DFS で ASCII connector (├── / └── / │) 付きで描画。
- `parse_since` helper: `1h` / `5m` / `30s` / `1d` 相対 + ISO-8601 UTC の両対応。

## Task Commits

Each task was committed atomically:

1. **Task 1: add failing tests for trace_query CLI (RED)** — `e5f325a` (test)
2. **Task 2: implement trace_query CLI with 4 output formats (GREEN)** — `9f6c79b` (feat)
3. **Task 3: add trace-query-recipes.md (10 recipes + tuning guide)** — `6e074b8` (docs)

_TDD サイクル: RED → GREEN (REFACTOR は不要、シンプルな stdlib pipeline)。RED 時点で `ModuleNotFoundError: No module named 'trace_query'` を確認してから GREEN 実装に移行。_

## Files Created/Modified

- `scripts/trace_query.py` — CLI 本体。`_build_parser()` / `parse_line()` / `matches()` / `emit_{ndjson,pretty,tsv,tree}()` / `_render_tree()` / `main()` を公開関数として定義。
- `tests/test_trace_query.py` — importlib.reload + sys.stdin 差し替え方式の unit test。test helper `_run_cli(jsonl, args)` と `_span_json(...)` で全 test を宣言的に記述。
- `docs/trace-query-recipes.md` — 10 レシピ (基本 / per-user / ERROR / privileged / duration 分布 / tree / follow / 集計 / iframe_rpc 監査 / token 集計) + チューニング + 関連リンク。

## Decisions Made

- **stdlib のみで実装**: プランの must_haves に書かれた制約を遵守。外部依存ゼロ + shebang 起動で docker 外からも手元マシンからも直接使える。
- **argparse 2 グループ化**: filter / output を別グループにして `--help` の可読性を上げた (generate_mcp_artifacts.py と同じ分け方)。
- **tree 描画の決定論化**: children を start_time でソート。unit test `test_tree_format_hierarchy` の安定性を確保。
- **pretty format で trace_id 先頭 8 文字表示**: UUID4 フル 36 文字は 1 行表示で邪魔になるため、prefix 8 文字 (`550e8400`) で運用ログの視認性を上げた。フル trace_id は `--format ndjson` / `tree` モードで確認できる。
- **docker prefix strip の pass-through**: `" | "` を含まない行（他 logging driver 互換）もそのまま処理する設計にして、将来 docker logging driver が変わっても動くようにした。
- **非 JSON 行は silent skip + exit 0**: pipeline を止めないために `json.JSONDecodeError` は `continue`。運用者が `docker compose logs | python3 scripts/trace_query.py` を途中で SIGPIPE で切った時に非 0 終了しないのも意図的。

## Deviations from Plan

None — プランを概ねそのまま実行。ただし下記の**軽微な拡張**を記載する:

- **Test 件数**: プランは「8+ test cases」を要求。実際は **19 testcase** (filter 5 + robust parse 3 + format 4 + advanced filter 3 + parse_since 4) を作成した。プラン §behavior に列挙された Test 1-10 に加えて、filter_by_operation / filter_by_tool_and_agent / skip_non_span_json / pretty_format / tsv_format / max_limits / parse_since_seconds_minutes_days / parse_since_iso_datetime / filter_by_since を補強してある。
- **docs レシピ件数**: プランは「8+ レシピ」「80+ 行」を要求。実際は **10 レシピ + 389 行 + 12 H2** にし、Recipe 9 (iframe_rpc 監査、Plan 05 の pool_name / row_count) と Recipe 10 (token 集計、Plan 01 spike 結果) を追加した。プラン §action の 13 section (1-10 + チューニング + 関連) に忠実。
- **CLI 実装行数**: プラン min_lines=180 に対して実装は **418 行**。TSV header の一括管理やエラー防御 (`_span_start_dt` tz fallback など) を追加したため増えたが、プラン must_haves の機能には一切抜けなし。

**Total deviations:** 0 auto-fixed issues — すべてプラン想定の範囲内。Rule 1-3 のいずれも発動せず。

## Issues Encountered

- **Worktree base が 1 つ古かった**: 初期 `git rev-parse HEAD` が `c7319d2` で期待値 `b6229e1` より古かった。`git reset --hard` で是正。worktree 自動生成時のブランチ作成タイミングズレと推測。
- **docker コンテナから worktree 内ファイルが見えない**: `copilot-langgraph-api-1` はメイン workspace (`/home/parallels/workspaces/copilot-langgraph`) をマウントしているため、worktree 内の `scripts/trace_query.py` / `tests/test_trace_query.py` は `/app` から見えない。システム Python (3.12.3 + pytest 9.0.2) で直接 pytest を走らせて 19/19 green を確認した。本 CLI は stdlib 専用なので docker 環境への依存がなく、システム Python での検証で十分。

## User Setup Required

None — 既存 docker logging driver rotation (quick 260418-tin 設定済み、`max-size: 50m` × `max-file: 3` 程度) にそのまま乗る。追加インフラも追加 env var も不要。

運用者はオプションで以下の env var を上書き可能 (Plan 02 で導入済み、本 Plan で運用指針を追加):

- `TRACE_ARGS_MAX_CHARS` (default 500)
- `TRACE_RESULT_MAX_CHARS` (default 1000)

## Plan 08 Integration Validation 推奨コマンド

実環境で span writer + CLI の統合動作を検証するには以下の順に叩く:

```bash
# 1. chat アプリで tool 呼び出しを発生させる
curl -X POST http://localhost:8000/api/chat ...  # (通常のチャット実行)

# 2. 直近 5 分の span 数をざっと数える
docker compose logs --since 5m api 2>&1 \
  | python3 scripts/trace_query.py --format ndjson \
  | wc -l

# 3. 自分の trace をピンポイントで tree 表示
TRACE_ID=$(docker compose logs --since 5m api 2>&1 \
  | python3 scripts/trace_query.py --user <GITHUB_LOGIN> --format ndjson \
  | jq -r '.trace_id' | tail -1)
docker compose logs api 2>&1 \
  | python3 scripts/trace_query.py --trace-id "$TRACE_ID" --format tree

# 4. ERROR があれば抽出
docker compose logs --since 1h api 2>&1 \
  | python3 scripts/trace_query.py --status ERROR --format pretty

# 5. privileged tool audit
docker compose logs --since 24h api 2>&1 \
  | python3 scripts/trace_query.py --privileged --format tsv > /tmp/priv.tsv
```

## TRACE_ARGS_MAX_CHARS チューニング推奨値 (200 名規模・社内運用前提)

| 状況 | args / result | 根拠 |
|------|---------------|------|
| **通常運用** | 500 / 1000 | default。50MB × 3 の docker logging driver rotation で約 1 ヶ月保持可能 |
| **インシデント解析時** | 2000 / 4000 | web_search / db_query の actual query が切れずに見える。原因特定後は default に戻すこと |
| **高頻度連打時** | 200 / 500 | web_search を毎分数百回叩く負荷試験時はログ容量圧縮優先 |

docker-compose.yml の `api.environment` で上書き、サービス再起動で反映。invalid 値 (空文字 / 非 int / 負数) は `app/observability/config.py` 側で default fallback するので typo crash なし。

## Next Phase Readiness

- **Plan 07 (audit_log DDL 削除)**: 本 Plan とは独立。`app/api/main.py` lifespan の 3 文削除のみ。
- **Plan 08 (統合検証)**: 上記「Plan 08 Integration Validation 推奨コマンド」を流用可能。
- **将来拡張（Phase 31 scope 外）**: OTLP exporter / admin UI / sampling は `trace_span` の writer 差し替え点で実装可能。本 CLI は JSONL stdin を読むだけなので、OTLP エクスポート後に逆変換で JSONL 化すれば同じ recipe がそのまま使える。

## Self-Check

自動チェック結果:

- `scripts/trace_query.py` — FOUND, chmod +x
- `tests/test_trace_query.py` — FOUND
- `docs/trace-query-recipes.md` — FOUND, 389 lines, 12 H2 sections
- commit `e5f325a` (RED) — FOUND in git log
- commit `9f6c79b` (GREEN) — FOUND in git log
- commit `6e074b8` (docs) — FOUND in git log
- `python3 -m pytest tests/test_trace_query.py` — 19 passed in 0.03s
- `python3 scripts/trace_query.py --help` — argparse help rendered with 11 filter + 3 output flags
- `grep -q 'scripts/trace_query.py' docs/trace-query-recipes.md` — OK
- `grep -q 'TRACE_ARGS_MAX_CHARS' docs/trace-query-recipes.md` — OK
- `python3 -c "import ast; ast.parse(open('scripts/trace_query.py').read())"` — OK
- `python3 -c "import ast; ast.parse(open('tests/test_trace_query.py').read())"` — OK

## Self-Check: PASSED

---
*Phase: 31-agent-mcp-observability*
*Completed: 2026-04-19*
