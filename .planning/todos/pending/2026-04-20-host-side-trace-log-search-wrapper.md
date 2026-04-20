---
created: 2026-04-20T06:03:01.731Z
title: Docker 外部から trace ログを検索できるラッパースクリプトを整備
area: tooling
files:
  - scripts/trace_query.py
  - docs/trace-query-recipes.md
---

## Problem

Phase 31 で observability 基盤 (stdout JSONL + `scripts/trace_query.py`) を構築したが、毎回以下のようなパイプを手入力する必要がある:

```bash
docker compose logs api worker | python3 scripts/trace_query.py --trace-id XXX --format tree
docker compose logs --since 10m api worker | python3 scripts/trace_query.py --tool web_search --format ndjson
docker compose logs --follow api worker | python3 scripts/trace_query.py --privileged
```

ホスト側から 1 コマンドで検索できないため運用時の friction が高い。`docker compose` コマンドの位置・サービス名・オプション組み立てを覚える必要があり、200 名規模の運用者全員に同じパイプを教える必要がある。

## Solution

`scripts/trace_logs` (shell) または `scripts/tracelog` (Python argparse) の thin wrapper を追加:

### 最低限の機能

- `trace_logs --trace-id TID` — 特定 trace の全 span を tree 表示
- `trace_logs --tool web_search --since 10m` — ツール名 + 時間窓で絞り込み
- `trace_logs --follow --privileged` — live stream + privileged ツールのみ
- `trace_logs --agent codeact --format tsv` — エージェント別の TSV 出力（スプレッドシート取込用）
- `--services api,worker,mcp-server` デフォルト + `--services all` オプション

### 内部実装

```bash
#!/usr/bin/env bash
# scripts/trace_logs — host-side trace query wrapper
set -euo pipefail

SERVICES="${SERVICES:-api worker}"
SINCE=""
FOLLOW=""
QUERY_ARGS=()

# Separate docker compose logs flags from trace_query.py flags
while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE="--since $2"; shift 2 ;;
    --follow|-f) FOLLOW="--follow"; shift ;;
    --services) SERVICES="${2//,/ }"; shift 2 ;;
    *) QUERY_ARGS+=("$1"); shift ;;
  esac
done

docker compose logs $FOLLOW $SINCE $SERVICES \
  | python3 "$(dirname "$0")/trace_query.py" "${QUERY_ARGS[@]}"
```

### ドキュメント更新

- `docs/trace-query-recipes.md` の先頭に wrapper 紹介セクションを追加 (`docker compose logs | python3 ...` レシピと並記)
- README.md もしくは docs/observability.md に運用者向け 1 page ガイド

### 検証 (Phase 31 と同じ 4 経路)

- 経路 1 Chat: `trace_logs --app chat --operation request --since 5m`
- 経路 2 SuperChat+web_search: `trace_logs --tool web_search --since 5m --format tree`
- 経路 3 CodeAct+execute_python: `trace_logs --tool execute_python --privileged`
- 経路 4 Canvas iframe RPC: `trace_logs --tool db_query --app canvas`

### Human-readable 出力強化（2026-04-20 追記）

Wave 6 統合検証で生出力を確認した際、既存の 4 形式（pretty / tree / tsv / ndjson）は**情報密度が高すぎてパッと見のサマリには向かない**ことが判明。運用者（200 名規模、多くはエンジニア以外）が「何が起きているか」を数秒で把握できる human-readable 層を wrapper に追加する。

候補機能:

- **ターミナルカラー** — OK=緑 / ERROR=赤 / privileged=true=黄 / 長時間 span (>1s)=シアン。`--no-color` / `--color=never` は従来動作。`NO_COLOR` 環境変数を尊重（<https://no-color.org/>）。
- **タイムライン（水平バー）** — 1 trace の span 群を ASCII bar で start/duration 可視化:
  ```
  [req]      ████████████░░░░░░░░░░░ 12.2s
   ├ routing ░░ 0.0s
   └ sub_agent ██████████████░░░░░░ 13.0s
      └ tool_call ██░░░░░░░░░░░░░░░ 120ms
  ```
- **エージェント / ツール別サマリ** — `trace_logs stats --since 1h` で集計表示:
  ```
  | エージェント | 呼び出し数 | 成功率 | 平均 duration | トークン総計 |
  |------------|----------|-------|-------------|-----------|
  | codeact    | 12       | 7/12  | 8.2s        | in:234k out:1.5k |
  | general-assistant | 5 | 5/5  | 5.1s        | in:120k out:890  |

  | ツール         | 呼び出し数 | 成功率 | 平均 duration | privileged |
  |---------------|----------|-------|-------------|-----------|
  | web_search    | 8        | 8/8   | 3.2s        | False     |
  | execute_python| 25       | 18/25 | 450ms       | True      |
  | db_query      | 12       | 11/12 | 80ms        | False     |
  ```
- **人間語への整形** — pretty 出力の改善:
  ```
  現在:
  [OK   ] tool_call  duration=62ms trace=861c2a90 user=6in app=canvas agent=iframe_rpc tool=db_query
  改善後:
  ✓ 06:57:19  [canvas/iframe_rpc]  db_query(SELECT now, version)  →  1 row (201 B)  62ms
  ✗ 06:57:31  [canvas/iframe_rpc]  db_query(INSERT ...)           →  BLOCKED: Only SELECT  35ms
  ```
  - アイコン (✓ / ✗ / ⚠)
  - ローカル時刻 (default) と UTC (`--utc`) 切り替え
  - SQL / ツール引数の 1 行要約（長文は `…` で省略）
  - 成功時は結果バイト数・失敗時はエラー理由を inline で
- **補助コマンド** — `trace_logs tail --follow` (alias for `--follow`)、`trace_logs recent <N>` (直近 N 分のサマリだけ)、`trace_logs watch <trace-id>` (そのトレースだけ follow) など、`git` / `docker` / `kubectl` 風のサブコマンド体系を検討。

**設計方針:**
- デフォルトは human-readable（カラー + 人間語 pretty）、**パイプ先が端末でない場合**は自動で `--format ndjson` にフォールバック（jq 連携を壊さない）。
- 既存の `trace_query.py` の 4 形式はそのまま残し、wrapper 側で「human / machine」の二層に整理する。

### Deferred (別 todo 候補)

- Grafana / Loki 連携（ログ集約基盤、ADR-0045 の Negative に記載の通り現時点では Deferred）
- trace tree を Web UI にも埋め込む（管理者向け admin dashboard）
- **Web UI ベースの trace viewer**（Canvas で自作できるか検証）

## Notes

- 2026-04-20: Phase 31 完了後の振り返りで user から「Docker 外側から検索できるスクリプトが欲しい」との要望。Phase 31 の親 todo (2026-04-18-mcp-tool-usage-impact-visibility.md) が大枠の observability 基盤を扱うのに対し、本 todo は **実装済み基盤の UX 向上**に絞ったスコープ。
- Phase 31 ADR-0045 の Decision 7「閲覧手段」を運用フレンドリーに強化する延長作業。
- 2026-04-20 追記: Phase 31 Wave 6 統合検証で user から「人間では見づらい」とのフィードバック。wrapper のスコープを **Docker 外実行 + Human-readable 出力** の 2 本柱に拡張。
