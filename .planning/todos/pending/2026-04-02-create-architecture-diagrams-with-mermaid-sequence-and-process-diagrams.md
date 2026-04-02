---
created: 2026-04-02T03:32:08.547Z
title: Create architecture diagrams with Mermaid sequence and process diagrams
area: docs
files:
  - docs/archi/
---

## Problem

システムの処理フローとプロセス構成を視覚的に示すドキュメントがない。コードを読まなくても全体像を把握できる図が欲しい。

## Solution

`docs/archi/` ディレクトリに以下の Mermaid.js 図を Markdown ファイルとして作成する:

1. **シーケンス図** (`sequence.md`) — ユーザーがメッセージを送信してから AI レスポンスが返るまでの処理フロー
   - ブラウザ → FastAPI → Redis Worker → LangGraph → Copilot SDK → GitHub Copilot
   - 認証フロー（Device Flow）も含める
   - SSE / Polling による非同期レスポンス配信

2. **プロセス構成図** (`process.md`) — docker-compose ベースのサービス構成
   - サービス: app（FastAPI）、worker（Redis Worker）、redis、postgres
   - ポートマッピング、ボリューム、依存関係を含める
   - Mermaid `graph` または `C4Context` / `flowchart` を使用
