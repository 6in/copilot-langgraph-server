# Phase 31 Spike: Copilot SDK reasoning / thinking token 露出調査

> **ステータス**: 🟢 確定済 (2026-04-19 実測完了)
>
> 3 モデル分の実測値を反映し、Plan 04 SubAgent span に載せる attribute を確定した。

---

## 目的

Phase 31 の `D-15 (取れる場合だけ span attribute に追加)` の **取れる / 取れない** を実測で判定し、Plan 04 (SubAgent span emit) が載せる attribute 名を確定する。

- `github-copilot-sdk` 0.2.0 は ``ASSISTANT_USAGE`` / ``ASSISTANT_REASONING`` / ``ASSISTANT_REASONING_DELTA`` イベントを emit することは **静的には確認済** (31-RESEARCH.md §5.1 で SDK enum + Data dataclass を直接読取、VERIFIED)。
- しかし、各モデルが実際にそれらのイベントを **発火させるか** は Copilot サーバー側の挙動依存。特に reasoning 系は deep-think 対応モデルしか出さないと推測される。
- Plan 04 で span attribute を「取れるもののみ」に絞るため、モデル × フィールドの露出マトリクスを作る。

---

## 実施手順

### 前提

- `docker compose` で `api` / `worker` / `postgres` / `redis` / `mcp-server` / `frontend` が Up
- `~/.copilot_sdk/token.enc` (worker コンテナ内) が有効な Device Flow トークンを持っている
- スパイクスクリプト `scripts/spike_copilot_reasoning.py` が Plan 01 Task 1 でコミット済 (5a3a3bd)

### 実行コマンド

```bash
# 1. docker 起動 (既に Up ならスキップ可)
docker compose up -d

# 2. 認証状態を確認 (/root/.copilot_sdk/token.enc があること)
docker compose exec -T worker ls -la /root/.copilot_sdk/token.enc
# → 無ければ http://localhost:5173/orochi/ で Device Flow 認証を先に完了

# 3. 3 モデル分の spike を実行
for MODEL in claude-haiku-4-5-20251001 claude-sonnet-4-6 gpt-4.1; do
  docker compose exec -T worker uv run python /app/scripts/spike_copilot_reasoning.py \
    --model "$MODEL" --prompt "東京の今日の天気を短く教えて" 2>&1 | tee -a /tmp/phase-31-spike.log
done

# 4. JSON 行だけを抜き出す
grep '"event":"spike-usage"' /tmp/phase-31-spike.log
```

### 期待される JSON 1 行

```json
{"event":"spike-usage","model":"claude-haiku-4-5-20251001","prompt_chars":20,"response_chars":42,"usage":{"input_tokens":123,"output_tokens":42,"cache_read_tokens":0,"cache_write_tokens":0,"conversation_tokens":165,"system_tokens":null,"tool_definitions_tokens":null},"reasoning_count":0,"reasoning_total_chars":0,"reasoning_delta_count":0,"reasoning_delta_total_chars":0,"reasoning_prefix":null,"event_counts":{"SessionEventType.ASSISTANT_TURN_START":1,"SessionEventType.ASSISTANT_MESSAGE":1,"SessionEventType.ASSISTANT_USAGE":1,"SessionEventType.ASSISTANT_TURN_END":1,"SessionEventType.SESSION_IDLE":1}}
```

(実際の値は実行時に差し替え)

---

## 結果

### 生 JSON 行

2026-04-19 実測 (docker compose exec worker 経由、prompt="東京の今日の天気を短く教えて"):

```text
{"event": "spike-usage", "model": "claude-haiku-4-5-20251001", "prompt_chars": 14, "response_chars": 200, "usage": {"input_tokens": 25135.0, "output_tokens": 180.0, "cache_read_tokens": 0.0, "cache_write_tokens": 0.0, "conversation_tokens": null, "system_tokens": null, "tool_definitions_tokens": null}, "reasoning_count": 0, "reasoning_total_chars": 0, "reasoning_delta_count": 0, "reasoning_delta_total_chars": 0, "reasoning_prefix": null, "event_counts": {"SessionEventType.PENDING_MESSAGES_MODIFIED": 2, "SessionEventType.SESSION_TOOLS_UPDATED": 1, "SessionEventType.USER_MESSAGE": 1, "SessionEventType.ASSISTANT_TURN_START": 1, "SessionEventType.SESSION_USAGE_INFO": 1, "SessionEventType.ASSISTANT_USAGE": 1, "SessionEventType.ASSISTANT_MESSAGE": 1, "SessionEventType.ASSISTANT_REASONING": 1, "SessionEventType.ASSISTANT_TURN_END": 1, "SessionEventType.SESSION_IDLE": 1}}
{"event": "spike-usage", "model": "claude-sonnet-4-6", "prompt_chars": 14, "response_chars": 224, "usage": {"input_tokens": 25141.0, "output_tokens": 183.0, "cache_read_tokens": 6486.0, "cache_write_tokens": 0.0, "conversation_tokens": null, "system_tokens": null, "tool_definitions_tokens": null}, "reasoning_count": 0, "reasoning_total_chars": 0, "reasoning_delta_count": 0, "reasoning_delta_total_chars": 0, "reasoning_prefix": null, "event_counts": {"SessionEventType.PENDING_MESSAGES_MODIFIED": 2, "SessionEventType.SESSION_TOOLS_UPDATED": 1, "SessionEventType.USER_MESSAGE": 1, "SessionEventType.ASSISTANT_TURN_START": 1, "SessionEventType.SESSION_USAGE_INFO": 1, "SessionEventType.ASSISTANT_USAGE": 1, "SessionEventType.ASSISTANT_MESSAGE": 1, "SessionEventType.ASSISTANT_REASONING": 1, "SessionEventType.ASSISTANT_TURN_END": 1, "SessionEventType.SESSION_IDLE": 1}}
{"event": "spike-usage", "model": "gpt-4.1", "prompt_chars": 14, "response_chars": 93, "usage": {"input_tokens": 20131.0, "output_tokens": 68.0, "cache_read_tokens": 0.0, "cache_write_tokens": 0.0, "conversation_tokens": null, "system_tokens": null, "tool_definitions_tokens": null}, "reasoning_count": 0, "reasoning_total_chars": 0, "reasoning_delta_count": 0, "reasoning_delta_total_chars": 0, "reasoning_prefix": null, "event_counts": {"SessionEventType.PENDING_MESSAGES_MODIFIED": 2, "SessionEventType.SESSION_TOOLS_UPDATED": 1, "SessionEventType.USER_MESSAGE": 1, "SessionEventType.ASSISTANT_TURN_START": 1, "SessionEventType.SESSION_USAGE_INFO": 1, "SessionEventType.ASSISTANT_USAGE": 1, "SessionEventType.ASSISTANT_MESSAGE": 1, "SessionEventType.ASSISTANT_TURN_END": 1, "SessionEventType.SESSION_IDLE": 1}}
```

### 露出マトリクス

| model | ASSISTANT_USAGE | input_tokens | output_tokens | cache_read_tokens | cache_write_tokens | ASSISTANT_REASONING event | reasoning_text chars | reasoning_delta count |
| ----- | --------------- | ------------ | ------------- | ----------------- | ------------------ | ------------------------- | -------------------- | --------------------- |
| claude-haiku-4-5-20251001 | ✓ | 25135 | 180 | 0 | 0 | ✓ (1 件) | 0 | 0 |
| claude-sonnet-4-6 | ✓ | 25141 | 183 | 6486 | 0 | ✓ (1 件) | 0 | 0 |
| gpt-4.1 | ✓ | 20131 | 68 | 0 | 0 | ✗ | 0 | 0 |

凡例:
- `✓` = イベント発火かつ非 null 値
- `null` = イベント発火したがフィールドが null
- `✗` = イベント自体が発火しない

**補足事項:**
- `conversation_tokens` / `system_tokens` / `tool_definitions_tokens` は 3 モデル全てで `null` — ASSISTANT_USAGE イベントには露出しない（SESSION_USAGE_INFO 等の別チャネルで出る可能性あり、本スパイクでは未確認）。
- `ASSISTANT_REASONING` イベントは claude-* 系では発火するが `reasoning_text` / `reasoning_opaque` / `reasoning_id` いずれも空/None（`reasoning_count: 1, reasoning_total_chars: 0`）。deep-think 有効時にだけ本文が入ると推測されるが、通常の `ainvoke` 経由ではテキストが取れない。
- `ASSISTANT_REASONING_DELTA` は 3 モデル全てで一度も発火せず。
- `cache_read_tokens` は Sonnet のみ `6486` と有意値（初回でも prompt cache hit）。Haiku / gpt-4.1 は `0`。

---

## span schema への反映判断

> **このセクションは実測マトリクスを見て人間が埋める。** ここに書いた attribute 名が Plan 04 の SubAgent span 実装に 1:1 で反映される。

### 採用する attribute 名一覧

**全モデルで非 null → 常時載せる (int cast 必須):**
- `input_tokens` — 25135 / 25141 / 20131
- `output_tokens` — 180 / 183 / 68
- `cache_read_tokens` — 0 / 6486 / 0（Sonnet のみ値あり、Haiku/GPT は 0 だが発火はする）
- `cache_write_tokens` — 0 / 0 / 0（常に 0 だが発火はする、将来のキャッシュ書込み検出用に保持）

SDK は `float | None` で返すが span attribute では `int()` に正規化する（`trace_query` の数値フィルタと統計集計の互換性のため）。

**None-guard 付きで載せる (取れた時のみ):**
- なし（現時点）

**reasoning_text は 0 chars かつ情報漏えいリスク → 載せない:**
- `ASSISTANT_REASONING` イベントは claude-* で発火するが `reasoning_text` は常に空文字列。`reasoning_prefix` / `reasoning_id` / `reasoning_opaque` も同様。
- 本文が入るモデル (deep-think 系) に将来切り替えた際は、T-31-01 mitigation として **文字数のみ** (`reasoning_chars`) の採用を検討。Phase 31 scope では何も載せない。

### reasoning_text / reasoning_opaque の扱い

- `reasoning_text` 本文は **全量 NG** (プロンプトに機密が含まれ得る→ログサイズも爆発)
- 今回の実測では 3 モデルすべて 0 chars だったため、Phase 31 では以下を採用:
  - [x] **載せない** — reasoning が全モデルで 0 件（イベントは発火するが本文なし）のため Phase 31 Plan 04 では span attribute を emit しない
  - [ ] 文字数のみ (`reasoning_chars`) を載せる — 将来 deep-think モデル対応時の候補
  - [ ] 200 字 prefix (`reasoning_prefix`) + 文字数を載せる — D-13 に準拠するが PII リスク残
- T-31-01 mitigation として、**本文フィールドは Phase 31 では emit しない** ことで情報漏えいリスクを封じる
- **結論: Phase 31 では reasoning 系 attribute を span に載せない。Plan 04 の SubAgent span は usage 4 フィールドのみ**

### Deferred (Phase 31 scope 外)

- `conversation_tokens` / `system_tokens` / `tool_definitions_tokens` — ASSISTANT_USAGE では常に null。別イベント `SESSION_USAGE_INFO` 等に露出する可能性あるが未調査。Phase 31 では見送り。
- `reasoning_id` / `reasoning_opaque` / `reasoning_text` — 3 モデル全てで空。deep-think モデル（例: GPT-5 Thinking 系）対応時に別フェーズで再調査して採用判断する。
- `ASSISTANT_REASONING_DELTA` 経路の streaming 計測 — 3 モデル全てでイベント発火ゼロ。streaming span は未実装判断。

---

## 結論

**Plan 04 で SubAgent span に emit する attribute の最終確定リスト:**

- [x] `input_tokens` (int, ASSISTANT_USAGE.input_tokens を `int()` cast) — 3 モデル全てで取得
- [x] `output_tokens` (int, ASSISTANT_USAGE.output_tokens を `int()` cast) — 3 モデル全てで取得
- [x] `cache_read_tokens` (int, ASSISTANT_USAGE.cache_read_tokens を `int()` cast) — 3 モデル全てで取得（Sonnet のみ有意値）
- [x] `cache_write_tokens` (int, ASSISTANT_USAGE.cache_write_tokens を `int()` cast) — 3 モデル全てで 0 だが発火は確認
- [ ] ~~`reasoning_chars`~~ — Phase 31 では載せない（全モデル 0 chars）
- [ ] ~~`reasoning_prefix`~~ — Phase 31 では載せない（T-31-01 mitigation）

**採用原則:**

1. **4 フィールドを常時載せる** — ASSISTANT_USAGE イベントは全モデルで発火確認済み。SubAgent 完了時に `span.set_attribute(...)` で常時 emit する。
2. **None-guard は不要だが防御的に実装** — 実測では null 値なしだが、SDK は型上 `float | None` を返すため、`if value is not None:` ガードを Plan 04 で入れる（SDK 挙動が将来変わる可能性あり）。
3. **reasoning 系は emit しない** — 本文は空、プレフィックスは PII リスク、Phase 31 の threat mitigation を優先。deep-think モデル対応時に別フェーズで再検討。
4. **int cast 必須** — SDK は `float` で返すが、整数トークン数をそのまま float で書くと JSONL の可読性が下がる + `trace_query` の数値フィルタに不利。`int(x)` で正規化。

**Plan 04 実装リファレンス (pseudo):**

```python
# app/providers/copilot.py の session.on(on_event) ハンドラで ASSISTANT_USAGE を捕捉
if event.type == SessionEventType.ASSISTANT_USAGE:
    usage = {
        "input_tokens": int(event.data.input_tokens) if event.data.input_tokens is not None else 0,
        "output_tokens": int(event.data.output_tokens) if event.data.output_tokens is not None else 0,
        "cache_read_tokens": int(event.data.cache_read_tokens) if event.data.cache_read_tokens is not None else 0,
        "cache_write_tokens": int(event.data.cache_write_tokens) if event.data.cache_write_tokens is not None else 0,
    }
    # SubAgent span に attach する
```

---

## 変更履歴

- 2026-04-19: scaffold 作成 (Phase 31 Plan 01 Task 2 checkpoint 待ち)
- 2026-04-19: 3 モデル (claude-haiku-4-5-20251001 / claude-sonnet-4-6 / gpt-4.1) で実測、マトリクスと結論を確定。Plan 04 は usage 4 フィールドのみ採用、reasoning 系は Phase 31 scope 外。
