---
created: 2026-04-06T01:45:03.984Z
title: Gem モデルに知識フィールドを追加してプロンプトに埋め込む
area: ui
files:
  - app/api/models.py
  - app/api/routes/gems.py
  - app/graph/builder.py
  - frontend/src/components/GemsScreen.tsx
  - frontend/src/types.ts
---

## Problem

Gem には System Prompt しか持てないため、FAQや固定資料などの「知識」を
Gem に持たせることができない。
ユーザーが `knowledge`（補足知識・参照資料）テキストを Gem に登録し、
チャット時にそれをシステムプロンプトに自動的に埋め込んで欲しい。

## Solution

- バックエンド: `Gem` モデルに `knowledge: str = ""` フィールドを追加（DB マイグレーション必要）
- API: `GemCreate` / `GemUpdate` スキーマに `knowledge` を追加
- LangGraph グラフ側: Gem を使ったチャット時にシステムプロンプトを組み立てる際、
  `knowledge` が存在すれば `system_prompt + "\n\n## 知識\n" + knowledge` のように埋め込む
  （または別途 SystemMessage として追加する）
- フロントエンド:
  - `GemInfo` 型に `knowledge` を追加
  - GemsScreen の作成・編集フォームに Knowledge テキストエリアを追加
  - カード表示には knowledge は表示しない（詳細は編集フォームのみ）
