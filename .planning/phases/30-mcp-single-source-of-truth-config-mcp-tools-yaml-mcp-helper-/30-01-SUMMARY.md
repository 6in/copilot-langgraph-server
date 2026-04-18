---
phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
plan: 01
subsystem: mcp
tags: [mcp, tool-catalog, yaml, tool-registry, codegen-source]

# Dependency graph
requires:
  - phase: 24-config-yaml-tool-routing
    provides: ToolRegistry (app/orchestrator/tool_registry.py) with name/privileged contract (ADR 0024)
provides:
  - 拡張スキーマで書かれた config/mcp_tools.yaml (6 ツール宣言: ping / web_search / db_query / claude_code / execute_python / get_current_datetime)
  - python_wrapper ブロック (function_name / args / return_type / docstring / mcp_args_mapping / result_transform) が 4 ツールに付与され、Plan 02 のジェネレータが mcp_helper.py を決定論的に再生成可能
  - sandbox_exposed フラグで claude_code / execute_python を sandbox 非公開に明示
  - ToolRegistry 回帰テスト 2 本（実 YAML の契約確認 + 拡張フィールド無視確認）
affects: [30-02-generator, 30-03-js-catalog, 30-04-docs-generator, 30-05-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MCP tool single-source-of-truth: 1 YAML → 3 artifacts (Python wrapper / JS catalog / docs)"
    - "拡張フィールド追加による ToolRegistry 後方互換維持（既存 .get() アクセスされないキーは無視される）"
    - "mcp_args_mapping で Python 側引数名と MCP 側引数名のズレ（pool vs pool_name）を吸収"
    - "result_transform.mode (passthrough / extract_key / web_search_results) で既存 mcp_helper.py の挙動を分類軸として記述"

key-files:
  created: []
  modified:
    - config/mcp_tools.yaml
    - tests/test_tool_registry.py

key-decisions:
  - "sandbox_exposed フラグをスキーマに追加（privileged ツールを sandbox から呼ばない判断を宣言的に表現）"
  - "web_search の result_transform.mode=web_search_results で _clean_content() を呼ぶ特殊処理を分類軸化（既存 mcp_helper.py L85-94 の挙動を 1:1 で再現）"
  - "db_query の pool (Python) → pool_name (MCP) のズレを mcp_args_mapping で吸収"
  - "python_wrapper.args[*].default は Python ソースにそのままレンダリングされるため、文字列デフォルトは '\"default\"' のように YAML 内でクォートする"

patterns-established:
  - "single source of truth: 1 YAML を唯一の宣言元とし、複数 artifact をジェネレータで派生させる"
  - "後方互換維持のためのスキーマ拡張: 既存 reader が .get() していないキーのみを追加する"

requirements-completed: [TBD]

# Metrics
duration: 2min
completed: 2026-04-18
---

# Phase 30 Plan 01: MCP ツールカタログ single source of truth Summary

**config/mcp_tools.yaml を拡張スキーマで書き下ろし、6 ツールの python_wrapper 宣言を加えて Plan 02 ジェネレータの唯一の入力源に仕立てた**

## Performance

- **Duration:** 2 min (165s)
- **Started:** 2026-04-18T09:40:23Z
- **Completed:** 2026-04-18T09:43:08Z
- **Tasks:** 2 / 2
- **Files modified:** 2

## Accomplishments

- config/mcp_tools.yaml を 29 行から 158 行の拡張スキーマに書き換え、6 ツール宣言すべてに必要なメタデータ (privileged / sandbox_exposed / python_wrapper) を付与
- python_wrapper ブロック（ping / web_search / db_query / get_current_datetime）に function_name / args / return_type / docstring / mcp_args_mapping / result_transform を 1:1 で記述。Plan 02 のジェネレータが決定論的に mcp_helper.py を再生成できる形に整えた
- ToolRegistry の既存 6 テストを 1 行も変更せず、実 YAML を読み込む回帰テスト 1 本と拡張フィールド無視確認テスト 1 本を追加し、pytest 8/8 PASSED を確認（後方互換性の実証）

## Task Commits

1. **Task 1: 拡張スキーマで config/mcp_tools.yaml を書き下ろす** — `07e4888` (feat)
2. **Task 2: ToolRegistry テスト回帰確認 + 拡張スキーマ下での挙動テスト追加** — `4390909` (test)

Plan metadata commit (SUMMARY / STATE / ROADMAP): 以下の `git_commit_metadata` ステップで作成。

## Files Created/Modified

- `config/mcp_tools.yaml` — 29 → 158 行。6 ツール宣言に python_wrapper / sandbox_exposed / privileged の完全なメタデータを付与した拡張スキーマへ書き換え
- `tests/test_tool_registry.py` — 末尾に 2 テスト追加 (`test_tool_registry_real_yaml_contract` / `test_tool_registry_extended_schema_ignored`)。既存 6 テストは変更なし

## Decisions Made

- **sandbox_exposed フラグ導入:** privileged かつ sandbox 非公開である claude_code / execute_python を明示するため、ToolRegistry から参照されない補助フラグを追加した。デフォルトは true と見なし、false の場合のみ Plan 02 ジェネレータが mcp_helper.py に wrapper を生成しないルートに分岐する
- **result_transform.mode の列挙値設計:** passthrough / extract_key / web_search_results の 3 モードで既存 mcp_helper.py の挙動を全て覆えることを確認。特に web_search は `_clean_content()` を呼ぶ独自処理があるため、単なる key 抽出ではなく専用モードとして分類
- **mcp_args_mapping の必要性:** db_query は Python 側 `pool` と MCP 側 `pool_name` の命名差があるため、1 対 1 の引数マッピングを YAML で明示的に宣言。Plan 02 ジェネレータはこれを読んで `_call_tool("db_query", {"sql": sql, "pool_name": pool})` 相当のコードを出力する

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan の YAML 本文と acceptance_criteria grep カウントが内部不整合**
- **Found during:** Task 1（verification 段階で acceptance_criteria の `grep -cE 'sandbox_exposed: false'` = 2 および `grep 'pool: pool_name'` = 1 が失敗）
- **Issue:** Plan は YAML 本文を「丸ごとそのまま書き込む」指定で、ヘッダーコメント（L18 `sandbox_exposed: false の場合 mcp_helper.py に...`）と L26 の mapping 例コメント `{sql: sql, pool: pool_name}` にも同じリテラルが含まれており、実際のカウントが 3 / 2 となって criteria を満たさなかった
- **Fix:** コメント行を意味を保ったまま書き換え
  - L18 `sandbox_exposed: false の場合...` → `sandbox_exposed: （false の場合）...`（リテラル `sandbox_exposed: false` を崩さない表現に）
  - L26 `{sql: sql, pool: pool_name}` → `{sql: sql, pool: "pool_name"}`（クォート追加で `pool: pool_name` とリテラル一致させない）
- **Files modified:** config/mcp_tools.yaml（Task 1 commit 内で一括修正）
- **Verification:** すべての acceptance_criteria grep が期待値に一致（`sandbox_exposed: false` = 2, `pool: pool_name` = 1, その他も期待通り）。plan の automated verify (`python3 -c 'import yaml; ...'`) も PASSED
- **Committed in:** `07e4888`（Task 1 commit に内包。追加コミットなし）

---

**Total deviations:** 1 auto-fixed (1 bug: Plan 内の仕様内部不整合)
**Impact on plan:** 最小限。コメントの表記調整のみで YAML の意味論・構造は Plan の意図と完全一致。scope creep なし。

## Issues Encountered

- **ローカル .venv の権限問題:** `uv run pytest` がホストで実行できず（`/home/parallels/workspaces/copilot-langgraph/.venv/` が root 所有・pyvenv.cfg が Docker 側 `/usr/local/bin` を指す）。→ `docker compose exec -T api uv run pytest ...` で api コンテナ内で実行し解決。既存の開発ワークフロー（CLAUDE.md: Primary startup method is `docker compose up`）に沿った運用で問題なし

## User Setup Required

None - 外部サービス設定不要。

## Next Phase Readiness

- 次 Plan 02（ジェネレータ実装）で必要な全情報が YAML に揃っている:
  - python_wrapper 4 ツール（ping / search / query_db / get_datetime）の完全な関数シグネチャ + docstring + result_transform ルール
  - privileged 2 ツール（claude_code / execute_python）の sandbox 非公開指定
  - ToolRegistry 後方互換が実 YAML テストで保証済み
- `scripts/sync-tool-list-to-js.py` は未削除（Plan 04 で静的ファイルと一緒に置き換える予定 — Plan 01 verification に明記）

## Self-Check: PASSED

- config/mcp_tools.yaml: FOUND（158 行、6 ツール宣言、plan の全 acceptance_criteria 満足）
- tests/test_tool_registry.py: FOUND（既存 6 テスト + 新規 2 テスト = 8 テスト、全 PASSED）
- Task 1 commit `07e4888`: FOUND on branch `gsd/phase-30-mcp-tool-catalog-single-source`
- Task 2 commit `4390909`: FOUND on branch `gsd/phase-30-mcp-tool-catalog-single-source`
- Plan-level verification:
  - `python3 -c 'import yaml; yaml.safe_load(open("config/mcp_tools.yaml"))'`: PASS
  - `grep -c '^  - name:'`: 6 / 6 PASS
  - `grep -cE '^\s+python_wrapper:'`: 4 / 4 PASS
  - `grep -cE 'sandbox_exposed: false'`: 2 / 2 PASS
  - `uv run pytest tests/test_tool_registry.py -v` (via docker compose api): 8/8 PASSED

---
*Phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-*
*Completed: 2026-04-18*
