---
created: 2026-04-13T13:03:10.290Z
title: 全エージェント共通の現在時刻ツールを追加しプロンプトに時刻を自動注入する
area: api
files:
  - mcp_server/tools/stubs.py
  - app/jobs/handlers/base.py
  - app/orchestrator/agent.py
---

## Problem

エージェント（SubAgent / ToolEnabledSubAgent）が現在の日時を知る手段がない。
日付や時刻に関する質問に対して不正確な回答をしたり、時刻依存のタスク（スケジュール確認・期限計算など）を正しく処理できない。
また、プロンプト送信時に現在時刻が含まれていないため、モデルが文脈として時刻を把握できない。

## Solution

### 1. MCP ツール `get_current_datetime` を追加

`mcp_server/tools/stubs.py` に `get_current_datetime` ツールを追加する。
- 引数なし
- 戻り値: ISO 8601 形式の現在日時（タイムゾーン付き）＋ 曜日・ロケール情報
- 全エージェントが MCP 経由で利用可能になる

### 2. プロンプトへの時刻自動注入

チャットリクエスト処理時（`TaskHandler.run()` または LangGraph グラフ呼び出し前）にシステムプロンプトの先頭、もしくはユーザーメッセージの前に現在日時を付加する。
例: `[現在時刻: 2026-04-13 13:00 JST (月曜日)]`

注入箇所候補:
- `app/jobs/handlers/base.py` の共通前処理
- `app/orchestrator/agent.py` の `SubAgent.invoke()` 内
