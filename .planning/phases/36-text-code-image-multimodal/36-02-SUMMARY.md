---
phase: 36-text-code-image-multimodal
plan: 02
subsystem: api
tags: [copilot-sdk, multimodal, file-attachment, model-catalog, fastapi, ttl-cache, jwt, langchain]

# Dependency graph
requires:
  - phase: 36-text-code-image-multimodal
    provides: "Plan 01 — A1 risk verdict / SDK contract pin / SubprocessConfig API 訂正 / displayName required の確認 / docker compose smoke PASS"
  - phase: 37-pdf-office-mcp
    provides: "AgentState.attachments + ADR-0048 フォルダ規約 + langgraph_handler の SystemMessage prepend"
provides:
  - "ChatCopilot._extract_attachments — HumanMessage.additional_kwargs['attachments'] → SDK FileAttachment dict 変換 (D-10/D-14/D-15)"
  - "ChatCopilot._agenerate / _astream — session.send_and_wait / send への attachments=sdk_atts 配線 (D-09)"
  - "ChatCopilot.list_models — SDK ModelInfo dataclass を D-14 dict に変換するヘルパー (D-16)"
  - "ChatCopilot.is_vision_model — model_id の vision フラグ参照 + fail-safe False (D-18)"
  - "GET /api/models route — TTL 1h キャッシュ + JWT 認証 + 503 graceful (D-07/D-16)"
  - "app/api/routes/attachments.py stub router — Plan 03 で本実装する場所を確保"
  - "app/api/main.py — attachments / models 両 router を hosted_apps の直前に include"
affects:
  - "phase-36 wave-2 plan-03 — ChatRequest.attachments + multipart upload route が attachments.router stub を拡張"
  - "phase-36 wave-3 plan-04 — worker / handler が is_vision_model を D-18 vision drop で利用、_extract_attachments の経路を埋める"
  - "phase-36 wave-5 plan-06 — frontend が GET /api/models を useModels hook 経由で消費"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SDK 隔離原則の継続: copilot.FileAttachment / ModelInfo の import は app/providers/copilot.py に閉じ、route 層には D-14 dict のみを露出"
    - "TTL 1h dataclass キャッシュ pattern (module-level _Cache) — graceful fallback は cache 残存時に古い payload を返す"
    - "displayName 必ず埋める方針 (path basename fallback) — SDK __required_keys__ の事実に合わせて防御的に補完"

key-files:
  created:
    - "tests/test_copilot_attachments.py — ChatCopilot multimodal helper の 11 unit test (5 _extract_attachments / 2 _agenerate / 2 list_models / 2 is_vision_model)"
    - "tests/test_api_models_route.py — GET /api/models の 5 integration test (200 / 401 / cache hit / TTL expiry / 503 graceful)"
    - "app/api/routes/models.py — GET /api/models (TTL 1h キャッシュ, JWT 認証, 503 graceful)"
    - "app/api/routes/attachments.py — Plan 03 用 stub APIRouter (空 router export のみ)"
    - ".planning/phases/36-text-code-image-multimodal/deferred-items.md — 6 件の pre-existing test_api_chat 失敗を Plan 03 / quick task 向けに記録"
  modified:
    - "app/providers/copilot.py — imports に FileAttachment + ModelInfo 追加、_extract_attachments / list_models / is_vision_model の 3 ヘルパー追加、_agenerate / _astream に attachments=sdk_atts 配線"
    - "app/api/main.py — route imports に attachments + models 追加、include_router を hosted_apps 直前に 2 行追加"
    - "tests/test_provider.py — test_send_and_wait_called_with_string を attachments=None + timeout kwarg 追加に対応 (Plan Step 7 で予期されていた regression 修正)"

key-decisions:
  - "SDK の FileAttachment.displayName は __required_keys__ に含まれるため (Wave 0 Plan 01 Deviation #2)、_extract_attachments は path basename fallback で必ず displayName を埋める方針に変更 (Plan 当初の name 必須 → 任意経路を強化)"
  - "attachments_extract MCP ツール (Phase 37) との並存を維持しつつ、本 plan は eager attach path のみを ChatCopilot に乗せる (D-11/D-12 の責務分離をコード層でも明示)"
  - "GET /api/models は 503 graceful — list_models 例外時に cache が残っていれば古い payload を返し UI 継続させる (D-16 stale データ許容方針、threat T-36-02-06)"
  - "test_provider.py の 厳密 assert_called_once_with は 部分 assert (args == ('[User]: hello',) + kwargs に attachments=None / timeout) に書き直す (TDD GREEN を阻害しない最小修正)"
  - "test_api_chat.py の 6 件 pre-existing failure は Plan 02 のスコープ外として deferred-items.md に記録 (CLAUDE.md / executor scope rule)"

patterns-established:
  - "Phase 36 SDK 配線コア層 = ChatCopilot wrapper に閉じる: 他モジュールは D-14 dict のみで attachments / model 情報を扱う"
  - "Module-level _Cache dataclass + per-test reset = TTL キャッシュ route のテスト容易性を担保 (テスト順序非依存)"
  - "TDD RED → GREEN を 1 commit ずつ分ける = test (RED) と feat (GREEN) を独立コミットすることで TDD ゲート遵守を git log で監査可能"

requirements-completed: [FIN-01, FIN-02]

# Metrics
duration: ~25min
completed: 2026-04-24
---

# Phase 36 Plan 02: ChatCopilot multimodal helpers + GET /api/models route Summary

**Copilot SDK 0.2.0 multimodal の SDK 配線コア層を ChatCopilot wrapper に集約し、SDK 隔離原則を守ったまま attachments / model catalog / vision 判定の 3 機能を有効化、加えて TTL 1h キャッシュ付き GET /api/models を JWT 認証下で公開した**

## Performance

- **Duration:** ~25 min (TDD 2 サイクル + regression 修正 + main.py 配線 + SUMMARY)
- **Started:** 2026-04-24T01:33:00Z
- **Completed:** 2026-04-24T01:58:37Z
- **Tasks:** 2/2 完了 (全 autonomous, checkpoint なし)
- **Files modified:** 3 created (新規 route 2 + テスト 2 = 4 を含む) / 3 modified (provider / main.py / 既存 test の regression 修正)
- **Tests:** 16 new (11 + 5) + 既存 29 件 GREEN = 計 45 GREEN

## Accomplishments

- **ChatCopilot 拡張完了**: `_extract_attachments` / `list_models` / `is_vision_model` の 3 ヘルパーを追加し、`_agenerate` と `_astream` の両ストリーミング経路で `attachments=sdk_atts` を SDK に配線. SDK 型 (`FileAttachment` / `ModelInfo`) の import は `app/providers/copilot.py` 内に閉じ、SDK 隔離原則 (D-09/D-15) を維持.
- **GET /api/models 公開**: JWT 認証下で `[{id, name, vision, vision_limits, billing_multiplier}, ...]` を返す REST endpoint を新規追加. dataclass `_Cache` で TTL 1h キャッシュを実装し、`list_models()` 例外時は cache 残存なら古い payload を返し空なら 503 — D-16 graceful 方針通り.
- **attachments stub router 配置**: Plan 03 (Wave 2) で multipart upload を実装する `attachments.router` を空 APIRouter として作成し、main.py の include_router 順序 (hosted_apps の直前) を確定. これで Plan 03 は新規ファイル作成不要で endpoint 追加のみに集中できる.
- **既存テスト regression 修正**: Plan の Step 7 で予期されていた `tests/test_provider.py::test_send_and_wait_called_with_string` の厳密 `assert_called_once_with` を、attachments=None + timeout kwarg 追加後も意図通り検証する形に書き直し (Deviation #1).
- **SDK isolation regression net 維持**: Wave 0 Plan 01 で整備した `tests/test_copilot_attachments_spike.py::test_sdk_imports_isolated_to_provider` が 引き続き GREEN — 本 plan の追加 import 2 行 (`FileAttachment` / `ModelInfo`) はすべて provider に閉じている.

## Task Commits

各タスクは TDD で red/green の 2 コミットに分けて記録した (TDD ゲート遵守を git log で監査可能):

1. **Task 1 RED: ChatCopilot multimodal helpers のテスト先行作成** — `cc10c79` (test)
2. **Task 1 GREEN: provider 配線 + 既存 test_provider.py の attachments=None / timeout 追加 regression 修正** — `f397f20` (feat)
3. **Task 2 RED: GET /api/models の 5 integration test 先行作成** — `d47c7bd` (test)
4. **Task 2 GREEN: models route + attachments stub + main.py 配線 + deferred-items.md 記録** — `c5fca57` (feat)

_Note: Plan 02 全体は `type: execute` (TDD plan ではなく execute plan) だが、各 task の `tdd="true"` 指定に従い red → green の 2 コミット分割で運用. Refactor phase は不要 (helper / route ともに最小実装で behavior を満たすため)._

## Files Created/Modified

**Created:**
- `tests/test_copilot_attachments.py` (357 lines) — ChatCopilot wrapper の 11 unit test. `_extract_attachments` 5 ケース / `_agenerate` 2 ケース / `list_models` 2 ケース / `is_vision_model` 2 ケース.
- `tests/test_api_models_route.py` (139 lines) — GET /api/models の 5 integration test. 200/401/cache hit/TTL expiry/503.
- `app/api/routes/models.py` (59 lines) — GET /api/models route, TTL 1h cache, JWT 認証, 503 graceful.
- `app/api/routes/attachments.py` (17 lines) — Plan 03 用 stub APIRouter.
- `.planning/phases/36-text-code-image-multimodal/deferred-items.md` — Plan 02 スコープ外で発見した 6 件の pre-existing failure を記録.

**Modified:**
- `app/providers/copilot.py` (576 → 712 行, +136 行) — imports に `FileAttachment` + `ModelInfo` 追加 (L36-42)、`_extract_attachments` (L394-440) + `list_models` (L326-368) + `is_vision_model` (L369-384) の 3 ヘルパー追加、`_agenerate` L188-192 + `_astream` L278 に `attachments=sdk_atts` 配線.
- `app/api/main.py` — route imports に `attachments, models` を追加、`include_router(attachments.router)` + `include_router(models.router)` を `hosted_apps.router` の直前に挿入.
- `tests/test_provider.py` — `test_send_and_wait_called_with_string` を厳密 `assert_called_once_with("[User]: hello")` から `args == ("[User]: hello",)` + `kwargs.get("attachments") is None` + `"timeout" in kwargs` の部分 assert に書き直し.

## Decisions Made

- **displayName fallback 方針**: Plan 本文の `_extract_attachments` 仕様は「a['name'] が str で非空のときのみ displayName を付ける」だったが、Wave 0 Plan 01 Deviation #2 で SDK `FileAttachment.__required_keys__` に `displayName` が含まれることが確認済. これに従い、name が無い / 空 / 非 str のケースでは `os.path.basename(path)` を fallback として **必ず** displayName を埋める実装にした. テスト `test_extract_attachments_displayname_falls_back_to_path_basename` で挙動を固定.
- **TDD で red/green 2 コミット分割**: type=execute plan だが各 task の `tdd="true"` を尊重し、test commit と feat commit を分けて TDD ゲート遵守を git log で監査可能にした. プロジェクトの ADR-0046 (integration check gate) と方向性を揃える.
- **deferred-items.md による pre-existing failure の隔離**: `tests/test_api_chat.py` の 6 件の失敗を `git stash` で Plan 02 の変更を一時退避した状態でも再現することを確認し、scope 外として deferred-items.md に記録. CLAUDE.md / executor の "Only auto-fix issues DIRECTLY caused by the current task's changes" ルールに従う.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 既存 test_provider.py::test_send_and_wait_called_with_string が attachments + timeout kwarg 追加で壊れる**
- **Found during:** Task 1 GREEN (`uv run pytest tests/test_copilot_bind_tools.py tests/test_provider.py` で 1 件 regression を検出)
- **Issue:** 既存テストが `mock_copilot["session"].send_and_wait.assert_called_once_with("[User]: hello")` の 1 引数のみ厳密 match. Plan 02 で `_agenerate` の `send_and_wait(prompt, attachments=sdk_atts, timeout=self.send_timeout)` 化により kwargs が追加され、必ず壊れる (Plan の Step 7 で予期されていた regression).
- **Fix:** assertion を `assert_awaited_once()` + `args == ("[User]: hello",)` + `kwargs.get("attachments") is None` + `"timeout" in kwargs` の部分 assert に書き直し. Plan の Step 7 が指示した最小修正.
- **Files modified:** `tests/test_provider.py` (test_send_and_wait_called_with_string 関数のみ)
- **Verification:** `uv run pytest tests/test_provider.py -v` → 11 passed (regression なし)
- **Committed in:** `f397f20` (Task 1 GREEN commit)

**2. [Rule 2 - Missing Critical] SDK FileAttachment.displayName が実態 required のため path basename fallback を強制**
- **Found during:** Task 1 RED 設計時 (Wave 0 Plan 01 Deviation #2 + spike note Next-Wave Impact から確認)
- **Issue:** Plan 本文の `_extract_attachments` は「a['name'] が str で非空のときのみ displayName を付ける」と書かれているが、SDK 0.2.0 の `FileAttachment.__required_keys__` は `frozenset({'displayName', 'type', 'path'})` で displayName は **required**. Plan 通り optional 扱いで実装すると、name が欠損した attachments で SDK が validation error を出すリスクがある (Wave 0 Plan 01 spike note Next-Wave Impact で明示的に警告されていた事項).
- **Fix:** `_extract_attachments` 実装で `name` が str 非空でないケースでは `os.path.basename(path)` を fallback として常に displayName を埋める. テスト `test_extract_attachments_displayname_falls_back_to_path_basename` を新規追加して挙動を固定 (テスト計 5 → 5 expected を 5 維持しつつ、実体的にはこのケースで `_extract_attachments` 系を 4 → 5 に増やした).
- **Files modified:** `app/providers/copilot.py` (`_extract_attachments` の displayName 補完ロジック), `tests/test_copilot_attachments.py` (新規テスト)
- **Verification:** `uv run pytest tests/test_copilot_attachments.py::test_extract_attachments_displayname_falls_back_to_path_basename -v` → PASSED. SDK 0.2.0 `__required_keys__` も docker exec で再確認 (frozenset({'displayName', 'type', 'path'})).
- **Committed in:** `cc10c79` (RED) + `f397f20` (GREEN)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug, 1 Rule 2 missing critical)
**Impact on plan:** 両 deviation とも Plan 当初の SDK 仕様前提を実態に合わせる最小修正で、Phase 36 全体方針 (D-09 / D-15 / additional_kwargs サイドカー) は完全に維持. Wave 0 Plan 01 spike note の Next-Wave Impact で予告されていた事項に Plan 02 で正面から対応した形. scope creep なし.

## Issues Encountered

- **Pre-existing test_api_chat.py 6 件失敗**: Plan 02 着手前から壊れているテスト (JWT cookie 不足 / DB AsyncMock 不整合) を発見. `git stash` で確認してスコープ外と判定し、`.planning/phases/36-text-code-image-multimodal/deferred-items.md` に Phase 36 Plan 03 / 別 quick task 向けに記録. Plan 02 では一切手を出さない.

## Threat Flags

なし — Plan の `<threat_model>` (T-36-02-01〜06) はすべて Plan 内で対処済 / accept disposition. 本 plan 実装で新規 surface 追加なし (attachments router は空 stub のため実エンドポイント追加なし、models route は JWT 認証 + キャッシュで T-36-02-01〜03 を mitigate, T-36-02-04 は `_extract_attachments` の 3 段フィルタで mitigate, T-36-02-05/06 は accept).

## User Setup Required

None - 本 plan は API 配線層のみで、外部サービスや環境変数の追加なし. docker compose で起動済みの api / worker / postgres / redis が引き続き動作.

## Next Phase Readiness

- **Plan 03 (POST/GET/DELETE /api/threads/{tid}/attachments)**: `app/api/routes/attachments.py` は空 stub として既に main.py に include 済. Plan 03 は同ファイルに endpoint を追加するだけで route 登録不要.
- **Plan 04 (worker / handler 配線)**: `ChatCopilot.is_vision_model` が D-18 fail-safe で利用可能. `_extract_attachments` は handler 側で HumanMessage.additional_kwargs に attachments dict を入れた後、何も追加実装せずに `provider._agenerate` 経由で SDK に届く.
- **Plan 06 (frontend useModels hook)**: `GET /api/models` は JWT 認証下で D-14 dict list を返す. TTL 1h キャッシュが効いているため frontend が頻繁に呼んでも SDK 呼出しは 1h に 1 回.
- **Blocker**: なし — Wave 1 完了 gate すべて GREEN, Wave 2 (Plan 03) 着手 OK.

## Self-Check: PASSED

- ✅ `app/providers/copilot.py` exists with new helpers (`grep -n "def _extract_attachments\|async def list_models\|async def is_vision_model" app/providers/copilot.py` → 3 lines)
- ✅ `app/api/routes/models.py` exists (59 lines)
- ✅ `app/api/routes/attachments.py` exists (17 lines, stub APIRouter)
- ✅ `app/api/main.py` includes 両 router (`grep "attachments.router\|models.router" app/api/main.py` → 含む)
- ✅ `tests/test_copilot_attachments.py` exists (357 lines, 11 tests GREEN)
- ✅ `tests/test_api_models_route.py` exists (139 lines, 5 tests GREEN)
- ✅ Commit `cc10c79` (test) reachable
- ✅ Commit `f397f20` (feat) reachable
- ✅ Commit `d47c7bd` (test) reachable
- ✅ Commit `c5fca57` (feat) reachable
- ✅ `docker compose exec api uv run python -m pytest tests/test_copilot_attachments.py tests/test_copilot_bind_tools.py tests/test_provider.py tests/test_api_models_route.py tests/test_copilot_attachments_spike.py tests/test_chat_history_additional_kwargs.py -v` → 45 passed
- ✅ `grep "attachments=sdk_atts" app/providers/copilot.py | wc -l` → 2 (期待値)
- ✅ `grep -rn "from copilot " app/ | grep -v "providers/copilot.py" | wc -l` → 0 (SDK 隔離原則維持)
- ✅ `from app.api.main import app; assert any('/api/models' in str(r) for r in app.routes)` → OK

---

*Phase: 36-text-code-image-multimodal*
*Plan: 02 (Wave 1)*
*Completed: 2026-04-24 — Wave 1 完了, Plan 03 (Wave 2) 着手 OK*
