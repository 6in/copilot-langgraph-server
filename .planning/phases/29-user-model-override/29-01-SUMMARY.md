---
phase: 29-user-model-override
plan: 01
subsystem: orchestrator
tags: [langgraph, subagent, model-selection, superchat, copilot]

requires:
  - phase: 09-superchat
    provides: OrchestratorHandler / SubAgentRegistry / ChatCopilot(model=...) の基盤
  - phase: 15-gem-canvas
    provides: GemSubAgent 継承構造（model パラメータ経由）

provides:
  - SubAgentRegistry / SubAgent.from_dir への model_override パラメータ追加
  - OrchestratorHandler での `job["model"]` → Registry への伝播
  - folder / folder+tools / codeact / gem の 4 種別 SubAgent で model_override 優先
  - 空文字 model 指定時のフォールバック（`or None` 正規化）

affects:
  - SuperChat UI モデル選択ドロップダウン（既存フロント動作が期待通りに反映）
  - 今後追加する SubAgent 種別（model パラメータを外部から渡せるパターンが確立）

tech-stack:
  added: []
  patterns:
    - "`model_override or meta.get('model', default)` フォールバック — 3 層（Handler / Registry / from_dir）で一貫"
    - "`job.get('model') or None` による空文字 → None 正規化 — JS UI 空文字送信対応"

key-files:
  created:
    - tests/test_model_override.py
  modified:
    - app/orchestrator/agent.py
    - app/jobs/handlers/orchestrator_handler.py

key-decisions:
  - "model_override は __init__ 時の 1 回で伝播（run() 実行時の動的切替はしない）"
  - "code-type agent (_load_code_agent) は対象外。独自 from_dir シグネチャを侵襲しない"
  - "空文字は Python の `or` で None に正規化。`dict.get('model', None)` は空文字を素通しするため不可"
  - "GemSubAgent は継承元の model 引数を使う。DEFAULT_MODEL を orchestrator_handler で参照"

patterns-established:
  - "Pattern: `override or default` フォールバック — UI 選択 / AGENT.md 固定 / ハードコード既定の 3 段優先"
  - "Pattern: 空文字安全な dict 読み取り — `dict.get(k) or None` イディオム"

requirements-completed: []

duration: 5min
completed: 2026-04-18
---

# Phase 29 Plan 01: User Model Override Summary

**SuperChat のフロントエンドで選択したモデルが全エージェント種別（folder / folder+tools / codeact / gem）で AGENT.md の `model` フィールドより優先されるようになった。**

## Performance

- **Duration:** 約 5 min
- **Started:** 2026-04-17T23:36:22Z
- **Completed:** 2026-04-17T23:40:30Z（approx）
- **Tasks:** 1 / 1
- **Files modified:** 3 (新規 1、変更 2)

## Accomplishments

- SuperChat UI でユーザーが選択したモデルが、各エージェントが AGENT.md に書かれた固定モデルを上書きして推論に使われるようになった
- モデル未選択（空文字送信）の場合は AGENT.md のモデルがフォールバックとして機能
- folder / folder+tools (ToolEnabledSubAgent) / codeact (CodeActSubAgent) / gem (GemSubAgent) の 4 種別全てで model_override が反映
- model_override 伝播の unit テスト 6 本を新規追加し全件 pass
- 通常 Chat モード（langgraph_handler 経路）や code-type agent には影響なし

## Task Commits

TDD を適用し、task 内を RED / GREEN の 2 コミットに分割:

1. **Task 1 (RED): failing テスト追加** — `4bb535f` (test)
2. **Task 1 (GREEN): model_override 実装 + テストフィクスチャ修正** — `2f21ddb` (feat)

_Note: TDD gate 満たす: test → feat の順序で commit。REFACTOR は不要と判断（コード重複なし）。_

## Files Created/Modified

- `tests/test_model_override.py` — 新規。6 ケースの unit テスト:
  - Test 1-3: SubAgentRegistry 経由で folder-type SubAgent への伝播 / None フォールバック / 空文字フォールバック
  - Test 4: ToolEnabledSubAgent への伝播
  - Test 5: CodeActSubAgent への伝播
  - Test 6: SubAgent.from_dir 直接呼び出しでの model_override 優先
- `app/orchestrator/agent.py` — 変更:
  - `SubAgent.from_dir(..., model_override: str | None = None)` シグネチャ拡張
  - `SubAgentRegistry.__init__(..., model_override: str | None = None)` シグネチャ拡張
  - `self._model_override = model_override or None` を保存
  - CodeActSubAgent 生成部（L.222）に `model_override or meta.get("model", "gpt-4.1")`
  - ToolEnabledSubAgent 生成部（L.234）に `model_override or meta.get("model", "claude-sonnet-4-6")`
  - SubAgent.from_dir 呼び出し 2 箇所（L.246, L.249）に `model_override=model_override`
  - code-type agent パスはコメントで「対象外」を明示
- `app/jobs/handlers/orchestrator_handler.py` — 変更:
  - 既存コメント「model is intentionally unused」を削除
  - `model_override: str | None = job.get("model") or None` を追加（空文字 → None 正規化）
  - `SubAgentRegistry(..., model_override=model_override)` に引数追加
  - `from app.orchestrator.gem_agent import GemSubAgent, DEFAULT_MODEL` に変更
  - `GemSubAgent(..., model=model_override or DEFAULT_MODEL)` に引数追加

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `or None` で空文字を正規化 | `dict.get("model", None)` は空文字 `""` を素通しするため、Copilot SDK に空モデル名が渡るリスクがある |
| `model_override` を `__init__` 時点で適用 | ChatCopilot は Pydantic の model フィールドを初期化時に渡す設計。`bind_tools` 後の変更はコストが高い |
| code-type agent は対象外 | `_load_code_agent` 経由の独自 from_dir はエージェントコード側で定義されており、破壊的変更になる |
| GemSubAgent には handler 側で直接 `model=` を渡す | Gem は DB から動的に生成されるため Registry を経由しない。DEFAULT_MODEL を明示 import してハードコード回避 |
| テストフィクスチャは `textwrap.dedent` をやめて行単位組立て | f-string 内で optional block を挿入すると YAML インデントが崩れ、フロントマターが壊れる |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] テストフィクスチャの AGENT.md テンプレートが optional tools ブロック挿入時に YAML を壊す**

- **Found during:** Task 1 GREEN フェーズ、Test 4 (ToolEnabledSubAgent) 実行時
- **Issue:** `textwrap.dedent(f"""... {tools_block} ...""")` の設計で、`tools_block = "tools:\n  - ping\n  - web_search_stub\n"` を挿入すると、
  - dedent は全行共通プレフィックスがないため削除ゼロになる
  - `  - ping` のインデントがフロントマター (4 スペース領域) と合わない
  - 結果、`tools:` 行は description YAML ブロック内に吸収され、`- ping` は文書本体扱いになり、`---` の閉じ境界が壊れる
  - YAML パーサーが `did not find expected <document start>` エラーで DEGRADED
- **Fix:** `textwrap.dedent` + f-string 方式を廃止し、`lines: list[str] = [...]` を build してから `"\n".join()` で書き出す行単位組立てに変更。`with_tools=True` / `agent_type=...` の有無で lines を伸縮させる
- **Files modified:** tests/test_model_override.py (`write_agent_md` ヘルパー関数)
- **Verification:** 6 テストケース全件 pass（修正前は Test 1-3 pass / Test 4 で KeyError）
- **Committed in:** `2f21ddb` (feat コミットに同梱 — 同じタスク内の GREEN 作業)

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** テストヘルパーの実装ミスを実装フェーズ中に発見・修正。プロダクションコードには影響なし。スコープ逸脱なし。

## Issues Encountered

- **既存テスト群に pre-existing failures が多数存在**（22 件）: `test_api_chat.py`, `test_api_jobs.py`, `test_sse.py`, `test_worker.py`, `test_graph.py`, `test_provider.py`, `test_tool_enabled_subagent.py`, `test_debate_handler.py`, `test_rpc_integration.py`, `test_orchestrator_graph.py`。
  - baseline 確認（自分の変更を git stash してから実行）したところ、全く同じ 22 件 + model_override の 6 件が失敗 = 合計 28 件失敗
  - 自分の変更後は 6 件が pass に転じて 16 件残る = 回帰ゼロ、6 件新規 green
  - **Scope boundary rule により本フェーズでは fix しない**。deferred 扱い
- ホスト側 `uv` は `.venv` のパーミッション問題で起動不可。`docker compose exec api uv run pytest` を代替ルートとして使用

## User Setup Required

なし。コード変更のみでフロントエンドの既存動作（モデル選択送信）をそのまま活用。デプロイ時は `docker compose build api worker && docker compose up -d api worker` で反映される。

## Known Stubs

なし。UI に渡る placeholder / TODO データなし。

## Deferred Issues

既存の pre-existing test failures 22 件は本フェーズ範囲外。主な分類:

- **401 認証エラー系** (test_api_chat / test_api_jobs / test_sse): JWT 認証周りのテストセットアップが古いセッション構造と乖離
- **async コンテキスト系** (test_graph / test_worker): AsyncMock 使用が期待される箇所で MagicMock が使われている
- **provider 系** (test_provider): Copilot SDK モック仕様が SDK 0.2.0 でずれている

これらは別フェーズ（または `/gsd-debug` quick）で扱うことを推奨。

## TDD Gate Compliance

`tdd="true"` task の gate 遵守:

- RED gate (`test(29-01): ...`): 4bb535f — テスト作成時 6/6 fail 確認済み
- GREEN gate (`feat(29-01): ...`): 2f21ddb — 実装後 6/6 pass 確認済み
- REFACTOR gate: 不要と判断（コード重複・スタイル問題なし）

## Verification Results

- [x] `uv run pytest tests/test_model_override.py -x -q` → 6 passed
- [x] `uv run pytest tests/ -q --ignore=tests/test_api_chat.py` → 自分の変更起因の fail なし（baseline diff で確認）
- [x] `grep -c "model_override" app/orchestrator/agent.py` → 12（≥6 OK）
- [x] `grep -c "model_override" app/jobs/handlers/orchestrator_handler.py` → 4（≥3 OK）
- [x] SuperChat / Chat / Canvas 経路の影響範囲チェック: `langgraph_handler.py` は無変更、通常 Chat モードは既存動作維持

## Self-Check: PASSED

Files:
- FOUND: tests/test_model_override.py
- FOUND: app/orchestrator/agent.py
- FOUND: app/jobs/handlers/orchestrator_handler.py
- FOUND: .planning/phases/29-user-model-override/29-01-SUMMARY.md

Commits:
- FOUND: 4bb535f (RED)
- FOUND: 2f21ddb (GREEN)
