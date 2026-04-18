---
phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
plan: 05
subsystem: infra
tags: [pre-commit-hook, mcp, drift-detection, pytest, git-hooks]

requires:
  - phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
    provides: "generate_mcp_artifacts.py --check mode, fully generated mcp_helper.py / tool-catalog-generated.js / docs/mcp-tools.md"
provides:
  - "Extended pre-commit hook installer that enforces MCP catalog drift via `generate_mcp_artifacts.py --check`"
  - "pytest coverage (4 scenarios) for the hook installer and drift blocking behavior"
  - "Durable automation that blocks commits when YAML and generated MCP artifacts diverge"
affects: [future-mcp-tool-additions, ci, contributor-workflow]

tech-stack:
  added: []
  patterns:
    - "Pre-commit hook (heredoc in installer) wraps `generate_mcp_artifacts.py --check` and blocks commits on drift"
    - "Integration-style pytest using a tmp_path git repo + --no-verify initial commit pattern"

key-files:
  created:
    - tests/test_install_hooks.py
  modified:
    - scripts/install-hooks.sh

key-decisions:
  - "既存 ADR INDEX ロジック (Phase 26) は一切書き換えず、STAGED_FILES 変数の共有のみで条件を再構成"
  - "drift 検知は `cd \"$REPO_ROOT\" && python3 scripts/generate_mcp_artifacts.py --check` 形式で実行し、acceptance_criteria の grep 文字列と一致させた"
  - "pytest fixture は `git commit --no-verify` で初期化を行い、hook を経由せずクリーン状態を作ってから drift シナリオを流す"

patterns-established:
  - "Pre-commit drift guard: generator が `--check` モードを持つなら hook で invoke し、非 0 終了を `exit 1` 変換してコミットをブロックする"
  - "Hook 自体を pytest で検証するには tmp_path に最小 repo を組み、generator で生成ファイルを再構築してから `--no-verify` で初期コミットする"

requirements-completed: [TBD]

duration: 12 min
completed: 2026-04-18
---

# Phase 30 Plan 5: Pre-commit Hook Extension Summary

**`config/mcp_tools.yaml` と生成アーティファクトの drift を `generate_mcp_artifacts.py --check` 経由で pre-commit 時に自動検知し、block する拡張 hook と 4 シナリオの pytest 検証を導入。**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-18T13:00:00Z
- **Completed:** 2026-04-18T13:12:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `scripts/install-hooks.sh` を拡張し、`.git/hooks/pre-commit` に MCP 4 パス (`config/mcp_tools.yaml` / `mcp_server/tools/mcp_helper.py` / `static/js/tool-catalog-generated.js` / `docs/mcp-tools.md`) の drift 検査ブロックを追加。既存 ADR INDEX ロジックは維持。
- drift 検出時は stderr に修正コマンド (`python3 scripts/generate_mcp_artifacts.py --target all` + `git add` + `git commit`) を含むガイダンスを出力してから `exit 1`。
- `tests/test_install_hooks.py` で 4 シナリオ (`test_hook_installed` / `test_no_drift_commit_passes` / `test_drift_commit_blocked` / `test_drift_fixed_by_regen`) を pytest でカバー。tmp_path に git repo を作り、実際に `git commit` を実行する統合テスト。
- 既存 pytest スイート (`test_tool_registry.py` / `test_mcp_helper_generated.py` / `test_tool_catalog_js.py` / `test_generate_mcp_artifacts.py` / `test_generate_adr_index.py`) 54 件 PASS (回帰なし)。
- 本 plan 自身のコミットが新 hook を通過し、スモークテスト合格を兼ねる。

## Task Commits

1. **Task 1: scripts/install-hooks.sh 拡張** — `c26be53` (feat)
2. **Task 2: tests/test_install_hooks.py 追加** — `9a4bc08` (test)

**Plan metadata commit:** (このファイル追加後の `docs(30-05)`)

## Files Created/Modified

- `scripts/install-hooks.sh` — ADR セクションと並列に「Phase 30: MCP ツールカタログ drift 検知」ブロックを追加。`STAGED_FILES` 変数を共通化し、MCP_PATHS_REGEX で 4 パスを判定、`cd "$REPO_ROOT" && python3 scripts/generate_mcp_artifacts.py --check` を呼んで exit 1 で commit をブロック。
- `tests/test_install_hooks.py` — 新規。`_run` ヘルパー、`temp_repo` fixture (git init → file copy → hook install → artifacts regen → `--no-verify` initial commit)、4 test functions。

## Decisions Made

- **Hook 内で generator を呼ぶ形式:** Plan 原案は `python3 "$REPO_ROOT/scripts/generate_mcp_artifacts.py" --check` だったが、acceptance_criteria の grep (`'generate_mcp_artifacts.py --check'`) にパス先のクォートが挟まり一致しない問題があったため、`cd "$REPO_ROOT" && python3 scripts/generate_mcp_artifacts.py --check` 形式に変更。既存 ADR 呼び出しとも整合的。
- **pytest 初期化に `--no-verify` を使用:** tmp_path の初期コミットで hook が走ると (hook 自体がまだ未成熟・`generate_mcp_artifacts.py` が `yaml` 依存を import でき無い場合を含む) 失敗するリスクがあるため、fixture の initial commit のみ `--no-verify` で通過させ、本番テストは `--no-verify` 無しで実行。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Hook 内 generator 呼び出しのパス形式を変更**
- **Found during:** Task 1 の acceptance_criteria 検証時
- **Issue:** Plan 提示の `python3 "$REPO_ROOT/scripts/generate_mcp_artifacts.py" --check` 形式だと、acceptance verify の `grep -q 'generate_mcp_artifacts.py --check'` に `"` が挟まって一致せず、criteria 1 件が FAIL していた。
- **Fix:** `cd "$REPO_ROOT" && python3 scripts/generate_mcp_artifacts.py --check` 形式に変更。動作 (CWD は REPO_ROOT、generator は self-resolving) は等価、かつ grep ターゲットの連続文字列が hook 内にそのまま現れる。
- **Files modified:** `scripts/install-hooks.sh`
- **Verification:** 10/10 acceptance_criteria 全 PASS。`OK_mcp_check` を確認。
- **Committed in:** `c26be53` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** acceptance_criteria を満たすための形式変更のみ。hook 挙動・セキュリティ上の差異なし。

## Issues Encountered

- `uv run pytest` が `.venv/lib64` の permission denied で失敗したため、plan 想定通り `python3 -m pytest` フォールバックに切り替えて実行。全テスト PASS。

## User Setup Required

None — 既存ワークフロー (`bash scripts/install-hooks.sh` を 1 回実行) に変化なし。新規クローン後の hook インストール手順は CLAUDE.md と `/add-mcp-tool` コマンドで既に案内済み。

## Next Phase Readiness

- **Phase 30 完了:** 本 plan で Phase 30 の 6 plan すべてが完了 (schema / generator / helper / JS catalog / docs+command / hook guard)。
- **Drift detection が有効化:** 今後 `config/mcp_tools.yaml` や生成 3 ファイルを触るとき、開発者が generator を忘れても pre-commit が block する。
- **次ステップ:** `gsd-sdk query phases.next` で新規フェーズ計画、または `/gsd-verify-work` で Phase 30 全体の verification。

## Self-Check: PASSED

- `scripts/install-hooks.sh` 存在 → FOUND
- `tests/test_install_hooks.py` 存在 → FOUND
- `c26be53` 存在 → FOUND (`feat(phase-30-05)`)
- `9a4bc08` 存在 → FOUND (`test(phase-30-05)`)
- plan-level `<verification>` 4 件 すべて PASS (冪等性 / ADR+MCP 両方実行 / 4 パス発火 / pytest 4 PASS)
- plan-level `<success_criteria>` 3 件 すべて PASS (手動編集 block / Phase 26 非破壊 / pytest 全 pass)

---
*Phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-*
*Plan: 05*
*Completed: 2026-04-18*
