---
created: 2026-04-02T04:14:22.102Z
title: Integrate LangGraph tool calling with async worker execution
area: api
files:
  - worker.py
---

## Problem

LLM にツールを提供する仕組みがない。LangGraph のお作法（`@tool` デコレータ / ToolNode）でツールを定義・提供したいが、ツールの実処理はワーカー内で動作させ、非同期処理ベースで実行できるようにしたい。

## Solution

LangGraph のツール機構を使いつつ、実処理をワーカー内に閉じ込める構成にする。

```
LLM → tool_calls → ToolNode
                     ↓
              ツール実体（Worker 内）
              非同期タスクとして実行
              ↓
              結果を ToolMessage として返却
              → LLM が続きを生成
```

- LangGraph の `@tool` / `ToolNode` / `bind_tools` でツール定義・グラフ結合は LangGraph のお作法に従う
- ツール実体は Worker 内で動作させる（HTTP 経由 / 直接呼び出し / 内部キュー等）
- 非同期実行をベースとする（`async def` ツール、または非同期ジョブとして投入）
- 既存の worker.py の処理タイプルーティング（routing facade todo）と組み合わせて設計する
- ツール一覧の管理・登録方法（動的ロード or 静的定義）も整理する
