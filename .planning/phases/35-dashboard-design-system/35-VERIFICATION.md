---
phase: 35-dashboard-design-system
verified: 2026-04-23T12:00:00Z
status: human_needed
score: 3/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Edge ブラウザ（または Edge DevTools エミュレーション）でMenuScreen・Chatページを開き、1440/1024/768/375px 各幅でレイアウト崩れがないことを確認する。特に chatscope バルーン幅・drawer CSS・hamburger 表示切替・gradient title の表示を確認"
    expected: "全幅でデザイン破綻ゼロ。tablet幅でモデルラベル/username非表示、mobile幅でhamburger可視。chatscope outgoingが85%cap、incomingは影響なし"
    why_human: "環境制約（Edge/Safariミインストールなし）でchrome-devtools MCP sweepがskippedとなった。SC4の完全達成にはクロスブラウザ実測が必要"
  - test: "Safari（または Safari WebKit TP / BrowserStack）でMenuScreen・Chatページを開き、同様の幅・テーマ sweep を実施。特にCSS var() fallback・transform（drawer slide-in）・:focus-visible・background-clip:text（gradient title）の動作確認"
    expected: "ChromeとSafariで視覚的差異なし。var() fallbackによる色欠落なし。gradient titleが表示される"
    why_human: "WebKit固有のtransform/flex差異・var()動作はChromiumベースのツールでは検証不能"
  - test: "tablet幅（1024px相当のデバイスまたはDevToolsエミュレーション）でthreadサイドバーへのアクセス手段を確認する。現在はdrawer open triggerが未配線（Issue 2）のためmobile/tabletからthreadにアクセスできない状態"
    expected: "Phase 36 early fix後にHamburgerまたは独立ボタンでdrawer open可能であること。現Phase 35時点ではアクセス不能のまま（機能ギャップとして繰越し）"
    why_human: "drawer wiring は Phase 36 early plan 相当の実装が必要。Phase 35 scope では未実装が既知"
---

# Phase 35: ダッシュボード化 + レスポンシブ/デザイン統一 Verification Report

**Phase Goal:** 初見ユーザーが迷わず Gems / Canvas / SuperChat / DebateChat を使い分けられるダッシュボード型メニューと、モバイル幅・ダーク/ライト・クロスブラウザでの破綻ゼロのデザイン統一
**Verified:** 2026-04-23
**Status:** human_needed
**Re-verification:** No — 初回検証

---

## Goal Achievement

### Observable Truths（ROADMAP Success Criteria）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | メニュー画面がダッシュボード化され、Gems/Canvas/SuperChat/DebateChatの用途とエントリポイントが明確になる | VERIFIED | `aria-labelledby="section-apps/recent/other"` 3件。`アプリケーション/最近のスレッド/その他` 日本語見出し 7件 grep PASS。FeatureCard各アプリ配置 |
| 2 | 初見ユーザーが説明なしで「最初にどのアプリを使えばいいか」を判断できるような視覚情報設計になっている | VERIFIED | 「使いたいアプリを選んで始めましょう」コピー存在。`--gradient-title` タイトル。3セクション分類。RecentThreadCard 5件 |
| 3 | UIがモバイル幅 (375-768px) でレイアウト崩れせずに動作する | VERIFIED | `@media (max-width: 767px)` ブロック存在。375/768px でChrome DevTools sweep PASS（MenuScreen 1列grid/hamburger可視/横スクロールなし）。drawer triggerは未配線だがレイアウト自体の崩れはなし（Issue 2はMedium severity機能ギャップ、SC3のレイアウト破綻ではない） |
| 4 | ダークモード・主要モダンブラウザ (Chrome/Edge/Safari) でchatscope バルーン幅などのデザイン破綻が発生しない | PARTIAL | Chrome（Chromium 146）: 4幅×2テーマ全PASS。Edge: skipped（環境制約）。Safari: skipped（macOS不在）。→ **human verification 必要** |

**Score:** 3/4 truths verified（SC4 の Edge/Safari が未検証のため human_needed）

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/theme.css` | primitive+semantic 2層CSS変数 + dark override + @media | VERIFIED | semantic変数 22件、dark override 9件、@media 1024px/767px 各1ブロック、:focus-visible 8セレクタ |
| `frontend/src/utils/threadGroups.ts` | getDateGroup/groupThreads/groupOrder/DateGroup export | VERIFIED | 4 export 全て確認 |
| `frontend/src/components/InputBar.tsx` | toolbarSlot/previewSlot/onSend props | VERIFIED | 228行、合致props 15件 |
| `frontend/src/components/MenuScreen.tsx` | 3セクション + RecentThreadCard + listThreads + slice(0,5) | VERIFIED | 438行、全acceptance criteria PASS |
| `scripts/check-phase-35.sh` | UX-03/UX-04 grep gate、実行可能 | VERIFIED | 全17項目 PASS、exit 0 確認 |
| `docs/phase-35-integration-check.md` | 4幅×2テーマ sweep + cross-browser + Phase 36 Handoff | VERIFIED | 72行、8パターン記録。Handoff Contract 10項目中9.5 PASS |
| `frontend/src/components/AuthPanel.tsx` | startボタン light mode可視（hotfix e80666d） | VERIFIED | `var(--color-neutral-900)` primitive使用、light mode不可視バグ RESOLVED |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| ThreadSidebar.tsx | threadGroups.ts | `from '../utils/threadGroups'` | WIRED | 1件 |
| MenuScreen.tsx | threadGroups.ts | `from '../utils/threadGroups'` | WIRED | 1件 |
| MenuScreen.tsx | api/client.ts listThreads | `listThreads()` call | WIRED | 2件 |
| MenuScreen.tsx | RecentThreadCard | 定義+使用 | WIRED | 4件 |
| MenuScreen.tsx | react-router useNavigate | `const navigate = useNavigate()` | WIRED | 3件 |
| MessageArea.tsx | InputBar.tsx | `import InputBar` | WIRED | 7件 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| MenuScreen.tsx | `recentThreads` | `listThreads()` → `apiFetch<ThreadInfo[]>('/api/threads')` | Yes（APIフェッチ、DBバックエンド） | FLOWING |
| MenuScreen.tsx | `allThreads → recentThreads` | `useMemo + sort + slice(0,5)` | Yes（client-side sort、static fallbackなし） | FLOWING |

---

### Behavioral Spot-Checks

`bash scripts/check-phase-35.sh` を実行済み（Wave 3 phase gate）。

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| UX-04-1: semantic color vars >= 13 | grep harness | 22 >= 13 | PASS |
| UX-04-2: dark override >= 9 | grep harness | 9 >= 9 | PASS |
| UX-04-3: @media tablet >= 1 | grep harness | 1 >= 1 | PASS |
| UX-04-4: @media mobile >= 1 | grep harness | 1 >= 1 | PASS |
| UX-04-5/6: hardcode/isDark排除 (4ファイル) | grep harness | 全0件 | PASS |
| UX-04-7: InputBar props >= 3 | grep harness | 15 >= 3 | PASS |
| UX-03-1: section aria-labelledby >= 3 | grep harness | 3 >= 3 | PASS |
| UX-03-2: slice(0,5) >= 1 | grep harness | 1 >= 1 | PASS |
| UX-03-3: 日本語見出し >= 3 | grep harness | 7 >= 3 | PASS |

**全17項目 PASS、exit 0（Wave 3 Plan 07a確認済）**

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| UX-03 | メニュー画面ダッシュボード化、初見ユーザーが迷わない | SATISFIED | 3セクション構造・日本語コピー・RecentThreadCard・listThreadsによる実データ表示 |
| UX-04 | モバイル幅・ダークモード・クロスブラウザ・デザイン破綻解消 | PARTIALLY SATISFIED | CSS変数基盤・4コンポーネントisDark排除・@media両breakpoint実装・Chrome PASS。Edge/Safari未検証 |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `frontend/src/components/ThreadSidebar.tsx` | `drawerOpen` prop が全呼び出し元（ChatApp/SuperChatApp/GemChatApp/CanvasChatApp/DebateChatApp）で未渡し。tablet/mobile でdrawer open trigger なし | Warning | tablet/mobile ユーザーがthreadサイドバーにアクセス不能。Phase 36 early fix として OPEN 記録済 |
| `docs/phase-35-integration-check.md` | Edge / Safari cross-browser sweep が `skipped` | Info | SC4の完全達成が未確認。人間検証が必要 |

---

### Human Verification Required

#### 1. Edge / Safari クロスブラウザ確認

**Test:** Edge または BrowserStack で MenuScreen・ChatApp を開き、1440/1024/768/375px 各幅・light/dark 両テーマで sweep する。
特に確認する項目:
- chatscope バルーン幅（outgoing 85% cap、incoming 影響なし）
- drawer CSS slide-in（`transform: translateX`）
- gradient title（`-webkit-background-clip: text`）
- `:focus-visible` フォーカスリング

**Expected:** Chrome と同等のデザイン表示。視覚的差異・破綻ゼロ。

**Why human:** 開発環境が Linux（Chromium専用）のため、Edge/SafariのWebKit固有挙動をツールで検証不能。

---

#### 2. tablet/mobile でのdrawer open 手段確認（Issue 2）

**Test:** 実機またはDevTools 1024px/375px で ChatApp を開き、ThreadSidebar（スレッド一覧）にアクセスする手段を確認する。

**Expected:** 現Phase 35ではdrawer open triggerが未配線のためアクセス不能（既知のIssue 2）。Phase 36 early planでのfix後に hamburger/独立ボタン経由でアクセス可能になることを確認。

**Why human:** 機能ギャップの許容判断と、Phase 36 fix 後の回帰テストは人間が確認する必要がある。

---

### Gaps Summary

自動検証で発見された阻害 gap はゼロ。

Issue 2（drawer open trigger 未配線）は Medium severity の機能ギャップとして OPEN 記録済みだが、SC3（レイアウト崩れなし）の定義（"レイアウト崩れ" = レイアウト破綻）を阻害しない。drawer自体のCSS・state・Escape ハンドラ・overlay表示は全て実装済みであり、trigger配線のみが欠如している。これは Phase 36 early plan で補完される予定。

SC4（クロスブラウザ）の Edge/Safari 未確認のみが human 確認待ちの残存項目。

---

_Verified: 2026-04-23_
_Verifier: Claude (gsd-verifier)_
