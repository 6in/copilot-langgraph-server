---
phase: 35
plan: 05
title: "Header.tsx isDark 排除 + var() 移行 + hamburger menu 追加"
status: draft
type: execute
wave: 1
depends_on: [01]
files_modified:
  - frontend/src/components/Header.tsx
autonomous: true
requirements: [UX-04]
requirements_addressed: [UX-04]
tags: [frontend, react, theme-migration, responsive, hamburger]
must_haves:
  truths:
    - "Header.tsx から isDark 三項分岐が除去されている（0 件）"
    - "Header.tsx の生 hex がなく（#7c6ff7 等が残っていない）、gradient は var(--gradient-title) を参照する"
    - "hamburger menu が `<details>` ベースで実装され、`.header-hamburger` className を持つ（desktop では display: none、Plan 06 の @media で mobile でのみ表示）"
    - "`.header-model-label` / `.header-user-login` / `.header-desktop-actions` className で tablet/mobile 非表示対象が明示されている（Plan 06 の @media で display 制御）"
    - "Back to menu / Logout / Theme toggle ボタンのコピーが日本語化されている"
  artifacts:
    - path: "frontend/src/components/Header.tsx"
      provides: "theme token 化された header + hamburger menu 受け皿"
      contains: "header-hamburger, header-model-label, header-user-login"
  key_links:
    - from: "Header.tsx (`.header-hamburger`)"
      to: "theme.css `@media (max-width: 767px)` ブロック (Plan 06)"
      via: "className based display toggle"
      pattern: "className=\"header-hamburger"
    - from: "Header.tsx title"
      to: "`--gradient-title` (Plan 01)"
      via: "inline style background"
      pattern: "var\\(--gradient-title\\)"
---

<objective>
Header.tsx の isDark 三項分岐（既存 5 件）を全排除し、inline style を CSS 変数参照に置換する。同時に mobile 幅で表示される hamburger menu を `<details>` ベースで新規実装する（display 制御は Plan 06 の theme.css @media へ委譲）。tablet 幅での「Model: ラベル非表示」「username 非表示」用の className も準備する。

**Purpose:** D-01（isDark 排除）+ D-02（4 コンポーネント token 移行）+ D-05/06（mobile hamburger）を同時達成。`--gradient-title` を適用することでタイトルグラデーションも共有 token 化する。

**Output:** Header.tsx が CSS 変数駆動になり、hamburger `<details>` 要素を持ち、Plan 06 の @media で mobile-only 表示切替が効くようになる。
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/35-dashboard-design-system/35-CONTEXT.md
@.planning/phases/35-dashboard-design-system/35-UI-SPEC.md
@.planning/phases/35-dashboard-design-system/35-RESEARCH.md
@.planning/phases/35-dashboard-design-system/35-PATTERNS.md
@.planning/phases/35-01-foundation-setup-SUMMARY.md

<interfaces>
<!-- hamburger 契約 (RESEARCH.md §Pattern 6 L626-651) + Pitfall 5 (L756-767) -->
- `<details>` ベース（追加 JS state 不要、Chrome / Edge / Safari / Firefox ネイティブ対応）
- `<summary>` 内に `<button>` を入れない（Safari クリック競合）
- `<summary>` 自体を clickable にし、`list-style: none` で ▸ 矢印を消す
- `aria-label="メニューを開く"` を summary に付与
- drop-down 内は `role="menu"` + `zIndex: 40` + `var(--color-surface)` 背景

<!-- UI-SPEC §Responsive Header 仕様 (L210) -->
| 幅 | 挙動 |
|---|------|
| Desktop (>1024px) | 既存 flex 横並び (back / title / appName / model / avatar / login / logout / theme) |
| Tablet (≤1024px) | "Model:" ラベル視覚的に隠す、username 省略 (avatar のみ)、logout ボタンテキストはアイコン化 or 短縮 |
| Mobile (≤767px) | title 以外を hamburger に集約 |

<!-- UI-SPEC §Copywriting Contract Header 部 (L399-405) -->
- `‹ メニュー`（既存 "‹ Menu" 日本語化）
- `モデル:`（既存 "Model:" 日本語化、tablet 以下は aria-label のみ）
- `ログアウト`（既存維持）
- `ライトモード / ダークモードを切り替え`（theme toggle aria-label 日本語化）

<!-- UI-SPEC §Token (L97-98) -->
- `--color-header-bg` / `--color-header-text` → 既存 `#24292e` / `#1e1e2e` / `#fff` 等を置換
- `--gradient-title` → Orochi Chat タイトルの linear-gradient 置換
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 01: Header.tsx isDark 排除 + inline style の hex → var() 移行 + 日本語化</name>
  <files>frontend/src/components/Header.tsx</files>
  <read_first>
    - frontend/src/components/Header.tsx 全行 （208 行）
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §9 (L668-747)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Copywriting Contract Header 部 (L399-405)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Example L694-706 (title gradient)
  </read_first>
  <action>
Header.tsx の isDark 三項排除と inline style の変数化を行う。

**Step A: isDark 関連宣言を削除**

既存 L65-67 付近の:
```tsx
const isDark = theme === 'dark';
const headerBg = isDark ? '#1e1e2e' : '#24292e';
const headerBorder = isDark ? '#3a3a52' : '#1b1f23';
```
を **全削除**。`theme = useCurrentTheme()` 自体は theme toggle UI（☀️/🌙 アイコン切替表示）に使っている場合は残す。使っていないなら削除。

**Step B: header root style を CSS 変数経由に**

既存 L70-80 付近:
```tsx
<header style={{
  ...
  background: headerBg,
  color: '#fff',
  gap: '1rem',
  borderBottom: `1px solid ${headerBorder}`,
}}>
```
を以下に置換:
```tsx
<header style={{
  display: 'flex',
  alignItems: 'center',
  padding: '0 var(--space-4)',
  height: '48px',
  background: 'var(--color-header-bg)',
  color: 'var(--color-header-text)',
  gap: 'var(--space-4)',
  flexShrink: 0,
  borderBottom: '1px solid var(--color-border)',
  position: 'relative',  // hamburger の absolute 子要素のため
}}>
```

**Step C: Orochi Chat タイトル gradient を var() に**

既存 L98-107 付近の:
```tsx
background: 'linear-gradient(90deg, #a78bfa, #7c6ff7, #38bdf8)',
```
を以下に置換:
```tsx
background: 'var(--gradient-title)',
```
既存 `WebkitBackgroundClip` / `backgroundClip` / `WebkitTextFillColor: 'transparent'` は維持。

**Step D: Back to menu / Logout / Theme toggle ボタンの hex → var() + 日本語化（B-2 必須化、但し書き削除）**

- `border: '1px solid #555'` → `'1px solid var(--color-border)'`
- `color: '#ccc'` → `'var(--color-header-text)'`（文字 visibility 維持のためそのまま、もしくは opacity 併用）
- `background: 'transparent'` は変更なし
- **ボタンラベル置換（日本語化必須、existing state に関わらず実施）**:
  - HTML entity版 `'&lsaquo; Menu'` → `'‹ メニュー'`（Unicode 文字 `‹`、半角スペース、`メニュー`）。現行 Header.tsx L95 verified で `&lsaquo; Menu` が存在しているので**必ず置換する**。
  - `'Logout'` → `'ログアウト'`（現行 L172 verified で英語 `Logout` が存在、**必ず置換する**）
  - `'Model:'` → `'モデル:'`（現行 L125 verified で英語 `Model:` が存在、**必ず置換する**）
  - theme toggle の `title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}` は **triage**: aria-label を `aria-label='ライトモード / ダークモードを切り替え'` に置換。title 属性の英語は temporary に据え置き可（将来 phase で日本語化）。
  - theme toggle の既存 `aria-label='Toggle light/dark mode'` → `aria-label='ライトモード / ダークモードを切り替え'`

**B-2 の根拠（Header.tsx 現行コード verified by Read）:**
- L95: `&lsaquo; Menu` — HTML entity 版
- L125: `Model:` — 英語
- L172: `Logout` — 英語
- L179: `aria-label="Toggle light/dark mode"` — 英語

上記 4 箇所は UI-SPEC §Copywriting Contract (L399-405) と一致しないため、本 plan で**例外なく置換**する。「既に日本語の場合は維持」という但し書きは削除（該当ケースが現行コードに存在しないため、但し書きがあると実装者が誤解する）。

**Step E: Model select ラベルを `className="header-model-label"` でマーク**

既存 Model select ラベル（例: `<span>Model: ...</span>` or `<label>Model:</label>`）を:
```tsx
<span className="header-model-label">モデル:</span>
```
のように `className="header-model-label"` 付きにする。Plan 06 の @media で tablet 以下に `.header-model-label { display: none; }` を当てる受け皿。

`aria-label` は残す（AT 向けに「モデル」情報は残したい）。例:
```tsx
<select aria-label="モデル">...</select>
```

**Step F: username span を `className="header-user-login"` でマーク**

既存 avatar + username 表示の username 部分を:
```tsx
<span className="header-user-login">{userInfo.login}</span>
```
のように className を付ける。Plan 06 で tablet 以下に `display: none` を当てる。

**Step G: desktop 向け action 群を `className="header-desktop-actions"` でラップ（optional）**

Model select / Logout / Theme toggle をまとめて `<div className="header-desktop-actions">...</div>` でラップする。Plan 06 で mobile 時 `display: none` にして hamburger に集約する。

**重要な制約:**
- **`#7c6ff7` / `#a78bfa` / `#38bdf8` / `#1e1e2e` / `#24292e` 等の生 hex を Header.tsx 内に残さない**（UX-04-5）
  - ただし `linear-gradient` を `var(--gradient-title)` に変えたことで `#a78bfa` / `#38bdf8` は Header から消える
- **isDark 三項 0 件**（UX-04-6）
- **avatar `<img>` や既存 back button / logout / theme toggle の機能は変更しない**
- **既存の role="img" / aria-label 等のアクセシビリティ属性は維持**
- **タイトル「Orochi Chat」のテキスト内容・font-family は変更しない**
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -cE 'isDark \?' frontend/src/components/Header.tsx` == 0 （UX-04-6）
    - `grep -c 'const isDark' frontend/src/components/Header.tsx` == 0
    - `grep -c '#7c6ff7' frontend/src/components/Header.tsx` == 0 （UX-04-5）
    - `grep -cE '#[0-9a-fA-F]{6}' frontend/src/components/Header.tsx` <= 1 （生 hex ほぼゼロ、border 等で rgba 使用は許容）
    - `grep -c 'var(--gradient-title)' frontend/src/components/Header.tsx` >= 1 （Orochi Chat タイトル）
    - `grep -c 'var(--color-header-bg)' frontend/src/components/Header.tsx` >= 1
    - `grep -c 'var(--color-header-text)' frontend/src/components/Header.tsx` >= 1
    - `grep -c 'header-model-label' frontend/src/components/Header.tsx` >= 1
    - `grep -c 'header-user-login' frontend/src/components/Header.tsx` >= 1
    - **B-2 日本語化必須 gate（全て blocking）**:
      - `grep -c '&lsaquo;' frontend/src/components/Header.tsx` == 0 （W-4: HTML entity が残っていない）
      - `grep -c '‹ メニュー' frontend/src/components/Header.tsx` >= 1 （Unicode `‹` + 半角スペース + `メニュー`）
      - `grep -c 'ログアウト' frontend/src/components/Header.tsx` >= 1
      - `grep -c 'モデル:' frontend/src/components/Header.tsx` >= 1
      - `grep -cE '^[^<]*\bLogout\b[^a-zA-Z]' frontend/src/components/Header.tsx` == 0 （英語 Logout が残っていない、コメント行・属性値は除外される grep）
      - `grep -c '>Logout<' frontend/src/components/Header.tsx` == 0 （JSX textContent として `Logout` が残っていない）
      - `grep -c '>Model:<' frontend/src/components/Header.tsx` == 0 （JSX textContent として `Model:` が残っていない）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
    - 手動: `/orochi/chat` で Header のタイトル gradient が維持、dark/light 切替で背景色が瞬時に切り替わる、back button / logout / theme toggle 全動作
  </acceptance_criteria>
  <done>
    Header.tsx の isDark 三項が排除され、inline style が CSS 変数経由。gradient は共有 token 化。日本語化完了。Plan 06 @media で tablet/mobile 表示切替する className が配置された。build/lint green。
  </done>
</task>

<task type="auto">
  <name>Task 02: Header.tsx に hamburger menu (`<details>` ベース) を追加</name>
  <files>frontend/src/components/Header.tsx</files>
  <read_first>
    - frontend/src/components/Header.tsx 全行 （Task 01 改修後の状態）
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pattern 6 (L626-651)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pitfall 5 (L756-767)
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §9 (L726-746)
  </read_first>
  <action>
Header の右側 action 群の末尾に hamburger menu を追加する。`<details>` ベースで追加 React state 不要、Safari / Chrome / Edge / Firefox ネイティブ対応。

**Step A: `<details className="header-hamburger">` 要素を追加**

`<header>...</header>` の内側、既存の action 群の横（最右端）に以下を追加する:

```tsx
<details className="header-hamburger" style={{ position: 'relative' }}>
  <summary
    aria-label="メニューを開く"
    style={{
      listStyle: 'none',
      cursor: 'pointer',
      padding: 'var(--space-1) var(--space-2)',
      fontSize: '1.25rem',
      color: 'var(--color-header-text)',
    }}
  >
    ☰
  </summary>
  <div
    role="menu"
    style={{
      position: 'absolute',
      right: 0,
      top: '100%',
      background: 'var(--color-surface)',
      color: 'var(--color-text)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: 'var(--space-2)',
      minWidth: '200px',
      zIndex: 40,
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-1)',
      marginTop: 'var(--space-1)',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    }}
  >
    {/* Phase 35 時点では Logout / Theme toggle を縦に並べる。
        Plan 06 で display 制御。Mobile 幅 (≤767px) でのみ表示。 */}
    {onLogout && (
      <button
        role="menuitem"
        onClick={onLogout}
        style={{
          padding: 'var(--space-2)',
          background: 'transparent',
          border: 'none',
          color: 'var(--color-text)',
          cursor: 'pointer',
          textAlign: 'left',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        ログアウト
      </button>
    )}
    <button
      role="menuitem"
      onClick={onToggleTheme}
      aria-label="ライトモード / ダークモードを切り替え"
      style={{
        padding: 'var(--space-2)',
        background: 'transparent',
        border: 'none',
        color: 'var(--color-text)',
        cursor: 'pointer',
        textAlign: 'left',
        borderRadius: 'var(--radius-sm)',
      }}
    >
      {theme === 'dark' ? '☀️ ライトモード' : '🌙 ダークモード'}
    </button>
  </div>
</details>
```

**ただし props `onLogout` / `onToggleTheme` / `theme` は既存の Header.tsx の props / hooks に合わせて適切に参照する**（既存シグネチャを確認すること）。

**Step B: デフォルト `display: none` は CSS 側（Plan 06）**

`.header-hamburger` は本 Plan では**inline style で display を指定しない**。theme.css の @media ブロック (Plan 06) で以下のように制御する:

```css
/* Plan 06 で theme.css に追加予定 */
.header-hamburger { display: none; }
@media (max-width: 767px) {
  .header-hamburger { display: inline-flex; }
  .header-desktop-actions { display: none; }
}
@media (max-width: 1024px) {
  .header-model-label, .header-user-login { display: none; }
}
```

**本 Plan は Header.tsx 側で `className="header-hamburger"` / `className="header-desktop-actions"` を置くだけ**。実際の @media CSS は Plan 06 の責務。

**Pitfall 5 対策（verified by RESEARCH.md L756-767）:**
- `<summary>` 内に `<button>` を入れない（Safari クリック競合）
- `<summary>` 自体を clickable にし `list-style: none` で ▸ 矢印を消す

**Pitfall 7 対策:** hamburger dropdown の z-index は 40（ConfirmModal 9999 / drawer backdrop 49 / drawer 50 より十分低い）。hamburger が開いている時にモーダル/drawer が表示されても、これらが hamburger を覆う（意図通り）。

**重要な制約:**
- hamburger は**React state を使わない**（`<details>` のネイティブ挙動）
- 既存の Logout / Theme toggle 呼び出しロジックは変更しない（同じ `onLogout` / `onToggleTheme` callback を hamburger 内で使う）
- desktop では CSS 側で `display: none` にするため hamburger は表示されない（本 Plan 時点で Plan 06 未完了なので desktop で見えてしまうが、Plan 06 で解消）
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '<details' frontend/src/components/Header.tsx` >= 1
    - `grep -c 'header-hamburger' frontend/src/components/Header.tsx` >= 1
    - `grep -c '<summary' frontend/src/components/Header.tsx` >= 1
    - `grep -c 'listStyle' frontend/src/components/Header.tsx` >= 1
    - `grep -c 'メニューを開く' frontend/src/components/Header.tsx` >= 1
    - `grep -cE '<summary[^>]*>\s*<button' frontend/src/components/Header.tsx` == 0 （Pitfall 5: summary 直下に button なし）
    - `grep -c 'ログアウト' frontend/src/components/Header.tsx` >= 1
    - `grep -c 'zIndex: 40' frontend/src/components/Header.tsx` >= 1
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
  </acceptance_criteria>
  <done>
    Header.tsx に `<details className="header-hamburger">` の dropdown が追加された。Logout / Theme toggle を含む。Pitfall 5（summary 内 button）回避済み。z-index 40 で ConfirmModal / drawer と衝突しない。Plan 06 の @media で mobile-only 表示切替。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `<details>` native toggle ↔ user click | ネイティブ挙動、React state なし、XSS リスクなし。 |
| hamburger dropdown (z-index 40) ↔ ConfirmModal (9999) / drawer (50) / backdrop (49) | 全て hamburger より高い。hamburger open 時に confirm / drawer が表示されても覆う（意図通り）。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-21 | Tampering | `<details><summary><button>` クリック競合（Pitfall 5）で Safari の初回クリックが効かない | mitigate | Task 02 action で `<summary>` 内に `<button>` を置かない設計を明示。acceptance で `grep -cE '<summary[^>]*>\s*<button' == 0` を確認。 |
| T-35-22 | DoS (visual) | gradient-title 変数が未定義 (Plan 01 の追加が漏れている場合) で Orochi Chat タイトルが真っ黒/真っ白（Pitfall 6） | mitigate | Plan 01 で `--gradient-title` を定義済み（acceptance: `grep -c '^\s*--gradient-title:' frontend/src/theme.css` == 1）。Task 01 action で Header 側が `var(--gradient-title)` を参照することを明示。 |
| T-35-23 | Elevation of Privilege | hamburger dropdown から Logout が発火して session 無効化 | accept | Logout 呼び出しは既存 `onLogout` callback と同じ（権限昇格なし）。確認ダイアログ（ConfirmModal）は既存仕様維持。 |
| T-35-24 | Information Disclosure | hamburger open 状態で別ユーザーに画面を覗かれる | accept | 社内 200 名規模運用、screen sharing 配慮は user 責務。 |
| T-35-25 | Repudiation | — | accept | 変更なし。 |

すべて LOW severity。security_enforcement 閾値は high のみなので block しない。
</threat_model>

<verification>
- `cd frontend && bun run lint && bun run build` 両方 exit 0
- `grep -cE 'isDark \?' frontend/src/components/Header.tsx` == 0
- `grep -c 'var(--gradient-title)' frontend/src/components/Header.tsx` >= 1
- `grep -c 'header-hamburger\|header-model-label\|header-user-login' frontend/src/components/Header.tsx` >= 3
- 手動 regression: `/orochi/chat` で Header のタイトル gradient 表示、dark/light 切替で背景色切替、back button / logout / theme toggle 動作、hamburger 内 Logout / Theme toggle も動作
</verification>

<success_criteria>
- UX-04-5（#7c6ff7 hardcode 0）+ UX-04-6（isDark 三項 0）が Header.tsx で green
- `<details>` ベース hamburger で React state を追加しない（追加 JS cost ゼロ）
- Pitfall 5（summary 内 button）を回避した Safari 互換設計
- Plan 06 の @media で `.header-hamburger`（mobile でのみ表示）・`.header-model-label` / `.header-user-login`（tablet 以下で非表示）が activate される受け皿が整った
- gradient-title が theme.css → Header.tsx → MenuScreen.tsx（Plan 06）の 3 箇所で共有される
</success_criteria>

<output>
完了後、`.planning/phases/35-dashboard-design-system/35-05-header-migration-SUMMARY.md` に以下を記録:
- 削除した isDark 三項の件数 (5 → 0)
- 置換した hex の件数
- 追加した className の一覧（header-hamburger / header-model-label / header-user-login / header-desktop-actions）
- hamburger dropdown の z-index 確認（40、ConfirmModal / drawer と競合なし）
- 日本語化した copy 件数
</output>
