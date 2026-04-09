---
created: 2026-04-08T12:36:35.365Z
title: Canvas アプリに iframe postMessage JSON-RPC API ブリッジを実装する
area: api
files:
  - docs/pre/iframe_app_enhanced.md
---

## Problem

Canvas アプリはシングル HTML ファイルの作成・プレビューのみで、HTML 内 JS から外部サービス（DB・AI・Web API）を呼び出す手段がなく、実用的なアプリを作れない。

## Solution

詳細仕様: `docs/pre/iframe_app_enhanced.md`

### アーキテクチャ概要

1. **表示側**: HTML アプリを `<iframe>` に入れた親フレームで表示する（直接表示ではない）
2. **通信**: iframe 内 JS → `postMessage` → 親フレーム → Redis → arq ワーカー → Redis → 親フレーム → `postMessage` → iframe
   - 既存の AI(LangGraph) 呼び出しと同じキュー方式
3. **プロトコル**: `iframe_app_api` 識別子付き JSON-RPC（method + params + id）

### 実装スコープ（初期）

**ワーカーサービス側 (`iframe_app_api` ルーター):**

- `QUERY` メソッド: SELECT 専用 DB クエリ
  - 入力: `{ pool_name, sql, user }`
  - 出力: `{ result: true, rows: [...] }`
  - DB プール設定は YAML ファイルから初期化時に読み込む
- `AI` メソッド: Copilot ワンショット AI 呼び出し
  - 入力: `{ model, prompt }`
  - 出力: `{ result: true, responseText: "..." }`

**フロントエンド側:**
- Canvas 表示コンポーネントを `<iframe>` ラッパーに変更
- Worker スレッドで postMessage ハンドラを実装
- iframe SDK（`canvasApi.query(...)` / `canvasApi.ai(...)`）を HTML に注入
