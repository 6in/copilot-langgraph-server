---
phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
plan: 04
subsystem: mcp
tags: [mcp, codegen, canvas, iframe, esmodule, js-catalog]

# Dependency graph
requires:
  - phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
    provides: "config/mcp_tools.yaml 拡張スキーマ (name / description / privileged)"
  - phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
    provides: "scripts/generate_mcp_artifacts.py build_js 関数 (--target js)"
provides:
  - "static/js/tool-catalog-generated.js (scripts/generate_mcp_artifacts.py --target js から自動生成された AVAILABLE_TOOLS を export する ES module)"
  - "static/js/iframe-rpc.js に import + re-export の 3 行を挿入し、ツールカタログ埋め込みを独立ファイルへ分離 (手書き RPC 本体は未変更)"
  - "tests/test_tool_catalog_js.py (生成 JS の形状検証 + drift 保護 + iframe-rpc.js 手書き RPC 回帰テスト)"
  - "scripts/sync-tool-list-to-js.py の削除 (責務が generate_mcp_artifacts.py に統合)"
affects: [phase-30-05-consumer-wiring, phase-30-06-docs-generation, canvas-iframe, codeact-agent]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "生成ファイルと手書きファイルの物理分離 (D-02): tool-catalog-generated.js は自動生成、iframe-rpc.js は手書き + re-export のみ"
    - "後方互換 re-export: iframe-rpc.js が from './tool-catalog-generated.js' で AVAILABLE_TOOLS を re-export することで、既存 Canvas iframe の import パスを変更せずに済ませる"
    - "Python-only pytest による JS 形状検証 (node ランタイムを CI に要求しない軽量アプローチ)"

key-files:
  created:
    - "static/js/tool-catalog-generated.js"
    - "tests/test_tool_catalog_js.py"
  modified:
    - "static/js/iframe-rpc.js (L20-40 の TOOL_CATALOG ブロックを 3 行 import + re-export に置換)"
  deleted:
    - "scripts/sync-tool-list-to-js.py (責務が generate_mcp_artifacts.py に統合)"

key-decisions:
  - "AVAILABLE_TOOLS の import パスは既存の Canvas iframe コンシューマとの後方互換のため iframe-rpc.js 側で re-export する (iframe-rpc.js から import している既存コードを改修不要にする)"
  - "Plan の 'grep references' ステップでヒットした docs/adr/0040-*.md / .planning/patterns.md / .planning/todos/pending/*.md / generate_mcp_artifacts.py 内コメントは本プラン スコープ外 — Plan 30-06 が docs/patterns.md 更新を担当する"
  - "テストは Python 正規表現ベース (Node ランタイム非依存) にし、drift 保護は build_js(load_tools()) の出力と実ファイル内容のバイト完全一致で担保する"

patterns-established:
  - "生成 ES module + 手書き RPC の物理分離: カタログは generated.js、RPC 本体は iframe-rpc.js、両者を re-export で接続する"
  - "生成ファイル + drift テスト + 手書き部回帰テスト の 3 点セット: 生成物の形状検証、drift 検知、手書き部の誤消去検知を同じテストファイルに集約する"

requirements-completed: [TBD]

# Metrics
duration: 8 min
completed: 2026-04-18
---

# Phase 30 Plan 04: MCP Tool Catalog を独立 ES module に分離 Summary

**`config/mcp_tools.yaml` から生成した `AVAILABLE_TOOLS` を `static/js/tool-catalog-generated.js` (自動生成 ES module) に分離し、`static/js/iframe-rpc.js` は 3 行の import + re-export のみで後方互換を維持。旧 `scripts/sync-tool-list-to-js.py` を削除して責務を `generate_mcp_artifacts.py` に一本化。**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-18T09:56:00Z
- **Completed:** 2026-04-18T10:04:08Z
- **Tasks:** 2
- **Files modified:** 4 (1 created generated / 1 created test / 1 modified / 1 deleted)

## Accomplishments
- `static/js/tool-catalog-generated.js` を新設 — `// DO NOT EDIT` ヘッダー + JSDoc テーブル + `export const AVAILABLE_TOOLS = [...]` を含む 2029 バイトの ES module
- `static/js/iframe-rpc.js` の L20-40 の TOOL_CATALOG ブロック (21 行) を L20-22 の 3 行 (コメント 2 行 + `export { AVAILABLE_TOOLS } from './tool-catalog-generated.js'`) に置換。手書き RPC 本体 (`pending` Map, message listener, `ai` / `query` / `call`) は 1 バイトも変更していない
- 旧 `scripts/sync-tool-list-to-js.py` を `git rm` で削除 — `generate_mcp_artifacts.py --target js` がこの責務を引き継ぐ
- `tests/test_tool_catalog_js.py` で 10 テスト追加: 生成 JS 形状 (header / export / 6 entries / privileged: true × 2), iframe-rpc.js の markerless 化, 後方互換 re-export, 手書き RPC の残存, 旧スクリプト削除, drift 検知 (`build_js(load_tools())` と実ファイルのバイト完全一致)

## Task Commits

1. **Task 1: JS カタログ分離 + iframe-rpc 書き換え + 旧 script 削除** — `f49954d` (feat)
2. **Task 2: tests/test_tool_catalog_js.py 追加** — `ecdceb3` (test)

**Plan metadata:** (will be committed after this SUMMARY.md)

## Files Created/Modified
- `static/js/tool-catalog-generated.js` — 新規作成 / `generate_mcp_artifacts.py --target js` の stdout を保存した自動生成 ES module (AVAILABLE_TOOLS 6 ツール定義 + JSDoc テーブル)
- `static/js/iframe-rpc.js` — TOOL_CATALOG マーカーブロック (L20-40) を 3 行の import + re-export に差し替え。L1-18 の docstring と L24+ の RPC 実装は無変更
- `scripts/sync-tool-list-to-js.py` — 削除 (責務が generate_mcp_artifacts.py に統合)
- `tests/test_tool_catalog_js.py` — 新規作成 / 10 テスト

## Decisions Made
- **後方互換維持のため iframe-rpc.js から re-export:** 既存 Canvas iframe / hosting shell は `import { AVAILABLE_TOOLS } from '.../iframe-rpc.js'` で参照している可能性があるため、iframe-rpc.js 側で `export { AVAILABLE_TOOLS } from './tool-catalog-generated.js'` し import path を変更不要にした
- **Plan スコープ境界の厳守:** plan 内の「`grep -rn sync-tool-list-to-js` で全参照を置換」ステップは、オーケストレータからの強い指示「files_modified リスト外を触らない」と `docs/*` / `.planning/patterns.md` / `CLAUDE.md` の明示的禁止と矛盾するため実施せず。該当参照 (`docs/adr/0040-*.md` / `.planning/patterns.md` / `generate_mcp_artifacts.py` 内コメント / `.planning/todos/pending/*.md`) は Plan 30-06 (docs + patterns.md 更新) が回収する設計
- **Python-only pytest + drift 検知で担保:** Node を CI に要求せず、`build_js(load_tools())` 出力と実ファイルのバイト完全一致で drift を検出する

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `uv run pytest` 不可能だったため host の `python3 -m pytest` で検証**
- **Found during:** Task 2 (テスト実行時)
- **Issue:** `.venv/` が Docker コンテナ内 (`/app/.venv/`) で生成されており、host の `uv run` がシンボリックリンク解決に失敗 (`failed to remove directory .venv/lib64: Permission denied`)。.venv ディレクトリ自体も root 所有
- **Fix:** host の `python3 -m pytest`（pyenv の Python 3.12.3 + pytest 9.0.2）で実行。pyproject.toml の rootdir と asyncio plugin は正しく読み込まれ、10 テスト全 PASSED
- **Files modified:** なし (テスト実行方法のみ変更)
- **Verification:** `python3 -m pytest tests/test_tool_catalog_js.py -v` → 10 passed. 上流プラン (tool_registry / mcp_helper_generated / generate_mcp_artifacts) の 37 テストも全 pass
- **Commit hash:** n/a (ツール実行の迂回のみ)

**2. [Rule 2 - Scope Boundary] plan 手順「全参照置換」は Plan 30-06 に委譲**
- **Found during:** Task 1 Step 3 (git rm 後の grep ステップ)
- **Issue:** Plan は `grep -rn sync-tool-list-to-js` でヒットした全参照を置換するよう指示するが、(a) ヒット箇所は `docs/adr/0040-*.md` / `.planning/patterns.md` / `.planning/todos/pending/*.md` / `generate_mcp_artifacts.py` 内コメント で、いずれも `files_modified` リスト外。(b) orchestrator prompt は `docs/*` / `.planning/patterns.md` / `CLAUDE.md` を明示的に禁止。(c) Plan 30-06 がまさに docs + patterns.md の更新を担当する
- **Fix:** 置換を実施せず、Plan 30-06 のスコープ内で処理される設計を維持。本 SUMMARY の Decisions に明記
- **Files modified:** なし
- **Verification:** iframe-rpc.js + tool-catalog-generated.js + tests/* + scripts/sync-tool-list-to-js.py (deletion) の 4 ファイルのみ変更。`git status` で `files_modified` リスト外のファイル変更なし
- **Commit hash:** n/a (scope decision)

---

**Total deviations:** 2 auto-fixed (1 blocking for test runner, 1 scope boundary)
**Impact on plan:** いずれもプラン成果物の品質には影響しない。ツール迂回は機能的等価、スコープ境界の決定は後続プラン (30-06) で正しく処理される

## Issues Encountered
なし

## User Setup Required
なし — 生成ファイルとテストの追加のみ

## Next Phase Readiness
- **Plan 30-04 完了条件を全て満たす:**
  - JS カタログが独立 ES module に分離 ✓
  - iframe-rpc.js から TOOL_CATALOG マーカー消滅 ✓
  - 旧 sync スクリプト削除 ✓
  - pytest 回帰テスト全 pass (10/10 + 上流 37/37) ✓
  - `build_js(load_tools())` と生成ファイルがバイト完全一致 (drift なし) ✓
- **Plan 30-05 / 30-06 準備完了:**
  - Plan 30-05 (consumer wiring): Canvas iframe と他コンシューマが `iframe-rpc.js` から変更なしに AVAILABLE_TOOLS を import 可能
  - Plan 30-06 (docs + patterns.md 生成): `docs/adr/0040-*.md` / `.planning/patterns.md` / `.planning/todos/pending/2026-04-18-mcp-tool-registration-consumer-propagation.md` / `scripts/generate_mcp_artifacts.py` 内コメントの `sync-tool-list-to-js` 残存参照を全て更新できる
- **ブロッカー:** なし

## Self-Check: PASSED

- `[ -f static/js/tool-catalog-generated.js ]` ✓
- `[ -f tests/test_tool_catalog_js.py ]` ✓
- `[ ! -f scripts/sync-tool-list-to-js.py ]` ✓
- `git log --oneline | grep f49954d` ✓ (Task 1 commit)
- `git log --oneline | grep ecdceb3` ✓ (Task 2 commit)
- `python3 -m pytest tests/test_tool_catalog_js.py -v` → 10 passed ✓
- `build_js(load_tools()) == read('static/js/tool-catalog-generated.js')` ✓ (byte-exact)
- `git status --short` → clean working tree ✓
- 上流回帰: tool_registry + mcp_helper_generated + generate_mcp_artifacts = 37 passed ✓

---
*Phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-*
*Completed: 2026-04-18*
