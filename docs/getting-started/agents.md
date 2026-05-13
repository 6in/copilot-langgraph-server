# Agents Catalog — SuperChat で選べるエージェント

SuperChat と Gem チャットで使われる「専門家エージェント」一覧。利用者視点の使い分けと、開発者視点での `AGENT.md` 規約をまとめた。

> **対応アプリ:** SuperChat (`apps/superchat/APP.md` の `agents:` に列挙されたものから自動ルーティング)。Gem チャットは Gem のシステムプロンプトのみで動くため、エージェントとは別系統。

---

## エージェント一覧

| エージェント | アイコン色 (UI) | 得意分野 | 使えるツール | モデル | 種類 |
|-------------|----------------|---------|-------------|--------|------|
| **code-reviewer** | (チップ色マップ) | Python / JS / TS の静的解析・リント・フォーマット指摘 | — (現状ツールなし) | claude-opus-4-6 | folder |
| **sql-analyst** | (チップ色マップ) | SQL クエリの実行計画解説・最適化提案 | — | claude-sonnet-4-6 | folder |
| **general-assistant** | (チップ色マップ) | 雑談・要約・翻訳・調べごとなど汎用対応 | `web_search` / `ping` / `db_query` / `attachments_list` / `attachments_extract` | claude-sonnet-4-6 | folder+tools (ReAct) |
| **codeact** | (チップ色マップ) | Python コードを実際に書いて実行し、結果を観察して答える | `execute_python` | gpt-4.1 | codeact (Plan → 1 回実行) |

> UI のエージェントチップ色は `frontend/src/utils/agentColor.ts` でマッピングしている。

---

## エージェント別ガイド

### code-reviewer — コードレビュー

**得意なクエリ:**
- 「以下の Python コード、レビューして (重大度別に)」
- 「この React コンポーネント、anti-pattern ないかチェックして」
- 「TypeScript の型定義、改善点ある？」

**苦手 / 対象外:**
- テスト実行・デプロイ・DB 操作 (`tools:` 宣言なし、コード生成ではなく指摘のみ)

**裏側:** モデル `claude-opus-4-6`。AGENT.md の system prompt で「指摘は error / warning / info の重大度付きで箇条書き」を強制。

### sql-analyst — SQL 最適化

**得意なクエリ:**
- 「この SELECT 文、インデックスは効いてる？」
- 「JOIN を `EXISTS` に書き換える価値ある？」
- 「実行計画 (EXPLAIN ANALYZE 出力) を読み解いて」

**苦手 / 対象外:**
- データ挿入・マイグレーション実行・スキーマ変更 (実行系はサポート外、分析と提案のみ)

**裏側:** モデル `claude-sonnet-4-6`。インデックス活用 / JOIN 効率 / サブクエリ / 実行計画の 4 観点で改善提案。

### general-assistant — 汎用アシスタント

**得意なクエリ:**
- 「議事録 (添付) を 5 行で要約して」
- 「最新の LangGraph の breaking change を Web で調べて」
- 「`users` テーブル、何件ある？」(db_query 経由)

**特徴:**
- **添付ファイル対応:** `attachments_list` / `attachments_extract` が使えるので、PDF / Office ファイルを聞き取り対象にできる。「`sample.pdf` の内容を教えて」と言われたら推測せず必ず `attachments_extract` を呼ぶ規約 (AGENT.md に明記)
- **Web 検索対応:** `web_search` 経由で Tavily に問い合わせ
- **DB 参照:** `db_query` で SELECT クエリのみ実行可能 (`db_pools.yaml` のプール名指定)
- **ヘルスチェック:** `ping` で MCP サーバー疎通確認

**裏側:** ReAct ループ (agent → ToolNode → agent → END) でツール呼び出しと推論を交互に実行する `ToolEnabledSubAgent`。

### codeact — Python 実行で問題を解く

**得意なクエリ:**
- 「数列 [1,2,3,4,5] の標準偏差を計算」
- 「フィボナッチ数列の 20 番目を求めて」
- 「`users` テーブルの登録月別ヒストグラムを Markdown テーブルで」
- 「以下の JSON を整形して欲しいキーだけ抜いて」

**特徴:**
- **`# Plan:` コメント必須:** コード冒頭で意図・必要情報・手順・出力形式を明示してから書く (AGENT.md ルール)
- **1 回実行型:** Plan に基づいて Python を 1 度書いて execute_python で実行、結果を観察 → 必要なら次のターンで再実行 (`max_iterations: 5`)
- **使用可能ライブラリ:** math, statistics, datetime, json, re, collections, itertools, functools, numpy, yaml, pydantic, mcp_helper, urllib
- **使用不可:** os, subprocess, sys, shutil (sandbox AST allowlist)
- **mcp_helper:** `search()` / `query_db()` / `get_datetime()` を Python コード内から呼び出せる

**苦手 / 対象外:**
- コードレビュー (→ code-reviewer)
- 純粋な SQL 最適化 (→ sql-analyst)
- Web 検索だけが目的の質問 (→ general-assistant の方が軽量)

**裏側:** モデル `gpt-4.1`。`agent_type: codeact` 指定により `CodeActSubAgent` (ReAct とは異なる直接実行型) としてロードされる。

---

## エージェント vs Gem の違い

似ているが用途が異なるので使い分ける。

| | 内蔵 SubAgent | Gem |
|--|---------------|-----|
| **定義場所** | `agents/<slug>/AGENT.md` (Markdown ファイル + frontmatter) | PostgreSQL `gems` テーブル (DB エントリ) |
| **編集者** | 開発者 (リポジトリへのコミット) | エンドユーザー (UI から自由に作成・編集) |
| **使えるツール** | `tools:` で宣言したものだけ | システム共通 (Canvas/Debate 以外の通常 Gem は general-assistant 相当のツール群) |
| **モデル** | AGENT.md の `model:` で固定 (例: gpt-4.1) | Gem 単位での切り替えは未対応 (今後検討余地) |
| **想定スコープ** | システム全体の専門家 (全ユーザー共通) | ユーザー個別 or 公開共有のテンプレート |
| **登録方法** | `agents/<slug>/AGENT.md` を追加してコンテナ再起動 (SubAgentRegistry が自動ロード) | UI の「Gem 作成」フォーム |
| **削除** | ファイル削除 + 再起動 | UI から削除 (DB から消える) |

**判断基準:**
- ある **タスク種別** (コードレビュー全般など) に対する標準的な振る舞いを全社共有したい → SubAgent
- ある **業務シナリオ** (◯◯部の議事録要約フォーマット遵守) に対する個人/部署専用の指示書を再利用したい → Gem

---

## エージェントの自動ルーティング (SuperChat 内部)

SuperChat の `OrchestratorGraph` は以下の流れで動く:

```text
ユーザー入力
  │
  ▼
┌─────────────┐
│ Router      │   LLM がクエリと各 agent の keywords / description を見て選択
│ (LLM 判定)  │   (ユーザーがチップで指定した場合は LLM をスキップ)
└──────┬──────┘
       │ 選ばれた agent 1 つ
       ▼
┌──────────────────────────────┐
│ SubAgent / ToolEnabledSubAgent│
│ - 通常: 直接応答             │
│ - tools あり: ReAct ループ    │
│ - codeact: Plan → 実行 → 観察 │
└──────────────┬───────────────┘
               │
               ▼
              END (応答返却)
```

ルーティングのヒント (各 AGENT.md 冒頭の `keywords:` / `description:`) が選択ロジックの入力になる。`general-assistant` は他のエージェントが明らかに適切でないときのフォールバック先として機能する (description で「他のエージェントが明らかに適切な場合はそちらを優先すること」を明記)。

---

## 開発者向け: 新しいエージェントを追加する

1. `agents/<slug>/AGENT.md` を作る (frontmatter: `name` / `keywords` / `description` / `model` / `tools:` 任意 / `agent_type: codeact` 任意)
2. system prompt 本体を frontmatter の下に書く
3. SuperChat で使いたい場合は `apps/superchat/APP.md` の `agents:` リストに `<slug>` を追記
4. コンテナ再起動 — `SubAgentRegistry` が起動時に自動ロード

**注意点 (CLAUDE.md ADR より):**
- `tools:` に **privileged ツール** (`claude_code` / `execute_python`) を入れると `SubAgentRegistry` が WARNING を出す
- `agent_type: codeact` は `tools: [execute_python]` 専用 (CodeAct パターン、Phase 28)
- `tools:` を宣言した SubAgent は `ToolEnabledSubAgent` として LangGraph mini ReAct グラフが構築される (Phase 21+)

詳細は [../adr/INDEX.md](../adr/INDEX.md) の `LangGraph・Graph` カテゴリと、`../../.planning/patterns.md` の SubAgent 関連パターンを参照。
