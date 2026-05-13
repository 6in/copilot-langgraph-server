---
phase: 39
plan: 02
subsystem: docs-adr
tags: [polish, adr, mermaid, docs, frontend, wave-1]
requirements: [UIFIX-01]
dependency_graph:
  requires:
    - "39-01 Wave 0 baseline (本 plan は code-touch なしで baseline 数値を維持)"
  provides:
    - "ADR-0053 (Mermaid Source default 恒久化の根拠) を後続レビュー者・AI agent に提供"
    - "MermaidBlock.tsx 冒頭から ADR-0053 への 1-hop pointer"
    - "scripts/generate_adr_index.py --check (将来の ADR plan の drift 検査用)"
  affects:
    - "INDEX.md は pre-commit hook で自動再生成された (Total 49 → 50)"
tech_stack:
  added: []
  patterns:
    - "ADR-0040 と同じ Frontend・UI カテゴリ ADR の 5 セクション構造 (Context / Decision / Alternatives Considered / Consequences / Related) を踏襲"
    - "pre-commit hook (generate_adr_index.py + git add) による INDEX.md 自動同期 (Phase 26)"
    - "Pitfall 6 厳守 — ADR は長文化可、ただし MermaidBlock.tsx 冒頭コメントへの転記は 2 行のみ"
key_files:
  created:
    - docs/adr/0053-mermaid-source-default-rationale.md
  modified:
    - .planning/adr-categories.yaml ('0053' エントリ追加)
    - docs/adr/INDEX.md (pre-commit hook で自動再生成、Frontend・UI に 0053 行追加、Total 50)
    - frontend/src/components/MermaidBlock.tsx (冒頭コメントに 2 行追記、import 以下は無変更)
    - scripts/generate_adr_index.py (--check フラグ追加 — Rule 3 deviation)
decisions:
  - "D-01 確定 (Mermaid View OS hang はドキュメント化のみで解消) を ADR-0053 として明文化、恒久修正候補は v6.1+ spike に defer"
  - "Pitfall 6 厳守: MermaidBlock.tsx 冒頭コメントは 2 行 + ADR-0053 link のみ (ADR 要約コピペ禁止)"
  - "generate_adr_index.py に --check フラグを追加 (Rule 3) — plan acceptance criterion #6 を満たすため。既存 generate_mcp_artifacts.py --check と同じ drift 検査パターン"
metrics:
  duration_minutes: ~12
  completed: 2026-05-13
  tasks_completed: 2
  files_created: 1
  files_modified: 4
---

# Phase 39 Plan 02: Mermaid View OS hang をドキュメント化のみで解消 (UIFIX-01) Summary

UIFIX-01 (Mermaid View OS hang) の D-01 確定方針 = 「ドキュメント化のみ」を実装。'source' default 恒久化の根拠を ADR-0053 として起票し、MermaidBlock.tsx 冒頭コメントから 1-hop で読めるようにした。View default 復帰の本質調査は v6.1+ spike に defer。

## What was delivered

### Task 1: ADR-0053 起票 + adr-categories.yaml に Frontend・UI エントリ追加

**新規ファイル `docs/adr/0053-mermaid-source-default-rationale.md`** (55 行) — Frontend・UI カテゴリ ADR の 5 セクション構造を踏襲:

- **Context** — v5.0 期間中の OS-level hang 観測、現状コード `MermaidBlock.tsx:36` の source-default が暫定対応であること、`.planning/todos/pending/2026-04-16-mermaid-view-os.md` の根本原因候補 5 案を転記
- **Decision** — (1) `'source'` default 恒久化 (2) View モードは lazy on-demand のみ (3) 恒久修正候補は v6.1+ spike に defer (4) MermaidBlock.tsx 冒頭から本 ADR への pointer
- **Alternatives Considered** — iframe srcdoc / Web Worker / 描画 queue 制御 / `mermaid.renderAsync` (v11+ API) の 4 案を表形式で比較、それぞれの trade-off を 1-2 文で明記
- **Consequences** — Positive (hang 確実回避 + Monaco 即時提供) と Trade-offs (View ボタン 1 クリック必要、根本修正は v6.1+ 持ち越し)
- **Related** — ADR-0037 / ADR-0040 / `.planning/todos/pending/2026-04-16-mermaid-view-os.md`

**`.planning/adr-categories.yaml`**:

- `"0052"` 行の直後、`missing:` の直前に `"0053": { primary: "Frontend・UI" }` を 1 行追加 (secondary なし、Mermaid は純粋 Frontend カテゴリ)
- インデント・クォート・記法は既存行と完全一致

**Commit:** `fd0d13b` — `docs(39-02): add ADR-0053 (Mermaid Source default rationale)` (3 files changed; INDEX.md は pre-commit hook により同 commit 内で自動再生成された)

### Task 2: MermaidBlock.tsx 冒頭コメント 2 行追記 + INDEX.md 再生成

**`frontend/src/components/MermaidBlock.tsx`** — 冒頭コメント (L1-7) に空コメント行 + 2 行追記:

```
//
// Why source-default: View-default で複数 mermaid ブロック同時 render が OS-level hang
// を起こすため (Phase 39 / UIFIX-01)。恒久修正候補は ADR-0053 参照、v6.1+ spike 予定。
```

- 追記後の冒頭コメントブロック: L1-L10 (10 行、acceptance ≤ 11 行を満たす)
- L11 (blank) + L12 以降 (`import` 文以下) は完全無変更 — `git diff frontend/src/components/MermaidBlock.tsx` で `import` 以降に hunk なしを確認

**`docs/adr/INDEX.md`** — pre-commit hook が Task 1 commit 時点で既に再生成済 (Total `49 → 50`、`Frontend・UI` セクションに `[0053](0053-mermaid-source-default-rationale.md) | Mermaid View デフォルトを Source 固定とする (UIFIX-01) | 2026-05-13` 行)。本 task 中で `python3 scripts/generate_adr_index.py` を明示再実行し、出力が現状の INDEX.md と完全一致することを確認 (差分ゼロ)。

**`scripts/generate_adr_index.py`** — `--check` フラグを追加 (詳細は Deviations セクション)。

**Commit:** `c74eca7` — `docs(39-02): link MermaidBlock header to ADR-0053 + add --check to generate_adr_index.py` (2 files changed, 29 insertions)

## Verification

### Task 1 verify (plan の `<verify>` ブロックを実行)

```
test -f docs/adr/0053-mermaid-source-default-rationale.md && \
  grep -c '## Context' / '## Decision' / '## Alternatives' / '## Consequences' / '## Related' && \
  grep -cE '"0053":\s*\{\s*primary:\s*"Frontend・UI"' .planning/adr-categories.yaml
```

→ すべて 1 を返却、exit 0。

### Task 2 verify

```
grep -c 'ADR-0053' frontend/src/components/MermaidBlock.tsx                       # 1
grep -c 'UIFIX-01' frontend/src/components/MermaidBlock.tsx                       # 1
grep -cE '\[0053\]\(0053-mermaid' docs/adr/INDEX.md                               # 1
python3 scripts/generate_adr_index.py --check                                     # exit 0
```

→ `OK: docs/adr/INDEX.md is up to date.` exit 0。

### Acceptance criteria 全項目

- [x] `docs/adr/0053-mermaid-source-default-rationale.md` が存在 (55 行、5 セクション)
- [x] タイトル `# 0053. Mermaid View デフォルトを Source 固定とする (UIFIX-01)`
- [x] `**Status:** Accepted` を含む
- [x] Related に ADR-0037, ADR-0040, `2026-04-16-mermaid-view-os.md` の 3 リンク
- [x] `.planning/adr-categories.yaml` に `"0053": { primary: "Frontend・UI" }` 行
- [x] 同 YAML の `missing:` リストに `"0053"` は含まれない
- [x] MermaidBlock.tsx 冒頭に `ADR-0053` が 1 回、`UIFIX-01` が 1 回出現
- [x] 冒頭コメントブロックは 10 行 (acceptance ≤ 11)
- [x] INDEX.md の Frontend・UI セクションに `[0053](0053-mermaid-source-default-rationale.md)` 行
- [x] INDEX.md 冒頭 `**Total:** 50 件`
- [x] `python3 scripts/generate_adr_index.py --check` exit 0
- [x] `git diff frontend/src/components/MermaidBlock.tsx` の変更が L1-L10 範囲のみ (import 以降無変更)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `scripts/generate_adr_index.py` に `--check` フラグを追加**

- **Found during:** Task 2 verify ステップ準備中
- **Issue:** Plan 39-02 Task 2 の `<verify>` および acceptance criterion #6 は `python3 scripts/generate_adr_index.py --check` の exit 0 を要求する。しかし現状の `scripts/generate_adr_index.py` には `--check` フラグが未実装で、フラグ名引数で起動しても無視され常に INDEX.md を上書きする (drift 検査にならない)。同 plan の install-hooks.sh も実際には `--check` なしで実行している。
- **Fix:** `argparse` で `--check` フラグを追加。`--check` 指定時は INDEX.md を書き換えず、生成内容 vs 既存ファイルを文字列比較し、一致なら "OK: ... is up to date." を出力して exit 0、差分があれば DRIFT メッセージを stderr に出して exit 1。既存の `generate_mcp_artifacts.py --check` と同じ contract。
- **Files modified:** `scripts/generate_adr_index.py` (+22 行、`argparse` import 追加、`main()` を `--check` 分岐対応に書き換え)
- **Why this is Rule 3, not Rule 4:** 既存スクリプトに小さなフラグを 1 つ足すだけで、生成ロジック自体には一切手を入れていない。アーキテクチャ変更ではなく、plan の verify を成立させるための tooling 不足の埋め合わせ。
- **Commit:** `c74eca7` (Task 2 と同 commit)

## Threat Flags

なし — 本 plan は ADR ドキュメント + 冒頭コメント 2 行追記 + tooling のみで、production code path と attack surface は不変。`threat_model` 内 T-39-02-01 (ADR に機密情報を含めない) と T-39-02-02 (L9 以降不変) の両方を満たす:

- ADR-0053 本文は技術記録のみ (認証情報・user data なし)
- MermaidBlock.tsx の `git diff` は L8 付近に 3 行追加のみ、`import` 以降は変更なし

## Known Stubs

なし — 本 plan には UI レンダリング向けのデータ stub もハードコード placeholder も含まれない。

## Notes for follow-up plans

- **39-03 以降の Wave 1 並列 plan**: 本 plan は `frontend/src/components/MermaidBlock.tsx` 冒頭コメントのみを触っており、同ファイルの内部実装 (L36 `useState('source')`、`renderDiagram` 等) は無変更。他 plan が同ファイルの本体ロジックを触る場合のコンフリクトリスクは冒頭コメント部のみで限定的。
- **v6.1+ 仕込み**: ADR-0053 の Alternatives Considered で 4 案を列挙済。後の `/gsd-spike` セッションで `iframe srcdoc` から検証着手するのが Pitfall 観点 (開発負荷とリスク) で妥当。
- **patterns.md 更新**: CLAUDE.md の D-15 「新規 ADR 追加直後は patterns.md に手動追記」ルール対象だが、本 plan の `files_modified` には含めず scope 外として記録。次の Wave 完了時 or Phase 39 全体 closeout の際にまとめて反映する判断 (Pitfall 7 「polish phase を肥らせない」)。

## Self-Check: PASSED

- [x] `docs/adr/0053-mermaid-source-default-rationale.md` — FOUND
- [x] `.planning/adr-categories.yaml` modified — '0053' 行存在 (`grep` で確認)
- [x] `docs/adr/INDEX.md` — `[0053]` 行存在、Total 50
- [x] `frontend/src/components/MermaidBlock.tsx` — `ADR-0053` + `UIFIX-01` を冒頭 10 行内に含む
- [x] `scripts/generate_adr_index.py --check` — exit 0
- [x] commit `fd0d13b` — git log で確認
- [x] commit `c74eca7` — git log で確認
