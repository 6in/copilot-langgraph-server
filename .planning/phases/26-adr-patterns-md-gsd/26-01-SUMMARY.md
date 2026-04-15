---
phase: 26-adr-patterns-md-gsd
plan: 01
subsystem: docs-tooling
tags: [adr, tooling, pre-commit, python, pytest]
dependency_graph:
  requires:
    - docs/adr/*.md（既存 30 件）
    - pyyaml（既存依存）
  provides:
    - .planning/adr-categories.yaml（カテゴリマッピング）
    - scripts/generate_adr_index.py（INDEX.md 生成スクリプト）
    - scripts/install-hooks.sh（pre-commit hook インストーラ）
    - tests/test_generate_adr_index.py（ユニットテスト 7 件）
  affects:
    - docs/adr/INDEX.md（自動生成物、初期版を commit）
    - .git/hooks/pre-commit（ローカルのみ、commit 対象外）
tech_stack:
  added: []
  patterns:
    - "yaml.safe_load() によるカテゴリ設定の読み込み（T-26-01 対策）"
    - "正規表現 2 本で ADR タイトル/日付をパース（標準 + ADR 0020 異種）"
    - "pre-commit hook の scripts/install-hooks.sh 方式（D-14）"
    - "D-03 準拠: INDEX.md 生成のみ、ADR 本文不変更"
key_files:
  created:
    - .planning/adr-categories.yaml
    - scripts/generate_adr_index.py
    - scripts/install-hooks.sh
    - tests/test_generate_adr_index.py
    - docs/adr/INDEX.md
  modified: []
decisions:
  - "Date 正規表現を `\\*\\*Date[*:\\s]+` に変更し、'**Date:**' と '**Date**:' の両方を吸収（計画の `\\*?\\*?:?` では ADR 0001 がマッチせずテストが失敗したため）"
metrics:
  duration_min: 4
  completed_date: "2026-04-15"
  tasks_completed: 3
  files_created: 5
---

# Phase 26 Plan 01: ADR 基盤ツールチェーン構築 Summary

ADR 30 件を 7 カテゴリに振り分けるマッピング YAML、INDEX.md 自動生成 Python スクリプト（pytest 7 件で検証）、docs/adr/ 変更時に INDEX.md を再生成する pre-commit hook のインストーラを整備し、Phase 26 後続プランが利用する実行基盤を完成させた。

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | .planning/adr-categories.yaml を作成 | `8f172eb` | .planning/adr-categories.yaml |
| 2 | generate_adr_index.py + pytest 実装（TDD） | `ccdcf70` (test), `13318c7` (impl) | scripts/generate_adr_index.py, tests/test_generate_adr_index.py, docs/adr/INDEX.md |
| 3 | install-hooks.sh + pre-commit hook 有効化 | `7a1ea91` | scripts/install-hooks.sh |

## What Was Built

### 1. `.planning/adr-categories.yaml`（50 行）

- 7 カテゴリ（Auth / LangGraph・Graph / MCP・Tools / Worker・Jobs / Frontend・UI / Infra・Deploy / Data・Persistence）を `categories:` リストで宣言
- `adr_categories:` マップに 30 件（0001-0033 から欠番 0015-0017 を除く）を primary / secondary で振り分け
- `missing:` リストに `"0015"`, `"0016"`, `"0017"` を明示（D-04）
- Phase 26 RESEARCH.md 調査結果 1 の表をそのまま YAML 化

### 2. `scripts/generate_adr_index.py`（104 行）

- `docs/adr/[0-9][0-9][0-9][0-9]-*.md` を走査し `parse_adr()` で (番号, タイトル, 日付) を抽出
- **`TITLE_RE = r'^# (?:ADR )?(\d+)[.:]\s+(.+?)\s*$'`** — 標準 `# 0001.` と ADR 0020 の `# ADR 0020:` を両方吸収
- **`DATE_RE = r'^\*\*Date[*:\s]+(\d{4}-\d{2}-\d{2})'`** — `**Date:**` と `**Date**:` の両方を吸収（後述の計画からの逸脱参照）
- `yaml.safe_load()` で adr-categories.yaml を読み込み（T-26-01 対策）
- `build_index()` で Markdown 文字列を構築し、カテゴリ別テーブル + `## 欠番` セクションを出力
- D-03 準拠: 生成先は `docs/adr/INDEX.md` のみ、ADR 本文には一切触れない
- 実行: `python3 scripts/generate_adr_index.py` → `Generated docs/adr/INDEX.md (4367 bytes)`

### 3. `tests/test_generate_adr_index.py`（70 行 / 7 テスト）

- `test_parse_standard_adr` — ADR 0001 標準フォーマットのパース
- `test_parse_adr_0020_alternate_format` — ADR 0020 異種フォーマットのパース（Pitfall 1 回避）
- `test_load_categories_structure` — YAML 構造（7 カテゴリ、30 エントリ、欠番 3 件）
- `test_build_index_has_all_categories` — 7 カテゴリ全ての見出しが含まれる
- `test_build_index_records_missing` — `## 欠番` セクションに 0015/0016/0017
- `test_build_index_includes_adr_0020` — ADR 0020 が `## MCP・Tools` セクション内に配置
- `test_build_index_total_count` — `**Total:** 30 件` の表記
- **結果: 7 passed in 0.04s**

### 4. `scripts/install-hooks.sh`（29 行）

- `set -euo pipefail` でエラー即中断
- `.git/hooks/pre-commit` をヒアドキュメントで生成（内部で `git diff --cached --name-only | grep -qE '^docs/adr/[0-9]{4}-.*\.md$'` でトリガ条件を判定）
- トリガ時: `python3 scripts/generate_adr_index.py` → `git add docs/adr/INDEX.md`（Pitfall 3 対策）
- regex で番号プレフィックスを要求しているため `INDEX.md` 自身の変更ではトリガされない（無限ループ回避）
- `chmod +x` で実行可能化
- **検証: 実行後 `.git/hooks/pre-commit` が実行可能で `generate_adr_index.py` を呼ぶことを確認**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Date 正規表現の修正**

- **Found during:** Task 2 GREEN フェーズ
- **Issue:** 計画に記載の正規表現 `^\*\*Date\*?\*?:?\s*(\d{4}-\d{2}-\d{2})` は `*` と `:` と `?` が non-greedy かつ 0-match を許容するため、`**Date:** 2026-04-03` 形式にマッチしなかった（test_parse_standard_adr が `date == '-'` で失敗）。
- **Fix:** `^\*\*Date[*:\s]+(\d{4}-\d{2}-\d{2})` に変更。`**Date` 後に続く `*` / `:` / 空白を文字クラスで 1 回以上吸収する形にし、`**Date:**` と `**Date**:` の両方を確実にマッチさせた。
- **Files modified:** scripts/generate_adr_index.py
- **Commit:** `13318c7`（修正は GREEN コミット内に含まれる）

この逸脱は計画の正規表現が ADR 0001 側（`**Date:**`）を見落としていたことに起因する。ADR 0020（`**Date**:`）との両立を実テストで検証したことで発見できた。

### 認証ゲート

なし

### アーキテクチャ変更

なし

## Verification Results

| 検証項目 | 結果 |
|---------|------|
| `python3 scripts/generate_adr_index.py` 実行 | OK — `Generated docs/adr/INDEX.md (4367 bytes)` |
| `pytest tests/test_generate_adr_index.py -xvs` | 7 passed |
| `.git/hooks/pre-commit` 存在 + 実行可能 | OK |
| `adr-categories.yaml` エントリ数 | 30 件 |
| カテゴリ数 | 7 件 |
| 欠番リスト | `['0015', '0016', '0017']` |

## Commits

- `8f172eb` feat(26-01): ADR カテゴリマッピング YAML を追加
- `ccdcf70` test(26-01): generate_adr_index の失敗テストを追加（TDD RED）
- `13318c7` feat(26-01): ADR INDEX 自動生成スクリプトを実装（TDD GREEN）
- `7a1ea91` feat(26-01): pre-commit hook インストールスクリプトを追加

## TDD Gate Compliance

- **RED gate:** `ccdcf70 test(26-01): generate_adr_index の失敗テストを追加` — テスト作成時 `ModuleNotFoundError` で正しく失敗
- **GREEN gate:** `13318c7 feat(26-01): ADR INDEX 自動生成スクリプトを実装` — 全 7 テスト pass
- **REFACTOR:** 不要（GREEN コード時点でクリーン）

## Known Stubs

なし — 全コード・設定が production-ready。

## Self-Check: PASSED

- FOUND: .planning/adr-categories.yaml
- FOUND: scripts/generate_adr_index.py
- FOUND: scripts/install-hooks.sh
- FOUND: tests/test_generate_adr_index.py
- FOUND: docs/adr/INDEX.md
- FOUND: commit 8f172eb
- FOUND: commit ccdcf70
- FOUND: commit 13318c7
- FOUND: commit 7a1ea91
