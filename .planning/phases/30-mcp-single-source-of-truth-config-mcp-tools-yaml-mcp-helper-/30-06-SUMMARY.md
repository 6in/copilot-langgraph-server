---
phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
plan: 06
subsystem: docs
tags: [mcp, docs, slash-command, claude-md, patterns, phase-30]

requires:
  - phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
    provides: "scripts/generate_mcp_artifacts.py --target docs (Plan 02)"
  - phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
    provides: "mcp_server/tools/mcp_helper.py regenerated (Plan 03)"
  - phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
    provides: "static/js/tool-catalog-generated.js (Plan 04)"
provides:
  - "docs/mcp-tools.md 自動生成カタログ (6 ツール, DO NOT EDIT)"
  - "docs/mcp-tool-add-manual.md 手書き手順書 (YAML スキーマ / 手書き境界 / privileged / pre-commit / 追加チェックリスト)"
  - ".claude/commands/add-mcp-tool.md スラッシュコマンド (7 ステップ自動化)"
  - "CLAUDE.md '## MCP Tool Catalog (Phase 30)' セクション (運用ルール)"
  - ".planning/patterns.md MCP・Tools セクション Phase 30 更新 (旧同期スクリプト廃止 + single-source-of-truth 新規パターン)"
affects: [future-mcp-tool-additions, gsd-planning, onboarding]

tech-stack:
  added: []
  patterns:
    - "single source of truth + deterministic generator + pre-commit drift check"
    - "slash-command walkthrough for repetitive multi-file additions"

key-files:
  created:
    - docs/mcp-tools.md
    - docs/mcp-tool-add-manual.md
    - .claude/commands/add-mcp-tool.md
    - .planning/phases/30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-/30-06-SUMMARY.md
  modified:
    - CLAUDE.md
    - .planning/patterns.md

key-decisions:
  - "docs/mcp-tools.md は `scripts/generate_mcp_artifacts.py --target docs` で生成 — 手書きマニュアルは別ファイル (docs/mcp-tool-add-manual.md) に分離して境界を明確化"
  - ".claude/commands/add-mcp-tool.md は .gitignore 対象 (.claude/) 配下だが、既存 create-adr.md が tracked である前例に倣い `git add -f` で明示コミット"
  - "patterns.md の ADR 番号は Phase 30 完了後に `/create-adr` で作成予定のため placeholder (`番号未定`) で暫定記載 — plan の objective コメントブロック通り"

patterns-established:
  - "MCP ツール single-source-of-truth: YAML + generator + pre-commit drift → 3 生成ファイル (helper.py / tool-catalog-generated.js / mcp-tools.md)"
  - "スラッシュコマンド経由の手順自動化 + 手書きマニュアル併設 (UX と理解の両立)"

requirements-completed: [TBD]

duration: 24 min
completed: 2026-04-18
---

# Phase 30 Plan 06: docs + slash command + CLAUDE.md + patterns.md Summary

**`docs/mcp-tools.md` を決定論的ジェネレータから初回生成し、手書き追加マニュアル・`/add-mcp-tool` スラッシュコマンド・CLAUDE.md 運用ルール・patterns.md 更新で Phase 30 の運用面を完成**

## Performance

- **Duration:** 24 min
- **Started:** 2026-04-18T10:07:26Z
- **Completed:** 2026-04-18T10:32:21Z
- **Tasks:** 2 (いずれも auto, tdd フラグは plan 上のみで実体は docs/artifact 追加のため RED/GREEN サイクル不要)
- **Files modified:** 5 (created: 3 / modified: 2) + SUMMARY.md

## Accomplishments

- `docs/mcp-tools.md` を `scripts/generate_mcp_artifacts.py --target docs` から初回生成（120 行、6 ツール詳細 + 一覧表 6 行、先頭 DO NOT EDIT）
- `docs/mcp-tool-add-manual.md` 手書きマニュアル (151 行) を新規作成 — YAML スキーマ全項目 / 手書き境界テーブル / result_transform 3 モード / privileged 基準 / pre-commit 挙動 / 追加チェックリスト / 削除手順 / ToolRegistry 互換性を網羅
- `.claude/commands/add-mcp-tool.md` (125 行) を `create-adr.md` スタイルで新規作成 — 7 ステップ (ツール名確定 → YAML → 実装雛形 → server.py → 再生成 → テスト雛形 → コミット)
- `CLAUDE.md` に新規 `## MCP Tool Catalog (Phase 30)` セクションを挿入（既存 9 セクションは一字一句保持、Developer Profile 領域も未変更）
- `.planning/patterns.md` MCP・Tools セクションを Phase 30 スキーマに更新（旧「iframe-rpc.js ツールカタログ埋め込み + 同期スクリプト」を「独立 ES module 参照」へ書き換え、新規「MCP ツール single-source-of-truth 化」エントリを追加）
- `python3 scripts/generate_mcp_artifacts.py --check` 全ターゲット drift なし (exit 0)

## Task Commits

1. **Task 1: docs/mcp-tools.md 生成 + mcp-tool-add-manual.md 新規作成** — `ccdc5bd` (docs)
2. **Task 2: /add-mcp-tool + CLAUDE.md + patterns.md 更新** — `da8ec53` (feat)

*Note: TDD の RED/GREEN/REFACTOR サイクルは適用外（本 plan はドキュメント/運用成果物のみ、テスト対象コード無し）*

## Files Created/Modified

- `docs/mcp-tools.md` (created, generated, 120 lines) — 自動生成ツールカタログ 6 ツール
- `docs/mcp-tool-add-manual.md` (created, handwritten, 151 lines) — 新規 MCP ツール追加マニュアル
- `.claude/commands/add-mcp-tool.md` (created, 125 lines) — 7 ステップスラッシュコマンド
- `CLAUDE.md` (modified, +31 lines) — `## MCP Tool Catalog (Phase 30)` セクション追加
- `.planning/patterns.md` (modified, +13 / -4 lines) — 旧 iframe-rpc 同期スクリプト記述を Phase 30 スキーマへ書き換え + 新規 single-source-of-truth エントリ

## Decisions Made

- `docs/mcp-tools.md` は生成ファイル、`docs/mcp-tool-add-manual.md` は手書きと明確分離（先頭 `DO NOT EDIT` 有無で判別、手書き境界テーブルで明示）
- `.claude/commands/add-mcp-tool.md` は `.gitignore` 対象の `.claude/` 配下だが、既存 `create-adr.md` が tracked である前例に倣い `git add -f` でコミット（同じ運用パターンを踏襲）
- patterns.md の ADR 番号は Phase 30 完了後の `/create-adr` 運用時に決定するため暫定 placeholder（`Phase 30 (ADR 番号未定 — /create-adr で追補予定)`）として記載 — plan 末尾の objective コメントブロックの運用方針通り

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `.claude/` が `.gitignore` により ignore されており最初の `git add` が失敗 → 既存 `create-adr.md` の tracking 状況を確認し `git add -f` で対応（Rule 3 — blocking but minor; 既存前例に倣い deviation 扱いせず通常フロー）

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 30 残タスクは Plan 05 (pre-commit hook で MCP drift 検知を統合) のみ。本 Plan 06 で `docs/mcp-tools.md` が REPO_ROOT に存在 + コミット済みなので、Plan 05 が hook を有効化しても drift は発生しない（wave 2 → wave 3 順序制約の目的達成）
- Phase 30 マージ前に `/create-adr` で設計判断を ADR 化し、patterns.md の `番号未定` 部分を実際の ADR 番号に差し替える運用が必要（plan 末尾コメントブロック参照）

## Self-Check: PASSED

- [x] `docs/mcp-tools.md` 存在確認 (FOUND)
- [x] `docs/mcp-tool-add-manual.md` 存在確認 (FOUND, 151 lines >= 120)
- [x] `.claude/commands/add-mcp-tool.md` 存在確認 (FOUND, 125 lines >= 80)
- [x] `CLAUDE.md` MCP Tool Catalog セクション追加確認 (FOUND)
- [x] `.planning/patterns.md` 新パターンエントリ追加確認 (FOUND)
- [x] Commit `ccdc5bd` 存在確認 (FOUND in git log)
- [x] Commit `da8ec53` 存在確認 (FOUND in git log)
- [x] `python3 scripts/generate_mcp_artifacts.py --check` exit 0
- [x] Generator byte-for-byte match で `docs/mcp-tools.md` と一致
- [x] Working tree clean
- [x] 既存 CLAUDE.md 全セクション保持 (Project / Technology Stack / Conventions / Architecture / Chrome DevTools MCP / Merge Safety Rules / GSD Workflow Enforcement / Developer Profile)
- [x] 旧文言 `sync-tool-list-to-js.py で自動更新可能` は patterns.md から削除済み

---
*Phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-*
*Completed: 2026-04-18*
