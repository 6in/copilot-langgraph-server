# Documentation Index — Copilot LangGraph Chat

このプロジェクトのドキュメントを「読む順番」で並べた入り口。最初にここを読めば、自分の目的に合った次の 1 ファイルにたどり着けるよう構成している。

> **対象読者:** 社内 200 名規模のエンドユーザーと、本リポジトリに新規参画する開発者の両方。
> **アプリ呼称:** Chat / SuperChat / Gems / Canvas / DebateChat — 詳細は [apps-guide.md](./apps-guide.md)。

---

## 1. はじめて触る人 (ユーザー)

> ログインして「何ができるか」を 5 分で把握したい場合。

1. **[../../README.md](../../README.md)** — プロジェクト概要・5 アプリ一覧・セットアップ
2. **[apps-guide.md](./apps-guide.md)** — どのアプリをいつ使うか / 判断フローチャート / 典型ユースケース
3. **[agents.md](./agents.md)** — SuperChat で選べるエージェントとそれぞれの得意分野
4. **[tools-for-users.md](./tools-for-users.md)** — AI が裏で使えるツール (Web 検索 / DB クエリ / ファイル抽出 等) の利用者視点ガイド

## 2. 自分用の AI 設定を作りたい人 (パワーユーザー)

> 既存アプリでは足りず、専用の指示書付き AI を用意したい場合。

1. [apps-guide.md § Gems](./apps-guide.md#gems) — Gem (システムプロンプト + 任意 knowledge) の作り方
2. [agents.md § エージェント vs Gem の違い](./agents.md#エージェント-vs-gem-の違い) — 内蔵 SubAgent と Gem の使い分け
3. [apps-guide.md § Canvas](./apps-guide.md#canvas) — HTML/JS で動くミニアプリ (Canvas App) を AI に作らせる

## 3. 仕組みを理解したい人 (開発者・運用者)

> リポジトリにコードを書く / 障害調査 / 機能追加を担当する場合。

1. **[../../CLAUDE.md](../../CLAUDE.md)** — リポジトリの設計原則と AI 協業ガイド (Architecture セクション必読)
2. **[../archi/sequence.md](../archi/sequence.md)** — チャット送信〜SSE 完了通知までのシーケンス図
3. **[../archi/process.md](../archi/process.md)** — Docker Compose 上のプロセス相関図
4. **[../nginx.md](../nginx.md)** — リバースプロキシ配下デプロイ時の URL プレフィックス処理
5. **[../mcp-tools.md](../mcp-tools.md)** — MCP ツール仕様 (自動生成、`config/mcp_tools.yaml` が SSoT)

## 4. 拡張する人 (機能追加担当)

> 新規ツール・エージェント・設計判断を追加する場合。

1. **[../mcp-tool-add-manual.md](../mcp-tool-add-manual.md)** — MCP ツール追加手順 (推奨: `/add-mcp-tool` スラッシュコマンド)
2. **[../adr/INDEX.md](../adr/INDEX.md)** — Architecture Decision Records のカテゴリ別索引
3. **[../../.planning/patterns.md](../../.planning/patterns.md)** — ADR 由来のパターンカタログ (設計判断の前に参照)
4. **[../trace-query-recipes.md](../trace-query-recipes.md)** — observability trace ログの SQL クエリ集 (Phase 31)

## 5. observability / 運用調査

> 本番でユーザーが「動かない」と言ってきたとき。

1. [../trace-query-recipes.md](../trace-query-recipes.md) — agent_traces / audit_logs テーブルを使った調査クエリ
2. [../phase-31-integration-check.md](../phase-31-integration-check.md) — observability 基盤の実装範囲
3. [../../CLAUDE.md § Chrome DevTools MCP](../../CLAUDE.md#chrome-devtools-mcp) — フロントエンド側の検証手順

---

## 索引: ファイル種別マップ

| ファイル | 種別 | 編集可否 |
|---------|------|---------|
| `README.md` | プロジェクト概要 (ユーザー + 開発者の最初の入り口) | 手書き |
| `docs/getting-started/index.md` | 本ファイル (reading order) | 手書き |
| `docs/getting-started/apps-guide.md` | 5 アプリの判断フロー + 典型ユースケース | 手書き |
| `docs/getting-started/agents.md` | SubAgent カタログ (利用者視点) | 手書き |
| `docs/getting-started/tools-for-users.md` | MCP ツール利用者視点ガイド | 手書き |
| `docs/mcp-tools.md` | MCP ツール技術仕様 | **自動生成** (`scripts/generate_mcp_artifacts.py`) |
| `docs/mcp-tool-add-manual.md` | MCP ツール追加手順 | 手書き |
| `docs/nginx.md` | nginx URL プレフィックス strip の仕組み | 手書き |
| `docs/archi/sequence.md` | シーケンス図 (Mermaid) | 手書き |
| `docs/archi/process.md` | プロセス図 (Mermaid) | 手書き |
| `docs/trace-query-recipes.md` | observability クエリ集 | 手書き |
| `docs/phase-*.md` | phase 別の integration check / spike note | 手書き (履歴扱い、最新仕様の真実源ではない) |
| `docs/adr/NNNN-*.md` | Architecture Decision Records | 手書き |
| `docs/adr/INDEX.md` | ADR カテゴリ別索引 | **自動生成** (pre-commit hook) |

> **編集可否について:** 「自動生成」のファイルを直接書き換えると pre-commit hook が drift を検知して commit がブロックされる (Phase 30)。修正は SSoT の YAML や ADR ファイル本体に対して行うこと。

---

## このドキュメントの位置づけ

このインデックスは **「最初に読むファイル」を一覧にした道しるべ** であり、各ドキュメントの内容は要約しない。要約は重複と陳腐化の元になるため、本体ファイルを直接読みに行ってほしい。

新規ドキュメントを追加した際は、上記の **読む順番のいずれかのセクション** か **索引テーブル** に必ず追記すること (孤立した md ファイルは存在しないことが目標)。
