# 0041. CodeAct は ReAct ループではなく直接実行方式を採用する

**Date:** 2026-04-18  
**Status:** Accepted

## Context

Phase 28 で CodeAct パターン（LLM がコードを生成・実行し結果を観察する推論ループ）を実装した。当初は既存の `ToolEnabledSubAgent` の ReAct ループ（LangGraph `tools_condition` による agent → ToolNode → agent サイクル）を使い、`execute_python` MCP ツールを呼ばせる設計だった。

しかし Copilot SDK 経由のモデル（gpt-4.1）がプロンプトベースのツール呼び出し JSON（`{"tool": "execute_python", "args": {"code": "..."}}`）に安定して従わないことが判明した。具体的には：

1. LLM がツール呼び出し JSON ではなく Markdown テキストで回答する（コードを実行せず「実行しました」と嘘をつく）
2. リトライ・フォールバック・プロンプト強化すべて効果なし
3. ReAct ループが recursion limit に到達してタイムアウト（Hello World で 150秒超）

## Decision

`CodeActSubAgent` を新設し、`ToolEnabledSubAgent` の ReAct ループを使わない直接実行方式を採用した。

フロー：
1. **LLM 呼び出し①** — ユーザー要求に対して Python コードを生成（```python ブロック）
2. **agent が execute_python を直接呼び出し** — LLM のツール呼び出し判断に依存しない
3. エラーなら LLM にフィードバックしてリトライ（最大5回）
4. **LLM 呼び出し②** — 実行結果をもとに最終回答を生成

MCP ツール（web_search, db_query 等）は `mcp_helper` ラッパーモジュールを通じて Python コード内から呼び出す。MCP サーバーに `/internal/call_tool` HTTP エンドポイントを追加し、サンドボックスのサブプロセスから `urllib.request` で直接アクセスする。

`AGENT.md` に `agent_type: codeact` を指定すると `SubAgentRegistry` が `CodeActSubAgent` を選択する。

## Alternatives Considered

1. **ToolEnabledSubAgent の ReAct ループをそのまま使う** — Copilot SDK モデルが JSON ツール呼び出しに従わないため断念。リトライ、フォールバック（コード抽出→合成 ToolCall）、プロンプト強化すべて試したが不安定だった。

2. **BoundChatCopilot に Markdown コードブロック自動変換を追加** — LLM が Markdown でコードを返した場合に `_try_parse_tool_call` で `execute_python` ToolCall に変換するフォールバックを実装。しかし LLM がコードブロックすら含まないケースが多発し、根本解決にならなかった。

3. **2段階リトライ（Phase 2 code-only request）** — 最初のテキスト応答後に「コードだけ書いて」と追加リクエスト。Phase 2 で tool_calls JSON が返る場合もあったが、一貫性がなく、追加の LLM 呼び出しでレイテンシも増大した。

4. **専用 StateGraph（generate → execute → observe → respond）** — 最も堅実だが実装コストが高い。CodeActSubAgent の直接実行方式で同等の効果が得られたため見送り。

## Consequences

**正の結果：**
- コード実行が 100% 確実（LLM の判断に依存しない）
- レスポンス時間が大幅改善（LLM 2回 + execute_python 1回で完結）
- mcp_helper 経由で MCP ツールを Python コード内から自由に組み合わせ可能
- MCP 通信が同一コンテナ内 localhost で高速（Worker 経由のコンテナ間通信を回避）

**負の結果：**
- `ToolEnabledSubAgent` と `CodeActSubAgent` の2つのエージェント実装が存在する（コード重複はないが概念が増える）
- mcp_helper は MCP サーバーの `/internal/call_tool` エンドポイントに依存（MCP サーバーダウン時にサンドボックスからのツール呼び出しが失敗）
- LLM がコードブロックを返さない場合のリトライ（「コードを書いて」と再要求）は1回だけ — それでもコードが返らなければテキスト応答になる

**注意事項：**
- `execute_python` のサンドボックスは mcp-server コンテナで実行される（worker ではない）
- `mcp_helper` の `urllib` と `mcp_helper` 自体が sandbox allowlist に追加されている
- AGENT.md の `model` フィールドは SuperChat モードではフロントエンド選択より優先される（別途 TODO で対応予定）
