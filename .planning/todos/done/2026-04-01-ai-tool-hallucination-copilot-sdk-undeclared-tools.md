---
created: 2026-04-01T00:31:49.705Z
title: AI ツール自己申告によるハルシネーションを防止する
area: api
files:
  - app/providers/copilot.py
  - app/graph/builder.py
---

## Problem

チャット UI でユーザーが「CLAUDE.md を読んで」と指示したところ、AI が「表示しました」と繰り返しつつファイル内容を一切返さなかった。

根本原因は 2 層ある：

1. **Copilot SDK が tool を自己申告する** — `PermissionHandler.approve_all` を渡した `create_session` により、SDK がモデルに対して bash/git/view/edit/web_fetch/sql/grep/glob 等のツール一覧を提示している可能性がある（Copilot Agent SDK のビルトインツール）。
2. **LangGraph 側にツールが配線されていない** — `app/graph/builder.py` の `chatbot_node` は `ToolNode` を持たず、`send_and_wait` の返り値 `response.data.content`（テキストのみ）しか取り出していない。結果として、モデルはツールを呼んだつもりで返答するが実行結果は一切存在しない。

チャット DB の最新スレッドで確認済み（18 メッセージ中、ファイル内容ゼロ）。

## Solution

選択肢 A — **ツールを正しく配線する**（フル対応）
- Copilot SDK のツール呼び出しループを `ChatCopilot._agenerate` 内で処理し、実行結果をフィードバックする
- または LangGraph `ToolNode` に read_file / bash 等を実装し、Copilot をプレーン LLM として使う

選択肢 B — **ツール自己申告を無効化する**（最小対応）
- `PermissionHandler` を `deny_all` または `PermissionHandler(lambda _: False)` に変更し、SDK がモデルにツールを提示しないようにする
- モデルに「ツールなし・テキスト回答のみ」と明示する SystemMessage を追加する

短期: 選択肢 B でハルシネーションを止める → 選択肢 A でツールを段階的に追加する
