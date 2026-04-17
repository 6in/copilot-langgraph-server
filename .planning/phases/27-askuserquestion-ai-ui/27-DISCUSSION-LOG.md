# Phase 27: AskUserQuestion の実装 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 27-askuserquestion-ai-ui
**Areas discussed:** 質問パネルの表示位置, バックエンド統合方式, 対応アプリ範囲, 回答後の履歴表示

---

## 質問パネルの表示位置

| Option | Description | Selected |
|--------|-------------|----------|
| メッセージ内埋め込み (推奨) | AI バブル内に QuestionPanel を表示。チャット履歴と一体化 | |
| 入力エリア置換 | テキスト入力欄を QuestionPanel に置き換える（work/uaw パターン） | ✓ |
| Claude に任せる | 技術的な制約と UX のバランスで最適な方式を選択 | |

**User's choice:** 入力エリア置換
**Notes:** 自動的に入力エリアの高さが調整される

| Option | Description | Selected |
|--------|-------------|----------|
| 無効化 (推奨) | 質問が未回答の間、入力欄をグレーアウト | ✓ |
| 常時有効 | 質問があっても自由にテキスト入力できる | |

**User's choice:** 無効化 (推奨)

---

## バックエンド統合方式

| Option | Description | Selected |
|--------|-------------|----------|
| system prompt 駆動 (推奨) | `<ask_user_question>` タグの JSON フォーマットを指示 | ✓ |
| 専用 API エンドポイント | バックエンドが質問を検出して構造化 JSON を返す | |
| Claude に任せる | 技術的なトレードオフで最適を判断 | |

**User's choice:** system prompt 駆動 (推奨)

| Option | Description | Selected |
|--------|-------------|----------|
| テキスト化して通常送信 (推奨) | 回答を「質問：回答」形式のテキストに変換して POST /api/chat | ✓ |
| 構造化 JSON で送信 | 回答を JSON オブジェクトとして専用エンドポイントに送信 | |

**User's choice:** テキスト化して通常送信 (推奨)

---

## 対応アプリ範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 全アプリ一律 (推奨) | Chat / SuperChat / GemChat / CanvasChat / DebateChat 全てで有効 | ✓ |
| SuperChat のみ先行 | まず SuperChat で検証し、他アプリには次フェーズで展開 | |
| SuperChat + Chat | 主要 2 アプリで先行 | |

**User's choice:** 全アプリ一律 (推奨)

| Option | Description | Selected |
|--------|-------------|----------|
| 共通ベース (推奨) | LangGraphHandler / OrchestratorHandler の共通システムプロンプトに追加 | ✓ |
| AGENT.md レベル | 各 AGENT.md に質問プロトコルを記載 | |
| Claude に任せる | 技術的に最適な注入レベルを判断 | |

**User's choice:** 共通ベース (推奨)

---

## 回答後の履歴表示

| Option | Description | Selected |
|--------|-------------|----------|
| ロック済みパネル (推奨) | 回答済みのパネルを半透明・チェックマーク付きで残す | |
| テキスト変換 | 回答後は「質問：回答」テキストとしてユーザーバブルに表示 | ✓ |
| 両方表示 | ロック済みパネル + ユーザー回答テキストの両方を履歴に表示 | |

**User's choice:** テキスト変換
**Notes:** 質問の内容とその回答を、テキストにして送信するのでそれがメッセージバブルに表示されていればよい。いわば普通のユーザーからのメッセージと同じ

| Option | Description | Selected |
|--------|-------------|----------|
| テキストで復元 (推奨) | 通常のマークダウンメッセージとして表示。追加実装不要 | ✓ |
| パネル復元 | 過去の質問メッセージを検出してロック済み QuestionPanel を再構築 | |

**User's choice:** テキストで復元 (推奨)

---

## Claude's Discretion

- QuestionPanel の TypeScript 化・スタイリング詳細
- parseJobResult での ask_user_question 検出ロジックの具体的実装
- system prompt への質問プロトコル追記の文言調整

## Deferred Ideas

None — discussion stayed within phase scope
