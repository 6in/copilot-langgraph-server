---
phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
plan: 03
subsystem: mcp
tags: [mcp, codegen, sandbox, python-wrapper, tdd]

# Dependency graph
requires:
  - phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
    provides: "config/mcp_tools.yaml 拡張スキーマ (python_wrapper ブロック)"
  - phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
    provides: "scripts/generate_mcp_artifacts.py build_helper 関数 (--target helper + --check)"
provides:
  - "mcp_server/tools/mcp_helper_utils.py (手書き基盤: _call_tool / _clean_content / _INTERNAL_URL / _TIMEOUT)"
  - "mcp_server/tools/mcp_helper.py (scripts/generate_mcp_artifacts.py --target helper から自動生成された 4 wrapper: ping / search / query_db / get_datetime)"
  - "tests/test_mcp_helper_generated.py (生成 helper の挙動回帰テスト + drift 保護)"
  - "config/sandbox_allowlist.yaml に mcp_helper_utils 追加 (sandbox から import 可能)"
affects: [phase-30-04-js-catalog, phase-30-06-docs-generation, codeact-agent, execute_python-sandbox]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "手書き基盤と自動生成コードの物理分離 (D-02): utils.py に primitives, helper.py はジェネレータ出力で上書き"
    - "from X import y 形式の bind 対象を理解したテスト patch: patch.object(caller_module, ...) で import 済みシンボルを差し替える"
    - "RED→GREEN TDD gate: test コミット時に現状 (手書き版) で 3 fail を確認 → feat コミットで 11/11 pass 化"

key-files:
  created:
    - "mcp_server/tools/mcp_helper_utils.py"
    - "tests/test_mcp_helper_generated.py"
  modified:
    - "mcp_server/tools/mcp_helper.py (手書き → 自動生成)"
    - "config/sandbox_allowlist.yaml (mcp_helper_utils 追加)"

key-decisions:
  - "mcp_helper.py は scripts/generate_mcp_artifacts.py --target helper の出力で完全上書きする。生成コードは from mcp_helper_utils import _call_tool, _clean_content で基盤を取り込む"
  - "sandbox allowlist に mcp_helper_utils を追加する (mcp_helper.py から import されるため、sandbox 内でも import 解決できる必要がある)"
  - "テストの patch 対象は mcp_helper モジュール (from A import x 形式で呼び出し側名前空間に bind されるため、mcp_helper_utils 側への patch は反映されない)"
  - "Plan 03 の drift 保証は helper 単体に限定する (js は Plan 04、docs は Plan 06 が担当、scripts/generate_mcp_artifacts.py --check は Plan 06 完了時に全体 exit 0 になる)"

patterns-established:
  - "手書き基盤 / 自動生成コードの物理分離パターン: utils.py は手動編集、メインファイルは generator の冪等上書き"
  - "自動生成ファイルの回帰テストで module import binding を考慮した patch.object() 対象選定"

requirements-completed: [TBD]

# Metrics
duration: 3 min
completed: 2026-04-18
---

# Phase 30 Plan 03: mcp_helper.py の自動生成化 Summary

**mcp_helper.py を手書き (_call_tool / _clean_content 含む 130 行) から scripts/generate_mcp_artifacts.py --target helper の出力に置換し、手書き基盤を mcp_helper_utils.py に分離 — YAML → generator 再実行のみで新ツールを反映できる体制を確立**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-18T09:55:34Z
- **Completed:** 2026-04-18T09:58:44Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 4 (created 2, modified 2)

## Accomplishments

- **手書き基盤モジュール化**: `_INTERNAL_URL` / `_TIMEOUT` / `_call_tool` / `_clean_content` を `mcp_server/tools/mcp_helper_utils.py` へ逐語コピーで切り出し (挙動改変なし)
- **mcp_helper.py の自動生成化**: `python3 scripts/generate_mcp_artifacts.py --target helper > mcp_server/tools/mcp_helper.py` の出力に置換 — 先頭に `# DO NOT EDIT` ヘッダー、4 関数 (ping / search / query_db / get_datetime) を YAML の `python_wrapper` から生成
- **回帰テスト追加**: `tests/test_mcp_helper_generated.py` 11 ケース — 4 関数の引数 mapping (ping / get_datetime の no-args passthrough、query_db の pool → pool_name 変換、search の _clean_content 適用)、DO NOT EDIT ヘッダー存在、utils import 存在、drift バイト完全一致
- **sandbox allowlist 更新**: `config/sandbox_allowlist.yaml` に `mcp_helper_utils` を追加、execute_python サンドボックスから `from mcp_helper_utils import ...` が解決可能に

## Task Commits

1. **Task 1: mcp_helper_utils 切り出し + allowlist** — `b9b97aa` (refactor)
2. **Task 2 RED: 回帰テスト追加** — `ae01fe9` (test)
3. **Task 2 GREEN: mcp_helper.py をジェネレータ出力で置換** — `4f04044` (feat)

## Files Created/Modified

- `mcp_server/tools/mcp_helper_utils.py` — **新規**。_call_tool + _clean_content + 接続定数の手書きモジュール (ヘッダーに "scripts/generate_mcp_artifacts.py は生成しない" を明記)
- `mcp_server/tools/mcp_helper.py` — **置換**。手書き 144 行 → 生成後 94 行 (4 関数のみ、基盤は utils から import)
- `tests/test_mcp_helper_generated.py` — **新規**。public API 回帰 + drift バイト完全一致の 11 ケース
- `config/sandbox_allowlist.yaml` — `mcp_helper_utils` を `mcp_helper` の直後に追加

## Decisions Made

- **patch 対象は mcp_helper スコープに統一**: `from mcp_helper_utils import _call_tool, _clean_content` 形式の import は呼び出し側 (mcp_helper) の名前空間にシンボルを bind するため、テストは `patch.object(mcp_helper, "_call_tool", ...)` で差し替える。mcp_helper_utils 側への patch は反映されない。
- **drift 保証の範囲は helper のみ**: Plan 03 は helper だけを生成物として上書きするため、`test_generator_check_mode_has_no_drift` は `gen.build_helper(...)` 出力との一致だけを検証する。`scripts/generate_mcp_artifacts.py --check` 全体は js / docs が未生成で exit 1 を返すが、それらは Plan 04 / Plan 06 のスコープ。
- **挙動は逐語コピー**: _call_tool / _clean_content を mcp_helper_utils に切り出す際、module docstring のみ手書き明記に変更し、ロジックは現行と 100% 同一。Phase 30 前の挙動を破壊しない。

## Deviations from Plan

### 想定内の制限（プラン本文と整合、プロンプト外形的な記述とのみ差分あり）

**1. [Rule 1 - スコープ制約] プロンプト記載の verification gate `python3 scripts/generate_mcp_artifacts.py --check` exits 0 は Plan 03 単独では満たせない**

- **発見タイミング:** Task 2 完了後の最終検証
- **事象:** プロンプト冒頭の「Verification gates (before SUMMARY.md)」に「`python3 scripts/generate_mcp_artifacts.py --check` exits 0」と記載されていたが、このコマンドは helper / js / docs の 3 ファイルすべてを比較するため、js (Plan 04 担当) と docs (Plan 06 担当) が未生成の現時点では exit 1 を返す。
- **プラン本文との整合:** `30-03-PLAN.md` の `<success_criteria>` には「scripts/generate_mcp_artifacts.py --check で **helper 部分が** drift なし」と明記されており、`<tasks>` 内の `test_generator_check_mode_has_no_drift` も helper 単体の一致だけを直接検証する設計。したがってプラン意図は「helper 単体の drift なし」が正しく、プロンプトの簡略記述との齟齬。
- **対応:** helper 単体の drift 保証は `test_generator_check_mode_has_no_drift` で pass 確認済み。全体 `--check` は Plan 06 完了時に自動的に exit 0 になる。Plan 03 の files_modified (`static/js/*`, `docs/*` は含まず) を逸脱して js / docs を生成することは協調ルール違反になるため、コード変更は行わなかった。
- **Files modified:** なし
- **Commit:** なし (ドキュメントで明記のみ)

---

**Total deviations:** 0 auto-fixed + 1 scope clarification  
**Impact on plan:** プラン本文の success_criteria に沿って実行。プロンプトの verification gate 記述とプラン本文の間に齟齬があったが、plan 内で明示された「helper 部分のみ」の範囲で完結。後続プラン (04 / 06) で全体 `--check` は自動的に exit 0 化する。

## Issues Encountered

- **uv による venv 再作成時の Permission エラー**: `uv run pytest` が `.venv/lib64` の削除に失敗した。worktree 環境固有の権限問題。`python3 -m pytest` で直接実行する運用に切り替えて全テスト pass を確認。Plan 内ファイルには影響なし。

## User Setup Required

None — 既存 CodeAct / execute_python サンドボックスから `from mcp_helper import search, query_db, get_datetime, ping` が引き続き動作し、追加のユーザー設定は不要。

## TDD Gate Compliance

- **RED gate:** `ae01fe9` (test コミット) 時点で手書き版 mcp_helper.py は 3 fail / 8 pass を示した — DO NOT EDIT ヘッダー / utils import 存在 / drift 一致の 3 テストが予定どおり fail。
- **GREEN gate:** `4f04044` (feat コミット) 後、11/11 pass。ジェネレータ出力で置換したことで DO NOT EDIT / utils import / drift 一致の 3 テストが通過。
- **REFACTOR:** 不要 (生成コードは決定論的で後改変しない設計)。

## Next Phase Readiness

- **Plan 30-04 (JS catalog) が実行可能**: Plan 03 の成果物は JS / docs 生成には依存しない。mcp_helper.py は既に drift なし状態でロックされており、Plan 04 / 06 で js と docs を書き出せば `scripts/generate_mcp_artifacts.py --check` 全体が exit 0 になる。
- **CodeAct エージェントへの影響なし**: `app/orchestrator/codeact_agent.py` は変更していない。サンドボックス内で `from mcp_helper import search, query_db, get_datetime, ping` が引き続き成功する (allowlist に `mcp_helper_utils` を追加済み)。
- **以降の新規 MCP ツール追加フロー**: `config/mcp_tools.yaml` に tool と python_wrapper ブロックを追記 → `python3 scripts/generate_mcp_artifacts.py --target all` を実行 → tests/test_mcp_helper_generated.py が drift を検出したら generator を再実行して commit。手書き mcp_helper.py の編集は行わない。

## Self-Check: PASSED

- **Files exist:**
  - `mcp_server/tools/mcp_helper_utils.py` — FOUND
  - `mcp_server/tools/mcp_helper.py` — FOUND (書き換え済み)
  - `tests/test_mcp_helper_generated.py` — FOUND
  - `config/sandbox_allowlist.yaml` — FOUND (mcp_helper_utils 含む)
- **Commits exist on branch gsd/phase-30-mcp-tool-catalog-single-source:**
  - `b9b97aa` — refactor(phase-30-03): extract mcp_helper_utils.py from mcp_helper.py — FOUND
  - `ae01fe9` — test(phase-30-03): add regression tests for generated mcp_helper.py — FOUND
  - `4f04044` — feat(phase-30-03): replace mcp_helper.py with generator output — FOUND
- **Acceptance criteria verification (再実行時):**
  - `head -1 mcp_server/tools/mcp_helper.py` に `DO NOT EDIT` — PASS
  - `grep -q 'from mcp_helper_utils import _call_tool, _clean_content' mcp_server/tools/mcp_helper.py` — PASS
  - `grep -c '^def '` == 4 — PASS
  - `grep 'def claude_code'` ヒットなし — PASS
  - `grep 'def execute_python'` ヒットなし — PASS
  - sandbox-style import 成功 — PASS
  - `python3 -m pytest tests/test_tool_registry.py tests/test_mcp_helper_generated.py tests/test_generate_mcp_artifacts.py` → 37 passed — PASS

---

*Phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-*
*Plan: 03*
*Completed: 2026-04-18*
