---
created: 2026-04-06T01:45:03.984Z
title: Gem モデルに説明フィールドを追加してリスト表示を改善する
area: ui
files:
  - frontend/src/components/GemsScreen.tsx
  - app/api/models.py
  - app/api/routes/gems.py
---

## Problem

GemsScreen の Gem カードに `system_prompt` の内容がそのまま表示されているため、
長いプロンプトがリストを占有して見づらい。
Gem の目的を一言で説明する `description`（短い説明文）フィールドが必要で、
カードにはプロンプト本文ではなく説明を表示すべき。

## Solution

- バックエンド: `Gem` モデルに `description: str = ""` フィールドを追加（DB マイグレーション必要）
- API: `GemCreate` / `GemUpdate` スキーマに `description` を追加
- フロントエンド:
  - `GemInfo` 型に `description` を追加
  - GemsScreen カードの表示を `system_prompt` → `description` に切り替え
  - 作成・編集フォームに Description 入力欄を追加
