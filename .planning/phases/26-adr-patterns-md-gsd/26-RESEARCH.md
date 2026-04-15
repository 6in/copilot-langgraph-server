# Phase 26: ADR 整理 + patterns.md 作成 + GSD プランニング統合 - Research

**Researched:** 2026-04-15
**Domain:** ドキュメント整備・ADR カタログ化・git hook・GSD ワークフロー統合
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** ゴールは「ADR からパターンを抽出して GSD が自動参照する状態を作ること」。ADR 本文リファクタや GSD ワークフローの本格改修は対象外。
- **D-02:** 成果物は 3 つ: (1) `.planning/patterns.md` (2) `docs/adr/INDEX.md` (3) `discuss-phase` ワークフロー側の canonical_refs 標準手順更新 + `CLAUDE.md` への運用ルール追記。
- **D-03:** ADR 整理は索引化 + カテゴリ分類のみ。本文は変更しない。
- **D-04:** 欠番 0015-0017 は "欠番" として INDEX.md に明示的に記録するだけ。補完はしない。
- **D-05:** Status 付与は本フェーズでは行わない。現状 ADR は全て "Accepted" の前提で索引する。
- **D-06:** `.planning/patterns.md` に置く。`PROJECT.md` / `REQUIREMENTS.md` / `STATE.md` と同階層。
- **D-07:** 1 パターンあたり 5-10 行（パターン名 + 要約 + 関連 ADR 番号リンク）。詳細解説は書かずリンク先 ADR を参照。
- **D-08:** パターンソースは ADR のみ。ADR にないパターンは載せない。
- **D-09:** カテゴリは 7 種: `Auth` / `LangGraph・Graph` / `MCP・Tools` / `Worker・Jobs` / `Frontend・UI` / `Infra・Deploy` / `Data・Persistence`
- **D-10:** `patterns.md` と `docs/adr/INDEX.md` で同じカテゴリ分類を使用（複数カテゴリにまたがる場合は主カテゴリに置き副カテゴリからクロスリンク）。
- **D-11:** 統合方式は canonical_refs への再帰的追加。`.planning/patterns.md` と `docs/adr/INDEX.md` を各フェーズの CONTEXT.md の `canonical_refs` に毎回記載する標準手順を `CLAUDE.md` に明記する。
- **D-12:** CLAUDE.md への `@import` による常時ロードはしない。
- **D-13:** GSD 本体 (`~/.claude/get-shit-done/`) には手を入れない。本リポジトリ側で完結。
- **D-14:** 新規 ADR 追加時の `INDEX.md` 更新は pre-commit hook で自動生成する。カテゴリ判定方式は計画段階で決める。
- **D-15:** `patterns.md` 本体は手動更新。新規 ADR 追加時の運用ルールを `CLAUDE.md` と `/create-adr` スキルに追記する。

### Claude's Discretion

- `adr-categories.yaml` を使うか ADR 内マーカーを使うかは計画段階で決めてよい（保守性優先）。
- pre-commit hook の言語（Python / Bash / Node）は既存プロジェクトの hook 規約に合わせる。
- `INDEX.md` の具体的な表形式（マークダウンテーブル / 入れ子リスト）は Claude が決めてよい。
- 既存 30 件を 7 カテゴリにどう振り分けるかの初期マッピングは Claude が下書きし、ユーザー確認を受ける。

### Deferred Ideas (OUT OF SCOPE)

- ADR 本文の Status 付与と Superseded 関係のマッピング
- 欠番 ADR 0015-0017 の補完
- `patterns.md` の自動生成化
- コードベース直接由来のパターン集
- GSD 本体ワークフロー (`~/.claude/get-shit-done/`) の改修

</user_constraints>

---

## Summary

Phase 26 は「ADR カタログ整備」フェーズ。コードを変更せず、ドキュメントと軽量スクリプト（pre-commit hook）と規約ファイル（CLAUDE.md）の整備が主体。

技術的難易度は低いが、設計判断が多い。`adr-categories.yaml` vs ADR 内マーカー方式の選択、INDEX.md のフォーマット設計、CLAUDE.md の追記箇所の特定が実作業の核心となる。特に pre-commit hook は既存ゼロ（`.pre-commit-config.yaml` 未存在、`.git/hooks/` に `.sample` のみ）なので、プロジェクトとして最初の hook 導入となる。

既存の 30 件 ADR（0001-0033、欠番 0015-0017）はフォーマットが高度に統一されており、H1 タイトル・`**Date:**`・`**Status:**` を正規表現でパース可能。ただし 0020 だけ `## Decisions` フォーマットがわずかに異なるため、パーサーは柔軟性が必要。

GSD 統合の核は CLAUDE.md への運用ルール追記だけでよい。`/gsd-discuss-phase` ワークフローは `canonical_refs` セクションを CONTEXT.md の MANDATORY セクションとして定義しており、CLAUDE.md に「フェーズ開始時に `.planning/patterns.md` と `docs/adr/INDEX.md` を canonical_refs に追加せよ」と明記するだけで機能する。

**Primary recommendation:** カテゴリ方式は `adr-categories.yaml`（外部マッピングファイル）を採用し、pre-commit hook は Python スクリプト（プロジェクト標準言語）で実装する。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ADR 索引生成 (INDEX.md) | Build-time Script | git hook | コミット時に自動実行 |
| パターンカタログ (patterns.md) | Documentation | — | 手動メンテナンス |
| カテゴリマッピング (adr-categories.yaml) | Configuration | pre-commit hook | hook がこれを読む |
| GSD 統合 (canonical_refs 標準手順) | CLAUDE.md 規約 | — | ドキュメント追記のみ |
| 運用ルール (ADR 追加時の手順) | CLAUDE.md + create-adr | — | 既存コマンドを拡張 |

---

## 調査結果 1: 全 ADR 一覧と 7 カテゴリへの初期マッピング

### 確認済み ADR（30 件、欠番 0015-0017）[VERIFIED: 実ファイル走査]

| No. | タイトル | Date | 主カテゴリ | 副カテゴリ |
|-----|---------|------|-----------|-----------|
| 0001 | nginx prefix-strip approach for URL routing | 2026-04-03 | Infra・Deploy | Frontend・UI |
| 0002 | API Path Prefix Management in React SPA | 2026-04-03 | Frontend・UI | Infra・Deploy |
| 0003 | Worker Pluggable Task Routing Facade | 2026-04-03 | Worker・Jobs | LangGraph・Graph |
| 0004 | Super-Agent サンプルをスタンドアロン実装し ChatCopilot を利用する | 2026-04-03 | LangGraph・Graph | — |
| 0005 | OrchestratorGraph Integration — Per-Job Construction over Shared State | 2026-04-04 | LangGraph・Graph | Worker・Jobs |
| 0006 | SuperChat Agent Selection UI and Mode Split | 2026-04-04 | Frontend・UI | LangGraph・Graph |
| 0007 | Application Packages — APP.md Definition Pattern | 2026-04-05 | LangGraph・Graph | Infra・Deploy |
| 0008 | Gem UX ナビゲーション — GemsScreen・GemChatApp・4 画面スクリーンモデル | 2026-04-06 | Frontend・UI | — |
| 0009 | Gem UX 強化 — 専用ナビゲーション・スレッド分離・description/knowledge フィールド | 2026-04-06 | Frontend・UI | Data・Persistence |
| 0010 | Gem 公開共有機能 — is_public フラグと Shared Gems セクション | 2026-04-06 | Data・Persistence | Frontend・UI |
| 0011 | マルチエージェント討論チャット — ターン制会話プラットフォーム | 2026-04-06 | LangGraph・Graph | Frontend・UI |
| 0012 | GemChatApp フレックスレイアウト修正 — height:100% から flex:1/minHeight:0 へ | 2026-04-07 | Frontend・UI | — |
| 0013 | Agent Identity in Chat UI — Per-Agent Color and Name Display | 2026-04-08 | Frontend・UI | — |
| 0014 | Phase 17 セキュリティ強化 — JWT ブロックリスト Redis 移行と未認証エンドポイントの修正 | 2026-04-07 | Auth | Worker・Jobs |
| 0015 | （欠番） | — | — | — |
| 0016 | （欠番） | — | — | — |
| 0017 | （欠番） | — | — | — |
| 0018 | Canvas iframe postMessage JSON-RPC ブリッジ | 2026-04-09 | Frontend・UI | Worker・Jobs |
| 0019 | Canvas アプリのスタンドアロンホスティングと parent-bridge.js 共通化 | 2026-04-09 | Frontend・UI | Infra・Deploy |
| 0020 | FastMCP Docker サービス基盤 (Phase 20) | 2026-04-10 | MCP・Tools | Infra・Deploy |
| 0021 | LangGraph bind_tools + ToolNode の実装: プロンプトエンジニアリング方式 | 2026-04-10 | LangGraph・Graph | MCP・Tools |
| 0022 | Tavily Web Search と JSON ベースツール呼び出しのモデル互換性 | 2026-04-13 | MCP・Tools | LangGraph・Graph |
| 0023 | MCP ツール本番実装 — db_query（SELECT-only ガード）と claude_code（サブプロセス + env sanitization） | 2026-04-13 | MCP・Tools | Data・Persistence |
| 0024 | MCP ツールカタログ検証（ToolRegistry）と関連バグ修正 | 2026-04-13 | MCP・Tools | Worker・Jobs |
| 0025 | 全エージェントへの現在日時・ログインユーザー自動注入 | 2026-04-13 | LangGraph・Graph | Auth |
| 0026 | スレッド削除時に threads テーブルの行も削除する | 2026-04-14 | Data・Persistence | — |
| 0027 | フロントエンドランタイムを Node.js/npm から Bun に移行 | 2026-04-14 | Frontend・UI | Infra・Deploy |
| 0028 | React Router v7 による URL ベースルーティングの導入 | 2026-04-14 | Frontend・UI | Infra・Deploy |
| 0029 | UI Todo バッチ実装 — Orochi ブランディング・Canvas/DebateChat 機能改善 | 2026-04-14 | Frontend・UI | — |
| 0030 | Canvas DB アクセスを MCP db_query ツール経由に移行 | 2026-04-14 | MCP・Tools | Data・Persistence |
| 0031 | Copilot SDK トークンストリーミング実装 — 3 層配管の発見と修正 | 2026-04-15 | LangGraph・Graph | Worker・Jobs |
| 0032 | db_pools.yaml 駆動の接続プールチューニングパラメータ | 2026-04-15 | Data・Persistence | Infra・Deploy |
| 0033 | Canvas iframe RPC `ai()` モデル指定機能とエイリアスホワイトリスト | 2026-04-15 | Frontend・UI | MCP・Tools |

### カテゴリ別件数サマリ

| カテゴリ | 主カテゴリ件数 |
|---------|--------------|
| Frontend・UI | 13 件（0002, 0006, 0008, 0009, 0012, 0013, 0018, 0019, 0027, 0028, 0029, 0031※, 0033） |
| LangGraph・Graph | 6 件（0004, 0005, 0007, 0011, 0021, 0025） |
| MCP・Tools | 5 件（0020, 0022, 0023, 0024, 0030） |
| Data・Persistence | 3 件（0010, 0026, 0032） |
| Worker・Jobs | 2 件（0003, 0031） |
| Infra・Deploy | 1 件（0001） |
| Auth | 1 件（0014） |

※ 0031 は LangGraph・Graph でもあり

---

## 調査結果 2: patterns.md エントリ候補（カテゴリ別下書き）[VERIFIED: 実 ADR 精読]

### Auth
- **JWT ブロックリストの Redis 移行** — httpOnly cookie に格納した JWT の logout 無効化は Redis ブロックリストで実現。インメモリ実装は再起動で無効化できないため Redis へ移行。関連 ADR: [0014](../docs/adr/0014-phase17-security-hardening-jwt-blocklist-redis-and-endpoint-auth.md)

### LangGraph・Graph
- **OrchestratorGraph Per-Job Construction** — OrchestratorGraph はリクエストごとに生成・廃棄する（アプリ起動時に1インスタンス共有しない）。github_token のマルチユーザー分離を実現するためのパターン。関連 ADR: [0005](../docs/adr/0005-orchestratorgraph-integration-per-job-construction.md)
- **APP.md 定義によるアプリケーションパッケージ** — `agents/menus/APP.md` でエージェントサブセットを宣言。コード変更ゼロでアプリ別エージェント構成が可能。関連 ADR: [0007](../docs/adr/0007-application-packages-app-md-pattern.md)
- **bind_tools プロンプトエンジニアリング方式** — Copilot SDK は OpenAI tool_calls 形式非対応のため、ツールスキーマをシステムプロンプトに JSON として注入し、テキスト応答を解析して tool_calls に変換する BoundChatCopilot パターン。関連 ADR: [0021](../docs/adr/0021-langgraph-bind-tools-toolnode-via-prompt-engineering.md)
- **エージェントプロンプトへの日時・ユーザー自動注入** — ToolEnabledSubAgent の system prompt 先頭に現在日時・ログインユーザーを毎回注入。エージェント AGENT.md には記載不要。関連 ADR: [0025](../docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md)
- **DebateChat ターン制マルチエージェントグラフ** — 複数 SubAgent が交互に発言するターン制を LangGraph ループで実現。DebateGraph ノードは state.turn_index で話者を決定。関連 ADR: [0011](../docs/adr/0011-debate-chat-multi-agent-turn-based-platform.md)
- **Token Streaming 3 層配管** — Copilot SDK ストリームを worker → SSE → frontend の 3 層で中継。notifier.py でチャンクをキューイングし SSE エンドポイントが消費。関連 ADR: [0031](../docs/adr/0031-copilot-sdk-token-streaming-three-layer-plumbing.md)

### MCP・Tools
- **FastMCP Docker 独立サービス基盤** — ツール実装を API サーバーに組み込まず FastMCP 独立コンテナとして分離。worker から streamable-http で接続。stdio は Docker 間通信不可、SSE はセッションアフィニティ問題あり。関連 ADR: [0020](../docs/adr/0020-fastmcp-docker-service-infrastructure.md)
- **MCP ツールカタログ YAML 検証 (ToolRegistry)** — `config/mcp_tools.yaml` に宣言ツールセットを定義し、worker 起動時に MCP 実ツールリストと双方向一致を検証。不一致で RuntimeError → デプロイ後の無言不整合を防止。関連 ADR: [0024](../docs/adr/0024-mcp-tool-catalog-validation.md)
- **db_query SELECT-only ガード** — `is_select_only()` ユーティリティで SELECT 以外をブロック。`app/utils/sql_safety.py` に配置し iframe-rpc と MCP ツールの両方から再利用。関連 ADR: [0023](../docs/adr/0023-mcp-db-query-and-claude-code-tools.md)
- **claude_code env sanitization** — Claude Code CLI サブプロセス起動前に `CLAUDECODE=1` 等の危険な環境変数を除去。タイムアウト 60 秒 + zombie プロセス対策。関連 ADR: [0023](../docs/adr/0023-mcp-db-query-and-claude-code-tools.md)
- **Tavily JSON モード互換性** — Copilot モデルは関数呼び出し非対応のため、Tavily 検索結果を JSON スキーマとして prompt に注入し text 応答から parse。関連 ADR: [0022](../docs/adr/0022-tavily-web-search-json-tool-calling-model-compatibility.md)

### Worker・Jobs
- **Worker Pluggable Task Routing Facade** — `dispatcher.py` がタスクタイプ（chat/orchestrator/canvas 等）を TaskHandler サブクラスへルーティング。handler 追加はコードのみで完結。関連 ADR: [0003](../docs/adr/0003-worker-pluggable-task-routing-facade.md)

### Frontend・UI
- **nginx prefix-strip URL ルーティング** — リバースプロキシで `/orochi` プレフィックスを strip して転送。FastAPI は `APP_PREFIX` で root_path 設定、Vite は `VITE_APP_BASE` でアセット URL を制御。関連 ADR: [0001](../docs/adr/0001-nginx-prefix-strip-for-url-routing.md), [0002](../docs/adr/0002-api-path-prefix-management-in-react-spa.md)
- **Canvas iframe postMessage JSON-RPC ブリッジ** — iframe 内 JS から `window.parent.postMessage` 経由で DB/AI ツールを呼び出す。JSON-RPC over postMessage パターン。`static/js/iframe-rpc.js` ライブラリとして配布。関連 ADR: [0018](../docs/adr/0018-canvas-iframe-postmessage-json-rpc-bridge.md)
- **Canvas スタンドアロンホスティングと parent-bridge.js 共通化** — `/apps/{app_id}/` でホスト時も iframe-rpc 機能を利用するため parent-bridge.js を共通化。CanvasPane と HostingShell で同一 relay ロジックを共有。関連 ADR: [0019](../docs/adr/0019-canvas-app-standalone-hosting-parent-bridge.md)
- **React Router v7 URL ルーティング** — BrowserRouter + Routes でアプリ種別・thread_id を URL に反映。APP_PREFIX 対応は `basename` prop で実現。nginx SPA fallback（`try_files`）が必要。関連 ADR: [0028](../docs/adr/0028-react-router-v7-url-based-routing-for-spa.md)
- **ai() モデル指定エイリアスホワイトリスト** — Canvas iframe RPC の ai() に model パラメータを追加する際、任意モデル名を通すのではなく YAML ホワイトリストでエイリアスを管理。関連 ADR: [0033](../docs/adr/0033-canvas-ai-model-selection-with-alias-whitelist.md)

### Infra・Deploy
- **Frontend Bun 移行** — フロントエンドランタイムを Node.js/npm から Bun に移行。Docker Compose build の `bun install` + `bun run build`。パッケージマネージャーとして npm の代替。関連 ADR: [0027](../docs/adr/0027-migrate-frontend-runtime-from-nodejs-to-bun.md)

### Data・Persistence
- **db_pools.yaml 駆動の接続プールチューニング** — DB 接続プールパラメータ（min_size/max_size/timeout 等）を `config/db_pools.yaml` で宣言。コード変更なしに環境別チューニングが可能。関連 ADR: [0032](../docs/adr/0032-db-pools-yaml-driven-tuning-params.md)
- **Gem is_public フラグによる公開共有** — Gem 公開は DB カラム `is_public` フラグで制御。共有 Gem は全ユーザーが読み取り可能で、GemsScreen に Shared Gems セクションを表示。関連 ADR: [0010](../docs/adr/0010-gem-public-sharing-is-public-flag.md)

---

## 調査結果 3: カテゴリ判定方式の比較（Claude の裁量）[VERIFIED: 実プロジェクト構造確認]

### 方式 A: `adr-categories.yaml`（外部マッピングファイル）

```yaml
# .planning/adr-categories.yaml
adr_categories:
  "0001": { primary: "Infra・Deploy", secondary: "Frontend・UI" }
  "0002": { primary: "Frontend・UI", secondary: "Infra・Deploy" }
  # ...
```

**メリット:**
- ADR 本文を変更しない（D-03 準拠）
- hook スクリプトが YAML を読むだけでよい（単純）
- カテゴリ変更は YAML のみで対応（ADR 本文に触らない）
- `patterns.md` と `INDEX.md` の両方から参照できる

**デメリット:**
- 新 ADR 追加時に YAML も更新が必要（手順が 2 ステップ）
- ADR とカテゴリ情報が分離している（同時更新漏れリスク）

### 方式 B: ADR 内マーカー（`<!-- category: Auth -->`）

**メリット:**
- ADR ファイルだけ更新すれば完結（1 ファイル）
- カテゴリ情報が ADR に内包

**デメリット:**
- 既存 30 件の ADR 本文に HTML コメントを追加する必要がある（D-03 準拠外の変更）
- ADR フォーマット標準（create-adr.md）に追記が必要

### 推奨: 方式 A（adr-categories.yaml）

D-03「ADR 本文は変更しない」という locked decision と完全整合する。新規 ADR 追加時は `docs/adr/NNNN-*.md` + `.planning/adr-categories.yaml` の 2 ファイル更新で済む。hook スクリプトのロジックもシンプル。

---

## 調査結果 4: pre-commit hook 方式の比較（Claude の裁量）[VERIFIED: 実環境確認]

### 現状確認

- `.pre-commit-config.yaml`: **存在しない** [VERIFIED: `ls` で確認]
- `.git/hooks/`: **全て .sample のみ**（実際の hook なし）[VERIFIED: `ls -la` で確認]
- `pre-commit` フレームワーク: **未インストール** [VERIFIED: `pre-commit --version` 失敗]
- プロジェクト標準言語: **Python 3.12** [VERIFIED: `python3 --version`]

### 方式比較

| 方式 | 導入コスト | 保守性 | プロジェクト整合性 |
|-----|----------|--------|------------------|
| `pre-commit` フレームワーク | 高（新ツール導入、`pip install pre-commit` 必要） | 高（YAML 宣言） | 低（現在未使用） |
| 素の git hook（Bash シェルスクリプト） | 低（.git/hooks/pre-commit に配置） | 中（手動管理） | 中（シンプル） |
| 素の git hook（Python スクリプト） | 低（.git/hooks/pre-commit でスクリプト呼び出し） | 高（プロジェクト標準言語） | 高（Python 環境あり） |
| husky（JavaScript） | 高（npm 依存、frontend/ は Bun ベース） | 中 | 低（Python プロジェクト） |

### 推奨: Python スクリプト + 素の git hook

`.git/hooks/pre-commit` に配置するが、実際のロジックは `scripts/generate_adr_index.py` に分離する。理由:

1. `.git/hooks/` は git 管理対象外のため、hook 本体ではなく呼び出しスクリプト自体を `scripts/` に置く
2. `scripts/generate_adr_index.py` は uv 環境（`uv run`）で実行可能
3. YAML パースには `pyyaml`（既に `pyproject.toml` の依存として存在）[VERIFIED: `pyproject.toml` 確認]

**実装パターン:**

```bash
# .git/hooks/pre-commit (手動インストール手順を CLAUDE.md に記載)
#!/bin/bash
python3 scripts/generate_adr_index.py && git add docs/adr/INDEX.md
```

```python
# scripts/generate_adr_index.py
"""docs/adr/INDEX.md を adr-categories.yaml から自動生成する"""
import yaml, re, pathlib
```

**注意:** `.git/hooks/` はリポジトリに含まれないため、新しい開発者は手動でインストールが必要。インストール手順を CLAUDE.md に記載することで対応（D-15 の運用ルールに含める）。

---

## 調査結果 5: GSD discuss-phase ワークフローの canonical_refs 構造 [VERIFIED: `~/.claude/get-shit-done/workflows/discuss-phase.md` 読み取り]

### 現在の実装

`discuss-phase.md` の Step `analyze_phase` に以下の指示がある（行 419-426）:

> **1b. Initialize canonical refs accumulator** — Start building the `<canonical_refs>` list for CONTEXT.md. This accumulates throughout the entire discussion, not just this step.
>
> - Source 1 (now): Copy `Canonical refs:` from ROADMAP.md for this phase.
> - Source 2 (now): Check REQUIREMENTS.md and PROJECT.md for any specs/ADRs referenced for this phase.
> - Source 3 (scout_codebase): If existing code references docs (e.g., comments citing ADRs), add those.
> - Source 4 (discuss_areas): When the user says "read X", "check Y", or references any doc/spec/ADR during discussion — add it immediately.
>
> This list is MANDATORY in CONTEXT.md.

### 統合方式の設計（D-11 実装）

GSD 本体（`discuss-phase.md`）は変更しない（D-13）。代わりに **CLAUDE.md の Conventions セクション**に以下を追記する:

```markdown
## ADR Pattern Reference (GSD Integration)

/gsd-discuss-phase を実行する際、canonical_refs には必ず以下を追加すること:

- `.planning/patterns.md` — ADR 由来のパターンカタログ（設計判断の前に参照）
- `docs/adr/INDEX.md` — ADR カテゴリ索引（関連 ADR 特定に使用）

これにより research-phase と planner が自動的に過去の意思決定パターンを参照する。
```

### なぜこれで機能するか

`discuss-phase.md` の `canonical_refs` は「Source 4: ユーザーが参照指示したドキュメント」が最も重要と明記されている。CLAUDE.md への追記は「discuss-phase 実行者（Claude）が CLAUDE.md を読んで canonical_refs に追加する」という流れになる。`discuss-phase.md` 自身は `CLAUDE.md` を required_reading に含めていないが、Claude の動作として CLAUDE.md のプロジェクト規約は常時読み込まれるため、この方式は確実に機能する [VERIFIED: CONTEXT.md の D-11 と discuss-phase.md の構造の整合確認]。

---

## 調査結果 6: CLAUDE.md の追記箇所特定 [VERIFIED: CLAUDE.md 全体確認]

### 現在の CLAUDE.md セクション構造

1. `## Project` — プロジェクト概要
2. `## Technology Stack` — スタックテーブル
3. `## Conventions` — 応答言語・マージワークフロー
4. `## Architecture` — Backend / Frontend / Infrastructure / Key Patterns
5. `## Chrome DevTools MCP`
6. `## Merge Safety Rules`
7. `## GSD Workflow Enforcement`
8. `## Developer Profile`

### 追記箇所の推奨

**箇所 1: `## Conventions` セクション末尾**（既存の応答言語・マージルールに並べる）

追記内容: 「ADR Pattern Reference (GSD Integration)」節 — `/gsd-discuss-phase` 実行時の canonical_refs 必須追加ルール

**箇所 2: `## GSD Workflow Enforcement` セクション末尾**

追記内容: `/create-adr` 実行後の patterns.md 手動更新義務ルール

理由: GSD ワークフロー強制ルールと同じセクションに置くことで、GSD コマンド使用時に一緒に参照される。

---

## 調査結果 7: `/create-adr` スキルへのリマインダー追加方法 [VERIFIED: `.claude/commands/create-adr.md` 読み取り]

### 現状の `/create-adr` スキルの手順

```
1. 次の ADR 番号を決定
2. トピックを推論
3. 自律的にリサーチ
4. ADR を書く
5. コミット
```

### 追記方法

`/create-adr` スキルは `.claude/commands/create-adr.md` に定義されており、**本リポジトリ内のファイル**（プロジェクトローカルコマンド）。つまり直接編集可能で GSD 本体には手を入れない。

**Step 5 の後に Step 6 を追加する:**

```markdown
**6. patterns.md 更新リマインダー**

ADR 作成後、パターンとして記録すべき設計判断が含まれていれば `.planning/patterns.md` にも追記する:

- patterns.md は手動更新（自動生成しない）
- 1 パターンあたり 5-10 行（パターン名 + 要約 + 関連 ADR 番号リンク）
- カテゴリは: Auth / LangGraph・Graph / MCP・Tools / Worker・Jobs / Frontend・UI / Infra・Deploy / Data・Persistence
- ADR にないパターンは追加しない（ADR が唯一の真実源）
```

---

## INDEX.md フォーマット設計（Claude の裁量）

### 推奨フォーマット（マークダウンテーブル方式）

```markdown
# ADR Index

**Generated:** {date}  
**Total:** {n} 件（欠番 3 件: 0015, 0016, 0017）

## Auth

| No. | タイトル | Date |
|-----|---------|------|
| [0014](0014-phase17-security-hardening-jwt-blocklist-redis-and-endpoint-auth.md) | Phase 17 セキュリティ強化 — JWT ブロックリスト Redis 移行と未認証エンドポイントの修正 | 2026-04-07 |

## LangGraph・Graph

| No. | タイトル | Date |
|-----|---------|------|
| ... | ... | ... |

...（7 カテゴリ）

## 欠番

| No. | 備考 |
|-----|------|
| 0015 | 欠番 |
| 0016 | 欠番 |
| 0017 | 欠番 |
```

**選択理由:**
- マークダウンテーブルは GitHub/MkDocs でそのまま表示可能
- `docs/adr/0033-*.md` の ADR フォーマット標準と視覚的に整合する
- カテゴリ見出し下にテーブルを並べる構造は patterns.md と同一のナビゲーション体験

---

## Standard Stack（本フェーズで使うツール）

| ライブラリ/ツール | バージョン | 用途 |
|----------------|-----------|-----|
| `pyyaml` | >=6.0.3（既存） | adr-categories.yaml パース [VERIFIED: pyproject.toml] |
| `pathlib` | stdlib | ADR ファイル走査 |
| `re` | stdlib | H1 タイトル・Date の正規表現抽出 |
| `python3` | 3.12（既存） | hook スクリプト実行環境 |

**追加インストール不要。** 全て既存環境で動作する。

---

## Architecture Patterns

### パーサーの正規表現パターン [VERIFIED: 全 30 件の ADR ヘッダー走査]

```python
# H1 タイトル抽出 (2 種類のフォーマットに対応)
# パターン A: "# NNNN. タイトル" (0001-0014, 0018-0019, 0021-0033)
# パターン B: "# ADR NNNN: タイトル" (0020 のみ)
title_re = re.compile(r'^# (?:ADR )?(\d+)[.:]\s+(.+)$', re.MULTILINE)

# Date 抽出 (2 種類のフォーマットに対応)
# パターン A: "**Date:** YYYY-MM-DD  " (末尾スペースあり)
# パターン B: "**Date**: YYYY-MM-DD"  (コロン前にスペースなし, 0020)
date_re = re.compile(r'^\*\*Date\*\*:?\s+(\d{4}-\d{2}-\d{2})', re.MULTILINE)
```

**ADR 0020 は H1 フォーマットと Date フォーマットが異なる**（`ADR NNNN:` 形式・`**Date**:` 形式）。パーサーは両方に対応する必要がある。

### スクリプト実行方式

```bash
# .git/hooks/pre-commit
#!/bin/bash
set -e

# docs/adr/*.md が変更に含まれる場合のみ実行
if git diff --cached --name-only | grep -q '^docs/adr/'; then
  python3 scripts/generate_adr_index.py
  git add docs/adr/INDEX.md
fi
```

```python
# scripts/generate_adr_index.py
#!/usr/bin/env python3
"""docs/adr/INDEX.md を .planning/adr-categories.yaml に基づいて自動生成する"""
```

---

## Don't Hand-Roll

| 問題 | 作るな | 使え | 理由 |
|-----|--------|------|------|
| YAML パース | 独自パーサー | `pyyaml`（既存） | 既に `pyproject.toml` に依存あり |
| ファイル走査 | glob 文字列操作 | `pathlib.glob()` | Python 標準で安全 |
| フォーマット判定 | 複雑な分岐 | 正規表現 2 パターン | ADR フォーマットは 2 種類のみ（検証済み） |

---

## Common Pitfalls

### Pitfall 1: ADR 0020 のフォーマット差異
**何が起きるか:** パーサーが `# 0020. ...` を期待すると `# ADR 0020: ...` を読み取れず、0020 がインデックスから脱落する
**原因:** 0020 は H1 が `# ADR 0020: タイトル` でコロン区切り（他は `# NNNN. タイトル` でドット区切り）。Date も `**Date**:` vs `**Date:**` で異なる
**回避:** 正規表現を `^# (?:ADR )?(\d+)[.:]` で両対応にする

### Pitfall 2: git hook がリポジトリに含まれない
**何が起きるか:** 新規クローン後、`.git/hooks/pre-commit` が存在せず INDEX.md が自動更新されない
**原因:** `.git/` はリポジトリ管理対象外
**回避:** `scripts/install-hooks.sh`（または CLAUDE.md の手順説明）で `cp scripts/generate_adr_index.py .git/hooks/pre-commit` を実行する手順を提供

### Pitfall 3: INDEX.md が git に未ステージングのまま hook が終了
**何が起きるか:** hook が `git add docs/adr/INDEX.md` をしないとコミット差分に INDEX.md が含まれず、コミット後に unstaged changes が残る
**原因:** git hook の `git add` 忘れ
**回避:** hook スクリプトの最後に `git add docs/adr/INDEX.md` を明示する

### Pitfall 4: `patterns.md` に ADR 外のパターンが混入
**何が起きるか:** 「ADR が唯一の真実源」ルールが崩れ、patterns.md と ADR の間で矛盾が生じる
**原因:** D-08 を守らずにコードベース直接由来のパターンを追加
**回避:** CLAUDE.md の運用ルールに「ADR にないパターンは載せない。まず ADR を作成してから patterns.md に追記する」と明記

### Pitfall 5: canonical_refs に patterns.md/INDEX.md を追加し忘れる
**何が起きるか:** 将来フェーズで研究者や計画者が過去のパターンを参照しない
**原因:** CLAUDE.md のルールを discuss-phase 実行時に見落とす
**回避:** CLAUDE.md の該当ルールを `## Conventions` の先頭寄りに配置し、発見しやすくする

---

## Environment Availability

| 依存 | 用途 | 利用可能 | バージョン | フォールバック |
|-----|------|---------|-----------|--------------|
| Python 3.12 | hook スクリプト | ✓ | 3.12.3 | — |
| pyyaml | YAML パース | ✓ | 6.0.3+（既存）| — |
| bash 5.1 | hook シェル | ✓ | 5.1.16 | — |
| pre-commit framework | hook 管理 | ✗ | — | 素の git hook で代替 |

**Missing dependencies with no fallback:** なし
**Missing dependencies with fallback:** `pre-commit` フレームワークは不要（素の git hook で実装）

---

## Validation Architecture

`workflow.nyquist_validation: true` のため以下を計画に含める。

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x（既存） |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run | `python3 scripts/generate_adr_index.py && diff docs/adr/INDEX.md /dev/stdin <<< "..."` |
| Full suite | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Behavior | Test Type | Approach | File |
|----------|-----------|----------|------|
| `generate_adr_index.py` が全 30 件を正しく分類する | unit | pytest でスクリプト出力を fixture と比較 | `tests/test_generate_adr_index.py` |
| 欠番 0015-0017 が INDEX.md に "欠番" として記録される | unit | 上記テストに含める | 同上 |
| ADR 0020 の異なるフォーマットが正しくパースされる | unit | 上記テストに含める | 同上 |
| patterns.md が 7 カテゴリの構造を持つ | manual verify | ファイル存在確認 + 目視 | — |

### Wave 0 Gaps

- [ ] `tests/test_generate_adr_index.py` — スクリプト出力検証

---

## Security Domain

Phase 26 はドキュメント整備・スクリプト作成フェーズ。認証・外部 API・データベース変更はない。ASVS 適用カテゴリなし。

**Security consideration（軽微）:** `generate_adr_index.py` が `docs/adr/*.md` をパースする際に任意コードを実行しない（`yaml.safe_load()` 使用、`eval()` 等を使わない）ことを確認する。

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ADR 0020 以外の全 ADR が `# NNNN. タイトル` + `**Date:** YYYY-MM-DD` フォーマットである | パーサー設計 | 将来追加された ADR でパーサーが失敗 → hook エラー |
| A2 | CLAUDE.md を Claude が常時読み込むため、CLAUDE.md への追記だけで discuss-phase 時の canonical_refs 追加が保証される | GSD 統合 | CLAUDE.md 未読の場合は canonical_refs 追加が保証されない。その場合は CONTEXT.md テンプレートへの直接追記が必要 |

---

## Open Questions (RESOLVED)

1. **adr-categories.yaml の初期振り分け（上記の下書き）のユーザー確認**
   - 上記「調査結果 1」の 7 カテゴリ割り当てはリサーチ段階での Claude 判断
   - 特に 0005（LangGraph主 / Worker副）、0025（LangGraph主 / Auth副）等の判断をユーザーに確認が必要
   - 推奨: 実行フェーズで `adr-categories.yaml` の初期版を Claude が作成し、ユーザーが編集する形にする
   - **RESOLVED:** Plan 01 Task 1 で `.planning/adr-categories.yaml` 方式を採用。Claude が初期振り分けを YAML として生成し、ユーザーは実行後の差分レビューで編集する運用とする。ADR 内マーカー方式は D-03（ADR 本文不変更）と抵触するため不採用。

2. **hook のインストール自動化の必要性**
   - `.git/hooks/pre-commit` は git 管理対象外
   - `scripts/install-hooks.sh` を作成するか、CLAUDE.md に手動手順を書くだけで十分か
   - 推奨: CLAUDE.md の手順記述で十分（プロジェクト規模 200 人以下で、主要開発者は数人）
   - **RESOLVED:** Plan 01 Task 3 で `scripts/install-hooks.sh` を作成する。CLAUDE.md だけの手動手順だと忘れやすく、新規クローン時の 1 コマンド化（`bash scripts/install-hooks.sh`）が運用コスト削減に繋がるため。スクリプトは idempotent で、CLAUDE.md の GSD Workflow Enforcement セクションから参照する。

---

## Sources

### Primary (HIGH confidence)
- 全 30 件の `docs/adr/*.md` を実際にファイル走査・ヘッダー抽出
- `~/.claude/get-shit-done/workflows/discuss-phase.md`（canonical_refs セクション）
- `.claude/commands/create-adr.md`（スキル本体）
- `.planning/config.json`（nyquist_validation 設定）
- `pyproject.toml`（依存ライブラリ確認）
- `.git/hooks/`（既存 hook 確認）

### Secondary (MEDIUM confidence)
- `CLAUDE.md` — セクション構造と追記箇所の推定

---

## Metadata

**Confidence breakdown:**
- ADR 一覧・フォーマット: HIGH — 全ファイル実走査済み
- カテゴリマッピング下書き: MEDIUM — Claude の判断、ユーザー確認が必要
- pre-commit hook 設計: HIGH — 環境確認済み（未インストール確認含む）
- GSD 統合方式: HIGH — discuss-phase.md の実装を確認
- CLAUDE.md 追記箇所: HIGH — 全セクション確認済み

**Research date:** 2026-04-15
**Valid until:** 2026-05-15（安定ドメイン・ADR 追加がなければ有効）
