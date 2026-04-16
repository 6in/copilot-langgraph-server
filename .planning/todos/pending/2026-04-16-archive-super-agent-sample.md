---
created: 2026-04-16T00:00:00.000Z
title: super-agent-sample/ をアーカイブ（または削除）
area: general
files:
  - super-agent-sample/
---

## Problem

`.planning/reports/2026-04-16-cleanup-inventory.md` §2 を参照。
`super-agent-sample/` は Phase 8 時代の独立サンプル（214 MB、大半は `.venv/`）。本体 `app/orchestrator/` に実装が移行しており現在は参照されていない。ルートに放置されているとクローン時のサイズ・ファイル探索のノイズになる。

## Solution

1. まず `.venv/` を削除して軽量化
2. 残ったソースを `.planning/archive/super-agent-sample/` へ移動、または完全削除
3. 関連 ADR・Plan ドキュメントの参照が存在するか確認。参照が残る場合は「（旧実装。削除済み。git 履歴で参照）」等の注記を添える
4. `.gitignore` に `super-agent-sample/.venv/` が無ければ追加（残しておく場合）

削除派の判断材料: git log で十分追跡可能なので完全削除でも問題ない。
