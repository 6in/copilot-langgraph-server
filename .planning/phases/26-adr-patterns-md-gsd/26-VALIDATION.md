---
phase: 26
slug: adr-patterns-md-gsd
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-15
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x（既存、pyproject.toml に設定済） |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_generate_adr_index.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 秒（Quick run 単体）/ ~60 秒（Full suite） |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_generate_adr_index.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | none (整備) | T-26-01 | YAML は `yaml.safe_load()` のみでロード（任意オブジェクト構築を防ぐ） | unit | `python3 -c "import yaml; d=yaml.safe_load(open('.planning/adr-categories.yaml')); assert len(d['adr_categories'])==30; assert d['missing']==['0015','0016','0017']; assert len(d['categories'])==7; print('OK')"` | ✅ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | none (整備) | — | ADR パーサーは静的ファイル read のみ、eval/exec なし | unit | `python3 scripts/generate_adr_index.py && pytest tests/test_generate_adr_index.py -xvs` | ✅ W0 | ⬜ pending |
| 26-01-03 | 01 | 1 | none (整備) | T-26-02 | git hook はローカル開発者のみ実行、外部入力なし（accept） | smoke | `bash scripts/install-hooks.sh && test -x .git/hooks/pre-commit && grep -q "generate_adr_index.py" .git/hooks/pre-commit` | ✅ | ⬜ pending |
| 26-02-01 | 02 | 2 | none (整備) | — | 生成された INDEX.md はスクリプト出力のみ（手動編集禁止） | smoke | `python3 scripts/generate_adr_index.py && grep -q "^# ADR Index" docs/adr/INDEX.md && grep -q "\*\*Total:\*\* 30 件" docs/adr/INDEX.md && grep -q "0015" docs/adr/INDEX.md && grep -q "0020" docs/adr/INDEX.md && grep -q "0033" docs/adr/INDEX.md` | ✅ | ⬜ pending |
| 26-02-02 | 02 | 2 | none (整備) | — | patterns.md は ADR リンクのみで任意 URL を含まない | smoke | `test -f .planning/patterns.md && [ $(grep -c "^## " .planning/patterns.md) -eq 7 ] && [ $(grep -c "\.\./docs/adr/" .planning/patterns.md) -ge 18 ]` | ✅ | ⬜ pending |
| 26-03-01 | 03 | 2 | none (整備) | — | CLAUDE.md 追記内容は文書変更のみ（コード影響なし） | smoke | `grep -q "ADR Pattern Reference" CLAUDE.md && grep -q "\.planning/patterns\.md" CLAUDE.md && grep -q "install-hooks\.sh" CLAUDE.md && ! grep -q "^@\.planning/patterns\.md" CLAUDE.md` | ✅ | ⬜ pending |
| 26-03-02 | 03 | 2 | none (整備) | — | create-adr.md 追記内容は文書変更のみ | smoke | `grep -q "patterns\.md" .claude/commands/create-adr.md && grep -q "adr-categories\.yaml" .claude/commands/create-adr.md` | ✅ | ⬜ pending |
| 26-03-03 | 03 | 2 | none (整備) | — | ROADMAP.md 更新は placeholder 置換のみ | smoke | `grep -q "Phase 26: ADR 整理" .planning/ROADMAP.md && ! grep -q "\[To be planned\]" .planning/ROADMAP.md && grep -q "\*\*Plans:\*\* 3 plans" .planning/ROADMAP.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_generate_adr_index.py` — Plan 01 Task 2 内の TDD ステップとして配置。generate_adr_index.py の parse_adr / load_categories / build_index をカバー（6 テスト）
- [x] pytest framework — 既存（pyproject.toml 設定済、インストール不要）
- [x] pyyaml — 既存（pyproject.toml 依存済）

*Wave 0 成果物は Plan 01 Task 2 の冒頭（RED フェーズ）で test ファイルを先に作成することで達成する。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| patterns.md の各エントリ本文が人間に読みやすく正確か | none | 自然言語要約の質は自動検証不可 | `.planning/patterns.md` を目視確認し、ADR 本文と食い違いがないかレビュー |
| INDEX.md のカテゴリ分類が D-09/D-10 の意図と合致しているか | none | 分類の妥当性は人間判断 | 7 カテゴリの並びを目視、特に secondary 所属が意図通りか |
| CLAUDE.md への追記が既存のトーン・構造と調和しているか | none | 文章品質は自動検証不可 | CLAUDE.md 全体を読み、追記セクションが浮いていないか確認 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references（`tests/test_generate_adr_index.py` は Plan 01 Task 2 の TDD RED フェーズで作成）
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-15
