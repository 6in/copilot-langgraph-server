# 0004. Super-Agent サンプルをスタンドアロン実装し ChatCopilot を利用する

**Date:** 2026-04-03  
**Status:** Accepted

## Context

OrchestratorGraph + SubAgent + MenuDispatcher アーキテクチャの動作確認サンプルを実装する際、2 つの設計上の選択が必要だった。

**1. 実装場所:** メインアプリ (`app/`) に組み込むか、独立したサブプロジェクトとして実装するか。  
**2. LLM プロバイダー:** 仕様書 (`docs/pre/phase1_spec.md`) が指定する `ChatAnthropic` を使うか、プロジェクト標準の `ChatCopilot` を使うか。

仕様書 (`docs/pre/phase1_spec.md`) は `langchain_anthropic.ChatAnthropic` + `ANTHROPIC_API_KEY` を前提としたコードを定義していたが、本プロジェクトは `github-copilot-sdk` + Device Flow 認証を基盤としており、`ANTHROPIC_API_KEY` を持たないユーザーがスモークテストを実行できない問題があった。

## Decision

1. **スタンドアロン実装:** `super-agent-sample/` を独自の `pyproject.toml` / `.venv` を持つ独立サブプロジェクトとして実装。`app/` への依存を持たない。
2. **ChatCopilot を採用:** `langchain_anthropic` を除去し、`app/providers/copilot.py` の `ChatCopilot` を `super-agent-sample/src/chat_copilot.py` としてコピー。`CopilotAuthManager` も `app/auth/manager.py` から `super-agent-sample/src/auth_manager.py` としてコピー。
3. **全体を async 化:** `ChatCopilot` は `_generate()` を実装せず `ainvoke()` のみをサポートするため、呼び出しチェーン全体 (`main` → `dispatcher` → `graph` ノード) を `async/await` + `asyncio.run()` に変換。

## Alternatives Considered

**ChatAnthropic をそのまま使う**  
仕様書に忠実だが `ANTHROPIC_API_KEY` が必要になりスモークテストを実行できなかった（実際に試して失敗を確認）。プロジェクトの認証基盤と乖離するため採用しなかった。

**app/ に直接組み込む**  
最終的な統合先ではあるが、サンプルとしての動作確認フェーズでは `app/` の FastAPI / arq / PostgreSQL の複雑さが不要。独立させることで純粋なアーキテクチャ検証ができる。Phase 9 で統合予定。

**app/providers/copilot.py を直接 import する**  
`sys.path` に `app/` を追加する方法もあるが、スタンドアロン性を損なう。コピーを置く方が依存関係が明示的で、将来の SDK 変更に対して独立して対応できる。

## Consequences

**メリット:**
- `ANTHROPIC_API_KEY` 不要でスモークテストが実行可能
- `super-agent-sample/` が `app/` と完全に独立しており、単独でアーキテクチャを学習・改変できる
- 14 件のユニットテストが LLM をモックしており CI で実行可能

**デメリット / 落とし穴:**
- `ChatCopilot` と `CopilotAuthManager` が 2 箇所に存在するため、メインアプリ側の変更が自動的にサンプルに反映されない（意図的な分離）
- **`src/copilot.py` という名前は使えない:** `PYTHONPATH=src` 環境で `copilot.py` を置くと `github-copilot-sdk` の `copilot` パッケージをシャドウして `AttributeError: module 'copilot' has no attribute 'CopilotClient'` が発生する。ファイル名は `chat_copilot.py` など SDK 名と衝突しない名前にすること。
- **`MagicMock(name=x)` の罠:** Python の `MagicMock(name=x)` はモックの repr 文字列を設定するだけで `.name` 属性を設定しない。テストで `.name` を検証する場合は `mock.name = "foo"` と明示的に代入すること。
- **テストアサーションの陳腐化:** `github_token=` → `auth_manager=` 移行後、`test_registry.py` のアサーションが旧パラメータ名のまま残っており検証ギャップを生んだ。プロバイダー引数の変更時はテストアサーションの同期確認が必要。
