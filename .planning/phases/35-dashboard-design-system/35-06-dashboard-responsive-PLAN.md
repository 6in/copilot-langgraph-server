---
phase: 35
plan: 06
title: "MenuScreen ダッシュボード化 + レスポンシブ @media 集約"
status: draft
type: execute
wave: 2
depends_on: [01, 02, 03, 04, 05]
files_modified:
  # B-4 明文化: theme.css への書き込みは **末尾への @media block 追加のみ**
  # Plan 02 が先に完了 (depends_on: [01, 02, 03, 04, 05]) しており、Plan 02 が触る
  # `[data-theme="dark"] .*-override` ブロックとは物理的に分離された末尾追加なので
  # merge conflict は起きない。
  - frontend/src/components/MenuScreen.tsx   # Task 01: 3 セクション再構築
  - frontend/src/theme.css                   # Task 02: 末尾に @media block 追加 (tablet/mobile)
autonomous: true
requirements: [UX-03, UX-04]
requirements_addressed: [UX-03, UX-04]
tags: [frontend, react, dashboard, responsive, media-query, chatscope-override]
must_haves:
  truths:
    - "MenuScreen.tsx が 3 セクション (`<section aria-labelledby=\"section-apps\">` / `section-recent` / `section-other`) 構造を持つ"
    - "MenuScreen.tsx の「最近のスレッド」が listThreads() → sort(updated_at desc) → slice(0, 5) で client-side 取得される"
    - "MenuScreen.tsx から isDark 三項分岐が除去されている（0 件）"
    - "theme.css に @media (max-width: 1024px) ブロックが集約追加されている"
    - "theme.css に @media (max-width: 767px) ブロックが集約追加されている"
    - "tablet 幅で .cs-message--outgoing .cs-message__content-wrapper { max-width: 85% !important } が効く（incoming には影響しない）"
    - "mobile 幅で .header-hamburger が display: inline-flex、.header-desktop-actions が display: none"
    - "tablet 幅で .sidebar-drawer が position: fixed + transform + transition で overlay"
    - "日本語コピー（「アプリケーション」「最近のスレッド」「その他」「使いたいアプリを選んで始めましょう」）が MenuScreen に存在する"
  artifacts:
    - path: "frontend/src/components/MenuScreen.tsx"
      provides: "セクション型ダッシュボード + FeatureCard (既存拡張) + RecentThreadCard (新規内部)"
      contains: "section-apps, section-recent, section-other, slice(0, 5)"
    - path: "frontend/src/theme.css"
      provides: "tablet / mobile @media override + drawer CSS + hamburger CSS + chatscope bubble tablet override"
      contains: "@media (max-width: 1024px), @media (max-width: 767px), .sidebar-drawer, .sidebar-backdrop, .header-hamburger"
  key_links:
    - from: "MenuScreen.tsx (handleThreadClick)"
      to: "React Router navigate (既存) / threadId select"
      via: "app_id に基づくアプリ別ルーティング"
      pattern: "navigate\\("
    - from: "MenuScreen.tsx (最近のスレッド)"
      to: "listThreads() from api/client.ts"
      via: "既存 API、client-side sort + slice"
      pattern: "listThreads\\("
    - from: "MenuScreen.tsx (date group label)"
      to: "utils/threadGroups.ts getDateGroup"
      via: "import (Plan 01 Task 02 で存在)"
      pattern: "from '../utils/threadGroups'"
---

<objective>
Phase 35 の「見える部分」を完成させる最終 plan。MenuScreen をセクション型ダッシュボード（アプリ / 最近のスレッド / その他）に再構築し、theme.css 末尾に `@media (max-width: 1024px)` / `@media (max-width: 767px)` 2 ブロックを集約追加してレスポンシブ挙動（drawer / hamburger / chatscope bubble tablet override）を activate する。

**Purpose:** UX-03（ダッシュボード化で初見ユーザーが迷わない）+ UX-04（tablet/mobile レスポンシブ）を達成。Plan 01-05 で整えた基盤（CSS 変数 / threadGroups.ts / InputBar 分離 / drawer state / hamburger 受け皿）をこの plan で消費して contract 化する。

**Output:**
- MenuScreen.tsx が 3 セクション構造 + RecentThreadCard 内部コンポーネント + client-side sort & slice
- theme.css 末尾に `/* Responsive */` セクション（~70 行）
- Phase 36 Handoff Contract 項目 1-8 のうち、8（MenuScreen セクション構造）と 6/7（@media 存在）が grep で verified になる
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
@.planning/phases/35-02-theme-hex-to-var-SUMMARY.md
@.planning/phases/35-03-messagearea-inputbar-split-SUMMARY.md
@.planning/phases/35-04-threadsidebar-migration-SUMMARY.md
@.planning/phases/35-05-header-migration-SUMMARY.md

<interfaces>
<!-- ThreadInfo 型 (verified: types.ts L37-42) -->
```typescript
export interface ThreadInfo {
  thread_id: string;
  updated_at?: string | null;
  label: string;
  app_id?: string;
  // gem_id は存在しない — RecentThreadCard クリック時のルーティングは app_id 中心
}
```

<!-- listThreads signature (verified: api/client.ts L72) -->
`export const listThreads = (appId?: string, gemId?: string) => { ... }`
第 1/2 引数を共に省略すれば全アプリ横断で返す。client-side sort が必須（Pitfall 3 - backend の order by に依存しない）。

<!-- MenuScreen 既存 Props (verified by Read: MenuScreen.tsx L10-17) -->
**現行 Props シグネチャ（変更しない、B-1 verified）**:
```typescript
interface MenuScreenProps {
  onNavigate: (app: AppDefinition) => void;  // 1 引数のみ、threadId は受け取らない
  onOpenGems: () => void;                    // 引数なし
  onOpenDebate: () => void;                  // 引数なし
  onOpenCanvas: () => void;                  // 引数なし
}
```

**B-1 Fix の設計方針:** 既存 handler は「アプリカードクリック → アプリ画面へ遷移」用で thread_id を受け取れない。
RecentThreadCard クリック時は既存 Props 経由ではなく、**MenuScreen 内で `useNavigate()` (react-router v7 declarative mode) を直接呼ぶ** 設計とする。これにより App.tsx の Props シグネチャ拡張が不要となり blast radius 最小化。

参照ルート（App.tsx Routes verified by Read: L256-273）:
- `chat` アプリ → `/chat/:threadId`
- `superchat` アプリ → `/superchat/:appSlug/:threadId` （ただし RecentThreadCard からは app_slug が無いので fallback）
- `gem` / `gems` → `/gemchat/:gemId/:threadId` （gem_id 無いため thread_id のみで復元する `/chat/` フォールバック or gems list へ）
- `canvas` → `/canvaschat/:threadId`
- `debate` → `/debate/:threadId`

**重要:** ThreadInfo には `gem_id` フィールドが存在しない（verified by types.ts L37-42）ので、Gem スレッドから `/gemchat/` へ直接復元はできない。Gem スレッドの場合は `/gems` （Gems 一覧）へ navigate し、ユーザーに gem を選び直してもらうフォールバック設計とする。

<!-- UI-SPEC §Dashboard Visual Design セクション構成 (L228-240) -->
1. タイトル（既存 h1 "Orochi Chat" + サブタイトル「使いたいアプリを選んで始めましょう」）
2. `<section aria-labelledby="section-apps"><h2 id="section-apps">アプリケーション</h2>...grid...</section>`
3. `<section aria-labelledby="section-recent"><h2 id="section-recent">最近のスレッド</h2>...5 cards...</section>`
4. `<section aria-labelledby="section-other"><h2 id="section-other">その他</h2>...helper...</section>`

<!-- UI-SPEC §Grid・余白 (L264-268) -->
- アプリカード grid: `grid-template-columns: repeat(auto-fill, minmax(220px, 1fr))`, gap `--space-4`, max-width 960px
- 最近のスレッドカード grid: `repeat(auto-fill, minmax(240px, 1fr))`, gap `--space-3`
- セクション間 gap: `--space-8`
- 画面外側 padding: `--space-12 --space-8`

<!-- UI-SPEC §Responsive + RESEARCH.md §Pattern 4 (L522-582) -->
tablet/mobile @media block 全文は RESEARCH.md §Pattern 4 L527-581 を参考にする。
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 01: MenuScreen.tsx をセクション型ダッシュボードに再構築（3 セクション + RecentThreadCard + 最近スレッド取得）</name>
  <files>frontend/src/components/MenuScreen.tsx</files>
  <read_first>
    - frontend/src/components/MenuScreen.tsx 全行（296 行、既存 FeatureCard / SkeletonCard pattern を把握）
    - frontend/src/api/client.ts L72 周辺（listThreads signature）
    - frontend/src/types.ts（ThreadInfo / AppDefinition 型）
    - frontend/src/utils/threadGroups.ts（Plan 01 Task 02 で作成済）
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Dashboard Visual Design (L225-268)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Copywriting Contract MenuScreen 部 (L362-374)
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §2 (L174-226 - RecentThreadCard アナログ)
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §6 (L391-490 - MenuScreen 再構築)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Example 3 (L849-942)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pitfall 3 (L734-747)
  </read_first>
  <action>
MenuScreen.tsx を 3 セクション構造に再構築する。既存 FeatureCard パターンは維持し、新しく内部コンポーネント `RecentThreadCard` を追加する。

**Step A: isDark 三項 + 既存の色変数宣言を削除**

既存 L17-27 付近の:
```tsx
const theme = useCurrentTheme();
const isDark = theme === 'dark';
const screenBg = isDark ? '#1e1e2e' : '#f5f5f5';
const cardBg = isDark ? '#2a2a3e' : '#fff';
const textColor = isDark ? '#e0e0e0' : '#333';
const cardBorder = isDark ? '#3a3a52' : '#ddd';
const subtitleColor = isDark ? '#a0a0b8' : '#666';
const mutedColor = isDark ? '#9090a8' : '#666666';
```
を**全て削除**。`useCurrentTheme` が他で使われていなければ import も削除。

**Step B: 最近のスレッド取得 + sort + slice**

MenuScreen 関数の state 部に以下を追加:

```tsx
import { useState, useEffect, useMemo } from 'react';
import { listThreads } from '../api/client';
import type { ThreadInfo } from '../types';
import { getDateGroup } from '../utils/threadGroups';

// ...関数内
const [allThreads, setAllThreads] = useState<ThreadInfo[]>([]);
const [threadsError, setThreadsError] = useState<string | null>(null);

useEffect(() => {
  let cancelled = false;
  listThreads()
    .then((res) => {
      if (!cancelled) setAllThreads(res ?? []);
    })
    .catch((e) => {
      if (!cancelled) setThreadsError(String(e?.message ?? e));
    });
  return () => {
    cancelled = true;
  };
}, []);

// Pitfall 3 対策: backend の order by に依存しない
const recentThreads = useMemo(
  () =>
    [...allThreads]
      .sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''))
      .slice(0, 5),
  [allThreads]
);
```

**listThreads 戻り値の形**は既存 `useThreads` フックの型を確認する。もし `{threads: ThreadInfo[]}` の wrapper なら `res.threads ?? []` に合わせる（Wave 0 で型を read で確認すること）。

**Step C: RecentThreadCard 内部コンポーネントを新規追加**

PATTERNS.md §2 の FeatureCard アナログを参考に:

```tsx
interface RecentThreadCardProps {
  thread: ThreadInfo;
  onClick: () => void;
}

function RecentThreadCard({ thread, onClick }: RecentThreadCardProps) {
  // アプリアイコン解決: app_id → 絵文字
  const appIcon = ((): string => {
    switch (thread.app_id) {
      case 'gem':
      case 'gems':
        return '💎';
      case 'canvas':
        return '🎨';
      case 'debate':
        return '💬';
      case 'superchat':
        return '🧠';
      default:
        return '💭';
    }
  })();

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
        transition: 'box-shadow 0.2s, transform 0.1s',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 4px 16px rgba(0,0,0,0.18)';
        (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLButtonElement).style.boxShadow = 'none';
        (e.currentTarget as HTMLButtonElement).style.transform = 'none';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        <span aria-hidden="true" style={{ fontSize: '1.25rem' }}>
          {appIcon}
        </span>
        <span
          style={{
            fontSize: '14px',
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
          }}
        >
          {thread.label}
        </span>
      </div>
      <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
        {getDateGroup(thread.updated_at)}
      </span>
    </button>
  );
}
```

**Step D: handleThreadClick ルーティング解決（B-1 useNavigate 直接呼び出し設計）**

**重要（B-1 verified）:** 既存 Props `onNavigate(app)` / `onOpenGems()` / `onOpenCanvas()` / `onOpenDebate()` はいずれも thread_id を受け取れない。
そこで **MenuScreen 内で `useNavigate()` (react-router v7) を直接呼び出す**。App.tsx の Props シグネチャ拡張は不要。

```tsx
// ファイル先頭の import 群に追加
import { useNavigate } from 'react-router';

// ...(MenuScreen 関数内、他 state の近く)
const navigate = useNavigate();

// thread.app_id に応じて対応ルートへ navigate する handler
const handleThreadClick = (thread: ThreadInfo) => {
  const tid = thread.thread_id;
  switch (thread.app_id) {
    case 'gem':
    case 'gems':
      // ThreadInfo には gem_id が無い（verified）ため、Gems 一覧へ戻すフォールバック
      navigate('/gems');
      break;
    case 'canvas':
      navigate(`/canvaschat/${tid}`);
      break;
    case 'debate':
      navigate(`/debate/${tid}`);
      break;
    case 'superchat':
      // RecentThreadCard には app_slug 情報が無いので、chat フォールバック
      navigate(`/chat/${tid}`);
      break;
    case 'chat':
    default:
      navigate(`/chat/${tid}`);
      break;
  }
};
```

**確認事項:**
- `useNavigate` は `react-router` package（v7 declarative）から import。App.tsx と同じ import 元を使う（verified by Read App.tsx L15）。
- 既存 Props（`onNavigate` / `onOpenGems` 等）は App.tsx から依然渡されているが、RecentThreadCard click では使わない（既存アプリカードクリックは従来どおり props 経由で維持される、Step E 参照）。
- `MenuScreen` は現状 `MenuScreenRoute` wrapper 経由で描画されている（verified by Read App.tsx L149-167）。この wrapper は Router 文脈の内側なので `useNavigate()` が hooks の rules 上合法（同一の Routes tree 内で呼ばれる）。

**Step E: return 文を 3 セクション構造に書き換え**

```tsx
return (
  <div
    className="menu-screen"
    style={{
      background: 'var(--color-bg)',
      color: 'var(--color-text)',
      padding: 'var(--space-12) var(--space-8)',
      minHeight: '100%',
      overflowY: 'auto',
    }}
  >
    <div style={{ maxWidth: '960px', margin: '0 auto' }}>
      {/* Hero */}
      <h1
        style={{
          fontFamily: 'var(--font-family-display)',
          fontSize: '2.8rem',
          fontWeight: 700,
          marginBottom: 'var(--space-2)',
          letterSpacing: '0.1em',
          background: 'var(--gradient-title)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          textAlign: 'center',
        }}
      >
        Orochi Chat
      </h1>
      <p
        style={{
          fontSize: '1rem',
          color: 'var(--color-text-muted)',
          marginBottom: 'var(--space-8)',
          textAlign: 'center',
        }}
      >
        使いたいアプリを選んで始めましょう
      </p>

      {error && (
        <div
          role="alert"
          style={{
            background: 'rgba(224, 82, 82, 0.1)',
            border: '1px solid var(--color-destructive)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-3) var(--space-4)',
            color: 'var(--color-destructive)',
            marginBottom: 'var(--space-8)',
          }}
        >
          アプリ一覧を取得できませんでした。ページを再読み込みしてください。
        </div>
      )}

      {/* Section 1: アプリケーション */}
      <section aria-labelledby="section-apps" style={{ marginBottom: 'var(--space-8)' }}>
        <h2
          id="section-apps"
          style={{
            font: 'var(--font-heading)',
            marginBottom: 'var(--space-4)',
            color: 'var(--color-text)',
          }}
        >
          アプリケーション
        </h2>
        <div
          className="menu-card-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 'var(--space-4)',
          }}
        >
          {/* 既存の FeatureCard 群を既存の apps state / 固定カードで並べる */}
        </div>
      </section>

      {/* Section 2: 最近のスレッド */}
      <section aria-labelledby="section-recent" style={{ marginBottom: 'var(--space-8)' }}>
        <h2
          id="section-recent"
          style={{
            font: 'var(--font-heading)',
            marginBottom: 'var(--space-4)',
            color: 'var(--color-text)',
          }}
        >
          最近のスレッド
        </h2>
        {threadsError ? (
          <p style={{ color: 'var(--color-destructive)' }}>
            スレッド一覧を取得できませんでした。時間を置いて再度お試しください。
          </p>
        ) : recentThreads.length === 0 ? (
          <div>
            <p style={{ color: 'var(--color-text-muted)', fontWeight: 600 }}>まだ会話がありません</p>
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
              上のアプリカードから新しい会話を始められます。
            </p>
          </div>
        ) : (
          <div
            className="menu-recent-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
              gap: 'var(--space-3)',
            }}
          >
            {recentThreads.map((t) => (
              <RecentThreadCard key={t.thread_id} thread={t} onClick={() => handleThreadClick(t)} />
            ))}
          </div>
        )}
      </section>

      {/* Section 3: その他 */}
      <section aria-labelledby="section-other">
        <h2
          id="section-other"
          style={{
            font: 'var(--font-heading)',
            marginBottom: 'var(--space-4)',
            color: 'var(--color-text)',
          }}
        >
          その他
        </h2>
        <p style={{ color: 'var(--color-text-muted)' }}>
          アプリが足りない場合は管理者にご相談ください。
        </p>
      </section>
    </div>
  </div>
);
```

**Step F: FeatureCard の inline style を var() 化**

既存 FeatureCard 内の `cardBg` / `cardBorder` / `textColor` / `subtitleColor` への参照を直接 `var(--color-surface)` / `var(--color-border)` / `var(--color-text)` / `var(--color-text-muted)` に置換。`#7c6ff7` hardcode があれば `var(--color-accent)` に。

**Step G: 空状態のコピーを日本語化**

- `"No applications available"` → `"利用可能なアプリがありません"`
- body: `"apps/ ディレクトリに APP.md を追加するとアプリとして認識されます。"`

**重要な制約:**
- **isDark 三項 0 件**（UX-04-6）
- **`#7c6ff7` を MenuScreen.tsx 内に残さない**（UX-04-5）
- **既存の FeatureCard / SkeletonCard / 固定カード（Gems/Canvas/Debate）構造は retain**
- **onNavigate / onOpenGems / onOpenDebate / onOpenCanvas の既存 signature は尊重**（handleThreadClick で既存ルーターを呼ぶだけ）
- **Rajdhani フォントタイトルは維持**（既存 index.html Google Fonts を触らない）
- **D-04: 添付ファイル関連は MenuScreen に出さない**（placeholder も作らない）
- **5 件固定（slice(0, 5)）**（UI-SPEC §Dashboard Visual Design）
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'aria-labelledby="section-' frontend/src/components/MenuScreen.tsx` >= 3 （UX-03-1）
    - `grep -c 'slice(0, 5)' frontend/src/components/MenuScreen.tsx` >= 1 （UX-03-2）
    - `grep -cE 'アプリケーション|最近のスレッド|その他' frontend/src/components/MenuScreen.tsx` >= 3 （UX-03-3）
    - `grep -c '使いたいアプリを選んで始めましょう' frontend/src/components/MenuScreen.tsx` == 1
    - `grep -c "from '../utils/threadGroups'" frontend/src/components/MenuScreen.tsx` >= 1
    - `grep -c 'listThreads' frontend/src/components/MenuScreen.tsx` >= 1
    - `grep -c 'RecentThreadCard' frontend/src/components/MenuScreen.tsx` >= 2 （定義 + 使用）
    - `grep -cE 'isDark \?' frontend/src/components/MenuScreen.tsx` == 0 （UX-04-6）
    - `grep -c '#7c6ff7' frontend/src/components/MenuScreen.tsx` == 0 （UX-04-5）
    - `grep -c 'var(--gradient-title)' frontend/src/components/MenuScreen.tsx` >= 1
    - `grep -c 'var(--color-accent)' frontend/src/components/MenuScreen.tsx` >= 1
    - **B-1 useNavigate gate**:
      - `grep -c 'useNavigate' frontend/src/components/MenuScreen.tsx` >= 1 （import + 呼び出し）
      - `grep -cE "from 'react-router'" frontend/src/components/MenuScreen.tsx` >= 1
      - `grep -c 'const navigate = useNavigate' frontend/src/components/MenuScreen.tsx` >= 1
      - `grep -c 'navigate(' frontend/src/components/MenuScreen.tsx` >= 1
    - **B-1 既存 Props シグネチャ維持 gate**:
      - `grep -c 'onNavigate?.' frontend/src/components/MenuScreen.tsx` == 0 （拡張引数を呼ばない）
      - `grep -cE "onOpenGems\?\.\(thread" frontend/src/components/MenuScreen.tsx` == 0 （thread 引数を渡さない）
    - `cd frontend && bun run --cwd . build` exit 0 （bun ビルドが通る = react-router import が正しい）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
    - 手動: `/orochi/` で 3 セクション（アプリ / 最近 / その他）が縦に並ぶ、最近スレッドが 5 件以下で並ぶ、dark/light 切替で色反映
  </acceptance_criteria>
  <done>
    MenuScreen が 3 セクション構造 + RecentThreadCard + client-side 5 件 sort になり、UX-03-1/2/3 grep gate green。isDark 三項 / hardcoded accent purple 排除済。既存アプリカード機能 retain。
  </done>
</task>

<task type="auto">
  <name>Task 02: theme.css 末尾に @media ブロック集約追加（tablet/mobile + drawer/hamburger CSS + chatscope bubble override）</name>
  <files>frontend/src/theme.css</files>
  <read_first>
    - frontend/src/theme.css 全行（Plan 01 で追加した変数 block、Plan 02 で置換した override block、Plan 04/05 で使う className を確認）
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Responsive Breakpoints (L192-222)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pattern 4 (L522-586)
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §5 (L374-388)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pitfall 2 (L721-731)
  </read_first>
  <action>
theme.css の**末尾**（既存全 override の後）に `/* Phase 35: Responsive */` コメントヘッダー付きで以下を追加する。

```css
/* ============================================================
   Phase 35: Responsive — base rules (theme 独立)
   drawer / hamburger の default 表示制御
   ============================================================ */
.sidebar-drawer {
  /* Desktop default: 既存 Sidebar 挙動を維持 (position: static 相当) */
  position: relative;
}
.header-hamburger {
  display: none;
}

/* ============================================================
   Phase 35: Responsive — Tablet (≤ 1024px)
   UI-SPEC §Responsive + RESEARCH §Pattern 4
   ============================================================ */
@media (max-width: 1024px) {
  /* MenuScreen: カード grid を狭く、padding 縮小 */
  .menu-screen {
    padding: var(--space-6) var(--space-4) !important;
  }
  .menu-card-grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)) !important;
  }

  /* Header: Model ラベル / username 非表示 */
  .header-model-label {
    display: none;
  }
  .header-user-login {
    display: none;
  }

  /* ThreadSidebar: drawer overlay として動作 */
  .sidebar-drawer {
    position: fixed !important;
    top: 48px;
    bottom: 0;
    left: 0;
    z-index: 50;
    width: min(80vw, 320px) !important;
    transform: translateX(-100%);
    transition: transform 0.2s ease-out;
    background: var(--color-surface);
    border-right: 1px solid var(--color-border);
    overflow-y: auto;
  }
  .sidebar-drawer.open {
    transform: translateX(0);
  }
  .sidebar-backdrop {
    position: fixed;
    inset: 0;
    z-index: 49;
    background: rgba(0, 0, 0, 0.5);
  }

  /* Chatscope bubble: outgoing のみ max-width 85% (Pitfall 2 — incoming は変更しない) */
  .cs-message--outgoing .cs-message__content-wrapper {
    max-width: 85% !important;
  }

  /* InputBar: padding 縮小、toolbarSlot が 1 行に収まらない場合に縦積み許容 */
  .chat-input-row {
    flex-wrap: wrap !important;
    padding: 10px !important;
  }
}

/* ============================================================
   Phase 35: Responsive — Mobile (≤ 767px)
   破綻回避のみ保証 (D-05)
   ============================================================ */
@media (max-width: 767px) {
  /* MenuScreen: 1 列固定 */
  .menu-screen {
    padding: var(--space-4) var(--space-3) !important;
  }
  .menu-card-grid,
  .menu-recent-grid {
    grid-template-columns: 1fr !important;
  }

  /* Header: hamburger 表示、desktop actions 非表示 */
  .header-hamburger {
    display: inline-flex !important;
  }
  .header-desktop-actions {
    display: none !important;
  }

  /* InputBar: textarea padding 縮小、Send ボタンは必ず表示 */
  .chat-textarea {
    padding: 0.5rem !important;
  }

  /* Chatscope bubble: 両サイド 100% 幅 */
  .cs-message--outgoing .cs-message__content-wrapper {
    max-width: 100% !important;
  }

  /* ThreadSidebar drawer: 幅を mobile 用に調整 */
  .sidebar-drawer {
    width: min(80vw, 320px) !important;
  }
}
```

**重要な制約:**
- **@media block は theme.css 末尾に集約配置**（RESEARCH.md Open Question #4 決定）。コンポーネント別 `.module.css` を新規作成しない（D-01 方針「追加ツールなし」）。
- **`.cs-message--incoming` は触らない**（Pitfall 2 — Monaco/AG Grid が潰れる）
- **drawer z-index = 50, backdrop z-index = 49**（Pitfall 7 — ConfirmModal 9999 より十分低い）
- **hamburger z-index = 40**（Plan 05 inline で指定済、ここでは確認のみ）
- **tablet の drawer は `transform: translateX(-100%)` → `.open` で `translateX(0)`** （`display: none` では transition が出ない）
- **mobile で breakpoint が切り替わる際、drawer 幅は `min(80vw, 320px)` を両方の @media で指定**（cascade で上書きされるが明示的に書く）
- **既存 `!important` 宣言は変更しない**（theme.css 全体の specificity 勝負）
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '@media (max-width: 1024px)' frontend/src/theme.css` >= 1 （UX-04-3）
    - `grep -c '@media (max-width: 767px)' frontend/src/theme.css` >= 1 （UX-04-4）
    - `grep -c '.sidebar-drawer' frontend/src/theme.css` >= 2 （base rule + @media 内）
    - `grep -c '.sidebar-backdrop' frontend/src/theme.css` >= 1
    - `grep -c '.header-hamburger' frontend/src/theme.css` >= 2 （base `display: none` + mobile `display: inline-flex`）
    - `grep -c '.cs-message--outgoing' frontend/src/theme.css` >= 1 （tablet override）
    - `grep -cE '\.cs-message--incoming .cs-message__content-wrapper\s*\{[^}]*max-width:\s*85%' frontend/src/theme.css` == 0 （Pitfall 2 — incoming に 85% が漏れていない）
    - `grep -c 'z-index: 50' frontend/src/theme.css` >= 1 （drawer）
    - `grep -c 'z-index: 49' frontend/src/theme.css` >= 1 （backdrop）
    - `grep -c 'translateX(-100%)' frontend/src/theme.css` >= 1
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
    - 手動: Chrome DevTools Responsive Mode で 1024px にすると ThreadSidebar が drawer overlay 化、`.cs-message--outgoing` の幅が 85% に縮小、incoming bubble は既存幅維持。Header の Model ラベル / username が非表示。
    - 手動: 767px で 1 列 grid、hamburger 表示、desktop actions 非表示。
  </acceptance_criteria>
  <done>
    theme.css 末尾に Phase 35 Responsive セクション（~70 行）が追加された。tablet/mobile で drawer / hamburger / bubble width / grid 挙動が activate する。Pitfall 2 回避（incoming bubble 触らず）、Pitfall 7 回避（z-index 適正）。build/lint green、Chrome DevTools Responsive で挙動 verified。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MenuScreen (client-side sort) ↔ listThreads API | backend の ORDER BY に依存せず client で sort（Pitfall 3）。 |
| drawer overlay ↔ ConfirmModal (stacking) | drawer z-index=50, backdrop=49, ConfirmModal=9999 → Confirm は確実に drawer の上に出る。 |
| tablet @media bubble cap (outgoing) ↔ Monaco/AG Grid (incoming) | incoming に max-width: 85% を漏らさないことで Monaco 潰れを防ぐ（Pitfall 2）。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-26 | Tampering | 最近スレッド表示が意図せず 5 件を超える (Pitfall 3) | mitigate | Task 01 action で `[...allThreads].sort(...).slice(0, 5)` を明示。acceptance で `grep -c 'slice(0, 5)'` >= 1。 |
| T-35-27 | DoS (visual) | tablet で Monaco Editor が 85% cap で潰れる (Pitfall 2) | mitigate | Task 02 action で `.cs-message--outgoing` のみに cap を当てることを明示。acceptance で `grep` で incoming に漏れていないことを verify。 |
| T-35-28 | Information Disclosure | mobile で Header hamburger を開くと Logout / Theme toggle が表示される — 画面共有時の情報漏洩 | accept | 社内 200 名規模、screen sharing 配慮は user 責務。Logout は destructive なので既存 ConfirmModal で確認ダイアログが出る（既存仕様）。 |
| T-35-29 | DoS (visual) | drawer open 中の z-index 衝突で ConfirmModal が操作不能 (Pitfall 7) | mitigate | Task 02 action で z-index 明示（drawer 50, backdrop 49）。ConfirmModal 9999 （verified Read L43）との差は 9900+。 |
| T-35-30 | Elevation of Privilege | app_id ベースルーティングで app_id 改ざんによる誤遷移 | accept | app_id は backend から返される thread metadata、untrusted input とは見なさない。誤遷移しても同じユーザーのスレッドのみアクセス可能（既存 JWT + github_login WHERE filter がバックエンドで効いている）。 |

すべて LOW severity。security_enforcement 閾値は high のみなので block しない。
</threat_model>

<verification>
- `cd frontend && bun run lint && bun run build` 両方 exit 0
- `bash scripts/check-phase-35.sh` で UX-03-1/2/3, UX-04-3/4 が PASS（他の UX-04-5/6/7 は Plan 03/04/05 で既に PASS しているはず）
- `docker compose up` → `/orochi/` で 3 セクションダッシュボードを目視確認
- Chrome DevTools Responsive Mode 1024px: ThreadSidebar drawer overlay 動作、Model ラベル非表示
- Chrome DevTools Responsive Mode 767px: 1 列 grid、hamburger 表示、desktop actions 非表示、横スクロールゼロ
- 最近スレッドカードをクリック → 対応アプリへ遷移
</verification>

<success_criteria>
- **UX-03 要件全て達成**:
  - UX-03-1 (3 セクション) grep PASS
  - UX-03-2 (5 件 slice) grep PASS
  - UX-03-3 (日本語見出し) grep PASS
  - UX-03-4 (初見ユーザー判別可能) は Plan 07 manual checker で判定
- **UX-04 要件達成**:
  - UX-04-3 / UX-04-4 (@media 1024/767) grep PASS
  - tablet で chatscope bubble / drawer / Header が意図通り動作（visual manual verify）
  - mobile で横スクロールゼロ（visual manual verify）
- Phase 36 Handoff Contract 項目 1-8 のうち 1/2/3/4/5/6/7/8 がすべて PASS（10 の cross-browser は Plan 07）
- MessageArea / ThreadSidebar / Header / MenuScreen 4 コンポーネント全てが CSS 変数駆動で dark/light 即座切替
</success_criteria>

<output>
完了後、`.planning/phases/35-dashboard-design-system/35-06-dashboard-responsive-SUMMARY.md` に以下を記録:
- MenuScreen.tsx 行数 before/after
- theme.css 行数 before/after（Plan 01 + 02 + 06 の累計）
- UX-03-1/2/3/4 の各 grep 結果
- UX-04-3/4 の各 grep 結果
- Chrome DevTools Responsive 1024/767/1440 各幅での screenshot 結果（どの要素が期待通り切り替わったか）
- scripts/check-phase-35.sh の実行結果（期待: UX-04-5/6/7 + UX-03-1/2/3 + UX-04-1/2/3/4 全て PASS、InputBar / MenuScreen 関連が完了していれば manual 部分以外全 PASS）
</output>
