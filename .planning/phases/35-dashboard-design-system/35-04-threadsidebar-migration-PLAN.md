---
phase: 35
plan: 04
title: "ThreadSidebar.tsx isDark 排除 + var() 移行 + drawer state 追加"
status: draft
type: execute
wave: 1
depends_on: [01]
files_modified:
  - frontend/src/components/ThreadSidebar.tsx
autonomous: true
requirements: [UX-04]
requirements_addressed: [UX-04]
tags: [frontend, react, theme-migration, drawer]
must_haves:
  truths:
    - "ThreadSidebar.tsx から isDark 三項分岐が除去されている（0 件）"
    - "ThreadSidebar.tsx の生 hex が CSS 変数参照に置換されている（#7c6ff7 / #0366d6 / #e05252 等）"
    - "drawerOpen state + Escape ハンドラ + backdrop 要素が追加されている（CSS は Wave 2 Plan 06 で @media 経由で activate）"
    - "date group ロジックは threadGroups.ts からの import で維持されている（ADR-0040 破壊なし）"
    - "New Chat ボタン背景が var(--color-accent) を参照（UI-SPEC Accent reserved-for #2）"
    - "active thread item 背景が var(--color-accent-subtle) を参照"
    - "削除ボタン hover 色が var(--color-destructive) を参照"
  artifacts:
    - path: "frontend/src/components/ThreadSidebar.tsx"
      provides: "theme token 化された sidebar + drawer 対応 state"
      contains: "drawerOpen, sidebar-backdrop, sidebar-drawer"
  key_links:
    - from: "ThreadSidebar.tsx (drawer state)"
      to: "theme.css `.sidebar-drawer` / `.sidebar-backdrop` (Plan 06 で定義)"
      via: "className 指定"
      pattern: "className=\"sidebar-(drawer|backdrop)"
---

<objective>
ThreadSidebar.tsx の isDark 三項分岐（既存 8 件）を全排除し、inline style を CSS 変数参照に置換する。同時に tablet/mobile で使用する drawer 挙動の state + Escape ハンドラ + backdrop 要素を追加する（視覚的な `@media` override は Wave 2 Plan 06 で theme.css に追加される）。

**Purpose:** D-01（isDark 排除）+ D-02（4 コンポーネント trokens 移行）+ D-06（レスポンシブ drawer）を同時達成。Plan 01 Task 02 で切り出した `threadGroups.ts` の import は既に完了済み。

**Output:** ThreadSidebar.tsx が CSS 変数駆動になり、drawer open/close の React state を持ち、`.sidebar-drawer` / `.sidebar-backdrop` className で CSS @media の受け皿を提供する。
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
<!-- ConfirmModal z-index (PATTERNS.md §Shared Patterns — verified by Read L43) -->
`ConfirmModal zIndex: 9999` — drawer backdrop は z-index 49, drawer 本体は 50 で安全（Pitfall 7 不発）。

<!-- threadGroups.ts import (Plan 01 Task 02 で導入済) -->
```typescript
import { getDateGroup, groupThreads, groupOrder, type DateGroup } from '../utils/threadGroups';
```

<!-- drawer 契約 (RESEARCH.md §Pattern 5 L588-618) -->
```tsx
const [drawerOpen, setDrawerOpen] = useState(false);

useEffect(() => {
  if (!drawerOpen) return;
  const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawerOpen(false); };
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}, [drawerOpen]);
```

<!-- UI-SPEC §Responsive drawer 仕様 (L209-212) -->
- Tablet (≤1024px): collapse デフォルト + drawer overlay (position: fixed, z-index 50, backdrop 50% 黒半透明)
- Mobile (≤767px): drawer overlay、幅 `min(80vw, 320px)`

<!-- UI-SPEC §Visual Accessibility Baseline (L466) -->
drawer は `role="dialog"` + `aria-modal="true"` + `aria-label="スレッド一覧"`。Escape で閉じる。Tab で drawer 外に抜けても許容（focus trap なし）。

<!-- UI-SPEC §Copywriting (L385-395) -->
- `+ 新しいチャット`（既存 "+ New Chat" の日本語化）
- `会話を絞り込む...`（既存 placeholder）
- `N / M 件一致`
- `まだ会話がありません` / `一致する会話がありません`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 01: ThreadSidebar.tsx isDark 三項排除 + inline style の hex → var() 移行</name>
  <files>frontend/src/components/ThreadSidebar.tsx</files>
  <read_first>
    - frontend/src/components/ThreadSidebar.tsx 全行 （498 行。Plan 01 Task 02 で threadGroups import 済）
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §8 (L574-665)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Color 60/30/10 (L163-189)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Copywriting Contract ThreadSidebar 部 (L386-395)
    - frontend/src/components/ConfirmModal.tsx L31-50 （既存 isDark prop の扱い — 本 Plan では変更しない）
  </read_first>
  <action>
ThreadSidebar.tsx の全コンポーネントから isDark 三項を削除し、inline style を CSS 変数参照に置換する。

**Step A: isDark 関連宣言を削除**

既存 L40 前後の:
```tsx
const theme = useCurrentTheme();
const isDark = theme === 'dark';
```
を **削除する**。

**ただし ConfirmModal への prop `isDark={isDark}` だけは保持する必要がある**（ConfirmModal.tsx は Phase 35 scope 外）。対処方法は 1 つ選ぶ:

- **案 A（推奨）**: ConfirmModal 呼び出し側で直接 `isDark={theme === 'dark'}` としインライン評価する。ただしそれには `theme` 変数は残す:
  ```tsx
  const theme = useCurrentTheme();  // isDark は削除、theme だけ残す
  ...
  <ConfirmModal ... isDark={theme === 'dark'} />
  ```
- **案 B**: `useCurrentTheme()` の戻り値を ConfirmModal に `isDark={useCurrentTheme() === 'dark'}` と直接渡す（ただし hook はトップレベル必須なので変数化が必要）。

**UX-04-6 grep gate は `isDark \?` 三項をカウントする**ため、`theme === 'dark'` は gate に引っかからない。案 A が clean。

**Step B: inline style の hex → var() 移行**

対象（PATTERNS.md §8 L578-634 抽出元 code excerpts を参照）:

| 箇所 | 既存 hex | 置換後 |
|------|----------|--------|
| sidebar-collapse-btn (L148-170) `color: '#555'` | `#555` | `var(--color-text-muted)` |
| sidebar-new-chat-btn (L178-194) `background: '#0366d6'` | `#0366d6` | `var(--color-accent)` （UI-SPEC Accent reserved-for #2） |
| sidebar-new-chat-btn `color: '#fff'` | `#fff` | `var(--color-accent-contrast)` |
| sidebar-new-chat-btn `border: '1px solid #ddd'` | `#ddd` | `var(--color-border)` |
| sidebar-filter-input border / bg | hex | `var(--color-border)` / `var(--color-surface)` |
| bulk-delete-btn (L249-263) `background: '#e05252'` | `#e05252` | `var(--color-destructive)` |
| bulk-delete-btn `color: '#fff'` | `#fff` | `var(--color-accent-contrast)` |
| sidebar-thread-item.active (L360-370) `background: '#e8f0fe'` | `#e8f0fe` | `var(--color-accent-subtle)` |
| sidebar-thread-delete-btn hover color | `#e05252` | `var(--color-destructive)` |
| date group 見出し color | `isDark ? hex : hex` | `var(--color-text-muted)` |
| sidebar-thread-item ホバー色 / 非 active 文字色 | `isDark ? hex : hex` | `var(--color-text)` |
| filter count ラベル | `isDark ? hex : hex` | `var(--color-text-muted)` |
| sidebar 全体背景 | `isDark ? hex : hex` | `var(--color-surface)` |

**spacing / radius の変数化**（optional だが D-02 scope 内）:
- `borderRadius: '6px'` → `'var(--radius-md)'`
- `borderRadius: '4px'` → `'var(--radius-sm)'`
- 頻出 padding / gap も `var(--space-*)` に置換可（冗長ならスキップ可、色優先）

**Step C: 日本語化（UI-SPEC §Copywriting Contract）**

以下のコピーを更新（既存英語を日本語化）:
- `"+ New Chat"` → `"+ 新しいチャット"`
- `placeholder="Filter conversations..."` → `placeholder="会話を絞り込む..."`
- `{filtered}/{total} matches` → `{filtered} / {total} 件一致`
- `"No conversations yet"` → `"まだ会話がありません"`
- `"No matches"` → `"一致する会話がありません"`

既存日本語コピー（`N件削除` / `全選択` / `全解除` / date group 5 ラベル）は**変更しない**。

**重要な制約:**
- **date group ロジックは threadGroups.ts import（Plan 01 Task 02）で既に切り出し済みなので変更しない**
- **ConfirmModal への `isDark` prop は残す**（ConfirmModal.tsx は Phase 35 scope 外）
- **filter / bulk select / CRUD 機能は変更しない**
- **Sidebar（chatscope）コンポーネントの使い方は変更しない**
- **`#7c6ff7` / `#0366d6` / `#1e1e2e` / `#2a2a3e` の生 hex を残さない**（UX-04-5）
- **isDark 三項は 0 件にする**（UX-04-6）
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -cE 'isDark \?' frontend/src/components/ThreadSidebar.tsx` == 0 （UX-04-6）
    - `grep -c 'const isDark' frontend/src/components/ThreadSidebar.tsx` == 0
    - `grep -c '#7c6ff7' frontend/src/components/ThreadSidebar.tsx` == 0 （UX-04-5）
    - `grep -c '#0366d6' frontend/src/components/ThreadSidebar.tsx` == 0
    - `grep -c 'var(--color-accent)' frontend/src/components/ThreadSidebar.tsx` >= 1 （New Chat ボタン）
    - `grep -c 'var(--color-accent-subtle)' frontend/src/components/ThreadSidebar.tsx` >= 1 （active thread 背景）
    - `grep -c 'var(--color-destructive)' frontend/src/components/ThreadSidebar.tsx` >= 1 （bulk delete）
    - `grep -c 'var(--color-surface)' frontend/src/components/ThreadSidebar.tsx` >= 1
    - `grep -c 'var(--color-text)' frontend/src/components/ThreadSidebar.tsx` >= 1
    - `grep -c '+ 新しいチャット' frontend/src/components/ThreadSidebar.tsx` == 1
    - `grep -c '会話を絞り込む' frontend/src/components/ThreadSidebar.tsx` == 1
    - `grep -c 'まだ会話がありません' frontend/src/components/ThreadSidebar.tsx` == 1
    - `grep -c "from '../utils/threadGroups'" frontend/src/components/ThreadSidebar.tsx` == 1 （Plan 01 Task 02 維持）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
    - 手動: `/orochi/chat` で ThreadSidebar の New Chat ボタン色が purple accent / dark mode 切替でも色反転、削除ボタン hover で赤、active thread 背景が accent subtle
  </acceptance_criteria>
  <done>
    ThreadSidebar.tsx の isDark 三項が排除され、inline style が CSS 変数経由になった。日本語化完了。date group / filter / CRUD / bulk select の既存機能は retain。build/lint green。
  </done>
</task>

<task type="auto">
  <name>Task 02: ThreadSidebar に drawer state + Escape ハンドラ + backdrop 要素を追加</name>
  <files>frontend/src/components/ThreadSidebar.tsx</files>
  <read_first>
    - frontend/src/components/ThreadSidebar.tsx 全行 （Task 01 改修後の状態）
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pattern 5 (L588-624)
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §8 (L637-665)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Responsive drawer 仕様 (L209-212 / L466)
  </read_first>
  <action>
ThreadSidebar.tsx に drawer state と backdrop 要素を追加する。実際の display 挙動（position: fixed / transform transition）は Wave 2 Plan 06 の theme.css `@media` block で定義するため、本 Plan では**React 側の state + DOM 構造のみ** 実装する。

**Step A: drawer state を追加**（W-3 変数名衝突解消）

既存 state 宣言群（ThreadSidebar 関数の先頭）に以下を追加。**uncontrolled 用の内部 state は必ず `internalDrawerOpen` 命名とする**（Step C で props 渡しの controlled mode を扱うため、最終的に公開される名前 `drawerOpen` と一意に分離する必要がある）:

```tsx
import { useState, useEffect } from 'react';  // 既存 import を確認、useState/useEffect が含まれていなければ追加

// ...(ThreadSidebar 関数内)
// 内部 state（uncontrolled mode 用）。controlled mode では props.drawerOpen が優先される（Step C 参照）。
const [internalDrawerOpen, setInternalDrawerOpen] = useState(false);

// NOTE: 実際に使う drawerOpen / setDrawerOpen の解決は Step C で行う。
// Step A / Step B では drawerOpen / setDrawerOpen が Step C で定義された識別子を参照する前提で書く。
```

Escape キーで drawer を閉じるロジックは Step C で drawerOpen が resolver として定義された後に追加する:

```tsx
// Step C の後に追加
useEffect(() => {
  if (!drawerOpen) return;
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') setDrawerOpen(false);
  };
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}, [drawerOpen]);
```

**Step B: DOM 構造に `.sidebar-drawer` / `.sidebar-backdrop` を導入**

既存 ThreadSidebar の return 文の**最上位構造**を以下のようにラップする（既存の `if (collapsed) { return ... }` 分岐も含めて、両パスで drawer wrapper を通す）:

```tsx
return (
  <>
    {drawerOpen && (
      <div
        className="sidebar-backdrop"
        onClick={() => setDrawerOpen(false)}
        aria-hidden="true"
      />
    )}
    <aside
      className={`sidebar-drawer ${drawerOpen ? 'open' : ''}`}
      role={drawerOpen ? 'dialog' : undefined}
      aria-modal={drawerOpen ? 'true' : undefined}
      aria-label={drawerOpen ? 'スレッド一覧' : undefined}
    >
      {/* 既存の Sidebar / collapse 分岐の中身すべて */}
    </aside>
    {/* ここで参照している drawerOpen は Step C で定義する resolver。
        uncontrolled mode なら internalDrawerOpen の値、
        controlled mode なら props.drawerOpen の値に解決される。 */}
  </>
);
```

**Step C: 親コンポーネントへの drawer 制御 prop を追加（Header からの開閉トリガー用）**

既存 ThreadSidebar のインターフェース `ThreadSidebarProps` に以下を追加（既存 props に追記）:

```tsx
interface ThreadSidebarProps {
  // ...既存 props
  drawerOpen?: boolean;           // 親（ChatApp 等）が Header hamburger から制御
  onDrawerOpenChange?: (open: boolean) => void;
}
```

そして内部の `drawerOpen` state はこれらの props があれば controlled mode、なければ uncontrolled mode になるよう実装する（Step A で `internalDrawerOpen` を宣言済、ここで**最終的な resolver**として同名 `drawerOpen` を組み立てる）:

```tsx
// props は ThreadSidebarProps のインスタンス。drawerOpen / onDrawerOpenChange は optional。
const drawerOpen = props.drawerOpen ?? internalDrawerOpen;
const setDrawerOpen = (next: boolean) => {
  if (props.onDrawerOpenChange) props.onDrawerOpenChange(next);
  else setInternalDrawerOpen(next);
};
```

**resolver が決まった後で、Step A で保留にした useEffect（Escape ハンドラ）と Step B で参照している `drawerOpen` 全てがこの resolver を参照する形になる**。uncontrolled / controlled のいずれでも同じ識別子 `drawerOpen` を使い、変数名の衝突（Step A で `drawerOpen` を直接宣言、Step C で再宣言で shadow warning）を避ける。

**ただし controlled mode が使われない間は既存呼び出し箇所（ChatApp / SuperChatApp / GemChatApp 等）を変更しない**（D-02 scope で本 Plan は ThreadSidebar のみ）。親コンポーネント側が drawerOpen / onDrawerOpenChange を渡さなければ従来通り動作する。

**Step D: desktop でも壊さない条件**

- `.sidebar-drawer` の CSS はデフォルトで `position: static` 相当（theme.css Plan 06 で `@media (max-width: 1024px)` の中でだけ `position: fixed` を有効化する）
- `aria-modal` / `role="dialog"` は `drawerOpen === true` の時のみ付く
- `.sidebar-backdrop` は `{drawerOpen && ...}` の条件レンダーで drawerOpen=false なら DOM に出ない

**重要な制約:**
- drawer の CSS スタイル（`position: fixed` / `transform` / backdrop color）は**本 Plan では書かない**（theme.css 側へ委譲、Plan 06）
- hamburger ボタン実装は**Header 側**（Plan 05）、本 Plan は ThreadSidebar の受け皿のみ
- 既存 collapsed / expanded 挙動を破壊しない（desktop で従来通り動く）
- Focus trap は**実装しない**（UI-SPEC §Visual Accessibility Baseline で許容外）
- `ConfirmModal` の z-index (9999) より drawer backdrop の z-index が低い設計（Plan 06 で 49 に設定）なので Pitfall 7 不発
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'drawerOpen' frontend/src/components/ThreadSidebar.tsx` >= 3
    - `grep -c 'setDrawerOpen' frontend/src/components/ThreadSidebar.tsx` >= 1
    - `grep -c 'Escape' frontend/src/components/ThreadSidebar.tsx` >= 1
    - `grep -c 'sidebar-backdrop' frontend/src/components/ThreadSidebar.tsx` >= 1
    - `grep -c 'sidebar-drawer' frontend/src/components/ThreadSidebar.tsx` >= 1
    - `grep -c 'role={drawerOpen' frontend/src/components/ThreadSidebar.tsx` >= 1
    - `grep -c "aria-label={drawerOpen" frontend/src/components/ThreadSidebar.tsx` >= 1
    - `grep -c 'useEffect' frontend/src/components/ThreadSidebar.tsx` >= 1 （Escape ハンドラ用）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
    - 手動: `/orochi/chat` を desktop 幅で開き、drawer が表示されず従来通り動作することを確認（CSS @media 未適用のため drawer state は立たない）
  </acceptance_criteria>
  <done>
    ThreadSidebar.tsx に drawer state・Escape ハンドラ・backdrop DOM 要素が追加された。desktop ではサイドバー挙動は従来通り。Plan 06 で theme.css @media block を追加すると tablet/mobile で drawer overlay が活性化する。build/lint green。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ThreadSidebar ↔ ConfirmModal (z-index stacking) | drawer backdrop (z-index 49, Plan 06 で定義) は ConfirmModal (z-index 9999, verified) より確実に低い — Pitfall 7 不発。 |
| user click ↔ drawer backdrop | backdrop クリックで drawer を閉じる。backdrop 自体は `aria-hidden="true"` で AT には非表示。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-16 | Tampering | isDark 削除に伴う ConfirmModal への prop 消失 | mitigate | Task 01 action で `isDark={theme === 'dark'}` のインライン化を明示。acceptance で `grep -c '<ConfirmModal' frontend/src/components/ThreadSidebar.tsx` が減っていないこと + ConfirmModal 動作の手動 regression。 |
| T-35-17 | DoS (visual) | drawer open 中に下層 UI を誤操作 | mitigate | backdrop `onClick={() => setDrawerOpen(false)}` + `aria-hidden="true"`。backdrop の透過を Plan 06 で 50% 黒半透明に設定 (pointer-events 自動で cover)。 |
| T-35-18 | Information Disclosure | Escape キーで drawer を閉じない → keyboard user が drawer に取り残される | mitigate | `useEffect` で keydown リスナーを登録 + cleanup でアンバインド。drawerOpen=false 時は listener 未登録（useEffect early return）。 |
| T-35-19 | Elevation of Privilege | — | accept | frontend UI のみ、権限なし。 |
| T-35-20 | Repudiation | — | accept | 既存 thread CRUD API 呼び出しは変更なし。 |

すべて LOW severity。security_enforcement 閾値は high のみなので block しない。
</threat_model>

<verification>
- `cd frontend && bun run lint && bun run build` 両方 exit 0
- `grep -cE 'isDark \?' frontend/src/components/ThreadSidebar.tsx` == 0
- `grep -cE '#(7c6ff7|0366d6|1e1e2e|2a2a3e|3a3a52)' frontend/src/components/ThreadSidebar.tsx` == 0
- 手動 regression: `/orochi/chat` で ThreadSidebar の CRUD（新規・リネーム・削除・一括削除）が全て動く、filter input / date group 表示が既存通り、dark/light toggle で色が切り替わる、drawer state は desktop では発火しない
- `grep -c 'sidebar-backdrop\|sidebar-drawer' frontend/src/components/ThreadSidebar.tsx` >= 2
</verification>

<success_criteria>
- UX-04-5（#7c6ff7 0 件）+ UX-04-6（isDark 三項 0 件）が ThreadSidebar.tsx で green
- Plan 06 で `@media (max-width: 1024px) { .sidebar-drawer { position: fixed; ... } }` を追加すれば tablet/mobile で drawer 挙動が有効化される状態
- 既存 CRUD / filter / date group / bulk select / ConfirmModal 連携が破壊されていない
- ADR-0040 スレッドサイドバー日付グループパターン維持（threadGroups.ts からの import）
- UI-SPEC §Copywriting Contract ThreadSidebar 項目が日本語化済み
</success_criteria>

<output>
完了後、`.planning/phases/35-dashboard-design-system/35-04-threadsidebar-migration-SUMMARY.md` に以下を記録:
- 削除した isDark 三項の件数 (8 → 0)
- 置換した hex の件数
- 追加した drawer state / Escape handler / backdrop の DOM diff
- 日本語化した copy 件数
- ConfirmModal 呼び出しの isDark prop 継続性の確認
</output>
