---
created: 2026-04-02T05:03:13.775Z
title: Investigate Agent-Skills integration mechanism
area: general
files: []
---

## Problem

`スキル名/SKILL.md` の仕組みを LangGraph のグラフ内でツールとして利用できるか調査が必要。
Claude Code のスキルとしてではなく、**LangGraph エージェントがスキルを呼び出せる仕組み**を作れるかが焦点。

具体的には:
- `SKILL.md` に定義されたスキルを LangGraph の Tool として登録できるか
- LangGraph のノード（エージェント）がスキルを選択・実行できるか
- スキルの入出力を LangGraph の State に組み込める設計にできるか

## Solution

1. `SKILL.md` のフォーマットと定義可能な情報を把握する
2. LangGraph の `@tool` デコレータや `StructuredTool` でスキルをラップできるか検討する
3. スキルのディスカバリー（ファイルスキャン → ツール登録）の仕組みを設計する
4. サンプルスキルを作成し、LangGraph グラフ内で呼び出しをテストする
