---
created: 2026-04-02T05:03:13.775Z
title: Investigate Agent-Skills integration mechanism
area: general
files: []
---

## Problem

Agent-Skills の仕組みをこのプロジェクトに組み込めるか調査が必要。具体的には、`スキル名/SKILL.md` というファイルを配置したときに、Claude Code がそれをスキルとして認識し、プロンプトの実行コンテキスト内でそのスキルが利用できるのかを確認する。

現状、GSD ワークフローのようなスキルシステムが Claude Code にビルトインされているが、このプロジェクト固有のカスタムスキル（例: Copilot SDK 操作、LangGraph グラフ管理など）を同様の仕組みで定義・実行できるかは未調査。

## Solution

1. Claude Code の Agent-Skills ドキュメントを調査する
2. `スキル名/SKILL.md` のファイル構造・フォーマット要件を確認する
3. プロジェクトルートまたは `.claude/` 配下に配置した場合の動作を検証する
4. 実際にサンプルスキルを作成してテストする
