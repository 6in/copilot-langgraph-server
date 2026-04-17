---
name: SuperChat
description: Multi-agent orchestration with selectable agents
icon: "⚡"
agents:
  - code-reviewer
  - sql-analyst
  - general-assistant
  - codeact
---

# SuperChat

複数のスペシャリストエージェントをルーターが自動選択するマルチエージェントチャット。
ユーザーが明示的にエージェントを選択することもできます。

**利用可能なエージェント:**
- `code-reviewer` — コードレビュー・品質チェック
- `sql-analyst` — SQL クエリ作成・最適化
- `general-assistant` — 汎用アシスタント
- `codeact` — Python コード実行で問題を解決

**特徴:**
- OrchestratorGraph による自動ルーティング
- エージェントチップで手動選択も可能
- スレッドごとに会話履歴を保持
