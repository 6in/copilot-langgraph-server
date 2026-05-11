---
phase: 35-dashboard-design-system
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - frontend/src/theme.css
  - frontend/src/utils/threadGroups.ts
  - frontend/src/components/ThreadSidebar.tsx
  - frontend/src/components/InputBar.tsx
  - frontend/src/components/MessageArea.tsx
  - frontend/src/components/Header.tsx
  - frontend/src/components/MenuScreen.tsx
  - frontend/src/components/AuthPanel.tsx
  - scripts/check-phase-35.sh
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 35: Code Review Report

**Reviewed:** 2026-04-23
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 35 は「Primitive + Semantic CSS 変数レイヤー」「isDark 三項の排除」「InputBar 分離」「MenuScreen 3 セクション化」「drawer state 基盤整備」を目的としたリファクタリング中心のフェーズ。機能面の破壊的変更は少なく、コードは全体的に Phase 設計どおりに実装されている。ただし以下の 3 点は修正推奨:

- **WR-01**: `ThreadSidebar.tsx` の drawer Escape ハンドラで `useEffect` の依存配列に `onDrawerOpenChange` / `propDrawerOpen` が抜けており、props 切替時に stale closure になる。
- **WR-02**: `MenuScreen.tsx` で `superchat` ケースが `/chat/{tid}` にフォールバックしている。コメントでは "app_slug 情報が無いので" と書かれているが、superchat のスレッドを chat ルートで開くとハンドラ不一致で壊れる可能性がある。
- **WR-03**: `AuthPanel.tsx` 内に theme 非対応のハードコード色 (`#f6f8fa`, `#d0d7de`, `#ccc`) が残存。Phase 35 の CSS 変数統一方針 (D-01) に反する。

Info レベルでは、未使用変数 (`theme` in ThreadSidebar が `ConfirmModal.isDark` 以外に使われていない → 実は ConfirmModal で使われているので OK）、冗長コメント、hamburger と desktop-actions 両方に `marginLeft: 'auto'` が設定されている構造リスクなどを記録する。

drawer state の UI トリガー未配線は SUMMARY に OPEN 項目として記録済み (Wave 4 verification) のため本レビューでは指摘しない。

## Warnings

### WR-01: useEffect 依存配列欠落により drawer Escape ハンドラが stale closure になる

**File:** `frontend/src/components/ThreadSidebar.tsx:72-79`
**Issue:**
`useEffect` で window に `keydown` リスナーを登録するが、依存配列に `[drawerOpen]` しか含めていない。クロージャーが参照する `setDrawerOpen` は `onDrawerOpenChange` プロップに依存しているため、親が `onDrawerOpenChange` を差し替えた場合、Escape キーで古いコールバックが呼ばれる (controlled → uncontrolled 切替時、または別の setter に差し替えた時)。現状は実害が出にくいが、controlled mode での props 差し替えで sync が崩れる。また ESLint `react-hooks/exhaustive-deps` ルールを入れている場合は警告が出る。

**Fix:**
```tsx
useEffect(() => {
  if (!drawerOpen) return;
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') setDrawerOpen(false);
  };
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
  // setDrawerOpen は propDrawerOpen/onDrawerOpenChange から導出されるため両方を deps に含める
}, [drawerOpen, onDrawerOpenChange, propDrawerOpen]);
```
もしくは `setDrawerOpen` を `useCallback` で安定化する方法もある。

---

### WR-02: MenuScreen の superchat フォールバックがルート不整合を起こす可能性

**File:** `frontend/src/components/MenuScreen.tsx:87-90`
**Issue:**
`superchat` の `ThreadInfo` に対し `/chat/{tid}` にフォールバックしている:
```tsx
case 'superchat':
  // RecentThreadCard には app_slug 情報が無いので、chat フォールバック
  navigate(`/chat/${tid}`);
  break;
```
しかし実際には SuperChat は独自のオーケストレーションハンドラ (`orchestrator_handler.py`) を使うため、同じ thread_id を Chat ハンドラで開くとメッセージ履歴は表示できても以降の送信で挙動が変わる（subagent ルーティングが利かない等）。また、ユーザーから見ると「SuperChat スレッドをクリックしたのに普通のチャットに遷移した」という UX バグになる。app_id が `superchat` であれば `/superchat/${tid}` 等の正しいルートへ遷移すべき、または「アプリ slug 情報が取れない場合はフォールバックせずアラート表示」のほうが安全。

**Fix:**
```tsx
case 'superchat':
  // SuperChat には専用ルートがあるはず。適切な path に合わせる
  navigate(`/superchat/${tid}`);
  break;
```
もし SuperChat の URL 設計が固まっていないなら、少なくとも console.warn で不整合を記録するか、エラーフィードバックを出すこと。App.tsx のルート定義を確認して正しい path を入れるのが望ましい。

---

### WR-03: AuthPanel にハードコード色が残存 (Phase 35 D-01 違反)

**File:** `frontend/src/components/AuthPanel.tsx:51, 78-79, 92`
**Issue:**
Phase 35 の方針では「isDark 三項排除 + CSS 変数統一」を全面適用するが、AuthPanel には以下のハードコード色が残っている:

- L51: `border: '1px solid #ccc'` (Start 認証ボタン)
- L78-79: `background: '#f6f8fa'`, `border: '1px solid #d0d7de'` (デバイスコード表示)
- L92: `border: '1px solid #ccc'` (Copy ボタン)

これらは dark mode では `theme.css` の `[data-theme="dark"] .auth-device-code` / `.auth-copy-btn` / `.auth-start-btn` で上書きされるため見た目上は問題ないが、**Light mode の色が theme.css の `--color-border` / `--color-surface` を経由しない**ため single source of truth (D-01) が崩れている。また `check-phase-35.sh` の hardcode 検査は `#7c6ff7` のみをチェックしており、他のハードコード色は検知しないため grep ベースでも漏れている。

**Fix:**
```tsx
// L51
border: '1px solid var(--color-border)',

// L73-82
<span className="auth-device-code" style={{
  fontSize: '2rem',
  fontWeight: 'bold',
  fontFamily: 'monospace',
  letterSpacing: '0.15em',
  background: 'var(--color-neutral-100)',  // 既存 primitive を利用
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: '0.5rem 1rem',
}}>

// L92
border: '1px solid var(--color-border)',
```
併せて `check-phase-35.sh` に AuthPanel を検査対象に含めるか、または hex pattern (`#[0-9a-fA-F]{3,6}`) を検出するチェックを追加するとリグレッションを防げる。

## Info

### IN-01: getDateGroup の diffDays < 0（未来日付）が "今日" に吸収される

**File:** `frontend/src/utils/threadGroups.ts:20`
**Issue:**
```ts
if (diffDays < 0 || diffDays === 0) return '今日';
```
未来日付 (タイムゾーンずれや時計ずれによる `updated_at` が now より後) を無条件に "今日" として扱っている。厳密には NTP ずれ等で起きうるエッジケース。意図的な実装に見えるがコメントがないと "バグかどうか判断できない"。

**Fix:** 意図を明記するコメントを追加する:
```ts
// NTP ずれ等で未来日付が来た場合も "今日" として扱う (防御的実装)
if (diffDays <= 0) return '今日';
```

---

### IN-02: groupThreads で同じキーを使用する複数スレッドの順序保証

**File:** `frontend/src/utils/threadGroups.ts:27-35`
**Issue:**
`groupThreads` は threads を入力順のままバケットに入れるのみで sort しない。呼び出し元 (`MenuScreen` は既に `localeCompare` で sort 済み、`ThreadSidebar` は backend 順に依存) 次第で順序が変わる。Phase 35 DESIGN-03 "Pitfall 3 対策: backend order by に依存しない client-side sort" を徹底するなら groupThreads 内でも sort する方が一貫性がある。

**Fix:** 必須ではないが、groupThreads 内でグループごとに `updated_at DESC` ソートを加えると安全:
```ts
for (const [group, items] of groups) {
  items.sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''));
}
```

---

### IN-03: ThreadSidebar の groupThreads シャドウイングで ESLint 警告の恐れ

**File:** `frontend/src/components/ThreadSidebar.tsx:14, 356`
**Issue:**
`import { groupThreads, groupOrder }` していながら、L356 の `.map` 内で `const groupThreads = grouped.get(groupLabel);` と同名変数を定義している。TypeScript 的には問題ないが、外側スコープの `groupThreads` 関数を参照できなくなるシャドウイングで、`no-shadow` ルールを入れている場合に警告が出る。可読性のためにも変数名を変えるべき。

**Fix:**
```tsx
{groupOrder.map((groupLabel) => {
  const threadsInGroup = grouped.get(groupLabel);
  if (!threadsInGroup || threadsInGroup.length === 0) return null;
  // ... 以降も threadsInGroup を使う
```

---

### IN-04: Header にレイアウト重複 (`marginLeft: 'auto'` の重複設定)

**File:** `frontend/src/components/Header.tsx:119, 194`
**Issue:**
`.header-desktop-actions` と `.header-hamburger` の両方に `marginLeft: 'auto'` を設定している。Desktop では hamburger が `display: none` なので問題ないが、Tablet (≤1024px) では hamburger は依然非表示で `header-user-login` / `header-model-label` が非表示化されるのみ。Mobile (≤767px) では `header-desktop-actions` が非表示、`header-hamburger` が表示される設計。両方同時に存在する中間幅 (例えば max-width:767px を満たさないタブレットギリギリ) で `marginLeft: auto` が両方同時に効き、レイアウトが想定と異なる可能性。

現状 responsive CSS は `768-1024px` で hamburger が隠れ `desktop-actions` が表示される状態になるので実害はないが、意図を明示するコメントを足すか、構造を見直すと良い。

**Fix:** コメントで明示するか、hamburger を常に表示側に寄せる設計に統一する。

---

### IN-05: AuthPanel が inline `@keyframes spin` 参照を持たない

**File:** `frontend/src/components/AuthPanel.tsx:100`
**Issue:**
```tsx
<span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span>
```
`spin` keyframe が `theme.css` に定義されていない (grep 済み: `typing-bounce` と `pulse` のみ定義)。どこか他の場所 (chatscope の ui-kit CSS など) に `@keyframes spin` があれば偶然動くが、依存元を失うと無音で回らなくなる。

**Fix:** `theme.css` に keyframe を追加する:
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

### IN-06: check-phase-35.sh の grep 検査が brittle

**File:** `scripts/check-phase-35.sh:33, 49-52`
**Issue:**
- L33: `^\s*--color-(bg|surface|border|text|accent|destructive|success|header)` で semantic 色変数を探すが、`--color-text-muted` / `--color-surface-elevated` も同じプレフィックスで始まるため expected "≥ 13" の中に重複カウントされうる。期待は満たすが "semantic カラーが何種あるか" の測定にはなっていない。
- L49-52: hardcode 検査が `#7c6ff7` と `isDark ?` の 2 種のみ。他の hardcode hex (`#24292e`, `#888`, `#999`, `#fff` 等) は見逃す (WR-03 で指摘のとおり AuthPanel の `#f6f8fa` 等も漏れている)。
- L68: `grep -c 'aria-labelledby="section-'` が期待 `≥ 3` だが、現状 3 つあるため PASS する一方、将来 section を追加・削除した際の sanity check として弱い。

**Fix:** (必須ではない) hardcode 検査を `#[0-9a-fA-F]{3,6}` に拡張、または `oklch(` / `rgb(` も含めた汎用 pattern にする。対象ファイルに AuthPanel を追加する。
```bash
for FILE in ...AuthPanel.tsx ...; do
  C=$(grep -cE '#[0-9a-fA-F]{3,6}' "$FILE" || true)
  check "UX-04-5b no-hardcode-hex in $(basename "$FILE") == 0" "$C" eq 0
done
```

---

_Reviewed: 2026-04-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
