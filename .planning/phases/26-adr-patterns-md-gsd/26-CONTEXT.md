# Phase 26: ADR 整理 + patterns.md 作成 + GSD プランニング統合 - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

これまで蓄積した 30 件の ADR (`docs/adr/`) から「再利用可能なパターン」を抽出してカタログ化し、GSD の discuss/plan フェーズが自動的にそれらを参照できる状態にする整備フェーズ。過去の意思決定を"次のフェーズで自動的に効く形"にする。

**In scope:**
- `.planning/patterns.md` の新規作成（ADR 由来のパターンカタログ）
- `docs/adr/INDEX.md` の新規作成（ADR 索引 + カテゴリ分類）
- pre-commit hook による `INDEX.md` 自動生成
- GSD `discuss-phase` ワークフローの canonical_refs 標準手順更新（`.planning/patterns.md` と `docs/adr/INDEX.md` を毎フェーズ記載）
- `CLAUDE.md` への運用ルール追記

**Out of scope:**
- ADR 本文の書き直し・Status 付与・廃止判定
- 欠番 0015-0017 の補完（欠番として記録するだけ）
- コードベースから直接パターンを抽出すること（ADR にないパターンは載せない）
- GSD agent / skill 自体のコード改修
- `CLAUDE.md` への `@import` でのグローバルロード

</domain>

<decisions>
## Implementation Decisions

### フェーズゴール
- **D-01:** Phase 26 のゴールは「ADR からパターンを抽出して GSD が自動参照する状態を作ること」。ADR 本文リファクタや GSD ワークフローの本格改修は対象外。
- **D-02:** 成果物は 3 つ: (1) `.planning/patterns.md` (2) `docs/adr/INDEX.md` (3) `discuss-phase` ワークフロー側の canonical_refs 標準手順更新 + `CLAUDE.md` への運用ルール追記。

### ADR 整理スコープ
- **D-03:** ADR 整理は索引化 + カテゴリ分類のみ。本文は変更しない。
- **D-04:** 欠番 0015-0017 は "欠番" として INDEX.md に明示的に記録するだけで、補完はしない。
- **D-05:** Status 付与（Accepted/Superseded/Deprecated）は本フェーズでは行わない。現状 ADR は全て "Accepted" の前提で索引する。

### patterns.md の置き場所と形式
- **D-06:** `.planning/patterns.md` に置く。`PROJECT.md` / `REQUIREMENTS.md` / `STATE.md` と同階層に並べることで、GSD ワークフロー固有の成果物として位置づける。`docs/` 配下には置かない。
- **D-07:** 構造はカテゴリ別カタログ形式。1 パターンあたり 5-10 行（パターン名 + 要約 + 関連 ADR 番号リンク）。詳細解説は書かず、リンク先の ADR を参照させる。
- **D-08:** パターンソースは **ADR のみ**。ADR にないパターンは載せない。これにより「ADR が唯一の真実源」ルールを強化する。

### カテゴリ分類
- **D-09:** カテゴリはテクノロジ層別の 7 カテゴリ: `Auth` / `LangGraph・Graph` / `MCP・Tools` / `Worker・Jobs` / `Frontend・UI` / `Infra・Deploy` / `Data・Persistence`。`CLAUDE.md` の Architecture セクションと対応させる。
- **D-10:** `patterns.md` と `docs/adr/INDEX.md` で同じカテゴリ分類を使用する（1 ADR が複数カテゴリにまたがる場合は主カテゴリに置き、副カテゴリからクロスリンク）。

### GSD 統合メカニズム
- **D-11:** 統合方式は **canonical_refs への再帰的追加**。`.planning/patterns.md` と `docs/adr/INDEX.md` を各フェーズの CONTEXT.md の `canonical_refs` セクションに毎回記載する標準手順を `discuss-phase.md` ワークフローと `CLAUDE.md` に明記する。
- **D-12:** CLAUDE.md への `@.planning/patterns.md` 等の `@import` での常時ロードはしない。コンテキスト肥大を避けるため、必要なフェーズでのみ canonical_refs 経由で読み込む。
- **D-13:** 既存の gsd-phase-researcher / gsd-planner のエージェント定義コードには手を入れない（GSD 本体は `~/.claude/get-shit-done/` 配下で、本リポジトリ外）。本リポジトリ側で完結する統合にとどめる。

### 運用・メンテナンス
- **D-14:** 新規 ADR 追加時の `INDEX.md` 更新は **pre-commit hook で自動生成**する。hook は `docs/adr/*.md` の変更を検知して `INDEX.md` を再生成する。`docs/adr/` 配下の ADR ファイルを走査し、H1 タイトルと "**Status:**" 行を読んでカテゴリ別に並べる。カテゴリ判定は ADR 側にマーカー（例: `<!-- category: Frontend -->` あるいはファイル名プレフィックス）を導入するか、明示的なマッピングファイル `.planning/adr-categories.yaml` を使うかは計画段階で決める。
- **D-15:** `patterns.md` 本体は手動更新。新規 ADR 追加時に「パターンとして patterns.md にも追記する」運用ルールを `CLAUDE.md` と `/create-adr` スキルの実行指示に追記する。自動生成しない（要約の粒度は人間判断が必要なため）。

### Claude's Discretion
- `adr-categories.yaml` を使うか ADR 内マーカーを使うかは計画段階で決めてよい（保守性優先）。
- pre-commit hook の言語（Python / Bash / Node）は既存プロジェクトの hook 規約に合わせる。
- `INDEX.md` の具体的な表形式（マークダウンテーブル / 入れ子リスト）は Claude が決めてよい。
- 既存の `docs/adr/` 30 件を 7 カテゴリにどう振り分けるかの初期マッピングは Claude が下書きし、ユーザー確認を受ける。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### ドキュメント配置と既存構造
- `CLAUDE.md` — プロジェクト規約、Architecture セクション、GSD ワークフロー強制ルール
- `.planning/PROJECT.md` — プロジェクトビジョンと非交渉事項
- `.planning/STATE.md` — 現在の進捗とマイルストーン情報
- `docs/adr/` — 既存 30 件の ADR（0001-0033, 0015-0017 欠番）
- `docs/archi/sequence.md`, `docs/archi/process.md` — アーキテクチャドキュメント（配置参考）

### GSD ワークフロー側の参照
- `~/.claude/get-shit-done/workflows/discuss-phase.md` — canonical_refs セクションの既存標準手順（読み取り専用。改修しない）
- `~/.claude/skills/create-adr/` — 新規 ADR 作成スキル（patterns.md 更新ルールを追記する候補）

### 類似実装の参考
- 既存の `.planning/phases/*/*-CONTEXT.md` — canonical_refs セクションの書式例
- `docs/adr/0033-canvas-ai-model-selection-with-alias-whitelist.md` — ADR フォーマット標準（H1 + `**Date:**` + `**Status:**` + Context/Decision/Consequences）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`docs/adr/` 命名規約**: `NNNN-slug.md` 形式で 0001-0033 まで連番。pre-commit hook からパース容易。
- **ADR フォーマット統一**: 全 ADR が `# NNNN. Title` / `**Date:**` / `**Status:**` ヘッダーを持ち、正規表現で抽出可能。
- **`.planning/` 階層**: `PROJECT.md` / `REQUIREMENTS.md` / `STATE.md` / `ROADMAP.md` が既に置かれており、`patterns.md` を並べても違和感がない。

### Established Patterns
- **CLAUDE.md のルール駆動**: プロジェクト規約（マージ手順・GSD 強制など）を CLAUDE.md に集約する方針が既に存在。運用ルール追加もこれに従う。
- **pre-commit hook**: 現状プロジェクトに git hook の明示的な運用があるかは計画段階で確認が必要（Phase 26 で新規導入の可能性あり）。

### Integration Points
- `CLAUDE.md` → 新しい運用ルール追記ポイント（ADR 追加時の INDEX/patterns 更新義務）
- `.planning/` → `patterns.md` 新規追加
- `docs/adr/` → `INDEX.md` 新規追加 + 必要ならカテゴリメタデータ
- git hooks → pre-commit フック（新規または既存を拡張）

</code_context>

<specifics>
## Specific Ideas

- **patterns.md の 1 パターンエントリの想定形式（例）:**
  ```
  ### Token Streaming (AI 応答のトークンストリーミング)
  Copilot SDK のトークンストリームを worker → SSE → frontend の 3 層で中継する。
  関連 ADR: [0031](./docs/adr/0031-copilot-sdk-token-streaming-three-layer-plumbing.md)
  ```
- **INDEX.md の想定形式:** カテゴリ見出し下にマークダウンテーブル (No. / タイトル / Date) を並べる。欠番は "— 欠番 —" と明示。
- **ユーザーは「ADR が唯一の真実源」を強く意識している:** patterns.md にコードベース由来のパターンを含めない決定はこの思想と整合する。

</specifics>

<deferred>
## Deferred Ideas

- **ADR 本文の Status 付与と Superseded 関係のマッピング** — 将来フェーズで実施。今回は全 ADR が Accepted 前提で索引化。
- **欠番 ADR 0015-0017 の補完** — 別フェーズで必要になったときに検討。
- **`patterns.md` の自動生成化** — 現状は手動運用。将来、パターン記述が安定してきたら ADR メタデータから自動生成することも検討可。
- **コードベース直接由来のパターン集（例: ChatCopilot の BaseChatModel ラッパー実装手順、lifespan 構成）** — ADR に昇格させてから patterns.md に載せる方針。別フェーズで ADR 化を検討。
- **GSD 本体ワークフロー (`~/.claude/get-shit-done/`) の改修** — 今回は本リポジトリ側で完結させる。GSD 側への patch は別途検討。

</deferred>

---

*Phase: 26-adr-patterns-md-gsd*
*Context gathered: 2026-04-15*
