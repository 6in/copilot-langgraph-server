# 0034. ADR カタログ化と patterns.md による GSD プランニング統合

**Date:** 2026-04-15
**Status:** Accepted

## Context

プロジェクト蓄積 ADR は 30 件（0001-0033、欠番 0015-0017）まで増え、再利用可能な設計判断が埋もれ始めていた。GSD の discuss/plan フェーズでは過去 ADR が自動参照されず、毎回人間が canonical_refs に手で積み直すか、そもそも参照されずに同じ議論を繰り返す状態だった。

同時に、`docs/adr/` に索引がなく 30 件のカテゴリ全体像を把握しづらい、新規 ADR 追加のたびに索引を手で並べ替える必要がある、という運用コストも顕在化していた。

目標は「過去の意思決定を *次のフェーズで自動的に効く形* にする」こと。ADR 本文の書き直しや Status 付与のような重い整備ではなく、索引化 + パターン抽出 + GSD ワークフローへの接続口を作ることに絞った。

## Decision

3 つの成果物でカタログ化と GSD 統合を実現する:

1. **`.planning/patterns.md`** — ADR 由来のパターンカタログ。7 カテゴリ（`Auth` / `LangGraph・Graph` / `MCP・Tools` / `Worker・Jobs` / `Frontend・UI` / `Infra・Deploy` / `Data・Persistence`）別にパターン名 + 要約 2-4 行 + 関連 ADR 相対リンクを記載。1 エントリ 5-10 行。`PROJECT.md` / `REQUIREMENTS.md` と同階層に置き、GSD 固有資産として位置づける。
2. **`docs/adr/INDEX.md`** — ADR 索引。`.planning/adr-categories.yaml`（番号 → primary/secondary カテゴリ）を元に `scripts/generate_adr_index.py` が自動生成。欠番 0015-0017 を `## 欠番` セクションに明示的に記録する。pre-commit hook (`scripts/install-hooks.sh` で導入) が `docs/adr/*.md` 変更時に自動再生成する。
3. **GSD 統合** — `CLAUDE.md` に ADR Pattern Reference ルールを追加し、各フェーズの CONTEXT.md の `canonical_refs` に `.planning/patterns.md` と `docs/adr/INDEX.md` を毎回記載する標準手順を明文化。`.claude/commands/create-adr.md` に patterns.md 更新リマインダを追加し、新規 ADR 作成フローで自然にパターンカタログが更新される経路を作った。

スコープ制約:
- **D-03:** ADR 本文は一切変更しない（索引化のみ）
- **D-04:** 欠番 0015-0017 は "欠番" として記録するだけで補完しない
- **D-05:** Status 付与（Accepted/Superseded/Deprecated）は行わない（全 ADR を Accepted 前提）
- **D-08:** patterns.md のソースは ADR のみ（コードベース直接由来のパターンは追加禁止 → ADR 唯一真実源ルールの強化）
- **D-12:** `CLAUDE.md` への `@.planning/patterns.md` の常時 `@import` はしない（コンテキスト肥大回避、必要なフェーズでのみ canonical_refs 経由でロード）
- **D-13:** GSD 本体（`~/.claude/get-shit-done/`）のコードには手を入れず、本リポジトリ側で完結させる

## Alternatives Considered

- **`CLAUDE.md` から patterns.md を `@import` で常時ロード:** 最もシンプルだが全セッションで 30 ADR 分のコンテキストを消費する。フェーズ単位のオプトインに劣る (D-12)。
- **`docs/` 配下に patterns.md を置く:** 一般的な配置だが `.planning/` に置くことで GSD ワークフロー固有の資産として可視化でき、`PROJECT.md` / `STATE.md` と並ぶ参照階層が自然になる (D-06)。
- **INDEX.md を手動メンテ:** ADR を追加するたびに並べ替えコストが発生し、欠番や日付の記載漏れリスクがある。pre-commit hook で自動生成する方が運用コストゼロ (D-14)。
- **patterns.md も自動生成化:** パターン名と要約の粒度は人間判断が必要で、機械生成では 30 ADR を 21 パターンに凝縮する判断ができない。手動更新 + create-adr スキルのリマインダ方式を採用 (D-15)。
- **ADR 側にカテゴリメタデータ（コメントマーカーなど）を埋める:** ADR 本文変更を伴うため D-03 違反。外部マッピングファイル `.planning/adr-categories.yaml` に分離。
- **GSD 本体の gsd-phase-researcher / gsd-planner エージェント定義を改修:** 本リポジトリ外（`~/.claude/get-shit-done/`）の変更になるため、単一リポジトリで完結できる CLAUDE.md ルール + create-adr スキル拡張で代替 (D-13)。

## Consequences

**Positive:**
- 過去 30 件の設計判断が 7 カテゴリ 21 パターンに凝縮され、新規フェーズで `canonical_refs` に 2 ファイル書くだけで過去資産が効くようになった
- pre-commit hook で INDEX.md が常に最新化され、人間が並べ替える必要がなくなった（新規 ADR 追加時のコストはほぼゼロ）
- `.planning/adr-categories.yaml` が ADR のカテゴリマッピング単一情報源となり、patterns.md / INDEX.md 両方から参照される（二重管理回避）
- ADR 0020 の異種フォーマット（`# ADR 0020:` / `**Date**:`）も正規表現で両対応しており、将来フォーマット揺らぎがあってもスクリプト修正で吸収できる

**Negative / Gotchas:**
- **pre-commit hook はリポジトリに自動インストールされない:** `.git/hooks/` は git で追跡されないため、新規クローン後に `bash scripts/install-hooks.sh` を手動実行する必要がある。この手順は `CLAUDE.md` の GSD Workflow Enforcement セクションに記載したが、忘れると INDEX.md が古くなる
- **patterns.md は手動更新:** 新規 ADR 追加時に patterns.md 追記と `.planning/adr-categories.yaml` への番号追加を忘れる可能性がある。`.claude/commands/create-adr.md` のステップ 6 がリマインダとして機能するが、`/create-adr` スキル経由で ADR を作らず手動で ADR を書いた場合は漏れる
- **正規表現のもろさ:** `TITLE_RE` / `DATE_RE` は現行 ADR フォーマットに合わせて調整済み。Plan 26-01 実行中に初期設計の `\*?\*?:?` が `**Date:**` にマッチしないバグを発見し `[*:\s]+` 文字クラス方式に修正した経緯があり、今後新しいフォーマット揺らぎが出たら同様の修正が必要
- **7 カテゴリの境界:** ADR 0014 (Auth + Worker・Jobs) のような複数カテゴリに跨る ADR は primary に置き secondary でクロスリンクする方針だが、patterns.md 側では primary のみで表現している。secondary 関連を追いたいときは `adr-categories.yaml` を直接見る必要がある
- **ADR 唯一真実源ルールの副作用:** コードベースから直接抽出したい有用パターン（例: ChatCopilot の BaseChatModel ラッパー実装手順、FastAPI lifespan 構成）は先に ADR 化しないと patterns.md に載せられない。この制約は意図的（D-08）だが、ADR 化の手間がボトルネックになる可能性がある
