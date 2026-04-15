# Phase 26: ADR 整理 + patterns.md 作成 + GSD プランニング統合 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 26-adr-patterns-md-gsd
**Areas discussed:** フェーズゴール / ADR 整理スコープ / patterns.md 置き場所 / 粒度 / GSD 統合方式 / カテゴリ / パターンソース / 更新運用

---

## フェーズゴール

| Option | Description | Selected |
|--------|-------------|----------|
| パターン抽出と GSD 自動参照 (Recommended) | ADR からパターンを抽出し patterns.md に集約、canonical_refs 経由で自動参照 | ✓ |
| ADR の本格リファクタ + patterns.md | ADR 本文書き直し・廃止判定・欠番整理まで実施 | |
| GSD プランニングのワークフロー改修中心 | patterns.md は副産物、hooks や agent skill 改修がメイン | |
| まず私の意図を説明したい | 自由記述で方向を決める | |

**User's choice:** パターン抽出と GSD 自動参照
**Notes:** ADR 本文には触れず、GSD が既存 ADR を自動参照できる状態を作ることに絞る。

---

## ADR 整理スコープ

| Option | Description | Selected |
|--------|-------------|----------|
| 索引+分類のみ (Recommended) | `docs/adr/INDEX.md` 作成、カテゴリ別分類、欠番はそのまま記録 | ✓ |
| 索引 + Status 付与 | 各 ADR に Accepted/Superseded/Deprecated を付与 | |
| 索引 + 本文リライト | 一部 ADR の本文を現状に合わせて更新 | |

**User's choice:** 索引+分類のみ
**Notes:** 本文は変更しない。欠番 0015-0017 は "欠番" と記録するのみ。

---

## patterns.md 置き場所

| Option | Description | Selected |
|--------|-------------|----------|
| `docs/patterns.md` | プロジェクトドキュメントの一部として `docs/` 直下 | |
| `.planning/patterns.md` (Recommended) | GSD ワークフロー固有の成果物として `.planning/` 配下、PROJECT.md と同階層 | ✓ |
| `docs/archi/patterns.md` | アーキテクチャドキュメント (`sequence.md`, `process.md`) と同じ場所 | |

**User's choice:** `.planning/patterns.md`
**Notes:** GSD が自動ロードしやすい場所に置く意図。

---

## 粒度・構造

| Option | Description | Selected |
|--------|-------------|----------|
| カテゴリ別のカタログ (Recommended) | 1 パターン 5-10 行、名前 + 要約 + ADR リンク | ✓ |
| 詳細な解説付きガイド | 1 パターン 30-50 行、使い所・コード例・anti-pattern を含む | |
| 最小限のリンク集 | 1 パターン 1 行要約と ADR リンクのみ | |

**User's choice:** カテゴリ別のカタログ
**Notes:** 詳細は ADR 本文を参照させる方針。

---

## GSD 統合方式

| Option | Description | Selected |
|--------|-------------|----------|
| canonical_refs に再帰的に追加 (Recommended) | CONTEXT.md の canonical_refs に patterns.md / INDEX.md を毎フェーズ記載する標準手順を CLAUDE.md に明記 | ✓ |
| CLAUDE.md から `@import` | `@.planning/patterns.md` で常時ロード | |
| gsd-phase-researcher の手順更新 | エージェント側指示に追加 | |
| 上記の複合 | CLAUDE.md + canonical_refs 手順の二重化 | |

**User's choice:** canonical_refs に再帰的に追加
**Notes:** コンテキスト肥大を避け、必要な時だけロードする方針。GSD 本体コードには手を入れない。

---

## カテゴリ分類

| Option | Description | Selected |
|--------|-------------|----------|
| テクノロジ層別 (Recommended) | Auth / LangGraph / MCP / Worker / Frontend / Infra / Data の 7 層 | ✓ |
| アプリケーション別 | Chat / SuperChat / Gems / Canvas / DebateChat / 共通基盤 | |
| 横断的な関心事 | エラーハンドリング / 認証 / ストリーミング / 永続化 / ... | |

**User's choice:** テクノロジ層別
**Notes:** CLAUDE.md の Architecture セクションと対応させる。

---

## パターンソース

| Option | Description | Selected |
|--------|-------------|----------|
| ADR のみ (Recommended) | 30 件の ADR を唯一のソースとする。「ADR が真実源」ルール強化 | ✓ |
| ADR + コードベース | ADR にないコードベース由来のパターンも含める | |

**User's choice:** ADR のみ
**Notes:** ADR にないパターンは patterns.md に載せず、必要なら先に ADR 化する。

---

## 更新運用

| Option | Description | Selected |
|--------|-------------|----------|
| 手動更新をルール化するのみ (Recommended) | `/create-adr` スキルと CLAUDE.md に更新義務を記載 | |
| 更新スクリプトを作る | `scripts/update-patterns.py` で ADR から INDEX.md を生成 | |
| pre-commit hook で自動生成 | コミット時に `docs/adr/` の変更を検知し `INDEX.md` を再生成 | ✓ |

**User's choice:** pre-commit hook で自動生成
**Notes:** INDEX.md は自動生成、patterns.md は手動更新（要約粒度は人間判断）という解釈で進める。

---

## Claude's Discretion

- `adr-categories.yaml` 方式 vs ADR 内マーカー方式の選択
- pre-commit hook の実装言語 (Python / Bash / Node)
- `INDEX.md` の具体的な表形式
- 既存 30 ADR の初期カテゴリマッピング（下書き後ユーザー確認）

## Deferred Ideas

- ADR 本文の Status 付与と Superseded 関係
- 欠番 0015-0017 の補完
- patterns.md の自動生成化
- コードベース由来のパターン（ADR 昇格経由で将来対応）
- GSD 本体ワークフロー (`~/.claude/get-shit-done/`) の改修
