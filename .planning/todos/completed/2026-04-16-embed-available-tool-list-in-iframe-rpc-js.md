---
created: 2026-04-16T07:35:00.000Z
title: 利用可能ツール一覧を iframe-rpc.js に埋め込み、スキル化する
area: tooling
files:
  - static/js/iframe-rpc.js
  - config/mcp_tools.yaml
  - app/api/main.py
---

## Problem

Canvas アプリから `call('ping', {})` のように MCP ツールを呼び出しても `IframeRpcHandler` が `QUERY` / `AI` しかサポートしておらず `Unknown method` になる。Canvas アプリ開発者がどのツールが利用可能かを知る手段もない。

## Solution

2 つの問題を解決:

### 1. iframe-rpc.js にツール一覧を埋め込む

`config/mcp_tools.yaml` のツールカタログを読み取り、`iframe-rpc.js` の先頭にコメントまたは定数として埋め込む:

```js
// Available tools (auto-generated from mcp_tools.yaml):
// - ping: MCP サーバーのヘルスチェック
// - web_search: Tavily 経由でリアルタイム Web 検索を実行
// - db_query: PostgreSQL に対して SELECT クエリを実行
// - claude_code: Claude Code CLI をサブプロセスとして実行 [privileged]
// - get_current_datetime: 現在の日時を JST で返す
export const AVAILABLE_TOOLS = ['ping','web_search','db_query','claude_code','get_current_datetime'];
```

### 2. スキル化（自動更新）

`mcp_tools.yaml` を変更した際に iframe-rpc.js のツール一覧を自動更新するスクリプト or pre-commit hook を用意:

- `scripts/sync-tool-list-to-js.py` — yaml を読んで js を更新
- または Claude Code スキル (`/sync-tools`) として登録
- pre-commit hook で `mcp_tools.yaml` の変更を検出したら自動実行

### 3. IframeRpcHandler の MCP ツール転送（別 todo 検討）

`call(method, params)` で任意の MCP ツールを呼べるよう `IframeRpcHandler` に MCP ツール転送ロジックを追加。ただしセキュリティ面（privileged ツールの制限等）の設計が必要なので、本 todo ではツール一覧の埋め込みとスキル化に絞る。
