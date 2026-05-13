---
phase: 39-ui-polish
plan: 06
subsystem: testing
tags: [pytest, mcp-catalog, drift, single-source-of-truth, phase-30, phase-37, phase-38]

# Dependency graph
requires:
  - phase: 39-ui-polish/01
    provides: BASELINE.md (pytest baseline 27 件, cwd= 6 件) を Wave 0 で確定
  - phase: 30
    provides: config/mcp_tools.yaml を single source of truth とする MCP ツールカタログ
  - phase: 37
    provides: attachments_list / attachments_extract の 2 ツールを YAML に追加 (test 側更新漏れ)
  - phase: 38/03
    provides: claude_code() signature から cwd 引数を破壊的削除 (test 側更新漏れ)
provides:
  - test_generate_mcp_artifacts 4 件の green (D-10 Pattern E 一部)
  - test_tool_catalog_js 1 件の green (D-10 Pattern E 一部)
  - test_tool_registry 1 件の green (D-10 Pattern E 一部)
  - test_mcp_server から cwd= 引数 6 箇所削除 (D-09 完了)
  - pytest baseline 27 → 21 件 (Pattern E 6 件減を達成)
affects: [39-07, 39-08, 39-09, 40-*, MCP 関連の全 phase]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "single-source-of-truth (config/mcp_tools.yaml) と test assertion の同期"
    - "Phase 30 自動生成パイプラインの drift 検知が production 側で動作することを test 側で再確認"

key-files:
  created:
    - .planning/phases/39-ui-polish/39-06-SUMMARY.md
  modified:
    - tests/test_generate_mcp_artifacts.py
    - tests/test_mcp_server.py
    - tests/test_tool_catalog_js.py
    - tests/test_tool_registry.py

key-decisions:
  - "test_build_helper_has_six_functions 内の assertion は YAML の function_name (list_attachments / extract_attachment) で記述。Plan の acceptance criteria L190 (`def attachments_(list|extract)`) は build_helper の実装命名 (function_name) と矛盾するため、Plan Step B の実装命名規則優先のガイダンス (L149) に従う"
  - "production code (app/ / mcp_server/) を一切変更しない方針を厳守"
  - "fastmcp 非 install 環境では test_mcp_server.py は skip されるため、本 plan は grep ベースで cwd= 0 件確認に留め、実行検証は Wave 3 (close plan) または docker compose env で別途実施"

patterns-established:
  - "Pattern: YAML SSoT 更新時の test drift は Phase 30 drift hook で検知できるが、test ファイル自体の数値・期待リストは hook 対象外。Phase 増分での tools 追加時には 4 つのテストファイル (test_generate_mcp_artifacts / test_tool_catalog_js / test_tool_registry / test_mcp_server) を必ず同期する"

requirements-completed: [UIFIX-04]

# Metrics
duration: 約 5 min
completed: 2026-05-13
---

# Phase 39 Plan 06: pytest 数値 drift + cwd 引数 + tool catalog drift 6 件解消 Summary

**Phase 37 で追加された attachments_list / attachments_extract の 2 ツールに対する test 側 assertion 更新 (6→8) + Phase 38 Plan 03 で破壊的削除された cwd= 引数の 6 箇所削除を 1 plan で実施し、pytest baseline 27 件 → 21 件 (Pattern E 6 件減) を達成した。**

## Performance

- **Duration:** 約 5 min
- **Started:** 2026-05-13T05:02:30Z 頃 (worktree spawn 時点)
- **Completed:** 2026-05-13T05:07:30Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- D-09 (pytest 数値 drift + cwd 引数 6 件削除) を完全解消
- D-10 Pattern E (tool catalog drift 6 件) を完全解消
- pytest 失敗件数を **27 件 → 21 件 (-6)** に減少 (Pattern E 6 件分の純減)
- production code (app/ / mcp_server/) に一切手を入れず、test only の修正で完結
- `grep -c 'cwd=' tests/test_mcp_server.py` を **6 → 0** に削減

## Task Commits

Each task was committed atomically:

1. **Task 1: tests/test_generate_mcp_artifacts.py の 6→8 件 + YAML 順更新** — `5f49d33` (test)
   - test_load_tools_has_six_tools → test_load_tools_has_eight_tools
   - test_build_helper_has_four_functions → test_build_helper_has_six_functions (python_wrapper 4→6)
   - test_build_js_order / test_build_docs_header_and_table の期待リストを 8 件に更新
2. **Task 2: tests/test_mcp_server.py から cwd="/tmp" 引数を 6 箇所削除** — `3f04929` (test)
   - L293/316/341/372/394/410 の `claude_code(prompt="test", cwd="/tmp")` から cwd= を削除
3. **Task 3: tests/test_tool_catalog_js.py + tests/test_tool_registry.py の 6→8 更新** — `28e099d` (test)
   - test_catalog_contains_six_tools → test_catalog_contains_eight_tools
   - test_tool_registry_real_yaml_contract の expected セットに attachments_list / attachments_extract を追加

## Files Created/Modified

- `tests/test_generate_mcp_artifacts.py` — 4 つの assertion (test_load_tools / test_build_helper / test_build_js_order / test_build_docs) を 8 ツール構成に更新。関数名 2 件をリネーム (six → eight, four → six)
- `tests/test_mcp_server.py` — `claude_code(prompt="test", cwd="/tmp")` パターンから `cwd="/tmp"` を 6 箇所削除 (replace_all で一括)
- `tests/test_tool_catalog_js.py` — `test_catalog_contains_six_tools` → `test_catalog_contains_eight_tools` にリネーム + 期待値 8 + attachments_list / attachments_extract の存在 assertion を追加
- `tests/test_tool_registry.py` — `test_tool_registry_real_yaml_contract` の expected セットを 6 → 8 件に拡張 (attachments_list / attachments_extract を追加)

## Decisions Made

- **Step B の assertion 命名は YAML `function_name` 優先**: Plan acceptance criteria L190 は `def attachments_(list|extract)` を 2 件以上要求するが、`build_helper` は `python_wrapper.function_name` を `def {fn_name}` として出力するため、実態は `def list_attachments` / `def extract_attachment`。Plan Step B L149 の「function_name は scripts/generate_mcp_artifacts.py の build_helper 実装での命名規則に従う」というガイダンスを優先し、assertion を `def list_attachments(` / `def extract_attachment(` に揃えた。最終達成基準である「全テスト green」は満たしている (18 passed)。
- **production code 不変**: app/ と mcp_server/ への変更は 0 行。本 plan は purely test refactor。
- **fastmcp install 環境での実行検証は scope 外**: Pitfall 5 通り `pytest.importorskip("fastmcp")` で skip される環境では cwd= 削除の影響を実測できないため、Wave 3 close plan もしくは docker compose env で別途検証する。本 plan は grep ベース 0 件確認で完了とする。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Documentation/Spec Drift] Plan acceptance criteria L190 の grep 文字列が build_helper 実装と矛盾**
- **Found during:** Task 1 (test_build_helper_has_six_functions assertion 設計時)
- **Issue:** Plan L190 は `grep -cE 'def attachments_(list|extract)' tests/test_generate_mcp_artifacts.py` が 2 以上を要求するが、build_helper は YAML の `python_wrapper.function_name` (`list_attachments` / `extract_attachment`) を `def {fn_name}` として出力するため、テスト assertion は `def list_attachments(` / `def extract_attachment(` が正しい。
- **Fix:** Plan Step B L149 (「function_name は scripts/generate_mcp_artifacts.py の build_helper 実装での命名規則に従う」) を優先し、assertion を `def list_attachments(` / `def extract_attachment(` で記述。Plan の真の意図 (8 件 build_helper 関数の存在確認) は満たしており、最終達成基準「全テスト green」も達成。
- **Files modified:** tests/test_generate_mcp_artifacts.py
- **Verification:** `pytest tests/test_generate_mcp_artifacts.py` 18 passed
- **Committed in:** 5f49d33 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 documentation/spec drift)
**Impact on plan:** Plan 仕様の grep ターゲット文字列誤記の修正のみ。scope 内、production code 不変、全テスト green。

## Issues Encountered

- **worktree path drift (序盤に発生・即時復旧)**: 序盤の Bash `cd /home/parallels/workspaces/copilot-langgraph` で main repo に cd した結果、最初の Edit 4 件が main repo の `tests/test_generate_mcp_artifacts.py` に適用された。即座に `git checkout -- tests/test_generate_mcp_artifacts.py` で main repo を元の状態に戻し、worktree 内の絶対パス (`/home/parallels/workspaces/copilot-langgraph/.claude/worktrees/agent-a1a997f8b583611ff/`) を使って改めて Edit を適用。以後のすべての Bash 操作は worktree 内 (`cwd` = worktree root) で完結させた。最終 main repo は変更なし、worktree のみコミット 3 件で完了。`worktree-path-safety.md` の絶対パスドリフト #3097 / #3099 に該当する事案であり、今後は最初から worktree 内の絶対パスで Edit/Read を行うべき (この実行ログは執行プロトコル改善のフィードバックとして記録)。

## Verification Snapshots

### Final pytest counts

```
$ python3 -m pytest tests/test_generate_mcp_artifacts.py tests/test_tool_catalog_js.py tests/test_tool_registry.py -v --tb=short 2>&1 | tail -5
36 passed in 0.23s

$ python3 -m pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no 2>&1 | tail -1
21 failed, 403 passed, 13 skipped, 1 xfailed, 1 xpassed, 57 warnings in 35.37s

$ grep -c 'cwd=' tests/test_mcp_server.py
0
```

### Pattern E 6 件解消の内訳

| Test | Before | After | Commit |
|------|--------|-------|--------|
| `tests/test_generate_mcp_artifacts.py::test_load_tools_has_six_tools` (renamed → eight_tools) | FAILED | PASSED | 5f49d33 |
| `tests/test_generate_mcp_artifacts.py::test_build_helper_has_four_functions` (renamed → six_functions) | FAILED | PASSED | 5f49d33 |
| `tests/test_generate_mcp_artifacts.py::test_build_js_order` | FAILED | PASSED | 5f49d33 |
| `tests/test_generate_mcp_artifacts.py::test_build_docs_header_and_table` | FAILED | PASSED | 5f49d33 |
| `tests/test_tool_catalog_js.py::test_catalog_contains_six_tools` (renamed → eight_tools) | FAILED | PASSED | 28e099d |
| `tests/test_tool_registry.py::test_tool_registry_real_yaml_contract` | FAILED | PASSED | 28e099d |

合計 6 件すべて RED → GREEN に遷移。

### pytest 失敗件数の baseline からの減少

- **BASELINE.md (2026-05-13 計測): 27 failed**
- **本 plan 完了後 (2026-05-13): 21 failed (-6)**
- Plan 04 (test_sse 2 件解消) はまだ未マージ状態の見込み (orchestrator 制御下で並行実行中)。Plan 04 完了後の合算で 19 failed の見込み (Pattern E 6 件 + Pattern A 2 件)。Wave 3 close 時の最終 target ≤ 2 件は後続 plan (07/08/09) が担う。

## Self-Check

ファイル存在確認:
```
$ ls -la tests/test_generate_mcp_artifacts.py tests/test_mcp_server.py tests/test_tool_catalog_js.py tests/test_tool_registry.py
すべて存在 (4 ファイル)
```

コミット存在確認:
```
$ git log --oneline -5
28e099d test(39-06): expand tool catalog assertions to 8 tools (D-10 Pattern E)
3f04929 test(39-06): drop cwd= kwarg from claude_code test calls (D-09)
5f49d33 test(39-06): update mcp artifacts assertions for 8 tools (D-09/D-10 Pattern E)
ad296e5 docs(phase-39): update tracking after wave 0
2e97eae chore: merge executor worktree (worktree-agent-a79489fc6f2aa3499)
```

## Self-Check: PASSED

## User Setup Required

None - test only の修正、外部サービスの設定変更不要。

## Next Phase Readiness

- **Plan 07 (Pattern D - mock 経路 4 件) への影響:** 本 plan は Pattern D に直接関与しないが、test 全体の pytest 速度・出力が安定したため、Plan 07 の failure 抽出がしやすくなる。
- **Plan 08 (Pattern A - JWT cookie 7 件) への影響:** 同上、独立。
- **Plan 09 (Pattern B/C - psycopg / LLM mock) への影響:** 同上、独立。
- **Wave 3 close plan:** 本 plan で記録した「fastmcp install env での cwd= 削除実行検証」は Wave 3 で実施する宿題として `39-VALIDATION.md` に記録 (orchestrator が STATE/ROADMAP 更新時に拾う想定。本 executor は VALIDATION.md には触らない)。

## Threat Flags

なし — test ファイルの assertion / kwargs 更新のみ。production code 不変、新規 attack surface なし。

---
*Phase: 39-ui-polish*
*Plan: 06*
*Completed: 2026-05-13*
