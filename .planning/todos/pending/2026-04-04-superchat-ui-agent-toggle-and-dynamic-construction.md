---
created: 2026-04-04T01:22:44.519Z
title: スーパーチャット UI でエージェント選択トグルと動的構築
area: ui
files:
  - app/jobs/handlers/orchestrator_handler.py
  - app/api/models.py
  - app/api/routes/chat.py
  - frontend/src/components/ChatApp.tsx
  - frontend/src/hooks/useChat.ts
  - agents/
---

## Problem

現在の Super モードは RouterNode が自動でエージェントを選ぶだけで、ユーザーが利用するエージェントを指定する手段がない。またチャットとスーパーチャットが同一画面内のトグルで切り替わる UX になっている。

## Solution

以下の2点をセットで実装する:

**1. UI の入口を2つに分ける**
- `/app` (チャット): 現行のシンプルチャットそのまま
- `/app/super` (スーパーチャット): 専用ページ or サイドバータブで切替
  - 入力エリア上部にエージェント選択トグル（複数選択可）を表示
  - `GET /api/agents` で利用可能エージェント一覧を取得して表示

**2. 動的エージェント構築**
- `GET /api/agents` エンドポイント追加 — `agents/` ディレクトリを読んで名前・説明一覧を返す
- `POST /api/chat` の `agents[]` フィールド追加 — 選択済みエージェントのみを渡す
- `OrchestratorHandler` で `SubAgentRegistry.from_defs(agents_payload, github_token)` 対応
  — ディスク読み込みをスキップして直接インスタンス化

**アーキテクチャ上の根拠:**
グラフはすでにリクエストごと構築される設計 (Phase 9 実装済み)。`SubAgent` は `name, description, model, system_prompt, github_token` があれば直接作れる構造なので、ファイル読み込みのバイパスは実装コスト低。
