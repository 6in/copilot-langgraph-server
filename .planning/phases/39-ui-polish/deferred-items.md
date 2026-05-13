# Phase 39 — Deferred Items

本 phase の plan 実行中に発見された、scope 外の小バグ・改善案を記録する。
D-12 上限ポリシーに従い、確定リスト (D-07..D-11) 以外で発見された項目はここに積み、v6.1+ で観察ベース再評価する。
同一ファイル・同一テストスイートを触る際の trivial fix も無条件で拾わず本ファイルに列挙してから判断する。

**最終 triage (2026-05-13, Plan 39-09 Task 3):** エントリ総数 **1 件** (Pitfall 7 上限 10 件 ≫ 1 件で抵触なし)。本 phase 開始時の `bun install` 再計測で対象 4 件は実態 0 件と確定したため、Pattern B 含む全 5 パターン scope 内完遂と整合的に v6.1+ 観察マターとして残置。Phase 39 close 後の handover として STATE.md Hand-offs to next phases に記載しない (理由: 観察ベースで再発しない見込み、再発時のみ v6.1+ で再 triage)。

---

## Plan 39-05 で発見された TS error 残り 4 件 (scope 外)

- **File:** frontend/src/components/MermaidBlock.tsx (html-to-image 解決 1 件 + implicit any 3 件 — RESEARCH.md L17 で当初観測)
- **Error / 由来:** D-08 scope (bulkRemoveThreads 6 + TS2459 Theme 1 = 7 件) 解消後に残存し得ると想定されていた scope 外の TS error。
  - html-to-image 解決 1 件: `node_modules` 内 `html-to-image` 型解決不能 (frontend/package.json に記載あり、docker compose build frontend または bun install で再 install 必要)
  - MermaidBlock implicit any 3 件: callback / params の型注釈不足、本来 explicit any もしくは具体型を付けるべき箇所
- **本 plan で扱わない理由:** CONTEXT.md D-08 が明示的に scope を 7 件と定義、D-12 上限ポリシーに従い「ついで修正」を抑制。
- **本 plan 実行時点での実測:** Plan 39-01 開始時の `bun install` で node_modules が再構築されたため、BASELINE.md L99-101 のとおり本 phase 開始時点では **7 件のみ**観測。Plan 39-05 Task 1 完了後の `bun x tsc -b --force` は **0 件** (D-08 確定 7 件解消、本 phase 開始時点で 4 件は既に消えていた)。RESEARCH.md L17 の追加 4 件は node_modules permission 由来 / 未 install 由来と確定。
- **いつ取り上げるか:** v6.1+ で観察ベース再評価。html-to-image は build re-install で自動解消する可能性大、MermaidBlock implicit any は Mermaid 関連 spike (UIFIX-01 defer 案件) と同時に対応するのが効率的。再発した場合は再 install / tsc 実行コマンド一覧 (Plan 39-01 Task 1 BASELINE 計測ログ) を参照する。

---
