# Trace 検索レシピ集（Phase 31 D-16..D-18）

このドキュメントは、Phase 31 の OTEL span-like JSONL から **運用者が docker シェルで直接**
trace を検索・集計するためのレシピ集です。すべての shell ブロックはコピペで動く完全形で
記載しています（abbreviation なし）。

**対象システム:** Copilot LangGraph Chat（200 名規模・社内運用）
**前提:**

- `docker compose` が動作している（`api` / `worker` / `postgres` / `redis` / `mcp-server` / `frontend`）
- `jq` がインストールされている（`apt install jq` など）
- Phase 31 の trace writer（`app/observability/trace.py`）が稼働している
- `scripts/trace_query.py` が実行可能（shebang 付き、stdlib のみで動作）

**Span スキーマ（10 top-level fields, D-07）:**

| field | 型 | 例 |
|-------|---|---|
| `trace_id` | str (UUID4) | `550e8400-e29b-41d4-a716-446655440000` |
| `span_id` | str (16 hex) | `a1b2c3d4e5f60718` |
| `parent_span_id` | str \| null | 親 span の id または root の場合 null |
| `operation_name` | str | `request` / `routing` / `sub_agent` / `tool_call` |
| `start_time` / `end_time` | str | ISO-8601 UTC microseconds with `Z` |
| `duration_ms` | int | 例: `4521` |
| `status_code` | str | `OK` / `ERROR` / `UNSET` |
| `status_message` | str \| null | 例外時の `TypeName: message` |
| `attributes` | dict | `user_id` / `app_id` / `agent_name` / `model_name` / `tool_name` / `privileged` など |

---

## 1. 基本: trace 行だけを抜粋する

docker compose logs は `api-1  | <raw log>` という prefix が先頭に付く。jq で JSON
解釈できる行のみ抽出して、その中から **span 行**（`trace_id` と `span_id` 両方を持つ）
だけをフィルタする。

```bash
docker compose logs api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -c 'select(type == "object" and .trace_id and .span_id)'
```

`sed` で docker のサービス prefix を剥がしてから `jq -c` に渡すのがポイント。
`jq` は raw 行（JSON でない行）を受け取ると `parse error` を吐いて非 0 終了する。
**このレシピでは `--unbuffered` を使わないため**、FastAPI の起動ログなど非 JSON 行が
混ざった場合はあとのレシピ通り `scripts/trace_query.py` に寄せるのが安全。

もしくは `trace_query.py` を使うと 1 コマンドで済む（prefix strip + 非 JSON skip を自動）：

```bash
docker compose logs api 2>&1 | python3 scripts/trace_query.py --format ndjson
```

---

## 2. 特定ユーザーの直近 1 時間のトレース

自分の github_login が `0hya6in` で、直近 1 時間の span を拾いたい場合：

```bash
docker compose logs --since 1h api 2>&1 \
  | python3 scripts/trace_query.py --user 0hya6in --since 1h --format pretty
```

`docker compose logs --since 1h` で docker 側で 1 時間に絞り、加えて `trace_query.py --since 1h`
でも span の `start_time` で再度フィルタする（docker logs が older ログを返しても安全）。

jq で同じことをする場合：

```bash
docker compose logs --since 1h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -c 'select(type == "object" and .attributes.user_id == "0hya6in")'
```

---

## 3. エラー発生 trace を抽出

```bash
docker compose logs api 2>&1 \
  | python3 scripts/trace_query.py --status ERROR --format pretty
```

jq で status_message まで整形して表示：

```bash
docker compose logs api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -c 'select(type == "object" and .status_code == "ERROR")
           | {time: .start_time, trace: .trace_id, op: .operation_name,
              tool: .attributes.tool_name, msg: .status_message}'
```

関連 ERROR span の全文脈を tree で見るなら：

```bash
# 直近のエラー trace_id を取り出す
TRACE_ID=$(docker compose logs --since 1h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -r 'select(type == "object" and .status_code == "ERROR") | .trace_id' \
  | tail -1)

# tree 表示で親子含めた全 span を確認
docker compose logs api 2>&1 \
  | python3 scripts/trace_query.py --trace-id "$TRACE_ID" --format tree
```

---

## 4. privileged ツール使用履歴（監査用）

`config/mcp_tools.yaml` の `sandbox_exposed: false` が付いているツールは
`attributes.privileged == true` で span に記録される（D-12）。監査用に直近 24 時間の
利用履歴を拾う：

```bash
docker compose logs --since 24h api 2>&1 \
  | python3 scripts/trace_query.py --privileged --format tsv > /tmp/privileged-24h.tsv
wc -l /tmp/privileged-24h.tsv
```

jq で最小情報に絞って抽出（スプレッドシート貼り付けにも便利）：

```bash
docker compose logs --since 24h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -c 'select(type == "object" and .attributes.privileged == true)
           | {time: .start_time, user: .attributes.user_id,
              tool: .attributes.tool_name, status: .status_code}'
```

---

## 5. 特定ツールの duration 分布（p50/p95/max）

例として `web_search` ツールのレスポンスタイム分布を出す：

```bash
docker compose logs api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -r 'select(type == "object"
                  and .operation_name == "tool_call"
                  and .attributes.tool_name == "web_search")
           | .duration_ms' \
  | sort -n \
  | awk 'BEGIN{c=0} {a[c++]=$1}
         END {if (c==0) {print "no samples"; exit}
              print "count=" c,
                    "p50=" a[int(c*0.5)],
                    "p95=" a[int(c*0.95)],
                    "max=" a[c-1]}'
```

`scripts/trace_query.py` で同じ絞り込みを行ってから duration だけ取り出すこともできる
（`--format ndjson | jq ...` のチェーン）：

```bash
docker compose logs api 2>&1 \
  | python3 scripts/trace_query.py --operation tool_call --tool web_search --format ndjson \
  | jq -r '.duration_ms' \
  | sort -n \
  | awk '{a[c++]=$1} END {print "p95=" a[int(c*0.95)] " max=" a[c-1]}'
```

---

## 6. trace_id で親子関係を tree 表示

1 つのリクエストが `request → routing → sub_agent → tool_call (× N)` のように
ネストしている様子を視覚化する。`scripts/trace_query.py --format tree` は
`parent_span_id` を辿って ASCII tree を描画する：

```bash
# トレースしたい trace_id を知っている場合（ユーザーから correlation_id を受け取った等）
TRACE_ID="550e8400-e29b-41d4-a716-446655440000"
docker compose logs api 2>&1 \
  | python3 scripts/trace_query.py --trace-id "$TRACE_ID" --format tree
```

出力例：

```
trace_id: 550e8400-e29b-41d4-a716-446655440000
└── [OK   ] request    duration=4521ms trace=550e8400 user=0hya6in app=superchat
    ├── [OK   ] routing    duration=89ms   trace=550e8400 user=0hya6in app=superchat agent=researcher
    └── [OK   ] sub_agent  duration=4100ms trace=550e8400 user=0hya6in app=superchat agent=researcher model=claude-sonnet-4-6
        ├── [OK   ] tool_call  duration=1200ms trace=550e8400 user=0hya6in app=superchat agent=researcher tool=web_search
        └── [ERROR] tool_call  duration=950ms  trace=550e8400 user=0hya6in app=superchat agent=researcher tool=db_query msg=permission denied
```

直近の自分のユーザー trace を自動で拾いたい場合：

```bash
TRACE_ID=$(docker compose logs --since 1h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -r 'select(type == "object" and .attributes.user_id == "0hya6in") | .trace_id' \
  | tail -1)
docker compose logs api 2>&1 \
  | python3 scripts/trace_query.py --trace-id "$TRACE_ID" --format tree
```

---

## 7. リアルタイム追跡（follow モード）

新しい trace が流れてくるのを追跡するには `docker compose logs --follow` と
`scripts/trace_query.py -f` を組み合わせる：

```bash
docker compose logs --follow api \
  | python3 scripts/trace_query.py --user 0hya6in --format pretty -f
```

特定の ERROR だけリアルタイムで監視したい場合：

```bash
docker compose logs --follow api \
  | python3 scripts/trace_query.py --status ERROR --format pretty -f
```

---

## 8. アプリ別・ツール別の利用集計（最近 24 時間）

どのアプリ（`chat` / `superchat` / `canvas` / `gem` / `debate`）で誰が何をどれだけ
呼んだかを集計する：

```bash
docker compose logs --since 24h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -r 'select(type == "object" and .operation_name == "tool_call")
           | [.attributes.app_id, .attributes.tool_name] | @tsv' \
  | sort \
  | uniq -c \
  | sort -rn
```

出力例（先頭が回数、続いて app_id と tool_name）：

```
  42  superchat    web_search
  18  canvas       db_query
  12  chat         execute_python
   3  gem          execute_python
```

ユーザー別の SubAgent 実行時間ランキング：

```bash
docker compose logs --since 24h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -r 'select(type == "object" and .operation_name == "sub_agent")
           | [.attributes.user_id, .attributes.agent_name, .duration_ms] | @tsv' \
  | awk '{sum[$1"\t"$2] += $3; cnt[$1"\t"$2]++}
         END {for (k in sum) print sum[k], cnt[k], k}' \
  | sort -rn \
  | head -10
```

---

## 9. iframe_rpc 経路のクエリ履歴（Canvas アプリ監査）

Canvas アプリ（`app_id="canvas"`）が iframe 経由で `db_query` / AI ツールをどう
呼んだかを追う。`attributes.pool_name` / `row_count` は Plan 05 で固有に追加された
運用 attribute：

```bash
docker compose logs --since 24h api 2>&1 \
  | python3 scripts/trace_query.py --app canvas --format ndjson \
  | jq -c 'select(.operation_name == "tool_call")
           | {time: .start_time, user: .attributes.user_id,
              tool: .attributes.tool_name, pool: .attributes.pool_name,
              rows: .attributes.row_count, status: .status_code}'
```

特定 pool（例: `prod_readonly`）への問い合わせのみ：

```bash
docker compose logs --since 24h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -c 'select(type == "object"
                  and .attributes.pool_name == "prod_readonly")
           | {time: .start_time, user: .attributes.user_id, status: .status_code}'
```

---

## 10. Token usage 集計（Plan 01 spike 結果に依存）

Plan 01 spike の結果、Copilot SDK が ASSISTANT_USAGE イベントで返す
`input_tokens` / `output_tokens` / `cache_read_tokens` / `cache_write_tokens`
の 4 フィールドが `sub_agent` span に emit される（haiku / sonnet / gpt-4.1 で
確認済み）。null-safe な select を必ず入れる（Landmine 11.6）：

```bash
docker compose logs --since 24h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -c 'select(type == "object"
                  and .operation_name == "sub_agent"
                  and .attributes.input_tokens != null)
           | {time: .start_time,
              user: .attributes.user_id,
              model: .attributes.model_name,
              input: .attributes.input_tokens,
              output: .attributes.output_tokens,
              cache_read: .attributes.cache_read_tokens,
              cache_write: .attributes.cache_write_tokens}'
```

ユーザー × モデル別の累積トークン（直近 24 時間）：

```bash
docker compose logs --since 24h api 2>&1 \
  | sed -E 's/^[^|]*\| //' \
  | jq -r 'select(type == "object"
                  and .operation_name == "sub_agent"
                  and .attributes.input_tokens != null)
           | [.attributes.user_id, .attributes.model_name,
              .attributes.input_tokens, .attributes.output_tokens] | @tsv' \
  | awk '{u=$1"\t"$2;
          in_t[u] += $3; out_t[u] += $4; cnt[u]++}
         END {for (k in in_t)
                printf "%s\tcalls=%d\tin=%d\tout=%d\n",
                       k, cnt[k], in_t[k], out_t[k]}' \
  | sort
```

**[注意]** reasoning / thinking 系の attribute は Phase 31 では emit しない（T-31-01
mitigation、全モデルで `reasoning_text` は空文字だったため）。Plan 01 spike レポートは
`docs/phase-31-reasoning-token-spike.md` を参照。

---

## チューニング: truncate 閾値（TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS）

Phase 31 の writer は tool 引数と結果を **デフォルトで**以下の閾値で prefix 切り詰めする
（D-11）：

| env var | 既定値 | 影響範囲 |
|---------|--------|---------|
| `TRACE_ARGS_MAX_CHARS` | 500 | `tool_call` span の `attributes.args_prefix`（JSON 文字列化後） |
| `TRACE_RESULT_MAX_CHARS` | 1000 | `tool_call` span の `attributes.result_prefix`（同） |

### 推奨運用値（200 名規模・社内運用）

| 状況 | args / result | コメント |
|-----|---------------|---------|
| **通常運用（default）** | 500 / 1000 | logging driver rotation（`max-size: 50m × 3` 程度）で 1 週間分は十分残る |
| **インシデント解析時** | 2000 / 4000 | 一時的に `docker compose up -d` 時に env で上書き。原因特定後は default に戻す |
| **高頻度ツール連打時** | 200 / 500 | `web_search` / `db_query` が毎分数百回走るような負荷試験時は短くしてログ容量を節約 |

上書き例（`docker-compose.yml` の `environment:` セクションに追加）：

```yaml
api:
  environment:
    TRACE_ARGS_MAX_CHARS: "2000"
    TRACE_RESULT_MAX_CHARS: "4000"
```

env var の invalid 値（空文字・非 int・負数）は writer 側ですべて default fallback する
ので、typo で crash することはない（`app/observability/config.py`）。

### logger rotation との兼ね合い

- docker logging driver は `max-size: 50m` × `max-file: 3` 程度の quick 設定済み
  （2026-04-18 `quick 260418-tin`）
- 1 span あたり `result_prefix=1000` のとき **平均 1.5KB**（JSON + 共通 attrs 含む）
- 1 日 1000 span なら 1.5MB → 50MB でざっくり 1 ヶ月分保持可能
- 大きく伸ばす前には `docker compose ps` で api コンテナのログサイズを確認すること

---

## 関連

- Phase 31 Research:
  [.planning/phases/31-agent-mcp-observability/31-RESEARCH.md](../.planning/phases/31-agent-mcp-observability/31-RESEARCH.md)
  （§6 CLI 設計 / §7 jq レシピ原案 / §11 ハマりどころ）
- Phase 31 Patterns:
  [.planning/phases/31-agent-mcp-observability/31-PATTERNS.md](../.planning/phases/31-agent-mcp-observability/31-PATTERNS.md)
- Phase 31 Context（決定事項 D-01..D-18）:
  [.planning/phases/31-agent-mcp-observability/31-CONTEXT.md](../.planning/phases/31-agent-mcp-observability/31-CONTEXT.md)
- Plan 01 reasoning / usage token spike:
  [docs/phase-31-reasoning-token-spike.md](phase-31-reasoning-token-spike.md)
- ADR INDEX: [docs/adr/INDEX.md](adr/INDEX.md)
- writer 本体: [app/observability/trace.py](../app/observability/trace.py)
- CLI: [scripts/trace_query.py](../scripts/trace_query.py)
