---
created: 2026-04-15T00:00:00.000Z
title: Canvas アプリから呼び出す AI リクエストにモデル指定機能を追加する
area: api
files:
  - app/orchestrator/apps.py
  - app/jobs/handlers/langgraph_handler.py
---

## Problem

Canvas アプリから iframe RPC 経由で呼び出す AI リクエストのモデルが固定されており、
用途に応じて軽量モデル（Haiku）や高性能モデルを使い分けることができない。
Canvas アプリの性質によって必要な推論能力が異なるため、コスト・速度のバランスを取れない。

## Solution

Canvas アプリの設定（または iframe RPC リクエストのパラメータ）にモデル指定フィールドを追加する。

- デフォルト: Haiku（軽量・高速・低コスト）
- 上書き可能: アプリ設定 or リクエスト時に `model` パラメータで指定
- 候補: `haiku` / `sonnet` / `opus` などのエイリアスで指定し、内部で実際のモデル ID に解決する

実装箇所の候補:
- `app/orchestrator/apps.py` — Canvas アプリ設定スキーマに `default_model` フィールドを追加
- `app/jobs/handlers/langgraph_handler.py` — ChatCopilot 初期化時にモデルを注入
