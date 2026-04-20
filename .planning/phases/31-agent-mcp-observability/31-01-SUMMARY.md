---
phase: 31-agent-mcp-observability
plan: 01
subsystem: observability
tags: [copilot-sdk, spike, reasoning-token, usage-token, docker-exec]

# Dependency graph
requires:
  - phase: 31-agent-mcp-observability
    provides: "31-RESEARCH §5 (SDK reasoning/usage field inventory, VERIFIED) + §5.4 成果物配置先"
provides:
  - "scripts/spike_copilot_reasoning.py — 常設のスパイクスクリプト (SDK upgrade 時の回帰確認に再利用可)"
  - "docs/phase-31-reasoning-token-spike.md — 3 モデル実測マトリクス確定 + Plan 04 採用 attribute リスト"
  - "Plan 04 SubAgent span attribute 確定: usage 4 フィールド (input_tokens/output_tokens/cache_read_tokens/cache_write_tokens) 採用、reasoning 系は Phase 31 では emit しない"
affects: [31-02, 31-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "session.on() を create_session wrap で注入: _ensure_client → monkey-patch llm._client.create_session に session.on(on_event) を差し込む手法（既存 ChatCopilot._astream は自前でハンドラ登録するがライブラリとしては未提供の為、外部スクリプトからの差し込みにはこの wrap が必要）"
    - "spike スクリプトの 1 行 JSON 出力規約 (docker logs grep/jq 前提)"

key-files:
  created:
    - "scripts/spike_copilot_reasoning.py"
    - "docs/phase-31-reasoning-token-spike.md"
  modified: []

key-decisions:
  - "spike スクリプトは /scripts に常設 — 使い捨てではなく SDK upgrade 回帰テストとして残す (31-PLAN Task 1 の注記)"
  - "reasoning_opaque しか返らないモデル向けに `<opaque:Nchars>` プレースホルダを captured_reasoning に入れる — reasoning_text=null でも存在は観測可能にする"
  - "session.on() 差し込みは ChatCopilot の公開 API を変更せず、_client.create_session を monkey-patch する方式 — プロダクトコードを spike 専用に汚さない"
  - "docker compose が down の状況で勝手に up -d しない — autonomous_false_plan の instruction + CLAUDE.md の worktree 安全性則に従い、実行はユーザーに委譲"

patterns-established:
  - "Phase 31 spike script: session.on() monkey-patch (ChatCopilot.ainvoke 非侵襲パターン)"
  - "spike 結果出力: single-line JSON (event=spike-usage) を stdout へ — docker logs grep 互換"

requirements-completed: [D-14, D-15]

# Metrics
duration: ~7min (scaffold + orchestrator 側で 3 モデル実測 + マトリクス確定)
completed: 2026-04-19
---

# Phase 31 Plan 01: Copilot SDK reasoning / usage spike — 3 モデル実測完了

**Copilot SDK 0.2.0 の ASSISTANT_USAGE / ASSISTANT_REASONING を ChatCopilot.ainvoke 経由で非侵襲に捕捉する再利用可能スパイクスクリプトと、3 モデル (claude-haiku-4-5-20251001 / claude-sonnet-4-6 / gpt-4.1) の実測マトリクスを確定。Plan 04 SubAgent span は usage 4 フィールドを採用し、reasoning 系は Phase 31 では emit しないと判定。**

## Performance

- **Duration:** ~7min (scaffold + 3 モデル実測 + マトリクス記入)
- **Started:** 2026-04-18 (本セッション)
- **Completed:** 2026-04-19 (orchestrator が docker Up を確認してから 3 モデル実測 + マトリクス確定)
- **Tasks:** 2/2 完了 (Task 1 fully auto; Task 2 は orchestrator が docker Up 確認のうえ実行)
- **Files modified:** 2 (新規作成、うち docs は scaffold → 実測値反映の 2 回コミット)

## Accomplishments

- `scripts/spike_copilot_reasoning.py` を新規作成: `argparse` で `--model` / `--prompt` / `--timeout` を受け取り、`ChatCopilot.ainvoke` 経由の呼び出しで `ASSISTANT_USAGE` / `ASSISTANT_REASONING` / `ASSISTANT_REASONING_DELTA` を capture して 1 行 JSON を stdout に吐く。
- 非侵襲な session.on() 差し込みパターンを確立: `llm._ensure_client()` した後に `llm._client.create_session` を monkey-patch し、wrap 版が session を返す前に `session.on(on_event)` を呼ぶ — `app/providers/copilot.py` には一切触れずに ainvoke の全パスで events を観測できる。
- `docs/phase-31-reasoning-token-spike.md` scaffold を作成: 目的・実施手順・生 JSON 保存場所・露出マトリクス (haiku / sonnet / gpt-4.1)・span schema への反映判断・結論 — Plan 04 が参照する採用 attribute 名の最終確定場所を TODO として明示。
- Self-check for Task 1: Python syntax valid (ast.parse OK)、ASSISTANT_USAGE/ASSISTANT_REASONING 参照あり、`__name__ == "__main__"` ガード実装済。

## Task Commits

1. **Task 1: Copilot SDK スパイクスクリプト作成** — `5a3a3bd` (feat)
2. **Task 2a: scaffold ドキュメント作成** — `c4e56a7` (docs, scaffold)
3. **Task 2b: 3 モデル実測 + マトリクス確定** — orchestrator 側で `docker compose exec worker uv run python /app/scripts/spike_copilot_reasoning.py` を 3 モデルに実行し、`docs/phase-31-reasoning-token-spike.md` に実測値と span schema 採用判断を反映 (次の commit で集約)

## Files Created/Modified

- `scripts/spike_copilot_reasoning.py` (新規, 211 行) — 常設のスパイク CLI。`docker compose exec -T worker uv run python /app/scripts/spike_copilot_reasoning.py --model <m> --prompt <p>` で実行。
- `docs/phase-31-reasoning-token-spike.md` (新規, 130 行) — scaffold。`## 結果` と `## span schema への反映判断` と `## 結論` セクションの TODO を人間が埋める。

## Decisions Made

- **session.on() は ChatCopilot 本体を触らずに monkey-patch で差し込む** — プロダクトコードの差分ゼロ。SDK API が変わって create_session のシグネチャ変更があっても `*args, **kwargs` の wrap で対応可能。将来 Plan 04 で span emit を正規実装する際は ChatCopilot 側に最小フックを追加すれば良い。
- **reasoning_opaque しか返らない場合は `<opaque:Nchars>` を入れて存在を記録** — reasoning_text=null かつ reasoning_opaque 有を「reasoning が存在した」と判定できる情報を残す。これが後続 Plan で「reasoning_prefix を載せるか文字数のみにするか」の判断材料になる。
- **spike の prompt は汎用の「東京の今日の天気を短く教えて」** — T-31-01 の mitigation (reasoning_text に PII を含めない) を遵守。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Write ツールの cwd 解決が worktree に向かなかった**
- **Found during:** Task 1 — Write 後に worktree の scripts/ にファイルが存在しない
- **Issue:** Write("scripts/spike_copilot_reasoning.py", ...) が親リポジトリ (`/home/parallels/workspaces/copilot-langgraph/scripts/`) に書き込まれ、worktree (`/home/parallels/workspaces/copilot-langgraph/.claude/worktrees/agent-a06df58e/scripts/`) には存在しなかった。worktree の git status からも新規ファイルが見えない状態。
- **Fix:** 親リポジトリに書かれたファイルを `/tmp/` に move してから、worktree 配下の絶対パスに `cp` で複製。以降の Write 呼び出しは worktree 絶対パスで実行。
- **Files modified:** （リカバリ操作のみ）
- **Verification:** `git status --short` で worktree 側に `?? scripts/spike_copilot_reasoning.py` が出現、`python3 -c "import ast; ast.parse(...)"` OK。
- **Committed in:** 5a3a3bd (Task 1 commit)

**2. [Rule 3 - Blocking] docker compose services ダウンによる Task 2 実測不可**
- **Found during:** Task 2 開始時 — `docker compose ps` で `api` / `worker` いずれも空
- **Issue:** プラン Task 2 は 3 モデル実測を要求するが、docker が down。`autonomous_false_plan` の方針「docker down 時は scaffold コミット + checkpoint:human-action 返却」に従う。
- **Fix:** scaffold 版 `docs/phase-31-reasoning-token-spike.md` (130 行) を作って checkpoint:human-action を返す。実測 3 行の JSON + マトリクス + span schema 反映判断はユーザーに委譲。
- **Files modified:** docs/phase-31-reasoning-token-spike.md (scaffold)
- **Verification:** test -f docs/phase-31-reasoning-token-spike.md + 130 行 ≥ 40 行 (success_criteria の最低行数は満たす)。
- **Committed in:** c4e56a7 (Task 2 scaffold commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking)
**Impact on plan:** どちらも実行環境の制約であり、計画意図 (3 モデルの実測マトリクス) からの逸脱はなし。scaffold に TODO が明示されており、ユーザー側で 4 ステップのコマンド実行後にマトリクスを埋めれば完了する。

## Issues Encountered

- worktree と親リポジトリの cwd 解釈ずれ — Write ツールが親の `scripts/` に書いたため、リカバリに 1 ステップ要した。次回以降は常に worktree の絶対パスで Write を呼ぶ。

## Next Phase Readiness

**Plan 01 完了。Plan 04 の SubAgent span 実装が着手可能。**

### 引き継ぎ事項 (Plan 04 向け)

**採用 attribute name (3 モデル実測で確定):**

| attribute | cast | 採用理由 |
| --- | --- | --- |
| `input_tokens` | `int(event.data.input_tokens)` | 3 モデル全て非 null (Haiku: 25135 / Sonnet: 25141 / GPT-4.1: 20131) |
| `output_tokens` | `int(event.data.output_tokens)` | 3 モデル全て非 null (180 / 183 / 68) |
| `cache_read_tokens` | `int(event.data.cache_read_tokens)` | 3 モデル全て発火 (Sonnet のみ有意値 6486、Haiku/GPT は 0) |
| `cache_write_tokens` | `int(event.data.cache_write_tokens)` | 3 モデル全て 0 だが発火確認 — 将来のキャッシュ書込み検出用に保持 |

**None-guard 方針:** SDK は型上 `float | None` を返すが、実測では全て非 null。念のため `if v is not None else 0` で防御的に整数化する。

**reasoning 系は Phase 31 scope 外:**
- ASSISTANT_REASONING イベントは claude-* で発火するが `reasoning_text` は常に空 (0 chars)。
- `reasoning_prefix` / `reasoning_id` / `reasoning_opaque` いずれも空/None。
- T-31-01 (PII 漏えい) mitigation として Plan 04 では reasoning 関連 attribute を emit しない。

**Deferred (Phase 31 では見送り):**
- `conversation_tokens` / `system_tokens` / `tool_definitions_tokens` — ASSISTANT_USAGE 常に null、他イベント (SESSION_USAGE_INFO 等) からの抽出は別フェーズで調査。
- deep-think モデル対応の reasoning_chars / reasoning_prefix — 将来の GPT-5 Thinking 系モデル追加時に別フェーズで再調査。

**プロダクトコード側の実装方針 (Plan 04):**
- `app/providers/copilot.py` の `_astream` / `ainvoke` 経路に `session.on(on_event)` を追加し、ASSISTANT_USAGE の usage dict を `trace_span()` コンテキストに attach するフックを入れる。
- spike スクリプトの monkey-patch 式は本実装では不要 — `ChatCopilot` に最小 callback 引数（または Event emitter）を生やす設計で、spike は現状のまま SDK upgrade 時の regression test として残る。

### Known Stubs

なし — spike スクリプトはすべて動作可能なコード (UI にデータを流さないため stub 概念適用外)。scaffold ドキュメントの `TODO` は「人間がマトリクスを埋める」ための placeholder であり、機能 stub ではない。

---

## Self-Check: PASSED

**Verification executed 2026-04-18 (post-commit):**

- `[ -f scripts/spike_copilot_reasoning.py ]` → FOUND
- `[ -f docs/phase-31-reasoning-token-spike.md ]` → FOUND (130 行)
- `git log --oneline | grep 5a3a3bd` → FOUND (`feat(31-01): add Copilot SDK reasoning/usage capture spike script`)
- `git log --oneline | grep c4e56a7` → FOUND (`docs(31-01): scaffold phase-31 reasoning-token spike report`)
- `python3 -c "import ast; ast.parse(...)"` → OK
- `grep ASSISTANT_USAGE scripts/spike_copilot_reasoning.py` → FOUND
- `grep ASSISTANT_REASONING scripts/spike_copilot_reasoning.py` → FOUND
- `grep '__name__ == ' scripts/spike_copilot_reasoning.py` → FOUND

---

*Phase: 31-agent-mcp-observability*
*Plan: 01*
*Completed: 2026-04-18 (scaffold + script); human execution pending (Task 2 matrix)*
