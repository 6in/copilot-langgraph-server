---
phase: 36-text-code-image-multimodal
plan: 04
subsystem: worker
tags: [worker, langgraph-handler, orchestrator-handler, agent-state, additional-kwargs, vision-drop, copilot-sdk, multimodal, tdd]

# Dependency graph
requires:
  - phase: 36-text-code-image-multimodal
    provides: "Plan 02 — ChatCopilot.is_vision_model (D-18 fail-safe) + _extract_attachments (HumanMessage.additional_kwargs → SDK FileAttachment)"
  - phase: 36-text-code-image-multimodal
    provides: "Plan 03 — ChatRequest.attachments → arq.enqueue_job(attachments=...) bridge + GET messages additional_kwargs 返却"
  - phase: 37-pdf-office-mcp
    provides: "AgentState.attachments + folder scan + attachments_helper.scan_thread_attachments / build_attachments_hint"
provides:
  - "worker.process_chat に attachments: list[dict] | None = None kwarg 追加 (D-14 dict のリスト)"
  - "LangGraphHandler._prepare_messages_input helper — job.attachments → HumanMessage.additional_kwargs + D-18 vision drop + SystemMessage 警告"
  - "OrchestratorHandler._prepare_new_attachments helper — job.attachments → state.new_attachments + D-18 vision drop (defense-in-depth)"
  - "AgentState TypedDict に new_attachments: list[dict] | None フィールド追加 (D-14/D-20)"
  - "ChatApp 経路の per-turn attachments → SDK 配線完了 (worker → handler → ChatCopilot._extract_attachments → SDK FileAttachment)"
affects:
  - "phase-36 wave-4 plan-05 — frontend useAttachments / useModels hook と本 plan の API/worker 配線が e2e で繋がる"
  - "phase-36 wave-5 plan-06 — frontend MessageArea attachment chip 描画は本 plan の additional_kwargs 永続化に依存"
  - "phase-36 wave-6 plan-07 — integration check + smoke での e2e 検証は本 plan までの worker 配線 + Plan 03 の REST 入口を全部使う"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "private helper 抽出による handler ロジック単体テスト (handle() 全体は AsyncPostgresSaver / build_graph と深く連結のため _prepare_messages_input / _prepare_new_attachments で testable surface を分離)"
    - "AsyncMock(is_vision_model=AsyncMock(return_value=...)) で ChatCopilot 互換 LLM をモック"
    - "Pitfall 10 None-guard: HumanMessage.additional_kwargs={'attachments': [...]} if [...] else {} の二段防御"
    - "vision drop fail-safe (D-18 defense-in-depth): UI pre-validate (Plan 06) を bypass されても worker 側で必ず画像を drop"

key-files:
  created:
    - "tests/test_worker_attachments_payload.py — worker.process_chat の attachments kwarg payload 配線 3 unit test"
    - "tests/test_langgraph_handler_attachments_v2.py — LangGraphHandler._prepare_messages_input の 6 unit test (空 / text / 画像 vision OK/NG / mix)"
    - "tests/test_orchestrator_handler_attachments.py — OrchestratorHandler._prepare_new_attachments + AgentState.new_attachments の 4 unit test"
  modified:
    - "app/jobs/worker.py — process_chat シグネチャ末尾に attachments kwarg + job dict 1 行追加"
    - "app/jobs/handlers/langgraph_handler.py — _prepare_messages_input helper 追加 + _handle_inner からの呼び出しに置換"
    - "app/jobs/handlers/orchestrator_handler.py — _prepare_new_attachments helper 追加 + _handle_inner で aggregator LLM 用 ChatCopilot 一時生成 + initial state に new_attachments を載せる"
    - "app/orchestrator/state.py — AgentState TypedDict に new_attachments: list[dict] | None フィールド追加"

key-decisions:
  - "private helper 抽出 (_prepare_messages_input / _prepare_new_attachments): handler の handle() 全体は AsyncPostgresSaver / build_graph / graph.astream_events と深く連結していて mock できないため、attachments → additional_kwargs/state 注入と D-18 vision drop の純粋ロジックを helper に切り出して unit test 可能にした (Plan 文の指示通り)"
  - "OrchestratorHandler は state.new_attachments まで配線、SubAgent 側 HumanMessage 注入は v6.1 defer: SubAgent (ToolEnabledSubAgent / GemSubAgent) 側で HumanMessage(additional_kwargs={...}) を組み立てる経路は app/orchestrator/ 側で複数ある。本 plan scope を超えるため Plan 07 Open Issues に残件計上 (CONTEXT.md Claude's Discretion: ChatApp 中心)"
  - "DebateChat handler は本 plan で未変更 (v6.1 defer): CONTEXT.md Claude's Discretion (Phase 36 は ChatApp 中心、他アプリは InputBar 流用の範囲で自動継承) に基づき、debate_handler.py の additional_kwargs 配線 + vision drop は対応外"
  - "OrchestratorHandler の vision 判定用 ChatCopilot は一時生成 + try/finally で close: SuperChat の SubAgent は各 AGENT.md の model 設定で動くため handler 単独で aggregator_model を判定するための軽量インスタンスを作って即 close (リソースリーク回避)"
  - "image_exts は {png, jpg, jpeg, webp} のみ: D-09 path-based attachments の対象拡張子。pdf / xlsx / docx 等は Phase 37 の attachments_extract MCP ツール経由 (lazy fetch) で扱うため D-18 drop の対象外 (text/code として常に pass through)"

patterns-established:
  - "Phase 36 worker / handler 配線層 = LangGraphHandler が ChatApp 中心の権威実装、OrchestratorHandler は state まで運ぶ minimal 配線、DebateChat は v6.1 defer の三層構造"
  - "ext 比較は (a.get('ext') or '').lower().lstrip('.'): JPEG / .png / png 全パターンに耐える正規化"
  - "_prepare_* helper の unit test = AsyncMock(is_vision_model=AsyncMock(return_value=bool)) で ChatCopilot を完全代替する pattern (provider 層に触れない)"

requirements-completed: [FIN-01, FIN-02]

# Metrics
duration: ~9min
completed: 2026-04-24
---

# Phase 36 Plan 04: worker / handler 配線層 (additional_kwargs 注入 + D-18 vision drop) Summary

**Phase 36 の worker / handler 配線層を完成 — REST 入口 (Plan 03 で配線済み) → arq worker process_chat → LangGraphHandler/OrchestratorHandler → HumanMessage.additional_kwargs / AgentState.new_attachments の per-turn attachments パイプを完全に繋ぎ、defense-in-depth で vision 非対応モデル時の画像 drop + SystemMessage 警告を worker 層で実装した**

## Performance

- **Duration:** ~9 min (TDD 3 サイクル + verification + SUMMARY)
- **Started:** 2026-04-24T02:27:50Z
- **Completed:** 2026-04-24T02:36:42Z (約 532 秒)
- **Tasks:** 3/3 完了 (全 autonomous, checkpoint なし)
- **Files modified:** 3 created (test files) / 4 modified (worker.py / 2 handler / state.py)
- **Tests:** 13 new tests (3+6+4) + 既存 plan 関連 7 件 GREEN = 20 GREEN total / 全テスト suite 360 件 regression なし

## Accomplishments

- **worker.process_chat が attachments kwarg を受けて handler に流す**: REST 入口 (Plan 03 で `arq.enqueue_job(attachments=body.attachments)` 配線済) から worker までの payload bridge を完成。signature 末尾に `attachments: list[dict] | None = None` を追加し、job dict に 1 行 `"attachments": attachments` を加えた。3 件の unit test (kwarg 受け渡し / 後方互換 None default / 未知 task_type 経路) で固定。
- **LangGraphHandler が ChatApp 経路の per-turn attachments を完全配線**: `_prepare_messages_input(job, effective_system_prompt, llm, model, prompt)` helper を抽出し、(1) `job.attachments` を `HumanMessage.additional_kwargs['attachments']` に注入、(2) D-18 vision 非対応モデル時は `ext in {png,jpg,jpeg,webp}` を drop、(3) drop 時は `effective_system_prompt` 末尾に「画像非対応モデル警告」セクションを追加。空 / None 時は `additional_kwargs={}` で Pitfall 10 None-guard。6 件の unit test で全分岐固定。`_handle_inner` 本体からは helper を 1 回呼ぶだけにリファクタ。
- **OrchestratorHandler が SuperChat 経路で state.new_attachments まで配線 + vision drop**: `_prepare_new_attachments(job, llm, model)` helper を抽出し、AgentState に `new_attachments: list[dict] | None` フィールドを追加。`_handle_inner` 内で aggregator_model 用に `ChatCopilot(github_token, model=aggregator_model)` を一時生成 → `is_vision_model` 判定 → `try/finally` で close → initial state に `"new_attachments": new_attachments or None` を載せる。SubAgent 側 HumanMessage 注入は v6.1 で別途検討 (Plan 07 Open Issues)。
- **defense-in-depth の D-18 vision drop**: UI pre-validate (Plan 06 担当) を bypass されたケース、API direct 呼び出し、CLI スクリプト経由など、worker 層に到達したすべての経路で画像が drop されるようになった。`is_vision_model` は Plan 02 で fail-safe False (例外時は drop 側に倒れる) で実装済み。
- **既存テスト全て regression なし**: Plan 関連の 360 件 (worker / orchestrator / langgraph / attachments / provider 全部) がすべて GREEN。`tests/test_worker.py` の 4 件 / `tests/test_api_chat.py` の 6 件失敗は `deferred-items.md` 記載の pre-existing milestone debt で、本 plan の変更で増減なし (stash 検証済み)。

## Task Commits

各タスクは TDD で red/green の 2 コミットに分けて記録 (TDD ゲート遵守を git log で監査可能):

1. **Task 1 RED: worker.process_chat に attachments kwarg を追加するテスト先行作成** — `7d43e71` (test)
2. **Task 1 GREEN: worker.process_chat に attachments kwarg を追加し job dict に詰める** — `203f47a` (feat)
3. **Task 2 RED: LangGraphHandler._prepare_messages_input の unit test 先行作成** — `d94a06e` (test)
4. **Task 2 GREEN: LangGraphHandler に _prepare_messages_input helper 追加 + D-18 vision drop** — `b6cd709` (feat)
5. **Task 3 RED: OrchestratorHandler._prepare_new_attachments + AgentState.new_attachments テスト先行作成** — `4bf2bc5` (test)
6. **Task 3 GREEN: OrchestratorHandler に _prepare_new_attachments + AgentState.new_attachments 追加** — `625d0a6` (feat)

_Note: Plan 04 全体は `type: execute` だが、各 task の `tdd="true"` 指定に従い red → green の 2 commit 分割で運用。Plan 02/03 で確立した運用を踏襲し TDD ゲート遵守を git log で監査可能にした。Refactor phase は不要 (helper / state ともに最小実装で behavior を満たすため)。_

## Files Created/Modified

**Created:**
- `tests/test_worker_attachments_payload.py` (116 lines) — worker.process_chat の attachments payload 配線 3 unit test。AsyncMock handler を `monkeypatch.setitem(worker.TASK_HANDLERS, "langgraph", ...)` で差し込み、job dict を capture して assert する pattern。
- `tests/test_langgraph_handler_attachments_v2.py` (194 lines) — LangGraphHandler._prepare_messages_input の 6 unit test。AsyncMock(is_vision_model=AsyncMock(return_value=...)) で ChatCopilot 互換 LLM をモック。`_text_att(name)` / `_image_att(name, ext)` factory で D-14 dict を組み立て。
- `tests/test_orchestrator_handler_attachments.py` (120 lines) — OrchestratorHandler._prepare_new_attachments の 3 unit test + AgentState.new_attachments フィールド存在の 1 test。

**Modified:**
- `app/jobs/worker.py` (202 → 209 行, +7 行) — process_chat signature に `attachments: list[dict] | None = None` を追加 (L146-149) + job dict に `"attachments": attachments` を追加 (L191-193)。
- `app/jobs/handlers/langgraph_handler.py` (233 → 290 行, +57 行) — `_prepare_messages_input(job, effective_system_prompt, llm, model, prompt) -> tuple[list, str]` helper を class level に追加 (L105-156)。`_handle_inner` 内 L207-211 で helper を呼ぶように置換し、既存の `messages_input = [HumanMessage(content=prompt)]` 行を削除。state_input は messages_input をそのまま使うので変更なし。
- `app/jobs/handlers/orchestrator_handler.py` (317 → 358 行, +41 行) — `_prepare_new_attachments(job, llm, model) -> list[dict]` helper を class level に追加 (L31-67)。`_handle_inner` 内 L256-269 で aggregator LLM (`ChatCopilot(github_token, model=aggregator_model)`) を一時生成して is_vision_model 判定 → try/finally で close、initial state (L289) に `"new_attachments": new_attachments or None` を追加。
- `app/orchestrator/state.py` (19 → 23 行, +4 行) — AgentState TypedDict に `new_attachments: list[dict] | None` フィールドを追加 (Phase 36 D-14/D-20 の per-turn attachments 用)。既存 `attachments` フィールド (Phase 37 D-12 の last-wins folder scan 結果) は保持。

## Implementation Map (どこで何が起こるか)

```
[REST 入口 — Plan 03]
POST /api/chat
  body.attachments: list[dict]
       │
       ▼
arq.enqueue_job("process_chat", ..., attachments=body.attachments)
       │
[Worker 入口 — Plan 04 Task 1]
       ▼
worker.process_chat(ctx, ..., attachments=...)        ← signature に kwarg 追加
  job = {..., "attachments": attachments}             ← job dict に詰める
       │
       ▼
TASK_HANDLERS[task_type].handle(ctx, job)
       │
       ├─── task_type == "langgraph"   ─── Plan 04 Task 2
       │      LangGraphHandler.handle(ctx, job)
       │       └─ _handle_inner
       │          ├─ folder scan (Phase 37 既存) → effective_system_prompt
       │          └─ messages_input, effective_system_prompt =
       │              await self._prepare_messages_input(            ← 新 helper
       │                  job, effective_system_prompt, llm, model, prompt)
       │                  │
       │                  ├─ job.attachments == None/[]  → empty {} (Pitfall 10)
       │                  ├─ vision_ok → そのまま additional_kwargs に注入
       │                  └─ vision NG  → 画像 drop + 警告 system_prompt 追加
       │              │
       │              ▼
       │          state_input = {"messages": [HumanMessage(... additional_kwargs={"attachments": [...]})], ...}
       │              │
       │              ▼
       │          graph.astream_events(state_input, ...)
       │              │ (chatbot_node の LLM 呼び出し時)
       │              ▼
       │          ChatCopilot._agenerate(messages)
       │              │
       │              ▼
       │          self._extract_attachments(messages)                ← Plan 02 既存
       │              → SDK FileAttachment dict のリスト
       │              ▼
       │          session.send_and_wait(prompt, attachments=sdk_atts)  ← Plan 02 既存
       │
       └─── task_type == "orchestrator" ─── Plan 04 Task 3
              OrchestratorHandler.handle(ctx, job)
               └─ _handle_inner
                  ├─ folder scan (Phase 37 既存)
                  ├─ aggregator_model = job.get("model") or "claude-sonnet-4.5"
                  ├─ _vision_llm = ChatCopilot(token, aggregator_model)   ← 一時生成
                  ├─ try:
                  │    new_attachments = await self._prepare_new_attachments(   ← 新 helper
                  │        job, _vision_llm, aggregator_model)
                  │        │
                  │        ├─ 空 → []
                  │        ├─ vision_ok → そのまま
                  │        └─ vision NG → 画像 (png/jpg/jpeg/webp) drop
                  │  finally: await _vision_llm.close()              ← リソース cleanup
                  │
                  └─ initial state = {..., "new_attachments": new_attachments or None}
                                                                       ▼
                                  ◆ ここで配線終了 (本 plan scope) ◆
                                                                       │
                                                                       ▼
                              SubAgent (ToolEnabledSubAgent / GemSubAgent) 側で
                              HumanMessage.additional_kwargs に state["new_attachments"] を
                              展開する経路は v6.1 検討 (Plan 07 Open Issues に残件計上)
```

## Decisions Made

- **private helper 抽出方針**: Plan 文の指示通り `_prepare_messages_input` / `_prepare_new_attachments` を抽出して unit test 可能にした。これにより handler の `handle()` 全体 (AsyncPostgresSaver + build_graph + graph.astream_events) の重い mock を避けつつ、attachments → additional_kwargs/state 注入 + D-18 vision drop の純粋ロジックを TDD で書けた。
- **OrchestratorHandler は state.new_attachments まで配線、SubAgent 側は v6.1 defer**: SuperChat 経路の SubAgent (ToolEnabledSubAgent / GemSubAgent) 側で HumanMessage を組み立てる箇所は app/orchestrator/ 配下に複数ある (agent.py / tool_agent.py / gem_agent.py)。本 plan で全箇所を改修するのは scope を超えるため、state に置くまでで完了。CONTEXT.md Claude's Discretion (ChatApp 中心) と整合し、Plan 07 Open Issues に残件として計上。SuperChat の実機での画像認識可否は Plan 07 smoke test で確認、不可なら v6.1 で SubAgent 側配線を追加。
- **DebateChat handler は本 plan で未変更**: CONTEXT.md Claude's Discretion に基づき、DebateChat 経路の attachments 対応は v6.1 defer。Plan 文の Task 2 内の指示も「debate_handler.py 修正は v6.1 defer」と明記。debate_handler.py / debate_graph.py は本 plan で 1 行も変更せず。
- **aggregator LLM の一時生成 + try/finally close**: SuperChat の SubAgent は各 AGENT.md の model 設定で動くため、handler 自身は LLM インスタンスを持たない。vision 判定だけのために `ChatCopilot(github_token, model=aggregator_model)` を一時生成し、`try/finally: await _vision_llm.close()` でリソースリークを防ぐ。`is_vision_model` は内部で list_models キャッシュ (Plan 02 で TTL 1h 実装済) を引くので毎回 SDK を呼ぶことはない。
- **image_exts は {png, jpg, jpeg, webp} に限定**: D-09 path-based attachments で SDK が直接読む対象。pdf / xlsx / docx 等の binary は Phase 37 の `attachments_extract` MCP ツール経由 (lazy fetch) で扱うため D-18 drop の対象外で text/code として常に pass through する。これにより「PDF 添付したのに画像非対応モデルだから消える」という UX 事故を回避。
- **ext 正規化は `(a.get("ext") or "").lower().lstrip(".")`**: D-14 dict は `"ext": "png"` を期待しているが、防御的に `.png` / `PNG` / `JPEG` 等の表記揺れに耐える。Test 5 で `"e.JPEG"` を drop することで pattern を固定。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] OrchestratorHandler の vision 判定 LLM のリソース cleanup を try/finally で保証**

- **Found during:** Task 3 GREEN 実装中 (handler 内で `_vision_llm = ChatCopilot(...)` を作るとき)
- **Issue:** Plan 文の Step 2 では「`aggregator_model = job.get("model") or "claude-sonnet-4.5"` で `ChatCopilot` を生成して `is_vision_model` を呼ぶ」とだけ書かれているが、`ChatCopilot` 内部に SDK subprocess へのハンドルがあるため close しないと Pitfall (リソースリーク + 残存 subprocess)。LangGraphHandler 既存実装は `finally: await llm.close()` で close している。
- **Fix:** OrchestratorHandler の `_handle_inner` 内に `try: new_attachments = await self._prepare_new_attachments(...) finally: await _vision_llm.close()` を入れ、判定後即 close する。`is_vision_model` は内部で list_models キャッシュ (Plan 02 で TTL 1h 実装済) を引くので close で次回パフォーマンスが落ちることはない。
- **Files modified:** `app/jobs/handlers/orchestrator_handler.py` (Task 3 GREEN コミットに含む)
- **Verification:** `await _vision_llm.close()` 行が finally ブロックにある: `grep -n "_vision_llm.close" app/jobs/handlers/orchestrator_handler.py` → 1 行。
- **Committed in:** `625d0a6` (Task 3 GREEN commit)

**2. [Rule 2 - Missing Critical] テストケース追加: `_text_att` empty list ケース (Pitfall 10 完全網羅)**

- **Found during:** Task 2 RED テスト作成時
- **Issue:** Plan 文の Test 2 は「attachments が None / []」と書かれているが、実装上 `None` と `[]` は通る経路が違う可能性がある (`job.get("attachments") or []` で正規化されるが、`additional_kwargs={}` を返すロジックは両方検証必要)。1 つの test に詰めるよりも 2 つに分けた方が回帰検出に強い。
- **Fix:** `test_langgraph_handler_no_attachments_passes_empty_kwargs` (None ケース) と `test_langgraph_handler_empty_list_passes_empty_kwargs` (空 list ケース) の 2 件に分割。両方とも `additional_kwargs == {}` + vision 判定が呼ばれない (`is_vision_model.assert_not_awaited()`) を assert。Plan 文の元 5 件 → 6 件に増えた (Plan 文の done 条件は「5 tests が GREEN」だが、Pitfall 10 完全網羅のため 6 件に拡張)。
- **Files modified:** `tests/test_langgraph_handler_attachments_v2.py` (Task 2 RED コミットに含む)
- **Verification:** `pytest tests/test_langgraph_handler_attachments_v2.py -v` → 6 passed
- **Committed in:** `d94a06e` (Task 2 RED) + `b6cd709` (Task 2 GREEN)

---

**Total deviations:** 2 auto-fixed (2 Rule 2 missing critical)
**Impact on plan:** Phase 36 全体方針 (D-09 / D-14 / D-15 / D-18 / additional_kwargs サイドカー) は完全に維持。Plan 文の指示の意図 (リソースリーク防止 + Pitfall 10 None-guard) を実装段階で defensive に補強しただけで、scope creep なし。

## Issues Encountered

- **Pre-existing test failures (deferred-items.md 既記録, milestone debt)**: `tests/test_worker.py` の 4 件 (`test_process_chat_saves_result` / `test_process_chat_error_handling` / `test_process_chat_closes_llm` / `test_orchestrator_handler_uses_checkpointer`) は Plan 04 着手前から AttributeError + AsyncMock セッション署名古い系で失敗しており、本 plan の変更を `git stash` で退避した状態でも同一失敗を再現。CLAUDE.md / executor scope rule (`Only auto-fix issues DIRECTLY caused by the current task's changes`) に従い手を出さない。`tests/test_api_chat.py` の 6 件失敗も Plan 02 で deferred 記録済 (JWT cookie / DB AsyncMock 不整合) で同様。
- **worktree base 不一致 (起動時に検出 → 即修正)**: 起動直後の `<worktree_branch_check>` で `ACTUAL_BASE` が `0d51621` (phase-37 の先) になっていたため `git reset --hard 05b2107` で Plan 03 完了時点に戻した。データロス無し (新規作業前の修正)。

## Threat Flags

なし — Plan の `<threat_model>` (T-36-04-01〜07) はすべて Plan 内で対処済 / accept disposition:

- **T-36-04-01 (UI bypass で非対応モデルに画像送付)**: `_prepare_messages_input` (LangGraph) と `_prepare_new_attachments` (Orchestrator) の両方で `is_vision_model == False` 時に `ext in {png,jpg,jpeg,webp}` を drop。Test 4 (vision drop) / Test 6 (mixed) で固定。**mitigate (BLOCKING) — 完了**.
- **T-36-04-02 (additional_kwargs に機密内容混入)**: D-14 dict は name/path/size/mime のメタデータのみで実ファイル内容は SDK subprocess 経由でしか読まない (Plan 02 で確認済)。**accept**.
- **T-36-04-03 (大量 attachments DoS)**: Plan 03 で 100MB hard cap + UI 側 5 画像制限。worker 側 array 長 cap は Phase 36 scope 外。**accept**.
- **T-36-04-04 (不正 shape の dict)**: Plan 02 `_extract_attachments` で `isinstance(a, dict) and a.get("kind") == "file" and isinstance(path, str) and path` の 3 段防御済み。本 plan の helper も `isinstance(a, dict)` ガードを噛ませている。**mitigate**.
- **T-36-04-05 (is_vision_model 例外時に True 誤返却)**: Plan 02 で fail-safe False 実装済。Exception 時は drop 側に倒れる。**mitigate**.
- **T-36-04-07 (SuperChat SubAgent が state.new_attachments を無視)**: 本 plan scope 外。Plan 07 Open Issues 計上。**accept (v6.1 検討)**.

新規 surface 追加なし (worker.process_chat の 1 kwarg / handler の private helper / state field 追加のみで、外部公開 API 増加なし)。

## User Setup Required

None - 本 plan は worker / handler 配線層のみで、外部サービスや環境変数の追加なし。docker compose で起動済みの api / worker / postgres / redis が引き続き動作。

## Next Phase Readiness

- **Plan 05 (Wave 4 — frontend useAttachments / useModels hook)**: 本 plan で worker → SDK 配線が完成。Plan 05 実装後に frontend → REST → worker → SDK の e2e flow が動く状態 (実機 smoke は Plan 07 で確認)。
- **Plan 06 (Wave 5 — frontend MessageArea attachment chip 描画)**: GET /api/threads/{tid}/messages の `additional_kwargs.attachments` (Plan 03 で配線済) が、本 plan の HumanMessage.additional_kwargs 注入により実データを返すようになった。Plan 06 はそのデータからチップを描画するだけ。
- **Plan 07 (Wave 6 — integration check + smoke)**: 本 plan までで ChatApp 経路の e2e (REST 入口 → worker → handler → ChatCopilot → SDK) が完全配線済。Plan 07 で smoke test を実行できる。SuperChat 経路は state.new_attachments まで運ばれているが SubAgent 側 HumanMessage 注入は未実装のため、SuperChat の画像認識可否は Plan 07 smoke で実測 → v6.1 検討の判断材料にする。
- **DebateChat 経路**: 本 plan で未変更。Plan 07 の Open Issues に「DebateChat handler の attachments 対応は v6.1 defer」を記載する。
- **Blocker**: なし — Wave 3 完了 gate すべて GREEN, Wave 4 (Plan 05) 着手 OK。

## Self-Check: PASSED

- ✅ `app/jobs/worker.py` exists with attachments kwarg + job dict (`grep -n "attachments" app/jobs/worker.py` → signature L149 + comment L146-148 + job dict L191-193 + comment 計 7 行)
- ✅ `app/jobs/handlers/langgraph_handler.py` exists with `_prepare_messages_input` helper (`grep -n "_prepare_messages_input" app/jobs/handlers/langgraph_handler.py` → 2 箇所: 定義 L105 + 呼出し L209)
- ✅ `app/jobs/handlers/langgraph_handler.py` has `additional_kwargs` (`grep -c "additional_kwargs" app/jobs/handlers/langgraph_handler.py` → 5 occurrences: docstring + 2 implementations + 1 comment)
- ✅ `app/jobs/handlers/langgraph_handler.py` has `is_vision_model` (`grep -n "is_vision_model" app/jobs/handlers/langgraph_handler.py` → 2 箇所: docstring + L130 呼出し)
- ✅ `app/jobs/handlers/orchestrator_handler.py` has `_prepare_new_attachments` (`grep -n "_prepare_new_attachments" app/jobs/handlers/orchestrator_handler.py` → 2 箇所: 定義 L31 + 呼出し L265)
- ✅ `app/jobs/handlers/orchestrator_handler.py` has `new_attachments` (`grep -n "new_attachments" app/jobs/handlers/orchestrator_handler.py` → 7 箇所: 定義 + 呼出し + state 注入)
- ✅ `app/orchestrator/state.py` has `new_attachments: list[dict] | None` (`grep -n "new_attachments" app/orchestrator/state.py` → 1 行 L23)
- ✅ `tests/test_worker_attachments_payload.py` exists (116 lines, 3 tests GREEN)
- ✅ `tests/test_langgraph_handler_attachments_v2.py` exists (194 lines, 6 tests GREEN)
- ✅ `tests/test_orchestrator_handler_attachments.py` exists (120 lines, 4 tests GREEN)
- ✅ Commit `7d43e71` (test) reachable
- ✅ Commit `203f47a` (feat) reachable
- ✅ Commit `d94a06e` (test) reachable
- ✅ Commit `b6cd709` (feat) reachable
- ✅ Commit `4bf2bc5` (test) reachable
- ✅ Commit `625d0a6` (feat) reachable
- ✅ `docker compose exec worker uv run python -m pytest tests/test_worker_attachments_payload.py tests/test_langgraph_handler_attachments_v2.py tests/test_orchestrator_handler_attachments.py tests/test_langgraph_handler.py tests/test_langgraph_handler_attachments.py -v` → 18 passed, 2 skipped
- ✅ Full-suite regression check (除外: deferred-items.md 記載の pre-existing failures) → 360 passed, 12 skipped, 2 xpassed
- ✅ DebateChat handler 未変更 (`git diff 05b2107 HEAD -- app/jobs/handlers/debate_handler.py` → 空差分): v6.1 defer 通り
- ✅ Stub patterns (TODO/FIXME/placeholder) は新規/変更ファイルにゼロ

---

*Phase: 36-text-code-image-multimodal*
*Plan: 04 (Wave 3)*
*Completed: 2026-04-24 — Wave 3 完了, Plan 05 (Wave 4 frontend hooks) 着手 OK*
