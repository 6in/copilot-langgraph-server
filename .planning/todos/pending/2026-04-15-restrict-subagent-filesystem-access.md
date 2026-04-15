---
created: 2026-04-15T14:12:00.000Z
title: SubAgent のローカルファイルシステムアクセスを制限する
area: auth
files:
  - agents/general-assistant/AGENT.md
  - app/orchestrator/tool_agent.py
  - app/orchestrator/agent.py
  - app/jobs/worker.py
---

## Problem

SuperChat 経由で `general-assistant` に「確認できるファイル一覧を教えて」と問いかけたところ、リポジトリ内のディレクトリ構成（`app/` `frontend/src/` `tests/` `agents/` `mcp_server/` `docs/adr/` `.planning/` `scripts/` `static/` `config/` `docker/` 等）と約 170 ファイル以上を把握している回答が返ってきた。

SubAgent がワーカーコンテナ内のローカルファイルシステムを自由に列挙・参照できている状態は、社内利用とはいえ明確なセキュリティリスク:

- 社内機密のコード・設計ドキュメント（ADR, .planning/）が AI 経由で漏洩しうる
- ユーザー入力次第で任意ファイルの中身を読み出される攻撃面になる
- `agents/*/AGENT.md` のシステムプロンプトや `.env` 系ファイルまで到達する恐れ

## Solution

SubAgent のツールセットから「ローカルファイル列挙・読み出し」系の機能を除外し、明示的に許可した MCP ツール以外で FS にアクセスできないようにする。

調査・対応候補:

1. `general-assistant` がどのツール経由で FS を見ているか特定
   - `ToolEnabledSubAgent` が `ctx["mcp_tools"]` から取り込んでいるツール一覧を確認
   - `agents/general-assistant/AGENT.md` の `tools:` / `mcp_tools:` フィールドを確認
   - LangChain 側の汎用 file tool が紛れていないか（`filesystem`, `read_file`, `list_directory` 等）
2. MCP サーバー (`mcp_server/`) が FS 系ツールを expose していないか確認
3. 不要な FS ツールをホワイトリストから削除
4. ReAct ループのシステムプロンプトでも「ファイル列挙・参照は禁止」を明示
5. regression test: SubAgent に FS 照会を投げたときにツール呼び出しが発生しないことを検証

優先度: **高**（セキュリティ起因、production 前に塞ぐべき）
