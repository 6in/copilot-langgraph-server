# Phase 35: ダッシュボード化 + レスポンシブ/デザイン統一 - Research

**Researched:** 2026-04-23
**Domain:** React 19 + Vite + TypeScript における CSS 変数ベースデザインシステム導入、レスポンシブ媒介クエリ初導入、controlled InputBar コンポーネント分離
**Confidence:** HIGH（既存コード調査は現物ベースで HIGH、外部推奨パターンは MEDIUM、@chatscope と CSS 変数の coexist 細部は LOW を明示）

---

## Summary

Phase 35 は既に `35-CONTEXT.md` の D-01〜D-09 および `35-UI-SPEC.md`（トークン階層 / 60/30/10 / Props Interface / Phase 36 Handoff Contract 10 項目）で **設計判断のほとんどが locked 済み**。本 RESEARCH は「planner がタスク分解で迷わないように、locked 決定をコード実装手順に落とすための具体情報」を補完することに徹する。新規フレームワーク導入なし（Tailwind / styled-components / CSS Modules / @media ライブラリはすべて NO）、プレーン CSS + inline style のみで完遂可能であることを verification した。

**Primary recommendation:** theme.css を **2 層構造に reorganize**（先頭に `:root` primitive / `[data-theme="dark"]` semantic 定義ブロックを追加、既存 398 行の hex 値を grep ベースで `var(--...)` に機械的置換）→ MessageArea.tsx から InputBar.tsx を controlled component として分離（`value`/`onChange`/`onSend`/`toolbarSlot`/`previewSlot` props）→ MenuScreen をセクション型に再構築 → 4 コンポーネント + theme.css の inline style を `var()` 参照に置換 → theme.css 末尾に `@media (max-width: 1024px)` と `@media (max-width: 767px)` ブロックを 1 箇所に集約。並列化可能な作業単位が明確なので Wave 0（変数基盤 + Wave 0 テスト）→ Wave 1（コンポーネント変数移行 + InputBar 分離）→ Wave 2（レスポンシブ + MenuScreen 再設計）→ Wave 3（accessibility + 整合検証）の 4 波構成が自然。

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Design Token Strategy (Area 1)**
- **D-01:** CSS custom properties（CSS 変数）で design token を実装する。`:root` と `[data-theme="dark"]` に `--color-bg`, `--color-accent`, `--color-text`, `--color-border`, `--space-*`, `--font-*` 等を定義し、コンポーネント側は `var(--...)` で参照する。`isDark` 三項分岐を排除することがゴール。chatscope override も同じ変数を使う。
- **D-02:** Phase 35 の移行対象は **base layer + 主要 4 コンポーネント**（`MenuScreen.tsx`, `MessageArea.tsx`, `ThreadSidebar.tsx`, `Header.tsx`）。残り（CanvasPane, GemsScreen, AuthPanel, ChatAgGridTable, DebateChatApp, SuperChatApp, GemChatApp, CanvasChatApp, ChatApp 等）は gradual で後続フェーズ（または polish phase 39）にて移行。
  - 注意: `MenuScreen.tsx` / `MessageArea.tsx` / `ThreadSidebar.tsx` は D-08（InputBar 分離）/ D-03（セクション型ダッシュボード化）でも同時に構造変更があるため、移行と再構築を 1 phase で統合する。

**Dashboard Redesign (Area 2)**
- **D-03:** MenuScreen を **セクション型ダッシュボード** 化（「アプリケーション」「最近のスレッド」「その他」の 3 セクション縦構造）。
- **D-04:** 添付ファイル関連情報は MenuScreen に出さない（placeholder も作らない）。

**Responsive Strategy (Area 3)**
- **D-05:** **タブレット（768-1024px）まで primary scope**、スマホ幅（375-767px）は **レイアウト破綻しない** ことのみ保証（機能フル対応は容認）。
- **D-06:** **desktop-first 2 breakpoint** 戦略。tablet `@media (max-width: 1024px)` / mobile `@media (max-width: 767px)`。
- **D-07:** PROJECT.md Out of Scope「モバイル対応 — PC ブラウザのみ対象」は v6.0 で policy 反転。Phase 35 完了時に PROJECT.md を更新。

**MessageArea Refactor (Area 4)**
- **D-08:** `MessageArea.tsx` から **`InputBar` コンポーネントを分離**。`toolbarSlot`（空）+ `previewSlot`（空）を予約。既存機能（typing indicator、streamPreview、QuestionPanel、resend、cancel）は MessageArea 側に残す。InputBar は controlled component。
- **D-09:** 添付ボタンの将来的な配置位置は **textarea 左の toolbar 行**（ChatGPT / Claude 方式）。Phase 35 では空の toolbar スロットを確保し、Phase 36 がそこに差し込む。

### Claude's Discretion（UI-SPEC で確定済み）

- 命名規則: 役割（semantic）primary + chatscope-specific のみ `--cs-*` 補助 → 採用される規則は `--color-*` / `--space-*` / `--radius-*` / `--font-*`（UI-SPEC §Token Naming で決定）
- 階層: **2 層（primitive + semantic）** — primitive は `:root` 固定、semantic は `:root` light + `[data-theme="dark"]` override
- chatscope override: **変数駆動置換**。`!important` は据え置き、値のみ `var()` に（polish scope 外）
- ダッシュボード構成: 3 セクション（アプリケーション / 最近のスレッド / その他）、"最近" は `GET /api/threads` を client-side で `updated_at` desc sort、先頭 5 件
- カード情報密度: `FeatureCard` 拡張、最終アクセス日時は Phase 35 では含めない
- ThreadSidebar mobile: **drawer 化**（position: fixed + backdrop、`min(80vw, 320px)`）
- Header mobile: hamburger menu（`<details>` ベースでシンプルに）
- InputBar Props: `value`/`onChange`/`onSend`/`onCancel`/`onAskMe`/`disabled`/`isThinking`/`placeholder`/`toolbarSlot`/`previewSlot`/`copyAllSlot`（UI-SPEC §InputBar Contract で確定）
- tablet chatscope バルーン: `.cs-message--outgoing .cs-message__content-wrapper { max-width: 85% !important }` を tablet 限定で追加
- 日本語コピー: すべて日本語統一（UI-SPEC §Copywriting Contract）

### Deferred Ideas（OUT OF SCOPE）

- **Phase 36 scope**: 添付ボタン実動作、ファイルプレビュー実装、multimodal 非対応モデル警告バナー、FIN-01/02 実装
- **Phase 38 scope**: 「最近生成したファイル」を MenuScreen に表示
- **Phase 39 scope**: chatscope バルーン幅（`CollapsibleCodeBlock` fit-content）、Mermaid hang、`test_sse.py` hang 修正（UIFIX-01 / 02 / 03）
- **v6.1+**: 残り 9 コンポーネントの design token 移行、スマホ幅（≤767px）の全機能対応、ネイティブモバイルアプリ、ダッシュボード widget 型（D-03 で採用見送り）
- **polish backlog**: `isDark` 三項の完全排除（Phase 35 は対象 4 コンポーネントのみ）、inline style 完全撲滅

</user_constraints>

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UX-03 | メニュー画面がダッシュボード化され、Gems/Canvas/SuperChat/DebateChat の使い分けが明瞭で初見ユーザーでも迷わない | §Dashboard Redesign 実装手順、UI-SPEC §Dashboard Visual Design の 3 セクション構成、`FeatureCard` 拡張手順、`GET /api/threads` client-side slice |
| UX-04 | UI がモバイル幅でも動作し、ダークモード・クロスブラウザ・chatscope バルーン幅などのデザイン破綻が解消される | §CSS 変数導入手順、§レスポンシブ実装戦略、§chatscope override 共存方針、§ブラウザ互換 `:focus-visible` / `@media`、§Validation Architecture（Chrome/Edge/Safari × light/dark × desktop/tablet マトリクス） |

</phase_requirements>

---

## Architectural Responsibility Map

Phase 35 は全て **Browser / Client** 単一階層で完結する。API 追加・backend 変更・worker 変更はゼロ。

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CSS 変数定義（primitive + semantic） | Browser (theme.css) | — | 全面 CSS で完結。JS/TS 実行不要 |
| `isDark` 三項排除 | Browser (React Component inline style) | — | `var()` でブラウザが theme 自動解決 |
| MenuScreen セクション型ダッシュボード | Browser (React Component) | — | `GET /api/apps` / `GET /api/threads` は既存。client-side sort + slice |
| InputBar 分離（controlled component） | Browser (React Component) | — | state は MessageArea に残し props 経由で注入 |
| レスポンシブ（tablet/mobile 挙動） | Browser (CSS @media) | — | CSS 媒介クエリのみ。`useMediaQuery` hook は不採用（後述） |
| ThreadSidebar drawer 化 | Browser (React + CSS) | — | `position: fixed` + backdrop で overlay |
| Header hamburger menu | Browser (React + `<details>` または state + CSS) | — | シンプル度最優先、focus trap は許容 |
| Phase 36 Handoff 検証可能化 | Browser (grep + manual screenshot) | Repository (test infra) | `grep` で verifiable な項目は CI 可、visual 項目は manual checker |

**何も触らない**: FastAPI routes、arq worker、MCP server、LangGraph graph、PostgreSQL スキーマ、Copilot SDK、Dockerfile、vite.config.ts（proxy 設定）、main.tsx（BrowserRouter 設定）、App.tsx（Routes 定義）、useTheme.ts / ThemeContext.ts。

---

## Standard Stack

### Core（追加導入ゼロ）

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.4（既存） | UI Component | 既存維持。`forwardRef` 不要で ref が通常 props として扱える点が InputBar 分離で有利 |
| TypeScript | 5.9.3（既存） | 型 | 既存維持 |
| Vite | 8.0.1（既存） | Build | 既存維持。CSS import は `main.tsx` で既に `import './theme.css'` 済み |
| `@chatscope/chat-ui-kit-react` | 2.1.1（既存） | Message / Sidebar UI | 据え置き。D-02 scope で override は theme.css 経由のみ |
| `@chatscope/chat-ui-kit-styles` | 1.4.0（既存） | chatscope 基本 CSS | 据え置き。`main.tsx` で import 済み |

### 新規導入: なし

**検証結果:** Phase 35 の実装に必要な全機能（CSS 変数、`@media`、`:focus-visible`、`position: fixed` drawer、controlled component）は **追加パッケージゼロ** で達成可能。UI-SPEC §Registry Safety の「shadcn 未導入、third-party なし」を維持。

### Alternatives Considered（すべて不採用）

| 代替案 | Could Use | Tradeoff | 判定 |
|--------|-----------|----------|------|
| Tailwind CSS | `tailwindcss ^3.x` | ユーティリティクラスで breakpoint が書きやすいが、全コンポーネント書き換え + chatscope `!important` 合戦。D-01 で採用見送り済み | **不採用（CONTEXT.md D-01）** |
| CSS Modules | (Vite 標準) | Scoped CSS は欲しいが、inline style との混在で理解コスト増 | **不採用** |
| styled-components / Emotion | `styled-components ^6.x` | theme provider が取れるが、runtime cost と JS bundle 増 | **不採用** |
| `useMediaQuery` hook | 自作 or MUI | JS 側で breakpoint を読めるが、state 同期ズレ・hydration mismatch リスク。Phase 35 では CSS `@media` のみで足りる | **不採用（JS 側で breakpoint 読まない方針）** |
| Radix UI Slot | `@radix-ui/react-slot` | `asChild` pattern で polymorphic だが、InputBar の slot は固定位置でよく named props で十分 | **不採用** |
| React Aria / react-aria-components | `react-aria` | Drawer の accessibility が堅牢だが、追加依存大。UI-SPEC §Visual Accessibility Baseline の最低線は自前で満たせる | **不採用（focus trap 許容の判断）** |

**Installation:**
```bash
# Phase 35 では実行不要。既存依存のみで完遂する。
```

**Version verification [VERIFIED: frontend/package.json]:**
- `react@^19.2.4`（2026-04 時点の React 19 系最新メジャー）
- `@chatscope/chat-ui-kit-react@^2.1.1`
- `vite@^8.0.1`
- `typescript@~5.9.3`

---

## Architecture Patterns

### System Architecture Diagram

**Phase 35 のデータフロー（既存との差分のみ）:**

```
[User opens /orochi/]
   ↓
App.tsx (Routes)
   ↓
MenuScreenRoute → MenuScreen.tsx
   ↓ （新規）
  Section 1: アプリケーション — getApps() で既存カード + 固定 3 カード
  Section 2: 最近のスレッド — listThreads() → sort by updated_at desc → slice(0, 5)
  Section 3: その他 — Phase 35 では helper text のみ
   ↓
[User clicks card] → navigate('/chat') etc.
   ↓
ChatRoute → ChatApp → MessageArea.tsx
   ↓ （Phase 35 で構造変更）
  MessageArea: messages state + inputValue state + streamPreview + QuestionPanel + pendingQuestion
   ↓ （新規分離）
  <InputBar
     value={inputValue} onChange={setInputValue}
     onSend={doSend} onCancel={onCancel} onAskMe={handleAskMe}
     isThinking={isThinking} disabled={disabled}
     toolbarSlot={null}        // ← Phase 36 が埋める
     previewSlot={null}        // ← Phase 36 が埋める
     copyAllSlot={<CopyAllButton ...>}  // 既存 UX 維持
  />

[CSS 変数解決フロー（Phase 35 新規）]
   ↓
<html data-theme="dark" | "light">  (既存 useTheme hook で設定)
   ↓
:root { --color-bg: #f5f5f5; --color-purple-500: #7c6ff7; ... }  (light)
[data-theme="dark"] { --color-bg: var(--color-dark-bg); ... }    (dark override)
   ↓
Component inline style: { background: 'var(--color-bg)' }
   ↓
Browser がテーマ切替時に自動再計算（React 再レンダー不要）
```

### Recommended Project Structure（差分）

**新規ファイル:**
```
frontend/src/
├── components/
│   └── InputBar.tsx         ← 新規（~120 行目安）
```

**変更ファイル:**
```
frontend/src/
├── theme.css                ← 398 行 → ~500 行（primitive + semantic block 追加 + @media block 追加、既存 hex を var() 置換）
├── components/
│   ├── MessageArea.tsx      ← 489 行 → ~340 行（InputBar 部分の抜き出し + inline style を var() に、isDark 三項除去）
│   ├── MenuScreen.tsx       ← 296 行 → ~350 行（セクション化 + 最近スレッドカード追加、inline style 変数化）
│   ├── ThreadSidebar.tsx    ← 498 行 → ~550 行（drawer 化の state + backdrop 追加、変数化）
│   └── Header.tsx           ← 208 行 → ~260 行（hamburger menu 追加、変数化）
```

**触らないファイル**: App.tsx、main.tsx、index.html、vite.config.ts、eslint.config.js、package.json、tsconfig.*、その他 components/（CanvasPane, GemsScreen, AuthPanel, ChatAgGridTable, DebateChatApp, SuperChatApp, GemChatApp, CanvasChatApp, ChatApp, QuestionPanel, GemSelector, ConfirmModal, MermaidBlock, MarkdownMessage）。ただし `AuthPanel` は theme.css 内の `.auth-*` クラス値が変数化される波及で**間接的に色が揃う**（これは意図した正の副作用 — UI-SPEC §Component Migration Scope）。

### Pattern 1: 2 層 CSS 変数トークン（primitive → semantic）

**What:** ブランド色・グレースケールを primitive 層に固定し、role-based な semantic 層が `var()` で参照する。semantic 層のみ `[data-theme="dark"]` で上書きする。
**When to use:** 複数テーマ対応 + chatscope 等の外部 UI kit と共存が前提の時。
**Example:**
```css
/* theme.css 冒頭に追加 */
:root {
  /* ========================================================
     Primitive tokens — ブランド色 (theme 不変、直接参照禁止)
     ======================================================== */
  --color-purple-300: #a78bfa;
  --color-purple-500: #7c6ff7;
  --color-cyan-400:   #38bdf8;
  --color-red-500:    #e05252;
  --color-green-500:  #22c55e;
  --color-blue-600:   #0366d6;
  --color-neutral-50:  #f5f5f5;
  --color-neutral-100: #f6f8fa;
  --color-neutral-200: #e1e4e8;
  --color-neutral-300: #d1dbe3;
  --color-neutral-400: #9090a8;
  --color-neutral-500: #888888;
  --color-neutral-700: #333333;
  --color-neutral-900: #24292e;
  --color-dark-bg:       #1e1e2e;
  --color-dark-surface:  #2a2a3e;
  --color-dark-elevated: #313145;
  --color-dark-border:   #3a3a52;
  --color-dark-text:     #e8e8f0;

  /* ========================================================
     Semantic tokens — 役割ベース (Light 値)
     ======================================================== */
  --color-bg:                var(--color-neutral-50);
  --color-surface:           #ffffff;
  --color-surface-elevated:  #ffffff;
  --color-border:            var(--color-neutral-300);
  --color-text:              var(--color-neutral-700);
  --color-text-muted:        var(--color-neutral-500);
  --color-accent:            var(--color-purple-500);
  --color-accent-contrast:   #ffffff;
  --color-accent-subtle:     #e8f0fe;
  --color-destructive:       var(--color-red-500);
  --color-success:           var(--color-green-500);
  --color-header-bg:         var(--color-neutral-900);
  --color-header-text:       #ffffff;

  /* Spacing (8-point scale) */
  --space-1:  4px;
  --space-2:  8px;
  --space-3:  12px;
  --space-4:  16px;
  --space-6:  24px;
  --space-8:  32px;
  --space-12: 48px;
  --space-16: 64px;

  /* Radius */
  --radius-sm:   4px;
  --radius-md:   6px;
  --radius-lg:   12px;
  --radius-full: 9999px;

  /* Typography */
  --font-body:    16px / 1.5 var(--font-family-body);
  --font-label:   14px / 1.4 var(--font-family-body);
  --font-heading: 600 20px / 1.3 var(--font-family-body);
  --font-display: 700 44.8px / 1.1 var(--font-family-display);
  --font-caption: 12px / 1.4 var(--font-family-body);
  --font-family-body:    system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-family-display: 'Rajdhani', sans-serif;

  /* Gradient (theme 不変) */
  --gradient-title: linear-gradient(90deg,
    var(--color-purple-300),
    var(--color-purple-500),
    var(--color-cyan-400)
  );
}

[data-theme="dark"] {
  /* ========================================================
     Semantic tokens — Dark 値 (primitive は継承)
     ======================================================== */
  --color-bg:               var(--color-dark-bg);
  --color-surface:          var(--color-dark-surface);
  --color-surface-elevated: var(--color-dark-elevated);
  --color-border:           var(--color-dark-border);
  --color-text:             var(--color-dark-text);
  --color-text-muted:       var(--color-neutral-400);
  --color-accent-subtle:    var(--color-dark-elevated);
  --color-header-bg:        var(--color-dark-bg);
  --color-header-text:      var(--color-dark-text);
  /* --color-accent / --color-accent-contrast / --color-destructive / --color-success
     は theme 不変なので再定義しない */
}
```

**なぜこれが Standard Stack か:** MDN / web.dev / CSS-Tricks のすべてが「primitive + semantic の 2 層 + `data-theme` 属性切替」を theming の現代標準として提示している。[CITED: developer.mozilla.org/Using_custom_properties]、[CITED: web.dev/learn/css/custom-properties]、[CITED: css-tricks.com/a-complete-guide-to-custom-properties/]

### Pattern 2: chatscope `!important` override の変数駆動化

**What:** 既存の `[data-theme="dark"] .cs-foo { color: #e8e8f0 !important; }` の **`!important` を外さずに値だけ変数化**。chatscope 本体の specificity に負けない特異性を保ったまま theme token に依存させる。
**When to use:** 外部 UI kit（chatscope, MUI, ant-design 等）が自前 CSS を強く当ててくるが、自前の theme に統一したい時。
**Example:**
```css
/* theme.css 既存 (移行前) */
[data-theme="dark"] .cs-main-container { background: #1e1e2e !important; }

/* theme.css 移行後 */
[data-theme="dark"] .cs-main-container { background: var(--color-bg) !important; }
```

**重要な挙動 [CITED: stefanjudis.com/the-surprising-behavior-of-important-css-custom-properties]:**
- `--x: red !important` と custom property 宣言側に付ける `!important` は **宣言のカスケード勝敗を決める** だけ。
- `background: var(--x)` 側の property が `!important` かどうかとは**独立**。
- つまり `background: var(--color-bg) !important;` は正しく機能し、chatscope 本体の **非-important** 宣言には確実に勝つ。
- 移行後も既存の override 構造を**全く壊さない**。

**Grep-verifiable な移行手順:**
```bash
# 移行中、変数化できていない hex 値を洗い出す
grep -nE '#[0-9a-fA-F]{6}' frontend/src/theme.css | grep -v '^[[:space:]]*--'
# 期待: primitive 宣言行以外は 0 件（移行完了の判定）
```

### Pattern 3: controlled InputBar 分離（state は MessageArea、UI は InputBar）

**What:** MessageArea が `inputValue` state を保持し、InputBar には `value`/`onChange` で注入。Send/AskMe/Cancel のイベントハンドラも MessageArea 側で構築し、InputBar は **UI branch（`isThinking ? Cancel : Send`）のみを担う**。
**When to use:** 入力欄を再利用したい or スロット追加拡張が予見される時。
**Example:**
```tsx
// frontend/src/components/InputBar.tsx （新規、~120 行目安）
import { useRef, type KeyboardEvent, type ReactNode } from 'react';

export interface InputBarProps {
  value: string;
  onChange: (next: string) => void;
  onSend: (text: string) => void;       // MessageArea 側で contextMessages も付けて wrap
  onCancel?: () => void;
  onAskMe?: () => void;
  disabled?: boolean;
  isThinking?: boolean;
  placeholder?: string;
  toolbarSlot?: ReactNode;
  previewSlot?: ReactNode;
  copyAllSlot?: ReactNode;
}

export function InputBar({
  value, onChange, onSend, onCancel, onAskMe,
  disabled, isThinking, placeholder,
  toolbarSlot, previewSlot, copyAllSlot,
}: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isInputDisabled = (isThinking ?? false) || (disabled ?? false);

  const handleSend = () => {
    const text = value.trim();
    if (!text || isInputDisabled) return;
    onSend(text);
    onChange('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleAskMe = () => {
    if (!onAskMe) return;
    const text = value.trim();
    if (!text || isInputDisabled) return;
    onAskMe();  // AUQ suffix 付与は MessageArea 側に残す（テキスト整形責務の集中）
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  return (
    <div className="chat-input-bar" style={{
      borderTop: '1px solid var(--color-border)',
      background: 'var(--color-surface)',
      flexShrink: 0,
    }}>
      {copyAllSlot && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '2px 8px 0' }}>
          {copyAllSlot}
        </div>
      )}
      {previewSlot && (
        <div style={{ padding: '8px 12px', maxHeight: '120px', overflowY: 'auto' }}>
          {previewSlot}
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 'var(--space-2)', padding: 'var(--space-3)' }}>
        {toolbarSlot && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', flexShrink: 0 }}>
            {toolbarSlot}
          </div>
        )}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder ?? 'Copilot に何でも聞いてみてください... (Ctrl+Enter で送信)'}
          disabled={isInputDisabled}
          rows={1}
          className="chat-textarea"
          style={{
            flex: 1, resize: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: '0.5rem 0.75rem',
            fontSize: '0.95rem', fontFamily: 'inherit', lineHeight: '1.5',
            outline: 'none', overflowY: 'auto', maxHeight: '160px',
          }}
        />
        {onAskMe && !isThinking && (
          <button onClick={handleAskMe} disabled={!value.trim() || isInputDisabled}
            title="AUQプロトコルで回答を要求"
            style={{ /* 既存の AskMe style を var() 化。AskMe は --color-success 枠 */ }}>
            AskMe
          </button>
        )}
        {isThinking && onCancel ? (
          <button onClick={onCancel} className="chat-cancel-btn"
            style={{ /* var() 化 */ }}>
            キャンセル
          </button>
        ) : (
          <button onClick={handleSend} disabled={!value.trim() || isInputDisabled}
            className="chat-send-btn"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: 'var(--color-accent)',
              color: 'var(--color-accent-contrast)',
              fontWeight: 'bold', height: '36px',
              cursor: value.trim() && !isInputDisabled ? 'pointer' : 'not-allowed',
              opacity: value.trim() && !isInputDisabled ? 1 : 0.5,
            }}>
            送信
          </button>
        )}
      </div>
    </div>
  );
}
```

**MessageArea.tsx 側の抜き出し:**
```tsx
// MessageArea.tsx （~340 行目安、変更点のみ示す）
// 【残す state】messages, isThinking, currentTool, streamPreview, excludedIndices, elapsed, pendingQuestion
// 【InputBar に渡す】inputValue, setInputValue + wrapped onSend / onCancel / onAskMe
const [inputValue, setInputValue] = useState('');

const handleSendWrapped = (text: string) => {
  // contextMessages の組み立ては MessageArea に残す
  if (enableResend && messages.length > 0) {
    const ctxMsgs: ContextMessage[] = messages
      .filter((_, i) => !excludedIndices.has(i))
      .map((m) => ({ role: m.role, content: m.content, ...(m.senderName ? { sender_name: m.senderName } : {}) }));
    onSend(text, ctxMsgs.length > 0 ? ctxMsgs : undefined);
  } else {
    onSend(text);
  }
};

const handleAskMeWrapped = () => {
  const text = inputValue.trim();
  if (!text) return;
  handleSendWrapped(text + AUQ_SUFFIX);
  setInputValue('');
};

// 既存の chat-input-bar ブロック (L384-L485) を以下に置換:
{pendingQuestion ? (
  <div className="chat-input-bar" style={{ padding: '0.75rem', background: 'var(--color-surface)', borderTop: '1px solid var(--color-border)' }}>
    <QuestionPanel questions={pendingQuestion.questions} onSubmit={onQuestionSubmit!} />
  </div>
) : (
  <InputBar
    value={inputValue}
    onChange={setInputValue}
    onSend={handleSendWrapped}
    onCancel={onCancel}
    onAskMe={handleAskMeWrapped}
    isThinking={isThinking}
    disabled={disabled}
    placeholder={placeholder}
    copyAllSlot={messages.length > 0 ? <CopyAllButton messages={messages} /> : undefined}
    // toolbarSlot / previewSlot は Phase 35 では未指定 (= undefined)
  />
)}
```

**ポイント:**
- `useState('')` は MessageArea に残す。親が「送信後の reset」まで責任を持つ pattern。
- AUQ suffix 付与（`+ AUQ_SUFFIX`）は **MessageArea 側に残す**。InputBar は「送信ボタンを押した」以上の意味論を持たない。
- `onCancel` は `isThinking` の時にだけ Cancel ボタンを出す（既存仕様を InputBar に閉じ込めた）。
- QuestionPanel 表示中は InputBar を **描画しない**（既存分岐を維持）。

**React 19 の利点 [CITED: dev.to/pandresdev/aschild-understanding-the-slot-pattern-in-react-ifo]:**
- React 19 では `ref` が通常の prop として扱えるため、将来 InputBar に `ref` を渡すとき `forwardRef` ラップが不要。

### Pattern 4: Desktop-first 2 breakpoint

**What:** desktop を default として CSS を書き、`@media (max-width: 1024px)` / `@media (max-width: 767px)` で縮退挙動のみ上書きする。既存コードが desktop 前提で書かれているため、既存 inline style を壊さない。
**When to use:** 既存 desktop-only アプリにレスポンシブを追加する時。
**Example:**
```css
/* theme.css 末尾に集約 */

/* ============================================================
   Responsive — Tablet (≤ 1024px)
   ============================================================ */
@media (max-width: 1024px) {
  /* MenuScreen: カード grid を狭く */
  .menu-screen { padding: var(--space-6) var(--space-4) !important; }
  .menu-card-grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)) !important; }

  /* Header: Model: ラベル非表示 (aria-label は JSX 側に残す) */
  .header-model-label { display: none; }
  .header-user-login { display: none; }  /* avatar だけ残す */

  /* InputBar: padding 縮小、toolbar 改行許容 */
  .chat-input-bar .chat-input-row { flex-wrap: wrap; padding: 10px !important; }

  /* Chatscope bubble: outgoing は 85% cap */
  .cs-message--outgoing .cs-message__content-wrapper { max-width: 85% !important; }

  /* ThreadSidebar: drawer 化のトリガー (JS 側で collapsed=true 相当の挙動) */
  .sidebar-drawer {
    position: fixed !important;
    top: 48px; bottom: 0; left: 0;
    z-index: 50;
    width: min(80vw, 320px) !important;
    transform: translateX(-100%);
    transition: transform 0.2s ease-out;
  }
  .sidebar-drawer.open { transform: translateX(0); }
  .sidebar-backdrop {
    position: fixed; inset: 0; z-index: 49;
    background: rgba(0, 0, 0, 0.5);
  }
}

/* ============================================================
   Responsive — Mobile (≤ 767px)
   ============================================================ */
@media (max-width: 767px) {
  /* MenuScreen: 1 列 */
  .menu-screen { padding: var(--space-4) var(--space-3) !important; }
  .menu-card-grid { grid-template-columns: 1fr !important; }

  /* Header: hamburger menu 表示 */
  .header-hamburger { display: inline-flex !important; }
  .header-desktop-actions { display: none !important; }

  /* InputBar: Send ボタンは必ず表示、textarea padding 縮小 */
  .chat-textarea { padding: 0.5rem !important; }

  /* Chatscope bubble: 両サイド 100% */
  .cs-message--outgoing .cs-message__content-wrapper { max-width: 100% !important; }
}
```

**重要:** CSS `@media` の breakpoint 値は **CSS 変数として使えない**（これは W3C 仕様）。[CITED: developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties]
→ `--bp-tablet: 1024px` を定義しても `@media (max-width: var(--bp-tablet))` は**動かない**。
→ JS 側で breakpoint を読む必要が出たら、`@media` 内の数値と JS 内のリテラルを二重管理することになる。Phase 35 は **JS 側で breakpoint を読まない方針** で設計し、全てを CSS `@media` で完結させる。[VERIFIED: caniuse.com/css-focus-visible], [CITED: ishadeed.com/article/the-state-of-mobile-first-and-desktop-first/]

### Pattern 5: ThreadSidebar drawer（position: fixed + backdrop + Escape で閉じる）

**What:** tablet/mobile では ThreadSidebar を drawer 化。Header の hamburger ボタンで開閉し、backdrop クリックまたは Escape キーで閉じる。
**When to use:** デスクトップと違うレイアウトに切り替える必要があり、トグル状態を CSS `@media` 単独で制御できない時。
**Example:**
```tsx
// ThreadSidebar.tsx の追加 state
const [drawerOpen, setDrawerOpen] = useState(false);

// Escape で閉じる
useEffect(() => {
  if (!drawerOpen) return;
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawerOpen(false); };
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}, [drawerOpen]);

// drawer open 時の render
return (
  <>
    {drawerOpen && <div className="sidebar-backdrop" onClick={() => setDrawerOpen(false)} />}
    <aside
      className={`sidebar-drawer ${drawerOpen ? 'open' : ''}`}
      role={drawerOpen ? 'dialog' : undefined}
      aria-modal={drawerOpen ? 'true' : undefined}
      aria-label={drawerOpen ? 'スレッド一覧' : undefined}
    >
      {/* 既存 Sidebar 中身 */}
    </aside>
  </>
);
```

**補足（精度 MEDIUM）:**
- ARIA `aria-expanded` は hamburger **button** 側に付ける。drawer 自体は `role="dialog"` + `aria-modal`。[CITED: developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/menuitem_role]
- Focus trap（drawer 内のみで Tab が循環する）は Phase 35 では許容しない（UI-SPEC §Visual Accessibility Baseline で明示: 「Tab で drawer 外に抜けても許容」）。本格対応は Phase 32/33 や将来 React Aria 導入時に実装。
- Desktop では `drawerOpen` state は使わず、既存の `collapsed`/`expanded` ロジックがそのまま有効。

### Pattern 6: Header hamburger menu（`<details>` ベース）

**What:** mobile 幅でのみ表示される `<details>` 要素を使い、追加 JS state なしで開閉できる。Chrome / Edge / Safari すべてでネイティブ挙動。
**When to use:** accessibility 最低限（Tab フォーカス + Enter で開く）で、focus trap 不要のシンプルなドロップダウン。
**Example:**
```tsx
// Header.tsx に追加
<details className="header-hamburger" style={{ display: 'none' /* @media で override */ }}>
  <summary aria-label="メニューを開く" style={{ listStyle: 'none', cursor: 'pointer', padding: '4px 8px' }}>
    ☰
  </summary>
  <div role="menu" style={{
    position: 'absolute', right: 0, top: '48px',
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-2)',
    minWidth: '200px',
    zIndex: 40,
  }}>
    {/* Model select, Logout, Theme toggle を縦に並べる */}
  </div>
</details>
```

**Note:** Tablet 幅では hamburger は出さず、Model select だけ縮小（aria-label 化）する方針（UI-SPEC §Responsive）。mobile 幅でのみ hamburger 化。

### Anti-Patterns to Avoid

- **`isDark` を JS で読んで三項分岐する (再発防止)**: `const bg = isDark ? '#1e1e2e' : '#f5f5f5'` を書かない。代わりに `background: 'var(--color-bg)'`。React 再レンダーなしでテーマが切り替わる利点を取り戻す。
- **`!important` を外しに行く**: chatscope と衝突する。UI-SPEC §Token Naming で明示: 「`!important` は据え置き、値のみ variable 化」。Polish は Phase 39+。
- **Tailwind を部分導入する**: CONTEXT.md D-01 で明示的に CSS custom properties に決定済み。
- **`useMediaQuery` で JS 側に breakpoint を持ち込む**: state 同期ズレ・hydration mismatch の温床。全て CSS `@media` で完結させる。
- **CSS 変数を `@media` 条件に使う**: `@media (max-width: var(--bp))` は仕様上不可。breakpoint 数値は `@media` 宣言内にハードコード、JS と同期する必要なし（JS で breakpoint を読まない）。
- **InputBar に `messages` 配列を渡す**: InputBar の責務は「入力 UI」のみ。`CopyAllButton` や context-exclusion checkbox は MessageArea に残す。slot に差し込む形で抽象化。
- **Drawer を `display: none` で消す**: アニメーションが出ない。`transform: translateX(-100%)` + `transition` で出し入れする。
- **MenuScreen で新規 API エンドポイントを追加する**: D-03 で明示的に client-side slice。既存 `GET /api/threads` のみ利用。

---

## Don't Hand-Roll

| 問題 | Don't Build | Use Instead | Why |
|------|-------------|-------------|-----|
| テーマ切替機構 | ThemeContext / useTheme を再実装 | 既存 `frontend/src/contexts/ThemeContext.ts` + `frontend/src/hooks/useTheme.ts` | D-02 scope 外。既存維持 |
| Font 読み込み | Rajdhani を CSS `@font-face` で自前ロード | 既存 `frontend/index.html` L8 の Google Fonts `<link>` | 既に動作中 |
| `#root` の 100% 高さ確保 | reset.css 追加 | 既存 `frontend/index.html` `<style>` ブロック | `html, body, #root { height: 100%; overflow: hidden }` は既存 |
| Route 構造 | React Router 設定変更 | 既存 `App.tsx` Routes | Phase 35 で URL 構造は変えない（D-03 は MenuScreen 内部のみ） |
| 日付 group 分類 | `getDateGroup` を新規実装 | 既存 `ThreadSidebar.tsx` L64-76 `getDateGroup()` を MenuScreen から import or 複製（utils へ切り出し推奨） | ADR-0040 確立パターン、壊さない |
| Scroll lock | `document.body.style.overflow = 'hidden'` を直接操作 | drawer open 時だけ `html, body { overflow: hidden }` は既に **既存の index.html で常時 hidden** なので不要 | 副作用回避 |
| Focus trap | 自前 `tabindex` 管理 | UI-SPEC で Phase 35 は許容外と明示 | 本格対応は React Aria 導入時 |
| drawer アニメーション | Framer Motion 導入 | CSS `transform` + `transition` | 1 行で足りる |

**Key insight:** 本 phase は **既存仕組みの書き換えではなく、データ表現層（色・余白・タイポ）の抽象化とコンポーネント境界の引き直し**。新規ライブラリ・API・機構を一切追加しなくて完遂できることが、全ての判断の前提。

---

## Runtime State Inventory

**Trigger 判定:** 本 phase は **リネーム/リファクタ phase に該当する**（CSS 変数移行は string 置換、コンポーネント分離は構造変更）。以下 5 カテゴリすべてを明示回答する。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | None — verified by `grep -r "7c6ff7\|1e1e2e\|2a2a3e\|3a3a52\|e8e8f0" --include="*.json"`。色値は JSON/DB に保存されない | なし |
| **Live service config** | None — frontend は静的ビルド。外部サービス設定に色・spacing は保存されていない | なし |
| **OS-registered state** | None — frontend 単体、systemd/Task Scheduler 無関係 | なし |
| **Secrets/env vars** | None — `VITE_APP_BASE`, `API_TARGET` のみ。色値・CSS 変数名を参照する env なし | なし |
| **Build artifacts / installed packages** | `frontend/dist/` が Phase 35 で出力する CSS 変数を含む bundle になる | Vite build 再実行（`bun run build`）で自動更新される。Phase 35 の integration check で再 build が必要 |

**canonical question の回答:** リポジトリ内の全 `.tsx` / `.css` ファイルが更新された後、以下の runtime 系に「古い状態」は残らない:
- PostgreSQL / Redis / arq job queue: 色・スタイル情報を保持しない
- browser localStorage: `theme`（'light'/'dark'）のみ保持。変数名変更ではない（D-01 で semantic key は既存踏襲）
- browser sessionStorage / IndexedDB: 使用していない（grep verify 可能）
- CDN / service worker: 存在しない

**唯一の注意点**: 既存ブラウザタブが **古い bundle** をキャッシュした状態で新 bundle 配信した直後、CSS 変数が未定義の状態で古い className が参照されると一瞬 style が崩れる可能性。**Vite cache busting**（ファイル名 hash）で自動解決されるため、対応不要。

---

## Common Pitfalls

### Pitfall 1: 既存 inline style の hex 値と theme.css の hex 値を片側だけ変数化する

**What goes wrong:** theme.css で `#7c6ff7` を `var(--color-accent)` にしたが、`Header.tsx` の inline style `background: 'linear-gradient(90deg, #a78bfa, #7c6ff7, #38bdf8)'` が残っている → ダーク/ライト切替時に Header タイトルの色が theme.css の変数と**無関係に固定**される。
**Why it happens:** theme.css と React コンポーネント inline style が別のチャネルを通っているため、grep 対象を片方に絞ると見落とす。
**How to avoid:** 移行対象 4 ファイル + theme.css の **すべてで同じ grep 条件** を実行する:
```bash
grep -nE '#[0-9a-fA-F]{3,6}|rgba?\([0-9 ,.]+\)' \
  frontend/src/theme.css \
  frontend/src/components/{MenuScreen,MessageArea,ThreadSidebar,Header}.tsx \
  frontend/src/components/InputBar.tsx
# 期待: primitive 宣言行（theme.css 先頭）以外は 0 件
```
**Warning signs:** Chrome DevTools で `<html>` の `data-theme` 属性をトグルしたのに色が変わらない箇所がある → その箇所の inline style に hex 値が残っている。

### Pitfall 2: chatscope `.cs-message__content-wrapper` の `max-width` を上書きすると Monaco/AG Grid が潰れる

**What goes wrong:** tablet breakpoint で `.cs-message--outgoing .cs-message__content-wrapper { max-width: 85% }` を追加した際、誤って `.cs-message--incoming` 側も変更してしまうと、**incoming の AI メッセージに含まれる Monaco Editor / AG Grid / CollapsibleCodeBlock が狭く潰れる**。
**Why it happens:** 既存 theme.css L59-76 が incoming だけ `max-width: 100%` を重ね付けしており、これを知らずに outgoing と同じルールで書くと打ち消し合う。
**How to avoid:** UI-SPEC §Responsive で明示されている通り、**outgoing のみに tablet override を追加**。incoming は theme.css L59-76 の既存ルールを tablet でも維持する:
```css
@media (max-width: 1024px) {
  .cs-message--outgoing .cs-message__content-wrapper { max-width: 85% !important; }
  /* incoming は触らない */
}
```
**Warning signs:** tablet 幅で Canvas や execute_python 応答内の Monaco が横スクロール必須になったら、incoming にルールが漏れている。

### Pitfall 3: MenuScreen で listThreads() が返す最新順が崩れている

**What goes wrong:** `GET /api/threads` のレスポンスが `updated_at` desc でない（API 実装依存）。client-side で sort せずに `slice(0, 5)` すると、更新した直後のスレッドが「最近」に出てこない。
**Why it happens:** `app/api/routes/threads.py` の ORDER BY が古い順だった場合や、複数アプリのスレッドを merge するときに app 内順序しか保たれない場合がある。
**How to avoid:** MenuScreen 側で明示的に sort する:
```tsx
const recentThreads = useMemo(
  () => [...allThreads]
    .sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''))
    .slice(0, 5),
  [allThreads],
);
```
**Warning signs:** MenuScreen の「最近のスレッド」に、さっき使ったスレッドが出ず、古いスレッドが並ぶ。

### Pitfall 4: AUQ suffix が InputBar に漏れる

**What goes wrong:** InputBar に AUQ suffix `\n\n[回答はAUQプロトコル（<ask_user_question>フォーマット）で返してください]` 付与ロジックを移してしまうと、「`onAskMe` を持たないアプリ（Canvas / Debate）」でも誤ってボタンが出る or 二重付与で送信される。
**Why it happens:** 既存 MessageArea L154 の `AUQ_SUFFIX` 定数が「送信時の加工」であり、InputBar に持ち込むとテキスト整形責務が分散する。
**How to avoid:** AUQ suffix 加工は **MessageArea に残す**。InputBar は `onAskMe: () => void` の opaque callback を受け取るだけで、AUQ の存在を知らない設計にする（Pattern 3 のコード例通り）。
**Warning signs:** AskMe ボタンを押したのに `<ask_user_question>` タグが二重に付与される / AskMe ボタンが Canvas/Debate に出る。

### Pitfall 5: `<details>` の summary 内に `<button>` を置くとクリック競合

**What goes wrong:** Header hamburger を `<details><summary><button>☰</button></summary>...</details>` にすると、summary クリックと button クリックがイベント競合し、Safari で一回クリックしないと開かない。
**Why it happens:** `<details>` の開閉トリガーは summary 自体。子要素の button がイベント bubble を止める。
**How to avoid:** `<summary>` 自体を clickable にし、内部に `<button>` を置かない:
```tsx
<summary style={{ listStyle: 'none', cursor: 'pointer' }} aria-label="メニューを開く">
  ☰
</summary>
```
`list-style: none` で ▸ 矢印を消す。
**Warning signs:** Safari で hamburger が一度目のクリックで開かない。

### Pitfall 6: CSS 変数が Safari で未定義フォールバックせず真っ黒/真っ白になる

**What goes wrong:** `background: var(--color-bg)` で `--color-bg` が typo 等で未定義だと、Safari は `initial` つまり `transparent` として扱う → 背景が親の色に透ける。
**Why it happens:** `var()` は第 2 引数でフォールバック指定可能だが、未指定だと `initial` の仕様。
**How to avoid:** **critical な背景・テキスト色にはフォールバック値を書く**:
```css
background: var(--color-bg, #f5f5f5);
color: var(--color-text, #333);
```
ただし全ての参照にフォールバックを付けると冗長なので、**body 直下・screen の primary 層** だけに絞る。
**Warning signs:** Safari で特定ページだけ真っ白/真っ黒、DevTools で `Computed` タブで `initial` が表示される。

### Pitfall 7: drawer backdrop の z-index が ConfirmModal より高くなる

**What goes wrong:** drawer open 中に ThreadSidebar の削除ボタンを押すと ConfirmModal が開くが、drawer backdrop が ConfirmModal の上に被る → modal が操作不能。
**Why it happens:** 既存 `ConfirmModal.tsx` の z-index を確認せず drawer backdrop に高い値を当てた。
**How to avoid:** **ConfirmModal の z-index を事前調査**（[VERIFIED: grep 推奨]）し、drawer backdrop は **ConfirmModal より低い** 値を使う:
```css
.sidebar-backdrop { z-index: 49; }    /* drawer 用 */
/* ConfirmModal の既存 z-index が例えば 100 なら問題なし */
```
planner タスクで **ConfirmModal.tsx の現行 z-index 値の確認** を最初のステップに含める。
**Warning signs:** drawer open 中の削除操作でモーダル UI が反応しない。

### Pitfall 8: MessageArea の state 分離漏れで resend / AUQ が壊れる

**What goes wrong:** `excludedIndices` (resend 時に送らないメッセージ idx set) や `elapsed` (thinking 秒数カウンタ) の state を InputBar に移すと、MessageArea の Message レンダー側との sync が切れて checkbox 状態と送信内容が食い違う。
**Why it happens:** 「InputBar を分離する」という指示だけで state の所属まで機械的に判断すると、`excludedIndices` は Message Footer の checkbox と結びついているのに誤って移動してしまう。
**How to avoid:** **InputBar に持っていく state は `inputValue` のみ**、と明文化する（本 RESEARCH §Pattern 3 参照）。他 state はすべて MessageArea に残す。
**Warning signs:** resend 時の「送信に含める」checkbox を外したのに送信内容に含まれる / thinking 秒数表示が 0 固定。

---

## Code Examples

### Example 1: `isDark` 三項の除去ビフォーアフター

```tsx
// ===== BEFORE (MenuScreen.tsx L21-26) =====
const theme = useCurrentTheme();
const isDark = theme === 'dark';
const screenBg = isDark ? '#1e1e2e' : '#f5f5f5';
const cardBg = isDark ? '#2a2a3e' : '#fff';
const textColor = isDark ? '#e0e0e0' : '#333';
const cardBorder = isDark ? '#3a3a52' : '#ddd';
const subtitleColor = isDark ? '#a0a0b8' : '#666';
const mutedColor = isDark ? '#9090a8' : '#666666';
// ...
<div style={{ background: screenBg, color: textColor }}>

// ===== AFTER =====
// useCurrentTheme / isDark 三項すべて削除
<div style={{ background: 'var(--color-bg)', color: 'var(--color-text)' }}>
// card: background: 'var(--color-surface)', border: '1px solid var(--color-border)'
// subtitle/muted: color: 'var(--color-text-muted)'
```
[Source: frontend/src/components/MenuScreen.tsx L17-27]

### Example 2: Accent reserved-for 箇所の置換

```tsx
// ===== BEFORE (ThreadSidebar.tsx L184-192: New Chat button) =====
<button className="sidebar-new-chat-btn" style={{
  background: '#0366d6',           // blue-600 だった（ブランド色ではない）
  color: '#fff',
  border: '1px solid #ddd',
}}>

// ===== AFTER =====
<button className="sidebar-new-chat-btn" style={{
  background: 'var(--color-accent)',              // purple-500 = ブランドアクセント
  color: 'var(--color-accent-contrast)',          // #fff
  border: '1px solid var(--color-accent)',        // accent と同色 border
}}>
```
[Source: frontend/src/components/ThreadSidebar.tsx L178-194]

**注意:** `#0366d6` (blue-600) は ThreadSidebar / MessageArea で primary CTA として使われていたが、UI-SPEC §Color (60/30/10) で **accent は purple-500 に統一**。ただし MessageArea の Send ボタン L469 `background: '#0366d6'` も `var(--color-accent)` に統一すること（UI-SPEC §Accent reserved-for リスト: Send ボタン背景は accent）。

### Example 3: Recent Threads セクション（新規）

```tsx
// MenuScreen.tsx に追加するセクション
interface RecentThreadCardProps {
  thread: ThreadInfo;
  onClick: () => void;
}

function RecentThreadCard({ thread, onClick }: RecentThreadCardProps) {
  return (
    <button
      className="recent-thread-card"
      onClick={onClick}
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4)',
        cursor: 'pointer',
        textAlign: 'left',
        color: 'var(--color-text)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-1)',
        transition: 'box-shadow 0.2s',
      }}
    >
      <span style={{
        fontSize: '14px',
        fontWeight: 600,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>{thread.label}</span>
      <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
        {getDateGroup(thread.updated_at)}  {/* utils に切り出した getDateGroup を使う */}
      </span>
    </button>
  );
}

// MenuScreen 本体での使用
const recentThreads = useMemo(
  () => [...allThreads]
    .sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''))
    .slice(0, 5),
  [allThreads]
);

return (
  <div className="menu-screen">
    <h1 style={{ /* 既存 Orochi Chat タイトル */ }}>Orochi Chat</h1>
    <p>使いたいアプリを選んで始めましょう</p>

    {/* Section 1: アプリケーション */}
    <section aria-labelledby="section-apps" style={{ marginTop: 'var(--space-8)' }}>
      <h2 id="section-apps" style={{ /* --font-heading */ }}>アプリケーション</h2>
      <div className="menu-card-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 'var(--space-4)' }}>
        {/* Gems / Canvas / 討論チャット + dynamic apps */}
      </div>
    </section>

    {/* Section 2: 最近のスレッド */}
    <section aria-labelledby="section-recent" style={{ marginTop: 'var(--space-8)' }}>
      <h2 id="section-recent">最近のスレッド</h2>
      {recentThreads.length === 0 ? (
        <p style={{ color: 'var(--color-text-muted)' }}>まだ会話がありません</p>
      ) : (
        <div className="menu-card-grid">
          {recentThreads.map(t => (
            <RecentThreadCard key={t.thread_id} thread={t} onClick={() => handleThreadClick(t)} />
          ))}
        </div>
      )}
    </section>

    {/* Section 3: その他 */}
    <section aria-labelledby="section-other" style={{ marginTop: 'var(--space-8)' }}>
      <h2 id="section-other">その他</h2>
      <p style={{ color: 'var(--color-text-muted)' }}>アプリが足りない場合は管理者にご相談ください。</p>
    </section>
  </div>
);
```

**handleThreadClick のルーティング方針:**
ThreadInfo に `app_id` / `gem_id` が含まれる場合:
- `gem_id` があれば `/gemchat/{gem_id}/{thread_id}` へ
- `app_id === 'chat'` なら `/chat/{thread_id}` へ
- `app_id === 'canvas'` なら `/canvaschat/{thread_id}` へ
- `app_id === 'debate'` なら `/debate/{thread_id}` へ
- それ以外（dynamic app）は `/superchat/{app_id}/{thread_id}` へ

ThreadInfo 型定義を確認して実装する（`frontend/src/types.ts` 未確認のため LOW confidence。planner が task 作成時に確認要）。

### Example 4: 日付グループ関数の utils への切り出し

```ts
// frontend/src/utils/threadGroups.ts （新規）
export type DateGroup = '今日' | '昨日' | '今週' | '先週' | 'それ以前';

export function getDateGroup(updatedAt?: string | null): DateGroup {
  if (!updatedAt) return 'それ以前';
  const now = new Date();
  const updated = new Date(updatedAt);
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffMs = todayStart.getTime() - new Date(updated.getFullYear(), updated.getMonth(), updated.getDate()).getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0 || diffDays === 0) return '今日';
  if (diffDays === 1) return '昨日';
  if (diffDays <= 7) return '今週';
  if (diffDays <= 14) return '先週';
  return 'それ以前';
}
```
[Source: 既存 frontend/src/components/ThreadSidebar.tsx L64-76 を移動]

**ThreadSidebar.tsx 側:** `import { getDateGroup } from '../utils/threadGroups'` に置換。MenuScreen も同 import を使う。**これにより同じロジックを 2 箇所で複製する Pitfall を防ぐ**。ADR-0040 の「スレッドサイドバー日付グループ」パターンを横展開可能な形に整える。

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SCSS / LESS + `$variables` | CSS custom properties（variables） | 2017 以降、2026 時点で全ブラウザ標準 | build time 変数 → runtime 変数、テーマ切替が JS 不要 |
| `prefers-color-scheme` 自動追従のみ | `data-theme` 属性 + 手動トグル + `color-scheme` 併用 | 2020 以降 | OS 設定に縛られない UX、既存コード踏襲 |
| `forwardRef` 必須の ref prop | React 19 で ref が通常 props | 2024-12 React 19 GA | component API がシンプル化、本 phase の InputBar 分離で恩恵 |
| `useState` + 手動 sidebar 開閉 state | `<details>` element | HTML5 標準、モダン環境で十分 | Safari / Chrome / Edge / Firefox 全対応、追加 JS 不要 |
| `:focus` 全表示 | `:focus-visible` でキーボード時のみ | Chrome 86+ / Edge 86+ / Safari 15.4+ / Firefox 85+ | マウスクリック時に不要な outline を消せる、2026 時点で safe [VERIFIED: caniuse.com/css-focus-visible] |
| polyfill `@supports not (display: grid)` | CSS Grid ネイティブ前提 | 2017 以降 | MenuScreen のカード grid で polyfill 不要 |

**Deprecated/outdated:**
- `.sass` 変数: Phase 35 では一切使わない。theme.css はプレーン CSS のみ。
- `IE11 対応`: 既に scope 外（v6.0 target は Chrome / Edge / Safari 最新のみ — UX-04）
- `window.matchMedia` を React で多用する: 本 phase では CSS `@media` に集中、JS 側で breakpoint 監視しない
- `element.attachShadow` + Web Components: 本 app はすべて React ツリー内。slot pattern は React props で足りる

---

## Assumptions Log

本研究で `[ASSUMED]` タグを付けた claim。planner と discuss-phase は以下を **user 確認の候補** として扱う。

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ThreadInfo 型に `app_id` / `gem_id` フィールドが存在し、MenuScreen の "最近のスレッド" クリック時のルーティングに使える | Code Example 3 / MenuScreen ルーティング | フィールド名が違う場合、Phase 35 実装タスクで型定義を確認する step を追加する必要。wave 0 で型確認タスクを 1 つ入れれば回避可能 |
| A2 | `GET /api/threads` が全アプリ横断で返す / per-app filter も可能 | Recent Threads セクション実装 | 横断クエリができない場合、Phase 35 で新規 API を追加することになるが、D-02 scope 外。workaround: per-app で複数 fetch → client 側 merge & sort（fetch 数は高々 5-6 個で 200 名規模なら許容） |
| A3 | ConfirmModal の既存 z-index が drawer backdrop (予定: 49) より高い | Pitfall 7 | 低い場合、drawer backdrop が modal を隠す。planner タスクの Wave 0 で ConfirmModal.tsx を 1 行 grep すれば 1 分で verify できる |
| A4 | `frontend/src/components/InputBar.tsx` 新規作成で knip (未使用コード検出) が通る | InputBar 分離後 | MessageArea から InputBar を使う import が通っていれば問題なし。Wave 2 の ESLint / knip でキャッチ可能 |
| A5 | tablet 幅での ThreadSidebar drawer 挙動トリガを「Header 側の hamburger」に寄せる（ThreadSidebar の自前 collapse と独立制御） | Pattern 5 / 6 | desktop / tablet / mobile で hamburger / collapse の役割を厳密にマッピングするには、planner が task で仕様を固める必要。本 RESEARCH では「mobile は drawer 必須、tablet は drawer 推奨、desktop は既存 collapse 維持」を仮定 |
| A6 | browser target が「Chrome / Edge / Safari 最新 3 バージョン」で、`:focus-visible` / CSS grid / CSS variables / `<details>` はすべて safe | State of the Art / Pitfall 全般 | v6.0 REQUIREMENTS / PROJECT.md に明記された target browser を確認。社内利用なので Chrome/Edge が実態だが Safari で検証も必要 |
| A7 | `frontend/src/types.ts` と `frontend/src/hooks/useThreads.ts` は触らず、`listThreads()` の戻りを MenuScreen 内で展開するだけで済む | MenuScreen 実装 | ThreadInfo 型を拡張する必要が発覚した場合、D-02 scope 外とも言えないため要相談 |

**補足:** 以上の A1-A7 は planner が **Wave 0（Setup）** で 10-15 分の grep + file read で解消可能な確認項目。本 phase の研究スコープを超える調査は避け、planner 側での verify ステップに委譲する設計を採用した。

---

## Open Questions

1. **ThreadInfo に `app_id` / `gem_id` / `app_type` が揃っているか**
   - What we know: `ThreadSidebar.tsx` では `label` / `updated_at` / `thread_id` のみ使用。`listThreads(appId, gemId)` は per-app filter が可能なので少なくとも backend では判別している。
   - What's unclear: レスポンス型にクライアント側が使える形で含まれているか。
   - Recommendation: Wave 0 で `frontend/src/types.ts` を 1 回読めば確定。planner タスクの最初のステップに組み込む。

2. **MenuScreen の "最近のスレッド" が全アプリ横断でフラット一覧になるべきか、アプリごとグループすべきか**
   - What we know: UI-SPEC §Dashboard Visual Design は「横 list or 1-2 列 grid」「直近 5 件」と規定。グループ分けは明示されていない。
   - What's unclear: 200名規模で「Chat の最近 3 件 + Canvas の最近 2 件」の混在が視認性として最適か。
   - Recommendation: 5 件フラット + 各カードに **アプリアイコン絵文字**（UI-SPEC 案）を付ける。アイコンが視覚的なグループ機能を果たす。

3. **tablet 幅での ThreadSidebar collapse と drawer の **二重制御**をどう扱うか**
   - What we know: desktop では既存 `collapsed` state + `◀ / ▶` トグル button、mobile では drawer が必要。tablet はどちらか選べる。
   - What's unclear: tablet で `collapsed` と `drawerOpen` の両方を持つか、tablet 以下は `drawerOpen` のみに一本化するか。
   - Recommendation: UI-SPEC §Responsive は「tablet で **drawer を採用、collapse ではない**」と明記（Claude's Discretion #6 決定）。tablet 以下では collapsed state を常時 true にし、drawer で overlay する。

4. **`@media` block を theme.css に集約するか、各コンポーネント inline に書くか**
   - What we know: 既存は inline style 中心、CSS ファイルは theme.css のみ。
   - What's unclear: `@media` は inline style に書けない（CSS 一等市民）ので必ず CSS ファイルに入れる必要がある。
   - Recommendation: **theme.css 末尾に `/* Responsive */` セクションとして集約**。各コンポーネント固有の className（既存の `.chat-*` / `.sidebar-*` / 新規 `.menu-*` / `.header-*`）にかける。component file 別 `.module.css` は導入しない（Vite 設定追加になる / D-01 の「追加ツールなし」方針に反する）。

5. **Phase 36 Handoff Contract 10 項目の grep-verifiable vs manual の仕分け**
   - What we know: UI-SPEC §Phase 36 Handoff Contract に検証方法が 10 項目で記載済み。
   - What's unclear: planner が VALIDATION.md に落とすとき、grep コマンドを commit-hook に組み込むか、manual checkpoint にするか。
   - Recommendation: §Validation Architecture で詳細仕分けを提示（以下参照）。

---

## Environment Availability

本 phase は既存コード/CSS/JSX 変更のみで外部依存ゼロ。ただし **integration check（手動 screenshot 取得）** で以下を使う:

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Compose | 統合テスト環境 | ✓ | — | — |
| Chromium (remote debugging) | chrome-devtools MCP で自動 screenshot | ✓ | — | 手動 Chrome で screenshot |
| Chrome / Edge / Safari 最新 | Phase 36 Handoff Contract #10 検証 | ✓（Chrome/Edge、Safari は macOS ユーザー側で実施） | — | Safari が環境になければ Chrome DevTools の Responsive Design Mode で 375/768/1024 をエミュレート |
| `bun` | frontend build / dev server | ✓（Docker 内） | — | — |
| Vite | dev server + production build | 8.0.1（既存） | — | — |

**Missing dependencies with no fallback:** なし

**Missing dependencies with fallback:**
- Safari 実機テスト: macOS を持たない環境では Chrome DevTools の "Toggle Device Toolbar" + `User-Agent=Safari` で近似。完全な verify は macOS 利用者に依頼する運用で OK（200名規模社内、Safari ユーザーは少数）

**Chromium 起動確認（CLAUDE.md 参照）:**
```bash
curl -s http://127.0.0.1:9222/json/version
# 空レスポンスなら:
# ! chromium --remote-debugging-port=9222 --no-first-run --no-default-browser-check &
```

---

## Project Constraints (from CLAUDE.md)

以下は CLAUDE.md の明示的な指令。Phase 35 plan は **すべて** これを満たすこと:

1. **応答言語 — 日本語統一**: GSD バナー・チェックポイント・commit message の人間向け説明部・UI コピーはすべて日本語（UI-SPEC §Copywriting Contract 準拠済み）。コードコメント / 変数名 / クラス名は英語 OK。
2. **Branch 必須**: `/gsd:execute-phase` 実行時、最初に `git checkout -b gsd/phase-35-dashboard-design-system` 等のブランチに乗ること。main で直接コミットしない。**現在既に `gsd/phase-35-dashboard-design-system` ブランチ上**（`git status` verified）。
3. **Merge workflow**: squash merge のみ。`--no-edit` / fast-forward 不使用。マージ前に `/create-adr` の振り返り確認。
4. **Merge safety**: 削除行数 > 追加行数 × 2 は停止。アプリコード削除を伴う場合は意図確認。本 phase は概ね **追加が大きい**（CSS 変数 block、InputBar 新規、MenuScreen セクション増） ため該当しにくいが、MessageArea 分離で -150 行 / +α 行のバランスになるのでコミット前に `git diff --stat` で確認。
5. **Chrome DevTools MCP**: `chrome-devtools` MCP 使用時は `curl http://127.0.0.1:9222/json/version` で起動確認。
6. **CSS 変数自動生成 hook は不使用**: `scripts/install-hooks.sh` の対象は ADR INDEX + MCP drift のみ。本 phase で新規 hook 追加はしない。
7. **ADR 追加時のルール（完了後）**: Phase 35 完了後、設計判断として残すべきパターンがあれば `.planning/patterns.md` の **Frontend・UI** セクションに 5-10 行で追加。本 phase で ADR 化すべき候補: (a) CSS 変数 2 層トークンパターン、(b) chatscope `!important` 温存による変数駆動置換、(c) controlled InputBar slot 予約パターン。
8. **`/create-adr` で Phase 35 振り返りを実施**（マージ前）。
9. **MCP ツール自動生成**: 本 phase は MCP 新規ツール追加なし → `config/mcp_tools.yaml` 編集不要、`scripts/generate_mcp_artifacts.py` 実行不要。

---

## Validation Architecture

> `.planning/config.json` の `workflow.nyquist_validation: true` なので本セクション必須。

### Test Framework

| Property | Value |
|----------|-------|
| Framework | **無し（frontend に test runner 未導入）** — Phase 35 で新規に追加する必要性は低い（非機能 UI 変更中心）。既存の Python pytest (`tests/`) は backend 用で本 phase 対象外。 |
| Config file | 無し |
| Quick run command | **`bun run --cwd frontend lint`**（ESLint 9 + typescript-eslint で constrained）+ **`bun run --cwd frontend build`**（`tsc -b` の type check を含む） |
| Full suite command | 上記 + **手動 checker sweep**（Checker Sign-Off に基づく 6 dimension の目視確認） |
| Phase gate | Lint green + Build green + Checker manual approval + Phase 36 Handoff Contract 10 項目 PASS |

**決定理由:** frontend に Vitest / Jest / Playwright を導入しない方針（UI-SPEC §Registry Safety「third-party なし」、D-01 系列「追加ツールなし」）。CSS 変数の正しさ・コンポーネント分離の正しさは **grep-verifiable static check + 手動目視 screenshot** で確認する。200 名規模社内利用で automated visual regression の ROI は低い。

### Phase Requirements → Test Map

**注: Nyquist sampling で phase gate PASS に必要な最小セット。Wave 0 で test infra が「ない」ことを明示し、grep/manual で代替する。**

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| UX-03-1 | MenuScreen が 3 セクション（アプリ/最近/その他）を持つ | static (grep) | `grep -c 'aria-labelledby="section-' frontend/src/components/MenuScreen.tsx` → 3 以上 | ✅ Wave 2 で追加 |
| UX-03-2 | 最近のスレッドが 5 件以下に slice されている | static (grep) | `grep -n 'slice(0, 5)' frontend/src/components/MenuScreen.tsx` → 1 件以上 | ✅ Wave 2 |
| UX-03-3 | "アプリケーション" / "最近のスレッド" / "その他" 日本語セクション見出し | static (grep) | `grep -cE 'アプリケーション\|最近のスレッド\|その他' frontend/src/components/MenuScreen.tsx` → 3 以上 | ✅ Wave 2 |
| UX-03-4 | 初見ユーザー向けに最初に使うアプリが判別可能 | manual | UI checker 目視（説明文/アイコン密度） | manual |
| UX-04-1 | `:root` に 13+ semantic 変数定義 | static (grep) | `grep -cE '^\s*--color-(bg\|surface\|border\|text\|accent\|destructive\|success\|header)' frontend/src/theme.css` → 13 以上 | ✅ Wave 0 |
| UX-04-2 | `[data-theme="dark"]` ブロック内で semantic override | static (grep) | `awk '/\[data-theme="dark"\]\s*{/,/^\}$/' frontend/src/theme.css \| grep -cE '^\s*--color-'` → 9 以上 | ✅ Wave 0 |
| UX-04-3 | `@media (max-width: 1024px)` が theme.css に存在 | static (grep) | `grep -c '@media (max-width: 1024px)' frontend/src/theme.css` → 1 以上 | ✅ Wave 2 |
| UX-04-4 | `@media (max-width: 767px)` が theme.css に存在 | static (grep) | `grep -c '@media (max-width: 767px)' frontend/src/theme.css` → 1 以上 | ✅ Wave 2 |
| UX-04-5 | `#7c6ff7` hardcode が 4 対象ファイルに 0 件 | static (grep) | `grep -c '#7c6ff7' frontend/src/components/{MenuScreen,MessageArea,ThreadSidebar,Header}.tsx` → すべて 0 | ✅ Wave 1 |
| UX-04-6 | `isDark ?` 三項分岐が 4 対象ファイルに 0 件 | static (grep) | `grep -cE 'isDark \?' frontend/src/components/{MenuScreen,MessageArea,ThreadSidebar,Header}.tsx` → すべて 0 | ✅ Wave 1 |
| UX-04-7 | `InputBar.tsx` が存在し、必須 props を受け取る | static (grep) | `test -f frontend/src/components/InputBar.tsx && grep -cE 'toolbarSlot\|previewSlot\|onSend' frontend/src/components/InputBar.tsx` → 3 以上 | ✅ Wave 1 |
| UX-04-8 | ダーク/ライト × desktop/tablet の 4 画面で破綻ゼロ | manual (screenshot) | Chrome DevTools Responsive Mode で 375/768/1024/1440 幅 × light/dark | manual |
| UX-04-9 | Chrome / Edge / Safari 最新で MenuScreen/Chat/Drawer 破綻ゼロ | manual (cross-browser) | 各ブラウザで `/orochi/`, `/orochi/chat`, drawer 開閉 | manual |
| UX-04-10 | TypeScript 型エラー 0 | automated | `bun run --cwd frontend build`（`tsc -b` を含む） | ✅ 既存 |
| UX-04-11 | ESLint エラー 0 | automated | `bun run --cwd frontend lint` | ✅ 既存 |

### Sampling Rate

- **Per task commit:** `bun run --cwd frontend lint && bun run --cwd frontend build` — TypeScript 型 + ESLint のみ（高速、10-20 秒）
- **Per wave merge:** 上記 + 該当 wave の grep-verifiable requirements（上記テーブルの ✅ Wave X）を実行
- **Phase gate:** 全 11 automated requirements が PASS + manual 4 項目（UX-03-4, UX-04-8, UX-04-9, および Phase 36 Handoff Contract の visual 項目）の checker 承認

### Wave 0 Gaps

既存テスト基盤が frontend にないが、Phase 35 では **test framework 追加をしない** 方針:

- [ ] **Wave 0 タスク**: `scripts/check-phase-35.sh`（新規、5 分目安）を追加し、上記 grep-based な 7 項目（UX-03-1〜3, UX-04-1〜7）を連続実行する 1 個のシェルスクリプトにまとめる。CI 統合なし、手動で phase gate 直前に 1 回実行。
- [ ] **Wave 0 タスク**: `frontend/src/utils/threadGroups.ts` を新規追加（`getDateGroup` 切り出し）。これだけ単体で unit test を書きたければ Vitest 追加を後続 phase で検討。
- [ ] **Wave 0 タスク**: ConfirmModal 既存 z-index を調査し、drawer backdrop z-index を確定（Pitfall 7 対応）。
- [ ] **Wave 0 タスク**: ThreadInfo 型定義（`frontend/src/types.ts`）を read し、MenuScreen "最近のスレッド" クリック時のルーティング規則を確定（A1 確認）。
- [ ] **Framework install**: 不要（テスト framework を Phase 35 では導入しない）

**理由で Phase 35 は test framework 追加をしない:**
1. D-01 / UI-SPEC §Registry Safety で「追加ツールなし」が locked
2. 非機能 UI 変更が中心で、automated visual regression の ROI が低い
3. 200名規模社内ツールでは manual sweep + CI 型チェックで十分
4. 将来 Vitest / Playwright を入れる場合は別 phase (v6.1+) で独立設計する方が適切

---

## 実装ウェーブ提案（planner 向け）

Planner が `/gsd-plan-phase` で task 分解する際の参考。これは **提案** であり、planner が最適解を決定する。

### Wave 0: Setup & Investigation
1. CSS 変数基盤: theme.css 先頭に `:root` primitive + semantic block を追加、`[data-theme="dark"]` に semantic dark override を追加（hex 値はまだ置換しない、追加のみ）
2. `frontend/src/utils/threadGroups.ts` に `getDateGroup` 切り出し、ThreadSidebar.tsx は import に置き換え
3. ConfirmModal z-index 確認（grep 1 回）
4. ThreadInfo 型確認（`frontend/src/types.ts` read 1 回）
5. `scripts/check-phase-35.sh` 新規追加（grep verification ハーネス）

### Wave 1: Token Migration（並列可）
1. **Wave 1a** — theme.css 既存 398 行の hex を `var(--...)` に機械的置換（`[data-theme="dark"]` ブロック内を中心に）
2. **Wave 1b** — MessageArea.tsx から InputBar.tsx 分離、`isDark` 三項除去、inline style 変数化
3. **Wave 1c** — ThreadSidebar.tsx の `isDark` 三項除去、inline style 変数化、`getDateGroup` import 化
4. **Wave 1d** — Header.tsx の `isDark` 三項除去、inline style 変数化

各 Wave 1x ごとに lint + build + 該当 grep verification を走らせる。

### Wave 2: Structure & Responsive
1. MenuScreen.tsx のセクション型ダッシュボード化（3 セクション、最近スレッド slice、RecentThreadCard 新規）
2. theme.css 末尾に `@media (max-width: 1024px)` / `@media (max-width: 767px)` block を集約追加
3. ThreadSidebar drawer state 追加、`role="dialog"` + Escape で閉じる、backdrop 実装
4. Header hamburger menu 追加（`<details>` ベース）、Model label の tablet 非表示
5. chatscope bubble tablet override（`.cs-message--outgoing .cs-message__content-wrapper { max-width: 85% !important }`）

### Wave 3: Accessibility & Final Polish
1. `:focus-visible` で 2px outline `var(--color-accent)` を新規ボタン群（FeatureCard / drawer hamburger / RecentThreadCard）に適用
2. AuthPanel は変数差し替えのみ（構造変更なし、1-line diff 相当）
3. Phase 36 Handoff Contract 10 項目 verification（grep 7 件 + manual 3 件）
4. Cross-browser sweep（Chrome / Edge / Safari × light/dark × desktop/tablet = 4 パターン最低 = 12 screenshot）
5. PROJECT.md の Out of Scope 更新（D-07: "モバイル対応 — PC ブラウザのみ対象" を削除 or 文言調整）

### Integration Check（ADR-0046 パターン）
- `docker compose up` → `/orochi/` → MenuScreen で 3 セクション表示を目視
- `/orochi/chat` → InputBar が表示される・Send/AskMe/Cancel が動く・AUQ protocol が動く
- ダーク/ライト切替が 4 コンポーネント全てで瞬時に反映される
- tablet 幅（Chrome DevTools Responsive 1024px）で drawer 開閉、hamburger なし、bubble width
- mobile 幅（Chrome DevTools Responsive 375px）で hamburger 表示、横スクロールゼロ
- 観察結果を `docs/phase-35-integration-check.md` に記録

---

## Sources

### Primary (HIGH confidence)
- **[VERIFIED: frontend/src/theme.css 1-397]** — 既存 398 行の構造把握、chatscope `!important` override 箇所の確認
- **[VERIFIED: frontend/src/components/{MenuScreen,MessageArea,ThreadSidebar,Header}.tsx]** — 現状の inline style 分布、`isDark` 三項箇所の grep、Component 境界
- **[VERIFIED: frontend/package.json]** — React 19.2.4 / @chatscope 2.1.1 / Vite 8.0.1 / TypeScript 5.9.3 確認
- **[VERIFIED: frontend/index.html]** — Rajdhani Google Fonts link、`html, body { overflow: hidden }` 既存確認
- **[VERIFIED: frontend/vite.config.ts]** — Vite proxy 設定は Phase 35 で変更不要
- **[VERIFIED: frontend/src/api/client.ts]** — `listThreads(appId?, gemId?)` の signature、`loadThreadMessages` の AUQ strip 既存
- **[VERIFIED: frontend/src/main.tsx]** — `theme.css` import 位置、BrowserRouter basename
- **[VERIFIED: .planning/phases/35-dashboard-design-system/35-CONTEXT.md]** — D-01〜D-09 すべて確認
- **[VERIFIED: .planning/phases/35-dashboard-design-system/35-UI-SPEC.md]** — Token 一覧 / Props Interface / Handoff Contract
- **[VERIFIED: .planning/REQUIREMENTS.md]** — UX-03 / UX-04 の定義
- **[VERIFIED: .planning/ROADMAP.md Phase 35]** — Success Criteria 4 項目
- **[VERIFIED: docs/adr/0037-chat-ui-batch-enhancements.md]** — native textarea 置換の経緯
- **[VERIFIED: docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md]** — スレッド日付グループ実装
- **[VERIFIED: docs/adr/0043-chat-history-content-normalization-defense-in-depth.md]** — `MarkdownMessage` / `CopyAllButton` 防御ガード、MessageArea 分離時の壊してはいけない behavior
- **[VERIFIED: docs/adr/0028-react-router-v7-url-based-routing-for-spa.md]** — Phase 35 で URL 構造を変えない理由
- **[VERIFIED: docs/adr/0001-nginx-prefix-strip-for-url-routing.md]** — `VITE_APP_BASE` / `APP_PREFIX`、本 phase で触らない範囲

### Secondary (MEDIUM confidence)
- **[CITED: developer.mozilla.org/en-US/docs/Web/CSS/Guides/Cascading_variables/Using_custom_properties]** — CSS custom properties の cascade / inheritance / `var()` fallback
- **[CITED: web.dev/learn/css/custom-properties]** — primitive + semantic 2 層の推奨
- **[CITED: css-tricks.com/a-complete-guide-to-custom-properties]** — custom properties の specificity ルール
- **[CITED: stefanjudis.com/today-i-learned/the-surprising-behavior-of-important-css-custom-properties/]** — `!important` on custom properties と実プロパティ側 `!important` の独立性
- **[CITED: caniuse.com/css-focus-visible]** — `:focus-visible` 2026 時点 browser support（Chrome 86+ / Edge 86+ / Safari 15.4+ / Firefox 85+）
- **[CITED: ishadeed.com/article/the-state-of-mobile-first-and-desktop-first]** — desktop-first vs mobile-first のトレードオフ
- **[CITED: browserstack.com/guide/media-query-for-desktop-tablet-mobile]** — 1024 / 768 / 767 breakpoint の実務標準
- **[CITED: dev.to/pandresdev/aschild-understanding-the-slot-pattern-in-react-ifo]** — React 19 での slot pattern と ref 通常 prop 化
- **[CITED: sandroroth.com/blog/react-slots]** — named ReactNode slot pattern の TypeScript 型
- **[CITED: developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/menuitem_role]** — drawer 用 `aria-expanded` / `aria-modal` / Escape ハンドリング

### Tertiary (LOW confidence — validation 必要)
- **[ASSUMED]** — ThreadInfo 型に `app_id` / `gem_id` が存在するかは `frontend/src/types.ts` を Wave 0 で確認する必要
- **[ASSUMED]** — ConfirmModal 既存 z-index が drawer backdrop より高いかは Wave 0 で grep 確認必要
- **[ASSUMED]** — `GET /api/threads` が全アプリ横断で返すかは `app/api/routes/` を Wave 0 で確認必要（あるいは per-app で複数 fetch の workaround 許容）

---

## Metadata

**Confidence breakdown:**
- **Standard stack**: HIGH — 追加導入ゼロ、既存 package.json で完結、全て verified
- **Architecture patterns**: HIGH — 全て既存コード + MDN/web.dev 標準の組み合わせ
- **Runtime state inventory**: HIGH — frontend 単体 phase で OS/DB/secret との結合なし、明示 verify
- **Common pitfalls**: HIGH — 8 件中 7 件は既存コードから具体的に発掘、1 件（Pitfall 7 ConfirmModal z-index）は Wave 0 で verify する仮定 MEDIUM
- **Code examples**: HIGH — 既存 MessageArea / ThreadSidebar / MenuScreen から直接抽出、inline style → var() の書き方は CSS 標準
- **Validation architecture**: HIGH（grep 項目）+ MEDIUM（manual 項目の基準妥当性）
- **Assumptions log**: 7 件明示、すべて Wave 0 で 5-15 分で verify 可能
- **Environment availability**: HIGH — 追加環境依存なし、Chromium 起動確認方法も CLAUDE.md 既出

**Research date:** 2026-04-23
**Valid until:** 2026-05-23（30 日 — React 19 / chatscope 2.x / CSS 仕様は stable、本 phase 完了まで 1-2 週間を見込めば余裕）

---

*Phase: 35-dashboard-design-system*
*Research: 2026-04-23*
