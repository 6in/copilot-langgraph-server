# Phase 28: CodeAct パターンの実装 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 28-codeact-llm
**Areas discussed:** 実行環境とサンドボックス, グラフ設計とループ構造, エージェント統合とUI表示, 対応言語と制約

---

## 実行環境とサンドボックス

| Option | Description | Selected |
|--------|-------------|----------|
| worker コンテナ内サブプロセス | claude_code.py と同じパターン。worker コンテナ内で subprocess で python を起動 | ✓ |
| MCP ツールとして mcp-server で実行 | mcp-server コンテナ内で Python を実行。既存 MCP 基盤を活用 | |
| 専用 sandbox コンテナ | Docker Compose に sandbox サービスを追加。最も安全だが構成が複雑化 | |

**User's choice:** worker コンテナ内サブプロセス
**Notes:** 既存の claude_code.py パターンを踏襲。シンプルさ優先

| Option | Description | Selected |
|--------|-------------|----------|
| 最小限（タイムアウトのみ） | 実行時間制限のみ。200名社内利用なので実用性優先 | |
| 中程度（タイムアウト+メモリ+ファイルI/O） | 実行時間 + メモリ制限 + 一時ディレクトリでファイル操作制限 | ✓ |
| 厳格（seccomp/ネットワーク制限含む） | seccomp プロファイル、ネットワーク無効化、ファイルシステム制限 | |

**User's choice:** 中程度（タイムアウト+メモリ+ファイルI/O）

| Option | Description | Selected |
|--------|-------------|----------|
| 1回 30秒 | ループ 1 回あたり 30 秒 | |
| 1回 60秒（claude_code と同じ） | claude_code.py と同じ 60 秒 | ✓ |
| Claude に任せる | リサーチ結果を見て適切な値を決める | |

**User's choice:** 1回 60秒（claude_code と同じ）

---

## グラフ設計とループ構造

| Option | Description | Selected |
|--------|-------------|----------|
| MCP ツールとして実装 | execute_python MCP ツールを作成し、既存 ToolEnabledSubAgent の ReAct ループで呼び出す | ✓ |
| 専用 CodeAct グラフ | code_gen → execute → observe → decide の専用 StateGraph を構築 | |
| ハイブリッド | MCP ツール + 専用エージェントノード | |

**User's choice:** MCP ツールとして実装
**Notes:** 既存の ReAct ループで自然に CodeAct パターンが実現する

| Option | Description | Selected |
|--------|-------------|----------|
| 5 ステップ | コード実行は重いので少なめに | ✓ |
| 10 ステップ（既存と同じ） | 既存 ReAct ループと同じ上限 | |
| Claude に任せる | リサーチ結果を見て決める | |

**User's choice:** 5 ステップ

| Option | Description | Selected |
|--------|-------------|----------|
| stdout + stderr + exit_code | 標準的な実行結果フォーマット | ✓ |
| 上記 + 変数スナップショット | stdout/stderr に加えてローカル変数状態も返す | |
| Claude に任せる | 実装詳細をリサーチで決める | |

**User's choice:** stdout + stderr + exit_code

---

## エージェント統合とUI表示

| Option | Description | Selected |
|--------|-------------|----------|
| CodeAct 専用エージェント新規作成 | agents/codeact/AGENT.md を作成。tools: true + mcp_tools: [execute_python] | ✓ |
| 既存 general-assistant に追加 | general-assistant の mcp_tools に execute_python を追加 | |
| 両方（専用 + 汎用） | 専用エージェントを作りつつ、general-assistant にも execute_python を解禁 | |

**User's choice:** CodeAct 専用エージェント新規作成

| Option | Description | Selected |
|--------|-------------|----------|
| 通常テキスト（Markdown） | AI の応答にコードブロックと実行結果が Markdown で含まれる | ✓ |
| 専用コード実行パネル | Canvas のような分割レイアウト | |
| Claude に任せる | 実装詳細をリサーチで決める | |

**User's choice:** 通常テキスト（Markdown）
**Notes:** 既存の MarkdownMessage で対応。フロントエンド変更不要

---

## 対応言語と制約

| Option | Description | Selected |
|--------|-------------|----------|
| Python のみ | Python のみ対応。ツール名も execute_python で明確 | ✓ |
| Python + シェルコマンド | Python に加えて bash コマンドも実行可能 | |
| 複数言語（Python/JS/Shell） | 複数言語対応 | |

**User's choice:** Python のみ

| Option | Description | Selected |
|--------|-------------|----------|
| 制限なし | 標準ライブラリ + pip パッケージをそのまま使える | |
| 危険モジュールのみブロック | os.system, subprocess 等の危険な呼び出しをブロック | |
| ホワイトリスト方式 | 許可したモジュールのみインポート可能 | ✓ |

**User's choice:** ホワイトリスト方式

| Option | Description | Selected |
|--------|-------------|----------|
| コード内に埋め込み | MCP ツール内に ALLOWED_MODULES を frozenset で定義 | |
| 設定ファイルで管理 | config/sandbox_allowlist.yaml 等で管理 | ✓ |
| Claude に任せる | 実装詳細をリサーチで決める | |

**User's choice:** 設定ファイルで管理

---

## Claude's Discretion

- サブプロセスの具体的なメモリ制限値
- ホワイトリストのデフォルト許可モジュール一覧
- CodeAct エージェントのシステムプロンプト文言
- execute_python MCP ツールの引数設計
- 実行結果の文字数制限

## Deferred Ideas

None — discussion stayed within phase scope
