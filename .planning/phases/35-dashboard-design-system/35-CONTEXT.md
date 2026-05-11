# Phase 35: ダッシュボード化 + レスポンシブ/デザイン統一 - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

初見ユーザーが迷わず Gems / Canvas / SuperChat / DebateChat を使い分けられるダッシュボード型メニューと、モバイル幅（タブレットまで）/ ダーク/ライト / 主要モダンブラウザでの破綻ゼロのデザイン統一を整備する。

**Phase 36 を見据えた設計**: 後続 Phase 36（ファイル入力 UI: 添付ボタン・画像/ファイルプレビュー・multimodal 非対応モデル警告）が破綻なく載ることを判断基準に含める。Phase 35 で先行して CSS 変数基盤・InputBar 構造・toolbar スロット予約まで行い、Phase 36 側の手戻りをゼロにする。

**対象要件:** UX-03（ダッシュボード化）、UX-04（レスポンシブ + デザイン破綻ゼロ）

**含まれないもの:**
- Phase 36 の添付機能本体（添付ボタンの実動作・プレビュー実装・multimodal 警告ロジック）
- チャット操作性そのもの（メッセージコピー、再送信、ストリーミング — Phase 34 scope）
- data-ai-role 属性（Phase 32 scope）
- UI バグ潰し（Mermaid hang、CollapsibleCodeBlock、chatscope バルーン幅 — Phase 39 scope）

</domain>

<decisions>
## Implementation Decisions

### Design Token Strategy (Area 1)
- **D-01:** CSS custom properties（CSS 変数）で design token を実装する。`:root` と `[data-theme="dark"]` に `--color-bg`, `--color-accent`, `--color-text`, `--color-border`, `--space-*`, `--font-*` 等を定義し、コンポーネント側は `var(--...)` で参照する。`isDark` 三項分岐を排除することがゴール。chatscope override も同じ変数を使う。
- **D-02:** Phase 35 の移行対象は **base layer + 主要 4 コンポーネント**（`MenuScreen.tsx`, `MessageArea.tsx`, `ThreadSidebar.tsx`, `Header.tsx`）。残り（CanvasPane, GemsScreen, AuthPanel, ChatAgGridTable, DebateChatApp, SuperChatApp, GemChatApp, CanvasChatApp, ChatApp 等）は gradual で後続フェーズ（または polish phase 39）にて移行。
  - **注意:** `MenuScreen.tsx` / `MessageArea.tsx` / `ThreadSidebar.tsx` は D-08（InputBar 分離）/ D-03（セクション型ダッシュボード化）でも同時に構造変更があるため、移行と再構築を 1 phase で統合する。

### Dashboard Redesign (Area 2)
- **D-03:** MenuScreen を **セクション型ダッシュボード**化する。「アプリケーション」「最近のスレッド」「その他」等の縦セクション構造で、Gems / Canvas / SuperChat / DebateChat の用途分けを明確化する。初見ユーザーが「どのアプリを最初に使うか」を判断できるレベルの情報設計（タイトル + 説明 + 例示）を目指す。
- **D-04:** 添付ファイル関連情報（最近アップロードしたファイル等）は MenuScreen に出さない。スレッド内階層に留める。Phase 36 / Phase 38 で必要性が生じたら再検討する（Phase 35 では placeholder も作らない）。
- **Claude's Discretion:** 具体的なセクション数・順序・最近スレッド表示件数・アプリカード内の情報密度（icon + title + description + 最終アクセス日時等を含めるか）は researcher / planner が決定する。グラデーションタイトル（Orochi Chat）は維持。

### Responsive Strategy (Area 3)
- **D-05:** モバイル対応は **タブレット（768-1024px）まで primary scope**、スマホ幅（375-767px）は **レイアウト破綻しない** ことのみ保証する（機能フル対応は容認）。Phase 36 の添付操作もタブレット幅では実用的に使える。スマホでは添付操作は UX 劣化前提。
- **D-06:** **desktop-first 2 breakpoint** 戦略。
  - `tablet`: `@media (max-width: 1024px)` — サイドバー折りたたみ / カード幅調整 / toolbar 縮小
  - `mobile`: `@media (max-width: 767px)` — レイアウト破綻回避（横スクロールゼロ・ボタン重なりゼロ）のみ保証
- **D-07:** PROJECT.md Out of Scope の「モバイル対応 — PC ブラウザのみ対象」は v6.0 で **policy 反転**。REQUIREMENTS.md UX-04 が新基準。Phase 35 完了時に PROJECT.md を更新する（phase 完了後の evolve ステップで `/gsd-evolve-project` または手動更新）。

### MessageArea Refactor (Area 4)
- **D-08:** `MessageArea.tsx` から **`InputBar` コンポーネントを分離**する。構造:
  ```
  <InputBar>
    <ToolbarSlot>        {/* 空。Phase 36 で 📎 添付ボタン / モデルセレクタを差し込む */}
    <PreviewSlot>        {/* 空。Phase 36 で添付チップ・画像サムネを差し込む */}
    <textarea>
    <SendButton>
    <CancelButton>
  </InputBar>
  ```
  既存機能（typing indicator、ストリーミング preview、QuestionPanel、resend、cancel）は MessageArea 側に残す。InputBar は controlled component として props 経由で state を受け取る。
- **D-09:** **添付ボタンの将来的な配置位置は textarea 左の toolbar 行**（ChatGPT / Claude 方式）。Phase 35 では空の toolbar スロットを確保し、Phase 36 がそこに差し込む。デスクトップ・タブレット両対応で実用的。
- **Claude's Discretion:** InputBar の props インターフェース詳細（onSend の signature、slot の React Node 受け取り方、controlled vs uncontrolled）、既存機能のマイグレーション粒度は planner が決定。

### Claude's Discretion
以下は研究 / 計画フェーズで判断する:
- CSS 変数の命名規則（`--chat-color-bg` vs `--color-chat-bg` vs `--cs-color-bg` 等）
- トークン階層（primitive: `--color-purple-500`、semantic: `--color-accent` の 2 層 vs 1 層のみ）
- chatscope の既存 CSS override との共存方法（変数で置換 vs override は据え置き）
- セクション型ダッシュボードの visual design（カード配置・spacing・secondary action 表示）
- 最近スレッド表示件数・group 分け（既存 ThreadSidebar の group 方式と整合）
- ThreadSidebar の mobile 時挙動（drawer 化 or collapse）
- Header の mobile 時挙動（stacked or hamburger menu）
- タブレット幅での chatscope バルーン width 調整値
- Phase 36 で使われる前提の追加スロット設計（InputBar 以外に attachment chip bar を別コンポーネント化するか等）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### パターンカタログ / ADR 索引
- `.planning/patterns.md` — ADR 由来のパターンカタログ（Frontend・UI セクションで chatscope バルーン制御、スレッドサイドバー日付グループ、AskUserQuestion プロトコル等を参照）
- `docs/adr/INDEX.md` — ADR カテゴリ別索引

### Phase 35 に直接関係する ADR
- `docs/adr/0037-chat-ui-batch-enhancements.md` — MessageInput を native textarea に置換した経緯、Mermaid render / SSE キャンセル分離 / collapsible code block
- `docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md` — Mermaid コピー / スレッドサイドバー日付グループ / 認証フロー改善
- `docs/adr/0043-chat-history-content-normalization-defense-in-depth.md` — BaseMessage.content 正規化 + ReactMarkdown ガード（MessageArea リファクタ時に壊さないこと）
- `docs/adr/0027-migrate-frontend-runtime-from-nodejs-to-bun.md` — Bun runtime（パッケージ追加時の前提）
- `docs/adr/0028-react-router-v7-url-based-routing-for-spa.md` — React Router v7、basename / nginx SPA fallback
- `docs/adr/0001-nginx-prefix-strip-for-url-routing.md` — `/orochi` prefix、VITE_APP_BASE

### 隣接 Phase のコンテキスト
- `.planning/ROADMAP.md` §Phase 35 / §Phase 36 — 本 phase の Goal と Phase 36 での受け皿要件
- `.planning/REQUIREMENTS.md` — UX-03 / UX-04 の定義、FIN-01〜04（Phase 36 が求めるファイル入力）
- `.planning/phases/37-pdf-office-mcp/37-CONTEXT.md` — 直近完了 phase、thread-files フォルダ規約が Phase 36 のアップロード先として決定済み
- `docs/adr/0048-thread-files-folder-convention.md` — Phase 36 が書き込む `/shared/thread-files/<github_login>/<thread_id>/` の規約

### 既存コード参照点（scout_codebase で特定）
- `frontend/src/theme.css` — 現行 `[data-theme="dark"]` overrides。CSS 変数化の移行元
- `frontend/src/contexts/ThemeContext.ts` + `frontend/src/hooks/useTheme.ts` — テーマ state 管理（変更なし予定）
- `frontend/src/components/MenuScreen.tsx` — D-03 ダッシュボード再構築対象、FeatureCard / SkeletonCard 既存
- `frontend/src/components/MessageArea.tsx` — D-08 InputBar 分離対象、500 行超
- `frontend/src/components/ThreadSidebar.tsx` — D-02 design token 移行対象、date group / filter 機能は維持
- `frontend/src/components/Header.tsx` — D-02 design token 移行対象
- `frontend/package.json` — `@chatscope/chat-ui-kit-react`（維持）、Tailwind は現状未導入

### 外部 UX リファレンス
- ChatGPT / Claude のメッセージ入力 UI（D-09 配置の参照 mental model）
- Gmail / Notion ダッシュボード（D-03 セクション型の参照、ただし実装は社内利用向けシンプル版で良い）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **ThemeContext + useTheme フック** (`frontend/src/contexts/ThemeContext.ts` / `frontend/src/hooks/useTheme.ts`): テーマ切替 state。CSS 変数化しても外側 API は変えない。
- **chatscope UI kit** (`@chatscope/chat-ui-kit-react`): 維持。`cs-*` クラスの override は theme.css で継続。
- **FeatureCard / SkeletonCard パターン** (`MenuScreen.tsx` 内の internal component): セクション型ダッシュボードでも再利用（装飾リッチ化）
- **ConfirmModal.tsx**: confirm dialog 既存。将来 mobile drawer 化時にも流用可能
- **date group + filter ロジック** (`ThreadSidebar.tsx`): D-02 移行時に roll-over（破壊しない）

### Established Patterns
- **`data-theme="dark"` 属性切替**: `<html>` に attribute を付ける方式。維持（D-01 の変数も同セレクタに定義）
- **chatscope `cs-*` クラス override**: `!important` で上書きする既存方針を継続。ただし値を CSS 変数経由にする
- **inline style + className 併用**: 現状の規範。Phase 35 後は「構造 props は inline、色/spacing は変数参照」に寄せる
- **ADR-0040 スレッドサイドバー日付グループ**: 今日/昨日/今週/先週/それ以前。D-02 の ThreadSidebar refactor で壊さない

### Integration Points
- **Phase 36（次）**: InputBar の ToolbarSlot に `<AttachmentButton />` と `<ModelSelector />` を差し込む。PreviewSlot に `<AttachmentChips />` を差し込む
- **Phase 32（未着手）**: `data-ai-role` 属性を新規セクション（MenuScreen、InputBar）にも付与する予定。命名規則に配慮
- **Phase 38（未着手）**: worker 生成ファイルのプレビューは MessageArea 側の MessageBubble 内に表示。D-04 により MenuScreen には出さない
- **Phase 39（未着手）**: chatscope バルーン幅（CollapsibleCodeBlock）/ Mermaid hang 等は Phase 35 スコープ外。ただし Phase 35 の CSS 変数導入が Phase 39 の修正を楽にする

### 既存コードの問題点（Phase 35 で解決）
1. **CSS 変数ゼロ**: 同じブランドカラー `#7c6ff7` が最低 10 ファイル・20 箇所以上に hardcoded。ダーク hex (`#1e1e2e`, `#2a2a3e`, `#3a3a52`) も同様に散在
2. **`@media` クエリゼロ**: `frontend/src/` 配下に media query が 1 件もない。responsive は未実装
3. **`MessageArea.tsx` 500 行超**: inline style が密集し、添付ボタン追加のスペースがない
4. **`isDark` 三項分岐**: テーマ state を JS 側で読んで三項で色を切り替える関数が各コンポーネントに散在。CSS 変数化で排除可能
5. **theme.css fragmentation**: per-component `[data-theme="dark"] .cs-foo` 上書きが 398 行にわたって並ぶ。token 化すれば 100 行以下に圧縮可能

</code_context>

<specifics>
## Specific Ideas

- **D-09 textarea 左 toolbar**: ChatGPT / Claude と同じメンタルモデル。`<Toolbar>[📎 添付] [モデル選択] ...</Toolbar> <textarea>` の横並び。ユーザーが迷わない。
- **D-03 セクション型**: Gmail の左パネル / Notion のホーム画面のような「セクション見出し + カード群」階層。widget 型より実装コストが低い。
- **D-01 CSS 変数**: `:root` に primitive + semantic の 2 層定義を推奨（例: `--color-purple-500` + `--color-accent`）。ただし具体は Claude's Discretion。

## Phase 36 へのハンドオフ契約

Phase 35 完了時点で Phase 36 が依拠できる前提:

1. **CSS 変数が定義済み** — `--color-accent`, `--color-bg`, `--color-text`, `--color-border`, `--space-*`, `--radius-*` 等（具体名は planner が決定）が `:root` と `[data-theme="dark"]` に存在
2. **`InputBar` コンポーネントが分離済み** — `frontend/src/components/InputBar.tsx` として独立、`ToolbarSlot` / `PreviewSlot` props を受け取る
3. **toolbar slot が空で予約済み** — Phase 36 は `<InputBar toolbarSlot={<AttachmentButton .../>} ...>` として差し込むだけで動く
4. **preview slot が空で予約済み** — Phase 36 は画像サムネ / ファイルチップをレンダリングする `<AttachmentChips />` を差し込むだけで動く
5. **tablet breakpoint が定義済み** — `@media (max-width: 1024px)` で InputBar の toolbar が縦並びに切り替わる等、Phase 36 の UI が破綻しない base が整っている
6. **`MenuScreen` のセクション構造が存在** — Phase 36 で「最近のアップロード」を足したくなった場合、セクション追加で対応可能（ただし D-04 により Phase 35 では不要）

</specifics>

<deferred>
## Deferred Ideas

- **Phase 36 scope**: 添付ボタン実動作・ファイルプレビュー実装・multimodal 非対応モデル警告バナー・FIN-01/02 実装
- **Phase 38 scope**: 「最近生成したファイル」を MenuScreen に表示（D-04 時点では不要）
- **Phase 39 scope**: chatscope バルーン幅（`CollapsibleCodeBlock` fit-content）、Mermaid hang、`test_sse.py` hang 修正（UIFIX-01 / 02 / 03）
- **v6.1+**: 全コンポーネントの design token 移行（Phase 35 は 4 コンポーネントまで）、スマホ幅（<=767px）の全機能対応、ネイティブモバイルアプリ、ダッシュボード widget 型（D-03 で採用見送り）
- **polish backlog**: `isDark` 三項の完全排除、inline style 完全撲滅（D-02 で部分対応）

</deferred>

---

*Phase: 35-dashboard-design-system*
*Context gathered: 2026-04-23*
