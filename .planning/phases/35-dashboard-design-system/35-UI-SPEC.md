---
phase: 35
slug: dashboard-design-system
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-23
---

# Phase 35 — UI Design Contract

> ダッシュボード化 + レスポンシブ/デザイン統一フェーズの UI 契約。gsd-ui-researcher が作成、gsd-ui-checker が検証する。
> 本契約は gsd-planner が CSS 変数タスク・MenuScreen 再設計・InputBar 分離・レスポンシブブレークポイント定義に変換する際の「確定済み決定事項」として消費される。

**対象要件:** UX-03 (MenuScreen ダッシュボード化)、UX-04 (レスポンシブ + デザイン破綻ゼロ)
**Phase 36 受け皿契約:** 本 SPEC §「Phase 36 Handoff Contract」参照。Phase 36 (FIN-01/02 添付 UI) が手戻りなく差し込めることを検証基準とする。

---

## Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none (CSS custom properties on `:root` + `[data-theme="dark"]`) | CONTEXT.md D-01 |
| Preset | not applicable | — |
| Component library | `@chatscope/chat-ui-kit-react@^2.1.1` (keep; override via CSS variables) | package.json |
| Icon library | 絵文字のみ (📎 / 💎 / 🎨 / 💬 / ☀️ / 🌙) — 新規アイコンライブラリは導入しない | CONTEXT.md scout |
| Font | システム default (`font-family: inherit`) + `Rajdhani` (タイトル "Orochi Chat" 専用) | Header.tsx / MenuScreen.tsx |
| shadcn ゲート判定 | N/A — CONTEXT.md D-01 で CSS custom properties を locked。shadcn 導入は scope 外 | CONTEXT.md D-01 |
| Theme 切替機構 | `<html data-theme="dark">` 属性切替 (既存維持 — `ThemeContext` / `useTheme` 変更なし) | CONTEXT.md code_context |

---

## Token Naming & Layering (Claude's Discretion #1, #2 決定)

### 命名規則: `--color-*` / `--space-*` / `--radius-*` / `--font-*` 系統

CSS 変数名は「**役割 (semantic) を primary とし、chatscope-specific override のみ `--cs-*` prefix を補助的に使う**」方針とする。

**決定理由:**
- `--chat-color-bg` は chatscope 以外 (MenuScreen・Header) でも使う値が混ざり、再利用を阻害する。
- `--cs-color-bg` を全体にふると非 chatscope コンポーネントに chatscope 依存が染み出す。
- `--color-bg` 中心の semantic naming なら、chatscope / app-specific / 将来の shadcn 併用いずれにも切り替え可能。

### 階層: **2 層 (primitive + semantic)**

| 層 | 目的 | 定義場所 | 参照方法 |
|----|------|---------|----------|
| Primitive | 生のブランドカラー・グレースケール | `:root` (theme 不変) | 直接参照禁止、semantic 層から `var()` 連鎖 |
| Semantic | 役割に紐づく抽象トークン | `:root` (light) + `[data-theme="dark"]` (dark) | コンポーネント側は必ず semantic 層を参照 |

**決定理由:**
- CONTEXT.md specifics §の推奨通り。
- primitive 層でブランド色を 1 箇所に固定することで「ダークモードだけ違う色に振る」柔軟性を確保しつつ、コンポーネント側の参照数を semantic 名に絞って読み替え可能に。
- Phase 36 で `--color-accent` を参照する添付ボタン追加時に、テーマ対応が自動で通る。

### Primitive Token 一覧 (定義: `:root`、theme 不変)

| 変数 | 値 | 現状 hardcoded 出現箇所 |
|------|----|------------------------|
| `--color-purple-300` | `#a78bfa` | MenuScreen / Header グラデーション |
| `--color-purple-500` | `#7c6ff7` | 主アクセント (10+ ファイルに hardcoded) |
| `--color-cyan-400` | `#38bdf8` | MenuScreen / Header グラデーション終端 |
| `--color-red-500` | `#e05252` | 削除ボタン・destructive |
| `--color-green-500` | `#22c55e` | AskMe ボタン (MessageArea) |
| `--color-blue-600` | `#0366d6` | New Chat / Send (light mode) |
| `--color-neutral-50` | `#f5f5f5` | MenuScreen 背景 (light) |
| `--color-neutral-100` | `#f6f8fa` | md-table header (light) |
| `--color-neutral-200` | `#e1e4e8` | md-table border (light) |
| `--color-neutral-300` | `#d1dbe3` | 入力欄 border (light) |
| `--color-neutral-400` | `#9090a8` | ダークテキスト muted |
| `--color-neutral-500` | `#888888` | ライトテキスト muted |
| `--color-neutral-700` | `#333333` | ライトテキスト primary |
| `--color-neutral-900` | `#24292e` | Header 背景 (light) |
| `--color-dark-bg` | `#1e1e2e` | ダーク primary surface |
| `--color-dark-surface` | `#2a2a3e` | ダーク secondary surface |
| `--color-dark-elevated` | `#313145` | ダーク hover / active |
| `--color-dark-border` | `#3a3a52` | ダーク border |
| `--color-dark-text` | `#e8e8f0` | ダーク primary text |

### Semantic Token 一覧 (定義: `:root` light + `[data-theme="dark"]` override)

| 変数 | Light 値 | Dark 値 | 用途 |
|------|---------|---------|------|
| `--color-bg` | `var(--color-neutral-50)` | `var(--color-dark-bg)` | 画面 primary 背景 (Dominant 60%) |
| `--color-surface` | `#ffffff` | `var(--color-dark-surface)` | カード / サイドバー / 入力バー (Secondary 30%) |
| `--color-surface-elevated` | `#ffffff` | `var(--color-dark-elevated)` | active thread item / hover |
| `--color-border` | `var(--color-neutral-300)` | `var(--color-dark-border)` | 区切り線・入力欄 border |
| `--color-text` | `var(--color-neutral-700)` | `var(--color-dark-text)` | primary テキスト |
| `--color-text-muted` | `var(--color-neutral-500)` | `var(--color-neutral-400)` | subtitle / 日付 / ヘルプ文 |
| `--color-accent` | `var(--color-purple-500)` | `var(--color-purple-500)` | 選択強調・send button・focus ring (Accent 10%) |
| `--color-accent-contrast` | `#ffffff` | `#ffffff` | accent 上のテキスト色 |
| `--color-accent-subtle` | `#e8f0fe` | `var(--color-dark-elevated)` | active thread 背景 |
| `--color-destructive` | `var(--color-red-500)` | `var(--color-red-500)` | 削除確認・エラーバナー |
| `--color-success` | `var(--color-green-500)` | `var(--color-green-500)` | AskMe ボタン (既存継続) |
| `--color-header-bg` | `var(--color-neutral-900)` | `var(--color-dark-bg)` | Header 背景 (light は暗め、dark は揃える) |
| `--color-header-text` | `#ffffff` | `var(--color-dark-text)` | Header テキスト |
| `--gradient-title` | `linear-gradient(90deg, var(--color-purple-300), var(--color-purple-500), var(--color-cyan-400))` | 同じ (theme 不変) | "Orochi Chat" タイトル (維持) |

### chatscope `cs-*` クラス override との共存 (Claude's Discretion #3 決定)

**方針: 変数駆動置換**
- `[data-theme="dark"] .cs-main-container { background: var(--color-dark-bg) !important; }` のように、theme.css 内の既存 `!important` 上書き自体は据え置き、色の値のみ CSS 変数に置換する。
- `!important` を外すと chatscope 内部スタイルに負ける fragile さは変わらないため、段階的解消は scope 外 (polish phase 39+)。
- **副次メリット**: theme.css 398 行のうち、重複色定義ブロックが 100 行程度に圧縮される (CONTEXT.md 既存問題点 #5)。

---

## Spacing Scale (Claude's Discretion: 標準 8-point scale)

CSS 変数として定義。値は multiples of 4。

| Token | 変数 | 値 | Usage |
|-------|------|----|------|
| `3xs` | `--space-1` | 4px | アイコンと文字の gap、1px border の隣接 |
| `2xs` | `--space-2` | 8px | コンパクト要素間、chip 内 padding |
| `xs` | `--space-3` | 12px | 小ボタン padding (`0.75rem` 相当) |
| `sm` | `--space-4` | 16px | 既定要素間、カード内 padding 下限 |
| `md` | `--space-6` | 24px | カード内 padding、セクション見出し下 margin |
| `lg` | `--space-8` | 32px | セクション間 gap (MenuScreen) |
| `xl` | `--space-12` | 48px | major セクション break |
| `2xl` | `--space-16` | 64px | page-level (MenuScreen 外側 padding 上限) |

**例外:**
- タップターゲット最低高さ **36px** を維持 (既存 Send / AskMe ボタンの `height: '36px'`)。タブレット幅では **40px** に引き上げ (`@media (max-width: 1024px)`)。
- Header 高さ **48px** は既存値を維持 (デスクトップ)。タブレット幅でも 48px のまま。
- 既存 chatscope バルーン内の装飾スペーシング (`theme.css` §Markdown 部) は据え置き。

**radius スケール:**

| 変数 | 値 | Usage |
|------|----|------|
| `--radius-sm` | 4px | inline 入力欄、小ボタン |
| `--radius-md` | 6px | 標準ボタン、textarea、filter input |
| `--radius-lg` | 12px | ダッシュボード card、Skeleton card |
| `--radius-full` | 9999px | avatar (`50%` → 明示化) |

---

## Typography

| Role | 変数 | Size | Weight | Line Height | Usage |
|------|------|------|--------|-------------|-------|
| Body | `--font-body` | 16px | 400 (regular) | 1.5 | デフォルト本文 (`rem` base = 16px 前提) |
| Label | `--font-label` | 14px | 400 | 1.4 | ボタンラベル、サイドバー item、フィルタ (`0.85rem` → 14px に揃える) |
| Heading | `--font-heading` | 20px | 600 (semibold) | 1.3 | ダッシュボードセクション見出し、card タイトル |
| Display | `--font-display` | 44.8px | 700 (bold) | 1.1 | "Orochi Chat" タイトル (既存 `2.8rem` を維持) |

**追加 (必要最小限):**

| 変数 | 値 | 用途 |
|------|----|------|
| `--font-caption` | 12px / 400 / 1.4 | 日付スタンプ、helper text、filter count (`0.7-0.78rem` 相当) |
| `--font-family-display` | `'Rajdhani', sans-serif` | "Orochi Chat" タイトル専用 |
| `--font-family-body` | system-ui, `-apple-system`, `BlinkMacSystemFont`, `'Segoe UI'`, sans-serif | その他全て (`inherit` の明示化) |

**決定理由:**
- 既存 MenuScreen / Header / MessageArea で使われている `0.7rem` / `0.75rem` / `0.78rem` / `0.8rem` / `0.82rem` / `0.85rem` / `0.9rem` / `0.95rem` / `1rem` / `1.25rem` / `2rem` / `2.8rem` の 12 段階を **5 段階 (12 / 14 / 16 / 20 / 44.8) に統合**する。
- 3-4 段階制約は守りつつ、チャット UI 特有の caption (日付) のために +1 段階 (12px) を許容する。weight は regular (400) / semibold (600) / bold (700) の 3 段のうち、display 専用に bold を確保、本文 2 段とする契約に合致。

---

## Color (60/30/10 契約)

| Role | 変数 | Light 値 | Dark 値 | Usage |
|------|------|---------|---------|-------|
| Dominant (60%) | `--color-bg` | `#f5f5f5` | `#1e1e2e` | MenuScreen / MessageList 背景、画面地 |
| Secondary (30%) | `--color-surface` | `#ffffff` | `#2a2a3e` | カード、ThreadSidebar、chat-input-bar、Header (dark) |
| Accent (10%) | `--color-accent` | `#7c6ff7` | `#7c6ff7` | 下記 reserved-for リストの要素限定 |
| Destructive | `--color-destructive` | `#e05252` | `#e05252` | 削除確認モーダル、エラーバナー、削除ボタン hover |

### Accent (`#7c6ff7`) reserved-for リスト

**使用可能な場所 (これ以外には使わない):**
1. Send ボタン背景 (InputBar)
2. New Chat ボタン背景 (ThreadSidebar)
3. textarea / filter input の `:focus` ring (`border-color`)
4. active thread item の左 3px アクセントボーダー (tablet 以降の視認性向上)
5. ダッシュボードカード `:hover` 時の border グラデーションまたは focus ring
6. "Orochi Chat" タイトルのグラデーション (purple-300 → purple-500 → cyan-400)
7. AuthPanel の link (Device Flow URL リンク)

**使ってはいけない例:**
- 通常テキスト、通常 border、通常ボタン (非 primary)、タブレット/モバイルでの装飾過多、カード全面塗り潰し、Header 背景。

**副次セマンティック色 (destructive / success):**
- `--color-destructive` (`#e05252`): 削除確認モーダル confirmLabel、bulk delete ボタン、sidebar-thread-delete-btn hover。
- `--color-success` (`#22c55e`): AskMe ボタン枠 (既存継続。accent ではない理由は AUQ が破壊的でないから)。

---

## Responsive Breakpoints (CONTEXT.md D-05, D-06 準拠)

**Desktop-first 2 breakpoint:**

| Breakpoint | 変数 | 条件 | 保証内容 |
|-----------|------|------|---------|
| Desktop | — | default (> 1024px) | 全機能フル (ベースライン) |
| Tablet | `--bp-tablet` | `@media (max-width: 1024px)` | レイアウト適応 + UX 実用レベル |
| Mobile | `--bp-mobile` | `@media (max-width: 767px)` | **破綻回避のみ** (横スクロールゼロ・重なりゼロ)、機能劣化許容 |

**注:** `--bp-tablet` / `--bp-mobile` は CSS `@media` 内で直接数値を書く (CSS 変数は media query 値としては使えない仕様) が、JS 側で参照する必要があればエクスポートする。ドキュメント上は参照値として契約に含める。

### コンポーネント別レスポンシブ挙動契約

| コンポーネント | Desktop | Tablet (≤1024px) | Mobile (≤767px) |
|---------------|---------|------------------|-----------------|
| **MenuScreen** | カード `grid-template-columns: repeat(auto-fill, minmax(220px, 1fr))`、padding `48px 32px`、max-width 960px | 1 列 or 2 列 auto-fill (minmax(180px, 1fr))、padding `24px 16px` | 1 列固定、padding `16px 12px`、"Orochi Chat" 1 行維持 (font-size 維持) |
| **ThreadSidebar** | 固定幅 (既存 width prop `collapsed:40px / expanded:auto`) を維持 | **collapse デフォルト** + トグルで drawer として右に overlay (position: fixed, z-index: 50, 背景 backdrop 50% 黒半透明) | collapse のみ (drawer 同様の overlay)、幅 `min(80vw, 320px)` |
| **Header** | 既存 flex 横並び (back / title / appName / model / avatar / login / logout / theme) | Model select のラベル "Model:" を視覚的に隠す (`aria-label` で AT 向けは残す)、login username を省略 (avatar のみ表示)、logout ボタンテキスト → アイコン化 (🚪 or 既存文字を短縮) | title 以外を「…」hamburger メニュー (ConfirmModal 流用は不要、シンプルな `<details>` ベース drop で十分) |
| **MessageArea + InputBar** | 横長 (chat-input-bar padding `12px 12px`) | chat-input-bar padding `10px 10px`、tablet で toolbarSlot が 1 行に収まらない場合は縦積み可 (toolbar 改行) | textarea 左右 padding `8px`、toolbarSlot は 2 行許容、Send ボタンは必ず表示 |
| **ThreadSidebar の drawer 化 (tablet/mobile)** | N/A | hamburger トグル: Header に `menu` ボタンを追加 (Claude's Discretion #6 決定: **drawer を採用、collapse ではない**)。drawer open 時は backdrop click で close | 同左 |

### chatscope バルーン幅 tablet 調整 (Claude's Discretion #8 決定)

Tablet (≤1024px) 時:
- `.cs-message--incoming` は既存の `max-width: 100% !important; width: 100%` を維持 (Monaco / AG Grid が狭まらないため)。
- `.cs-message--outgoing .cs-message__content-wrapper { max-width: 85% !important; }` を新規追加 (desktop は chatscope default の `fit-content` を維持)。ユーザーメッセージがモバイル寄りの画面で改行しすぎて縦に伸びるのを防ぐ。

Mobile (≤767px) 時:
- 両 `--incoming` / `--outgoing` に `max-width: 100%` で強制、Monaco は横スクロール前提 (scope 外 — UIFIX-02 Phase 39)。

---

## Dashboard Visual Design (Claude's Discretion #4 決定)

### セクション構成 (縦順)

| 順 | セクション | 見出し | 内容 |
|----|-----------|--------|------|
| 1 | タイトル | (見出し無し、既存 h1) | "Orochi Chat" グラデーションタイトル + サブタイトル "Choose an application to get started" |
| 2 | **アプリケーション** | `h2` "アプリケーション" (`--font-heading`) | Gems / Canvas / 討論チャット + `GET /api/apps` の dynamic アプリカード群 (grid) |
| 3 | **最近のスレッド** | `h2` "最近のスレッド" (`--font-heading`) | 直近 5 件のスレッドカード (横 list or 1-2 列 grid) + "すべてのスレッドを見る" CTA。API は **既存の `GET /api/threads` を使い、client side で `updated_at` desc ソート・先頭 5 件スライス** (Claude's Discretion #5 決定) |
| 4 | **その他** | `h2` "その他" (`--font-heading`) | (将来枠) - Phase 35 では空 or "アプリが足りない場合は管理者に相談" level の helper text 1 文のみ (D-04 尊重: 最近アップロード/生成ファイルは置かない) |

**決定理由:**
- 3 セクションは「アプリ (今すぐ何をやるか) / 履歴 (続ける) / その他 (逃げ道)」の迷わない 3 分岐。Gmail/Notion ダッシュボードの簡易版。
- "最近のスレッド" は 5 件固定: 200名規模で 5 件以上は ThreadSidebar に委譲するのが moral hazard なし。
- "その他" セクションを今から作る理由: Phase 36 (添付)・Phase 38 (出力) で再登場する可能性があるため、空枠を残すのみ。

### カード情報密度

**アプリカード (`FeatureCard` 拡張):**

| 要素 | 内容 | Phase 35 の扱い |
|------|------|----------------|
| Icon | 絵文字 (2rem) | 既存維持 |
| Title | 1 行 (`--font-heading` weight 600) | 既存維持 |
| Description | 2 行まで (`--font-label`) | 既存維持 |
| Last access (最終アクセス日時) | — | **含めない** (Phase 35 scope: app-level アクセス履歴 API 未整備。必要時は Phase 36 以降で追加) |
| Hover | translateY(-2px) + box-shadow | 既存維持、色は CSS 変数化 |
| Focus ring | 2px outline `--color-accent` | **新規追加** (accessibility 強化) |

**最近のスレッドカード (新規):**

| 要素 | 内容 |
|------|------|
| Icon | アプリアイコン (スレッドが属するアプリの絵文字) |
| Title | thread.label (1 行、truncate) |
| Date group | 日付グループラベル ("今日" / "昨日" / "今週" 等、ThreadSidebar と同ロジックの再利用) |
| Click | 対応アプリに遷移 + threadId select |

### グリッド・余白

- アプリカード grid: `grid-template-columns: repeat(auto-fill, minmax(220px, 1fr))`、gap `--space-4` (16px)、max-width 960px。
- 最近のスレッドカード grid: `repeat(auto-fill, minmax(240px, 1fr))`、gap `--space-3` (12px)。
- セクション間 gap: `--space-8` (32px)。
- 画面外側 padding: `--space-12 --space-8` (desktop)、tablet `--space-6 --space-4`、mobile `--space-4 --space-3`。

---

## InputBar Contract (CONTEXT.md D-08, D-09 準拠)

### ファイル配置

**新規:** `frontend/src/components/InputBar.tsx`

### Props Interface (Claude's Discretion #9 決定)

```ts
interface InputBarProps {
  // 送信系
  value: string;
  onChange: (next: string) => void;
  onSend: (text: string, contextMessages?: ContextMessage[]) => void;
  onCancel?: () => void;  // thinking 中のみ有効
  onAskMe?: () => void;   // AUQ 起動

  // 状態
  disabled?: boolean;
  isThinking?: boolean;   // true なら Send → Cancel 切替
  placeholder?: string;

  // スロット (Phase 36 で埋まる)
  toolbarSlot?: React.ReactNode;    // textarea 左の横並び toolbar (📎 / ModelSelector 等)
  previewSlot?: React.ReactNode;    // textarea 上の添付チップ・画像サムネ帯

  // UX 補助 (Phase 35 では InputBar 外で描画するが、prop 経由で差し込み可)
  copyAllSlot?: React.ReactNode;    // 既存の CopyAllButton を差し込む枠
}
```

**決定理由:**
- `value` / `onChange` を分離 (controlled) することで MessageArea 側が inputValue state を保持し続け、resend / AUQ submit 時の state 連動を維持する。
- `onSend` は既存 MessageArea のシグネチャをそのまま踏襲 (`contextMessages?: ContextMessage[]`) — 将来 ContextMessage 送信をボタンから起動する拡張を殺さない。
- slot は **named React.ReactNode props** として渡す (`toolbarSlot={<AttachmentButton .../>}`)。children 1 つだと「どこに差し込むか」で迷うため禁止。
- `isThinking` で Send / Cancel を切り替える責務は InputBar 内に閉じる。MessageArea は「何を送るか」だけ管理し、UI branch は持ち込まない。

### 内部レイアウト

```
┌────────────────────────────────────────────┐
│ [previewSlot]              ← Phase 36 で埋まる: 添付チップ・画像サムネ
├────────────────────────────────────────────┤
│ [toolbarSlot]  [textarea]  [AskMe] [Send]  ← 1 行 (desktop)
│                            [AskMe] [Send]  ← 2 行 (tablet 狭) — textarea と Send の間に toolbar 改行
└────────────────────────────────────────────┘
│ [copyAllSlot] (flex-end)                    │ ← 既存 CopyAllButton (MessageArea から差し込み)
```

- toolbarSlot は **textarea の左側** (D-09 確定: ChatGPT / Claude メンタルモデル)。
- 各スロットが空 (`null` / `undefined`) なら、その帯は DOM に出さない (空帯を残さない)。
- textarea は既存 `className="chat-textarea"` + inline style を CSS 変数参照に置換。`rows={1}` + `onInput` で auto-resize は既存ロジックを InputBar に移設。
- Send / Cancel は同じ位置 (textarea 右) に排他表示 (Cancel は `isThinking && onCancel` が両方 true の時のみ)。

### 追加で分離する子コンポーネント (Claude's Discretion #10 決定)

**Phase 35 ではしない。**

Phase 36 で PreviewSlot 内に `<AttachmentChips />`、ToolbarSlot 内に `<AttachmentButton />` / `<ModelSelector />` を差し込む段階で判断する。Phase 35 の責務は slot を「空で予約する」までで止める。理由:
- slot は `React.ReactNode` で型付けしてあり、子コンポーネント化は差し込む側の自由度。
- Phase 36 で凝集しすぎる設計を先に作ると、添付仕様に合わない可能性がある。

---

## Component Migration Scope (CONTEXT.md D-02 準拠)

Phase 35 でトークン移行する 4 + 1 コンポーネント。**それ以外は触らない**。

| # | コンポーネント | 変更種別 | 主な変更内容 |
|---|---------------|---------|-------------|
| 1 | `frontend/src/theme.css` (変数基盤) | 新規 + 既存圧縮 | `:root` + `[data-theme="dark"]` に全 primitive / semantic 変数を宣言、既存 398 行の hex を `var(--...)` に置換 |
| 2 | `MenuScreen.tsx` | リデザイン + 変数移行 | セクション型ダッシュボード化、`isDark` 三項排除、CSS 変数参照、focus ring 追加 |
| 3 | `MessageArea.tsx` | InputBar 分離 + 変数移行 | InputBar を外に出す、入力 UI は props 受け渡しで維持、変数参照 |
| 4 | `InputBar.tsx` | 新規 | 上記 Props Interface 通り |
| 5 | `ThreadSidebar.tsx` | 変数移行 + tablet drawer | date group 維持、drawer 化対応、`isDark` 三項排除 |
| 6 | `Header.tsx` | 変数移行 + mobile 対応 | hamburger menu (mobile)、`isDark` 三項排除 |

**触らないコンポーネント** (Phase 35 scope 外 — Phase 39 以降の polish で再訪):
- `CanvasPane`, `GemsScreen`, `AuthPanel`, `ChatAgGridTable`, `DebateChatApp`, `SuperChatApp`, `GemChatApp`, `CanvasChatApp`, `ChatApp`, `QuestionPanel`, `GemSelector`, `ConfirmModal`, `MermaidBlock`, `MarkdownMessage`

ただし `AuthPanel` は既存 `auth-*` クラスが theme.css に残っているため、**変数差し替えのみ (構造変更なし)** は許容 (1-line diff 相当)。

---

## Copywriting Contract

全て日本語 (CLAUDE.md 規約)。技術用語・ボタン名で英語が混在する箇所 (Send / New Chat / Menu など) は既存踏襲。

### MenuScreen

| 要素 | Copy |
|------|------|
| タイトル (h1) | `Orochi Chat` (既存維持) |
| サブタイトル | `使いたいアプリを選んで始めましょう` (既存 "Choose an application..." を日本語化) |
| セクション h2 (アプリ) | `アプリケーション` |
| セクション h2 (最近) | `最近のスレッド` |
| セクション h2 (その他) | `その他` |
| "すべてのスレッドを見る" CTA | `すべてのスレッドを見る →` (最近スレッドセクション右上) |
| 空アプリ heading | `利用可能なアプリがありません` (既存 "No applications available" を日本語化) |
| 空アプリ body | `apps/ ディレクトリに APP.md を追加するとアプリとして認識されます。` |
| 空スレッド heading | `まだ会話がありません` |
| 空スレッド body | `上のアプリカードから新しい会話を始められます。` |
| エラー alert | `アプリ一覧を取得できませんでした。ページを再読み込みしてください。` (既存英語文言の日本語化) |

### InputBar

| 要素 | Copy |
|------|------|
| Primary CTA (Send) | `送信` (既存 "Send" を日本語化。ラベルのみ変更、短縮記号 →や矢印は追加しない) |
| Cancel | `キャンセル` (thinking 中表示時) |
| AskMe | `AskMe` (既存踏襲、AUQ の固有機能名として維持) |
| Placeholder | `Copilot に何でも聞いてみてください... (Ctrl+Enter で送信)` (既存英語の日本語化) |

### ThreadSidebar

| 要素 | Copy |
|------|------|
| New Chat | `+ 新しいチャット` (既存 "+ New Chat" の日本語化) |
| Filter placeholder | `会話を絞り込む...` (既存 "Filter conversations..." の日本語化) |
| 全選択 / 全解除 | 既存維持 (日本語) |
| `N件削除` | 既存維持 |
| Filter count | `N / M 件一致` (既存 "N / M matches" の日本語化) |
| Empty (no threads) | `まだ会話がありません` (既存 "No conversations yet" の日本語化) |
| Empty (no matches) | `一致する会話がありません` (既存 "No matches" の日本語化) |
| 日付グループラベル | 既存維持 (今日/昨日/今週/先週/それ以前) |

### Header

| 要素 | Copy |
|------|------|
| Back to menu | `‹ メニュー` (既存 "‹ Menu" の日本語化) |
| Model: | `モデル:` (desktop のみ、tablet 以下は aria-label のみ) |
| Logout | `ログアウト` (既存維持) |
| Theme toggle aria-label | `ライトモード / ダークモードを切り替え` (既存英語の日本語化) |

### Destructive Confirmations (既存 ConfirmModal 経由)

| Action | Copy (message) | confirmLabel |
|--------|---------------|--------------|
| Logout | `ログアウトしますか？` (既存維持) | `ログアウト` |
| Thread 単体削除 | `「{label}」を削除しますか？` (既存維持) | `削除` |
| Thread 一括削除 | `{N}件のスレッドを削除しますか？` (既存維持) | `{N}件削除` |

**Phase 35 では新規 destructive action は導入しない** (CONTEXT.md scope 外)。

### Error State

| 要素 | Copy |
|------|------|
| アプリ一覧取得エラー | `アプリ一覧を取得できませんでした。ページを再読み込みしてください。` (role="alert", destructive 色の枠) |
| スレッド一覧取得エラー | `スレッド一覧を取得できませんでした。時間を置いて再度お試しください。` (MenuScreen 最近セクション内) |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | — | not applicable (shadcn 未導入) |
| third-party registries | — | 宣言なし |

**判定:** CONTEXT.md D-01 で CSS custom properties が locked。新規 UI コンポーネントライブラリは導入しない。Safety Gate N/A。

---

## Phase 36 Handoff Contract (CONTEXT.md Phase 36 契約の検証可能化)

Phase 35 完了時点で Phase 36 (FIN-01/02 添付 UI) が手戻りなく着手できるための検証ポイント。Planner はこのリストを task acceptance criteria に分解する。

| # | 要件 | 検証方法 |
|---|------|---------|
| 1 | `:root` に下記 semantic 変数が全て定義されている: `--color-bg` / `--color-surface` / `--color-surface-elevated` / `--color-border` / `--color-text` / `--color-text-muted` / `--color-accent` / `--color-accent-contrast` / `--color-accent-subtle` / `--color-destructive` / `--color-success` / `--color-header-bg` / `--color-header-text` / `--space-1..16` / `--radius-sm/md/lg/full` / `--font-body/label/heading/display/caption` / `--font-family-body/display` / `--gradient-title` | `grep -E '^\s*--color-(bg\|surface\|border\|text\|accent\|destructive\|success)' frontend/src/theme.css` で 13 件以上ヒット |
| 2 | `[data-theme="dark"]` に同じ semantic キーの dark 値が全て override されている | 同 grep を `[data-theme="dark"]` ブロック内に限定して同数 |
| 3 | `frontend/src/components/InputBar.tsx` が存在し、export する関数コンポーネントが上記 Props Interface を満たす | `grep "toolbarSlot" frontend/src/components/InputBar.tsx` が 1 件以上、`grep "previewSlot"` も同 |
| 4 | `InputBar` は `toolbarSlot` を textarea の左側に、`previewSlot` を textarea の上に render する (空の場合は帯を出さない) | スクリーンショット or storybook ベースの目視 (gsd-ui-checker) |
| 5 | MessageArea.tsx は InputBar をインポートし、既存の UX (typing indicator / streamPreview / QuestionPanel / resend / cancel) はすべて retain されている | 既存 e2e manual 手順で regression なし |
| 6 | `@media (max-width: 1024px)` の媒介クエリが theme.css または各コンポーネント CSS に最低 3 箇所 (MenuScreen / Header / InputBar) に定義されている | `grep -rn "@media" frontend/src` で該当行数 >= 3 |
| 7 | `@media (max-width: 767px)` の媒介クエリも最低 3 箇所 (MenuScreen / ThreadSidebar / Header) に定義されている | 同様に grep |
| 8 | MenuScreen が「アプリケーション / 最近のスレッド / その他」の 3 セクションを持ち、Phase 36 で "最近のアップロード" を 4 番目として追加可能な構造 | MenuScreen 内 `<section>` または見出し付き div が 3 つ (aria-labelledby で確認) |
| 9 | ブランドカラー `#7c6ff7` が新規に hardcoded で追加されていない (移行対象 4 ファイル外も含めて `--color-accent` 経由で参照される) | `grep -rn "#7c6ff7" frontend/src --exclude=theme.css` の件数が phase 35 開始前と同等以下 (ゴール: 変数経由で 0 件に近づく、Phase 35 は移行対象 4 ファイル分だけ減る許容) |
| 10 | Chrome 最新 / Edge 最新 / Safari 最新 (UX-04) の 3 ブラウザで、desktop + tablet 幅で MenuScreen / Chat / ThreadSidebar drawer がレイアウト破綻なく表示される | gsd-ui-checker の手動目視 + スクリーンショット (ダーク/ライト × desktop/tablet = 4 パターン最低) |

**Phase 36 側が破る可能性のある契約 (Phase 35 で先に防御する):**
- Phase 36 の `<AttachmentButton>` / `<AttachmentChips>` 内部で `#7c6ff7` を再 hardcode しないよう、Phase 35 で `--color-accent` を公開契約としてドキュメント化 (本 SPEC §Token Layering で実施済み)。
- Phase 36 のプレビューチップが多すぎた場合に PreviewSlot が InputBar を押し上げて textarea を潰さないよう、previewSlot は `max-height: 120px; overflow-y: auto;` を InputBar 側で付与する (本 SPEC §InputBar Contract 内部レイアウト注釈で確定)。

---

## Visual Accessibility Baseline

Phase 35 では本格対応は scope 外 (Phase 32/33 で AI-UI 操作基盤と並走する想定) だが、新規追加コンポーネントが既存水準を下回らないこと:

| 項目 | 要件 |
|------|------|
| Focus ring | 新規追加ボタン (ダッシュボードカード・drawer hamburger・InputBar 分離後の button) に `:focus-visible` で 2px outline `--color-accent` を付与 |
| キーボード操作 | 既存挙動を破壊しない (Tab / Enter / Escape)。drawer 化時は Escape で閉じる |
| ARIA | drawer の hamburger に `aria-expanded` / `aria-controls`、drawer 自体に `role="dialog"` or `aria-modal` を付ける |
| Color contrast | `--color-text` on `--color-bg` が WCAG AA (4.5:1) を満たす (既存値で満たしている想定、Checker で確認) |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: 日本語統一、CTA/エラー/空状態すべて定義済み
- [ ] Dimension 2 Visuals: ダッシュボード 3 セクション構造、InputBar スロット契約
- [ ] Dimension 3 Color: 60/30/10 split、accent reserved-for リスト明示
- [ ] Dimension 4 Typography: 4-5 段階 + 2 weight (+ display bold)、行間契約
- [ ] Dimension 5 Spacing: 8-point scale、例外明示 (36px/40px タップターゲット)
- [ ] Dimension 6 Registry Safety: N/A (shadcn 未導入、third-party なし)

**Approval:** pending
