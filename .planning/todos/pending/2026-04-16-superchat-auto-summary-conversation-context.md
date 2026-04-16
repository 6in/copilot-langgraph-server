---
created: 2026-04-16T03:15:00.000Z
title: SuperChat 自動サマリモード — 会話文脈を LLM 応答内で圧縮・引き継ぎ
area: api
files:
  - app/orchestrator/agent.py
  - app/orchestrator/tool_agent.py
  - app/orchestrator/graph.py
  - app/orchestrator/state.py
---

## Problem

SuperChat の SubAgent は毎ターン `state["input"]`（今回のプロンプト）しか受け取らず、過去の会話文脈を持たない。通常チャットは LangGraph checkpointer で全履歴を累積するが、SuperChat は SubAgent 呼び出し時にリセットされる。結果として「さっきの続き」「それについて詳しく」等の文脈依存リクエストに対応できない。

全履歴を渡すとプロンプトが肥大化し、Copilot SDK のタイムアウト (120s) を超過するリスクがある。要約用に別途 LLM を呼ぶと Copilot の回数課金が増える。

## Solution

**自動サマリモード（トグル ON/OFF）** を導入し、追加の LLM 呼び出しなしで会話文脈を圧縮・引き継ぐ:

### 仕組み

1. **応答にサマリを埋め込む**: SubAgent の system prompt に「応答の末尾に `<!-- summary: ... -->` で会話サマリを付与せよ」と指示
2. **次ターンでサマリを注入**: 前回の応答からサマリタグを抽出し、次の SubAgent 呼び出し時のプロンプトに `=== 過去の会話サマリ ===` として挿入
3. **フロントで非表示**: `<!-- summary: ... -->` を MarkdownMessage でストリップして表示しない
4. **AgentState に保持**: `state["conversation_summary"]` フィールドを追加し、checkpointer で永続化

### プロンプト設計案

```
[System] あなたは {agent_name} です。{system_prompt}

自動サマリモードが有効です。応答の末尾に以下のフォーマットで
会話のサマリを必ず付与してください:
<!-- summary: ここに会話の要点を 200 文字以内で記述 -->

[User]
=== 過去の会話サマリ ===
{前ターンの summary、初回は「なし」}
=== ユーザーの質問 ===
{state["input"]}
```

### トグル制御

- UI: SuperChat ヘッダーに「自動サマリ」トグルスイッチ
- API: `auto_summary: bool` を job payload に追加
- SubAgent: `auto_summary=True` 時のみサマリ指示を system prompt に注入

### 懸念と対策

| 懸念 | 対策 |
|------|------|
| LLM がサマリ生成を忘れる | フォールバック: サマリが無ければ前回のサマリをそのまま引き継ぎ |
| フォーマット崩れ | `<!-- summary: ... -->` より ````json {"summary": "..."}``` ` の方が安定する可能性 — 要検証 |
| サマリ品質の劣化（ターン増加） | サマリ上限を 300 文字に設定し、古い情報は自然に落ちる設計 |
| Copilot 回数課金 | 追加 LLM 呼び出しゼロ — 応答生成と同時にサマリも生成 |
