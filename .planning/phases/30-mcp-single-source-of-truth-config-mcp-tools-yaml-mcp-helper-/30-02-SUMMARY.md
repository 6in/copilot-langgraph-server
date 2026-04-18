---
phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
plan: 02
subsystem: tooling
tags: [mcp, yaml, code-generation, determinism, drift-detection, pytest]

requires:
  - phase: 30
    provides: "config/mcp_tools.yaml の拡張スキーマ (python_wrapper / mcp_args_mapping / result_transform) を持つ 6 ツールカタログ"
provides:
  - "scripts/generate_mcp_artifacts.py: config/mcp_tools.yaml のみを入力にする決定論的アーティファクトジェネレータ (helper / js / docs / all / --check)"
  - "tests/test_generate_mcp_artifacts.py: 18 テストで build_helper / build_js / build_docs / _generate_wrapper_body / check_all を 1:1 カバー"
  - "pre-commit hook 化の前提となる --check drift 検知 (unified_diff + fix 指示)"
  - "バイト完全一致の末尾改行規約 (build_* 戻り値は末尾 '\\n' 1 文字で終了)"
affects: [30-03, 30-04, 30-05, 30-06]

tech-stack:
  added: []
  patterns:
    - "YAML 宣言駆動のジェネレータ (config/mcp_tools.yaml → 3 ターゲット同時生成)"
    - "末尾改行規約 (build_* は末尾 '\\n' 1 文字) で check_all のバイト完全一致を安定化"
    - "monkeypatch 対応の _rel_or_abs() ヘルパーで ROOT 外パスにも堅牢"

key-files:
  created:
    - scripts/generate_mcp_artifacts.py
    - tests/test_generate_mcp_artifacts.py
  modified: []

key-decisions:
  - "build_helper は 'from mcp_helper_utils import _call_tool, _clean_content' を import 行に固定 (Plan 03 で手書きヘルパーを分離する前提)"
  - "python_wrapper が無いツール (claude_code / execute_python) は mcp_helper.py に関数を生成しない (sandbox_exposed: false の宣言が自動的に反映)"
  - "db_query の mcp_args_mapping を {pool: pool_name} と解釈し、Python 側 `pool` を MCP 側 `pool_name` にリネームする差分吸収ロジックをジェネレータに閉じ込め"
  - "result_transform.mode を passthrough / extract_key / web_search_results の 3 分岐で分類し、既存 mcp_helper.py の挙動を 1:1 再現"
  - "JS 出力の AVAILABLE_TOOLS 配列順は YAML tools 順と 1:1 に一致 (test_build_js_order で担保)"
  - "build_* の末尾改行は常に単一 '\\n' (rstrip('\\n') + '\\n' で正規化) — check_all のバイト完全一致比較を安定させる"
  - "Plan 02 では --target all をディスク書き出しすると mcp_helper.py を上書きして既存挙動を変えてしまうため、実ファイルの書き換えは Plan 03/04/06 に委譲する (ジェネレータ本体とテストだけを導入)"

patterns-established:
  - "Generator + --check drift 検知: ADR INDEX パターン (scripts/generate_adr_index.py) と同じ単体テストスタイル (sys.path.insert('scripts')) を踏襲"
  - "Rule 1 auto-fix: テスト実装中に検出したジェネレータ側のパス整形バグ (Path.relative_to(ROOT) ValueError) を _rel_or_abs ヘルパーで修正"

requirements-completed: []

duration: 10 min
completed: 2026-04-18
---

# Phase 30 Plan 02: scripts/generate_mcp_artifacts.py deterministic generator Summary

**config/mcp_tools.yaml のみを入力として mcp_helper.py / tool-catalog-generated.js / docs/mcp-tools.md を決定論的に生成するジェネレータ (argparse: --target helper|js|docs|all + --check) と 18 件の pytest スイートを新設。**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-18T09:41:00Z
- **Completed:** 2026-04-18T09:51:33Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments

- `scripts/generate_mcp_artifacts.py` (471 行) が 3 ターゲットを単一 YAML から決定論的に生成。同一入力で常にバイト完全一致する出力を返す (末尾 `\n` 1 文字で終了)。
- `build_helper` は python_wrapper を持つ 4 ツール (search / query_db / get_datetime / ping) の関数定義を YAML 順で生成。claude_code / execute_python は python_wrapper 非定義のため自動的に除外される。
- `build_js` は 6 ツール全てを JSDoc テーブルと AVAILABLE_TOOLS 配列に出力し、privileged ツール (claude_code / execute_python) に `privileged: true` タグ + JSDoc に ` [privileged]` 接尾辞を付与。
- `build_docs` は `# MCP Tools Catalog` + 概要表 + 6 ツール詳細セクション (privileged 警告 + Sandbox Helper シグネチャ + docstring コードブロック) を生成。
- `--check` モードは on-disk ファイルと build_* 結果をバイト完全一致比較し、不一致時に `[drift] out of sync` + unified_diff + Fix 指示を stderr 出力して exit 1 (missing ファイルは `[drift] missing`)。
- `tests/test_generate_mcp_artifacts.py` 18 件全 PASS。`test_build_js_order` / `test_trailing_newline` / `test_determinism` / `test_check_all_*` の 5 種で decisive な契約を担保。

## Task Commits

1. **Task 1: ジェネレータ本体実装** — `bf053da` (feat)
2. **Task 2: pytest 単体テスト** — `e166868` (test)
3. **Task 2 付随修正: check_all パス整形の堅牢化 (Rule 1 auto-fix)** — `02377c7` (fix)

_Note: TDD サイクルは Task 1 (本体 feat) → Task 2 (test 追加) → Task 2 内で検出した Rule 1 バグを別 commit で分離 (fix)。_

## Files Created/Modified

- `scripts/generate_mcp_artifacts.py` (新規, 471 行 + 12 行追記 = 483 行) — argparse / load_tools / _format_arg / _format_docstring / _mcp_args_literal / _generate_wrapper_body / build_helper / build_js / build_docs / write_all / _rel_or_abs / _check_one / check_all / main の関数構成。chmod +x 適用済み。
- `tests/test_generate_mcp_artifacts.py` (新規, 300 行) — 18 テスト関数。`sys.path.insert(0, 'scripts')` 方式で generate_mcp_artifacts をモジュールとして import。monkeypatch による HELPER_PATH / JS_PATH / DOCS_PATH すり替えで tmp_path 上で安全に drift 検知を検証。

## Decisions Made

- **mcp_helper_utils への分離は Plan 03 の担当。** Plan 02 ジェネレータは `from mcp_helper_utils import _call_tool, _clean_content  # noqa: F401` を import 行に固定発行する。Plan 03 で utils モジュールを新設し、そこからジェネレータの出力 (mcp_helper.py 全体) を置き換える。
- **`mcp_args_mapping` YAML キーは Python 側引数名、値は MCP 側引数名と解釈する。** db_query の `pool: pool_name` は「Python 関数が `pool` 引数を受け取り、MCP には `pool_name` として送信する」ことを意味する。ジェネレータは `{"pool_name": pool}` という dict リテラルに変換して `_call_tool` に渡す。
- **`result_transform.mode` の 3 分岐 (passthrough / extract_key / web_search_results) は既存 mcp_helper.py の挙動を 1:1 再現する。** 既存の `result.get("rows", [result])` パターンは extract_key で、`r["content"] = _clean_content(...)` は web_search_results でそれぞれ発行される。
- **末尾改行は `rstrip("\\n") + "\\n"` で強制正規化。** check_all のバイト完全一致比較で「末尾 `\\n` が 2 個あるかどうか」の揺れが drift 偽陽性にならないことを test_trailing_newline で担保。
- **Plan 02 では実ファイル書き出しを行わない。** mcp_helper.py / tool-catalog-generated.js / docs/mcp-tools.md の実体は Plan 03 / 04 / 06 が `--target all` または個別ファイル書き出しで生成する。Plan 02 は「ジェネレータとテスト」だけをコミットするため、既存 mcp_helper.py の挙動や iframe-rpc.js には一切影響が無い。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] check_all の Path.relative_to(ROOT) が tmp_path で ValueError になる**

- **Found during:** Task 2 (`test_check_all_detects_drift_missing` 実装・実行時)
- **Issue:** `check_all()` の Fix メッセージ生成ロジックが `HELPER_PATH.relative_to(ROOT)` を呼んでいたため、pytest が monkeypatch で HELPER_PATH を `/tmp/...` に差し替えると `ValueError: ... is not in the subpath of ...` で例外終了してしまう。ジェネレータ自身の堅牢性バグでもあり (外部パスを渡すユースケースがテスト以外でも起こりうる)、ValueError は silent killer なので Rule 1 (バグ修正) で即時対応。
- **Fix:** `_rel_or_abs(path: Path) -> str` ヘルパーを追加し、`path.relative_to(ROOT)` が失敗した場合は `str(path)` を返す。`check_all()` の Fix メッセージと、`main()` の `--target all` 書き出しログの両方を `_rel_or_abs` 経由に統一。
- **Files modified:** scripts/generate_mcp_artifacts.py (+14 -2)
- **Verification:** `test_check_all_detects_drift_missing` / `test_check_all_detects_drift_mismatch` / `test_check_all_pass_when_match` の 3 件が PASS。既存 16 件にも回帰なし (全 18 件 PASS)。
- **Committed in:** 02377c7 (fix commit、Task 1 の本体コミット bf053da とは分離)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 バグ修正)
**Impact on plan:** テスト容易性とジェネレータ自身の堅牢性が両方向上。挙動変更なし (成功パスは純粋に `str(path.relative_to(ROOT))` と等価)。スコープクリープなし。

## Issues Encountered

- **uv run pytest が venv 権限エラー。** `.venv/bin/python3` が root 所有 (Docker ビルド時生成) で uv がホスト側で再作成できず、uv run 経路は使えなかった。ホスト pyenv に pytest 9.0.2 が入っていたので `python3 -m pytest` に切り替えて実行。テスト自体は全 PASS。ホスト環境の運用上の制約であり、CI (Docker) 経路には影響なし。

## Known Stubs

None — ジェネレータはすべての出力パスを実装済み。Plan 03/04/06 で実ファイル書き出しを実行するまで mcp_helper_utils.py / tool-catalog-generated.js / docs/mcp-tools.md は存在しないが、これはプランの設計通り (Plan 02 は「ジェネレータとテストだけを導入し、成果物は後続プランで出力」というフェーズ分割の意図通り)。

## User Setup Required

None — ホスト/CI 共にセットアップ変更不要。

## Next Phase Readiness

- **Plan 03 準備完了:** `scripts/generate_mcp_artifacts.py --target helper` の出力が Plan 03 の `mcp_helper.py` 新バージョンそのもの。`from mcp_helper_utils import _call_tool, _clean_content` の import が前提になるので、Plan 03 は (1) `mcp_helper_utils.py` を手書きで新設 (現 mcp_helper.py の L1-64 を移植) (2) `--target all` または `--target helper` > mcp_helper.py` を実行 (3) 回帰テストで sandbox 経路を再確認、の順で進められる。
- **Plan 04 準備完了:** `--target js` の出力が Plan 04 の `static/js/tool-catalog-generated.js` 新規ファイル。iframe-rpc.js はこれを import するよう書き換え、旧 `scripts/sync-tool-list-to-js.py` は削除可能。
- **Plan 05 準備完了:** `--check` モードはすでに実装済み。`scripts/install-hooks.sh` に MCP drift 検知フックを追加するだけでよい (pytest 連動テストも Plan 05 の範疇)。
- **Plan 06 準備完了:** `--target docs` の出力が `docs/mcp-tools.md` 新規ファイル。手書き側 (`docs/mcp-tool-add-manual.md`) と分離した状態で公開できる。

## Self-Check: PASSED

- [x] scripts/generate_mcp_artifacts.py 存在確認: `[ -f scripts/generate_mcp_artifacts.py ]` → OK (471 + 12 = 483 行、実行権限付き)
- [x] tests/test_generate_mcp_artifacts.py 存在確認: `[ -f tests/test_generate_mcp_artifacts.py ]` → OK (300 行、18 テスト関数)
- [x] 3 コミットが git log に存在: bf053da / e166868 / 02377c7 すべて確認済み
- [x] `python3 -m pytest tests/test_generate_mcp_artifacts.py` 18 passed
- [x] 決定論性: `python3 scripts/generate_mcp_artifacts.py --target {helper,js,docs}` 2 回実行結果がバイト完全一致
- [x] DO NOT EDIT ヘッダー: 3 ターゲット全てで head -1 が対応コメントで始まる
- [x] Plan 02 の verification gate: プランの `<verification>` 記載 4 条件 (構文 OK / 3 ターゲット stdout 生成 / pytest 全 PASS / 既存ファイル無変更) すべて満たす
- [x] mcp_helper.py / iframe-rpc.js は変更されていない (`git diff HEAD~3 -- mcp_server/tools/mcp_helper.py static/js/iframe-rpc.js` が空)

---
*Phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-*
*Completed: 2026-04-18*
