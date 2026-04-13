# 0022. Tavily Web Search と JSON ベースツール呼び出しのモデル互換性

**Date:** 2026-04-13  
**Status:** Accepted

## Context

Phase 22 では `web_search_stub` を Tavily API を使った本番ツールに差し替え、エージェントが
リアルタイム情報を取得して回答できるようにすることが目標だった。

`BoundChatCopilot` は JSON ベースの prompt engineering でツール呼び出しを実現している。
具体的には `TOOL_SYSTEM_PROMPT_TEMPLATE` をシステムプロンプトとして注入し、
モデルに `{"tool": "<name>", "args": {...}}` 形式の JSON のみで応答するよう指示する。
応答を `_try_parse_tool_call()` でパースして `AIMessage(tool_calls=[...])` に変換する設計。

UAT で 2 件の major ギャップが発覚した:

1. **モデルが内部知識で回答してツールを呼ばない** — "If no tool is needed, respond normally"
   という文言がモデルに逃げ道を与えていた（GPT-4.1 はトレーニング済みの Python 3.14
   情報を持っており、検索を必要と判断しなかった）
2. **GPT-4.1 がツール呼び出し JSON の出力を拒否する** — GitHub Copilot 経由の GPT-4.1 は
   MCP アーキテクチャに関する内部知識を持ち、「自分はバックエンドのツールを直接呼べない」
   と判断して JSON 出力を拒否、または JSON に説明文を混在させる

## Decision

1. **`TOOL_SYSTEM_PROMPT_TEMPLATE` をシンプルな JSON 指示形式に整理**: 大きなセクション
   (`## MANDATORY`, `## CITING SOURCES`) を排除し、1 ブロックの明快な指示にまとめた。
   リアルタイム情報が必要なケースでのツール呼び出しを促し、`source_urls` の引用を指示する。

2. **`general-assistant` を Claude Sonnet 4.6 で動作させる**: `AGENT.md` に
   `model: claude-sonnet-4-6` を明記（既定値）。Claude Sonnet 4.6 は
   `TOOL_SYSTEM_PROMPT_TEMPLATE` の JSON 指示に正しく従い、純粋な JSON ツール呼び出しを出力する。

3. **`_try_parse_tool_call` に Attempt 3 を追加**: モデルが JSON に説明文を混在させた場合
   （例: `{"tool": "web_search", ...}\n---\n申し訳ありませんが...`）でも、
   ブラケットカウント方式で JSON オブジェクトを抽出してパースできるよう拡張した。

4. **AGENT.md のツール使用ルール（日本語）は持たせない**: 英語の `TOOL_SYSTEM_PROMPT_TEMPLATE`
   と日本語の AGENT.md 両方にツール指示を持たせると、モデルが「動作解説モード」に入り
   ツールの呼び出し方を説明するだけになることが判明。指示は `TOOL_SYSTEM_PROMPT_TEMPLATE` 1 箇所に集約する。

5. **ツール実行中 UI インジケーター**: ContextVar → Redis キー → SSE ポーリングの
   チェーンでツール実行ステータスをフロントエンドにリアルタイム通知する実装を追加。

## Alternatives Considered

- **TOOL_SYSTEM_PROMPT_TEMPLATE を更に強化（MANDATORY セクション追加）**: 試みたが
  GPT-4.1 は逆に「アーキテクチャを知っているので呼べない」と説明するようになり逆効果だった。

- **AGENT.md にも日本語でツール指示を追加**: 実装済みだったが、二重の system message
  がモデルを混乱させることを確認。AGENT.md から削除した。

- **LangGraph callbacks でツール進捗通知**: `on_tool_start` コールバックで通知する
  方式も検討したが、arq worker と API サーバーが別プロセスのため Redis 経由の
  共有が必要。ContextVar + Redis の組み合わせで解決した。

- **GPT-4.1 向けの回避策**: モデルの自己認識を上書きする強制的なプロンプトは
  倫理的リスクがあり品質も不安定。Copilot API が提供するモデルの中で
  JSON 指示に素直に従う Claude Sonnet 4.6 を使う方が健全。

## Consequences

**正の影響:**
- Claude Sonnet 4.6 ベースのエージェントでは天気・ニュース等のリアルタイム情報への
  web_search 呼び出しが安定動作する
- `source_urls` が回答に引用され、情報源が明示される
- ツール実行中 UI インジケーター（`🔍 web_search を実行中: "query"`）でユーザーに
  処理状況がリアルタイムで伝わる
- `_try_parse_tool_call` の堅牢化により JSON 混在レスポンスでもツール実行が可能

**制約・注意点:**
- **GPT-4.1 (GitHub Copilot) は JSON ベースツール呼び出しに非対応**: JSON を出力しても
  説明文と混在させる、または出力を拒否する。BoundChatCopilot を使うエージェントは
  `model: claude-sonnet-4-6` (または Claude 系モデル) を使うこと。
- **モデルがトレーニング済み知識を持つ質問ではツールを呼ばない場合がある**: Python 3.14
  のような「モデルが知っている」情報は内部知識で答えてしまう。これは LLM の正常な
  挙動であり、プロンプトだけでは完全には制御できない。完全な強制には前処理でのキーワード
  マッチングや native function calling の導入が必要。
- **SSE ツール通知は arq worker と API が同じ Redis インスタンスを共有する前提**:
  Redis が分離される構成変更時は `push_tool_event` の保存先も見直すこと。
- **ContextVar は同一イベントループ内でのみ伝播する**: arq worker の複数ジョブが
  並行実行される場合、各ジョブの ContextVar は独立しているため問題ないが、
  スレッドプールを使う構成に変更した場合は注意が必要。
