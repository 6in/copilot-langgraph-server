# 0055. docs/getting-started/ サブフォルダで onboarding ドキュメントを集約する

**Date:** 2026-05-13
**Status:** Accepted

## Context

本番 200 名規模のロールアウトを控え、「このシステムで何ができるか」を一望できる利用者向けドキュメントが不在だった (todo `2026-05-13-document-chat-system-capabilities-tools-agents-apps-overview.md`)。情報は以下に散らばっていた:

- `README.md` には概要と起動手順、5 アプリの table はあるが「いつどれを使うか」「アプリ間の違い」「典型ユースケース」のような利用者目線の整理がない
- `docs/mcp-tools.md` は `config/mcp_tools.yaml` から自動生成される技術仕様で、利用者視点のユースケース説明には向かない
- `agents/<slug>/AGENT.md` は SubAgentRegistry が自動ロードする内部設定ファイルで、利用者から見て「SuperChat で選べるエージェントとそれぞれの得意分野」を一覧する場所として機能していない
- Gem テンプレ・初期サンプル・onboarding hints が一切ない

利用者向け文書を 4 ファイル (reading-order index / apps-guide / agents catalog / tools-for-users) 新規追加するにあたり、それらを `docs/` 直下に並べると、既に存在する技術リファレンス (`mcp-tools.md` / `nginx.md` / `trace-query-recipes.md` / `mcp-tool-add-manual.md` / phase 別 integration check ノート / `archi/` / `adr/` / `slides/`) と混在してさらに散らかる懸念があった。

実装直後の中間状態 (commit `2e77751`) では実際に 4 ファイルを `docs/` 直下に置いたが、ユーザーから「docs フォルダが散らかっているのでサブフォルダに集約しよう」と指摘を受け、再配置することにした。

## Decision

利用者向け onboarding ドキュメントは **`docs/getting-started/`** サブフォルダに集約する。技術リファレンスドキュメントは引き続き `docs/` 直下に置く。

具体的なファイル配置:

- `docs/getting-started/index.md` — reading-order エントリーポイント (5 トラック構成: ユーザー / パワーユーザー / 開発者 / 拡張担当 / 運用調査)
- `docs/getting-started/apps-guide.md` — 5 アプリの判断フローと典型ユースケース
- `docs/getting-started/agents.md` — SubAgent カタログ + Gem との違い
- `docs/getting-started/tools-for-users.md` — MCP ツールのユースケース別整理

`README.md` の「ドキュメントの読み方」セクションと「関連資料」セクションは `docs/getting-started/index.md` を起点として案内する。

**docs/ 直下に残すもの (技術リファレンス):**

- `mcp-tools.md` (自動生成) / `mcp-tool-add-manual.md` / `nginx.md` / `trace-query-recipes.md`
- `archi/` (シーケンス図・プロセス図) / `adr/` (本ファイル群) / `slides/`
- `phase-*.md` (phase 別 integration check / spike ノート — 履歴扱い)

**今後 docs を追加する際の判断基準:**

- 「初めて触る人 / 利用者がまず読むもの」→ `docs/getting-started/` 配下
- 「特定機能の技術仕様・運用調査クエリ・設計記録」→ `docs/` 直下 (または `docs/archi/` や `docs/adr/`)

## Alternatives Considered

### A. `README.md` を章立てで大幅拡充

`README.md` 内に「ユーザーガイド」「アプリ判断フロー」「エージェントカタログ」等を追記し、外部ファイル分割を避ける案。

**却下理由:** 4 ファイル合計 538 行を `README.md` に詰めると、起動手順や環境変数といった「最初に読まれるべき情報」が深く埋もれてしまう。`README.md` は概要 + 起動経路に専念、深掘り情報は外部ファイルへ、というのが既存の構成スタイル (CLAUDE.md / docs/* 群) と整合する。

### B. ユーザー向け / 開発者向けで README を分離 (`README.user.md` + `README.dev.md`)

ルート直下に 2 ファイル並列で置く案。

**却下理由:** リポジトリ標準は `README.md` 単一エントリ。README が複数あると新規参画者がどちらを開くべきか迷う。`docs/getting-started/index.md` を案内する形のほうが「reading order が `docs/` に集約される」という一貫性が出る。

### C. すべてを `docs/` 直下に並列配置 (中間状態 commit `2e77751`)

`docs/index.md` `docs/apps-guide.md` `docs/agents.md` `docs/tools-for-users.md` を直接置いた案。最初の実装はこの形だった。

**却下理由:** ユーザー指摘の通り `docs/` 直下のファイル数が膨れ上がる。`mcp-tools.md` (技術自動生成) と `apps-guide.md` (利用者向け手書き) が同じ階層にあると、新規ドキュメント追加時に「どこに置くべきか」の判断軸が定まらない。サブフォルダで「読者の役割別に物理分離」したほうが将来の判断コストが下がる。

### D. `docs/user-guide/` や `docs/onboarding/` 命名

`getting-started/` の代わりに他の命名を採用する案。

**却下理由:** `getting-started/` は OSS / 技術ドキュメントの慣用表現 (e.g. Vite, Next.js, Stripe API docs) で、新規参画者にとって意味が即座に伝わる。`user-guide/` だと「機能リファレンス全部」のニュアンスが入りやすく、`onboarding/` だと「初日だけ読むもの」というニュアンスでスコープが狭くなる。

## Consequences

### Positive

- **新規参画者の reading order が明確化:** `README.md` → `docs/getting-started/index.md` → 役割別 3 ファイルという階段が出来た
- **物理分離による判断軸の固定:** 新規ドキュメント追加時に「利用者向けか / 技術リファレンスか」の二択で配置先が決まる
- **`docs/` 直下のファイル数を抑制:** 自動生成・技術系ファイルのみが残り、何を見るべきかが視覚的にも明瞭

### Negative / Gotchas

- **相対パスの 1 段深さ調整が必要:** `docs/getting-started/*.md` から `../CLAUDE.md` (project root の CLAUDE.md は `../../CLAUDE.md`)、`../archi/sequence.md` 等への参照は注意。リネーム時に `../` 階数の手動更新が発生する (今回 11 箇所)
- **`docs/getting-started/index.md` 内の「索引: ファイル種別マップ」も追従更新が必要:** 索引内のパス表記がリポジトリ実体と乖離すると陳腐化する
- **将来「半ば利用者向け / 半ば開発者向け」のドキュメントが出てきた場合は判断が割れる可能性:** その時は本 ADR の決定軸 (「初めて触る人がまず読むか」) を基準に判断する
- **`docs/getting-started/index.md` は手書き索引なので、新規ドキュメント追加時の追記漏れリスクあり:** 索引末尾の「新規ドキュメント追加時の追記ルール」を遵守して防止する

### Migration record

- 初期実装 commit `2e77751` — `docs/` 直下に 4 ファイル新規作成
- リネーム commit `f2ad294` — `git mv` で `docs/getting-started/` 配下へ集約。すべての rename は 90%+ 類似度で履歴維持 (66% は index.md でパス参照を 1 段深く修正したため)
- 影響を受けた相対パス参照: 11 箇所 (`../README.md` → `../../README.md`、`./adr/INDEX.md` → `../adr/INDEX.md` 等)
- `README.md` の入り口 6 箇所も追従更新済み
