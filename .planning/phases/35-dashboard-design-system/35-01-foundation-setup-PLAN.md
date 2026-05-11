---
phase: 35
plan: 01
title: "Foundation Setup — CSS 変数基盤 + utils 切り出し + 検証ハーネス"
status: draft
type: execute
wave: 0
depends_on: []
files_modified:
  - frontend/src/theme.css
  - frontend/src/utils/threadGroups.ts
  - frontend/src/components/ThreadSidebar.tsx
  - scripts/check-phase-35.sh
autonomous: true
requirements: [UX-04]
requirements_addressed: [UX-04]
tags: [frontend, theme, css-variables, utility-extraction]
must_haves:
  truths:
    - "theme.css 先頭に primitive + semantic の 2 層 CSS 変数ブロックが存在する"
    - "[data-theme=\"dark\"] ブロックに semantic 変数の dark override が存在する"
    - "frontend/src/utils/threadGroups.ts が getDateGroup / groupThreads / groupOrder / DateGroup を export する"
    - "ThreadSidebar.tsx が threadGroups.ts から import して使う（重複実装ゼロ）"
    - "scripts/check-phase-35.sh が存在し実行可能で grep ベース verification を連続実行する"
  artifacts:
    - path: "frontend/src/theme.css"
      provides: "primitive + semantic CSS 変数の宣言、:root と [data-theme=\"dark\"] 両方"
      contains: "--color-bg, --color-surface, --color-border, --color-text, --color-accent, --color-destructive, --color-success, --color-header-bg, --space-1..16, --radius-sm/md/lg/full, --gradient-title"
    - path: "frontend/src/utils/threadGroups.ts"
      provides: "日付グループ分類ユーティリティ（MenuScreen 最近スレッドと ThreadSidebar で共有）"
      exports: ["getDateGroup", "groupThreads", "groupOrder", "DateGroup"]
    - path: "scripts/check-phase-35.sh"
      provides: "UX-03-1〜3 / UX-04-1〜7 の grep 検証ハーネス"
      contains: "set -euo pipefail"
  key_links:
    - from: "frontend/src/components/ThreadSidebar.tsx"
      to: "frontend/src/utils/threadGroups.ts"
      via: "import getDateGroup / groupThreads / groupOrder / DateGroup"
      pattern: "from '../utils/threadGroups'"
    - from: "frontend/src/theme.css"
      to: "frontend/src/theme.css (semantic layer uses primitive via var())"
      via: "var(--color-*) 連鎖"
      pattern: "var\\(--color-"
---

<objective>
Phase 35 の基盤となる CSS 変数トークン体系（primitive + semantic 2 層）を theme.css に追加し、後続 Wave で消費される共有ユーティリティ（threadGroups.ts）と検証ハーネス（check-phase-35.sh）を準備する。

**Purpose:** Wave 1 以降のファイル別 migration が並列実行できる基盤を Wave 0 で確定する。theme.css は Plan 02 で単独占有 → Plan 06 で末尾追記という順序で書き込みされる。

**Output:**
- `theme.css` に 2 層 CSS 変数ブロック追加（既存 hex は置換しない、追加のみ）
- `utils/threadGroups.ts` 新規（ThreadSidebar の date group ロジックを切り出し）
- `ThreadSidebar.tsx` を import ベースに書き換え
- `scripts/check-phase-35.sh` 新規（Phase 35 grep gate ハーネス）
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/35-dashboard-design-system/35-CONTEXT.md
@.planning/phases/35-dashboard-design-system/35-UI-SPEC.md
@.planning/phases/35-dashboard-design-system/35-RESEARCH.md
@.planning/phases/35-dashboard-design-system/35-PATTERNS.md
@.planning/phases/35-dashboard-design-system/35-VALIDATION.md
@.planning/patterns.md

<interfaces>
<!-- ThreadInfo 型 (verified by Read: frontend/src/types.ts L37-42) -->
```typescript
export interface ThreadInfo {
  thread_id: string;
  updated_at?: string | null;
  label: string;
  app_id?: string;  // gem_id フィールドは無い（A1 verified）
}
```

<!-- ThreadSidebar 既存 date group ロジック (verified by Read: ThreadSidebar.tsx L61-86) -->
既存 `DateGroup` / `groupOrder` / `getDateGroup` / `groupThreads` を丸ごと utils へ移動する。

<!-- ConfirmModal z-index 確定値 (verified by Read: ConfirmModal.tsx L43) -->
`zIndex: 9999` — drawer backdrop 用の z-index:49 / drawer:50 と衝突しない（Pitfall 7 不発）。

<!-- install-hooks.sh の pattern (PATTERNS.md §4) -->
`#!/usr/bin/env bash` + 日本語 header + `set -euo pipefail` + `REPO_ROOT="$(git rev-parse --show-toplevel)"`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 01: theme.css 先頭に primitive + semantic 2 層 CSS 変数ブロックを追加</name>
  <files>frontend/src/theme.css</files>
  <read_first>
    - frontend/src/theme.css (現行 397 行、先頭の既存構造を把握)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Token Naming & Layering (L34-106)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Spacing Scale (L108-137)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Typography (L140-160)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pattern 1 (L204-301)
  </read_first>
  <action>
theme.css の既存 `:root { color-scheme: light dark; }` ブロック（L1-3 付近）の直後に、以下 2 ブロックを追加する。**既存の 397 行の hex 値は一切変更しない。追加のみ。**

**追加ブロック 1: `:root` に primitive + semantic light + spacing + radius + font + gradient を追加**

UI-SPEC §Primitive Token 一覧 (L58-80) に記載された 19 primitive すべて、UI-SPEC §Semantic Token 一覧 (L82-98) に記載された 14 semantic すべて、UI-SPEC §Spacing Scale (L116-123) の 8 値、UI-SPEC §Typography (L143-156) の 5 font shorthand + 2 family 変数、`--gradient-title`、radius 4 値を verbatim で宣言する:

```css
/* ============================================================
   Phase 35: Design Tokens — Primitive Layer (theme 不変、直接参照禁止)
   ============================================================ */
:root {
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
     Phase 35: Design Tokens — Semantic Layer (Light 値)
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

  /* Spacing scale (8-point) */
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

  /* Font families */
  --font-family-body:    system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-family-display: 'Rajdhani', sans-serif;

  /* Font shorthand (role based) */
  --font-body:    400 16px/1.5 var(--font-family-body);
  --font-label:   400 14px/1.4 var(--font-family-body);
  --font-heading: 600 20px/1.3 var(--font-family-body);
  --font-display: 700 44.8px/1.1 var(--font-family-display);
  --font-caption: 400 12px/1.4 var(--font-family-body);

  /* Gradient (theme 不変) */
  --gradient-title: linear-gradient(90deg,
    var(--color-purple-300),
    var(--color-purple-500),
    var(--color-cyan-400)
  );
}
```

**追加ブロック 2: `[data-theme="dark"]` に semantic dark override を追加**

theme.css の上記 `:root` ブロックの直後、既存 `[data-theme="dark"] .cs-main-container` 等の override より前に追加する:

```css
/* ============================================================
   Phase 35: Design Tokens — Semantic Layer (Dark override)
   primitive は theme 不変のため再定義しない。
   accent / destructive / success も theme 不変。
   ============================================================ */
[data-theme="dark"] {
  --color-bg:               var(--color-dark-bg);
  --color-surface:          var(--color-dark-surface);
  --color-surface-elevated: var(--color-dark-elevated);
  --color-border:           var(--color-dark-border);
  --color-text:             var(--color-dark-text);
  --color-text-muted:       var(--color-neutral-400);
  --color-accent-subtle:    var(--color-dark-elevated);
  --color-header-bg:        var(--color-dark-bg);
  --color-header-text:      var(--color-dark-text);
}
```

**重要な制約（D-01, D-02 準拠）:**
- 既存 `[data-theme="dark"] .cs-*` 等の override ブロックは**一切変更しない**（Wave 1 Plan 02 が機械的に hex → var() 置換する）
- 変数名は UI-SPEC §Primitive / Semantic Token 一覧の表どおり（タイプミス厳禁 — Pitfall 6: Safari で未定義 var() は transparent になる）
- `--color-accent` / `--color-accent-contrast` / `--color-destructive` / `--color-success` は**dark ブロックで再定義しない**（theme 不変）

**副次的注意:** `bun run --cwd frontend build` で `tsc -b` + Vite ビルドが通ること。CSS 変数追加のみなので TypeScript 影響なし。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run lint &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -cE '^\s*--color-(bg|surface|border|text|accent|destructive|success|header)' frontend/src/theme.css` >= 13 （:root + [data-theme="dark"] 合計）
    - `grep -c '^\s*--color-purple-500:' frontend/src/theme.css` == 1 （primitive）
    - `grep -c '^\s*--color-dark-bg:' frontend/src/theme.css` == 1
    - `grep -c '^\s*--space-1:' frontend/src/theme.css` == 1
    - `grep -c '^\s*--radius-sm:' frontend/src/theme.css` == 1
    - `grep -c '^\s*--font-display:' frontend/src/theme.css` == 1
    - `grep -c '^\s*--gradient-title:' frontend/src/theme.css` == 1
    - `awk '/\[data-theme="dark"\]\s*{/,/^\}$/' frontend/src/theme.css | grep -cE '^\s*--color-'` >= 9 （dark ブロック内の semantic override）
    - `cd frontend && bun run build` exit 0 （`tsc -b` + Vite build green）
    - `cd frontend && bun run lint` exit 0
    - theme.css の既存 397 行の hex 値は変更されていない（`git diff frontend/src/theme.css` で既存 hex が削除されていないことを確認）
  </acceptance_criteria>
  <done>
    primitive + semantic 2 層 CSS 変数が theme.css 冒頭に宣言され、`:root` と `[data-theme="dark"]` 両方に semantic トークンが存在する。既存 397 行の既存 override には変更なし（追加のみ）。build/lint 共に green。
  </done>
</task>

<task type="auto">
  <name>Task 02: threadGroups.ts を新規作成し ThreadSidebar.tsx を import 化</name>
  <files>frontend/src/utils/threadGroups.ts, frontend/src/components/ThreadSidebar.tsx</files>
  <read_first>
    - frontend/src/components/ThreadSidebar.tsx L1-100 （既存 import 構造と date group 関数実装 L61-86 を確認）
    - frontend/src/utils/agentColor.ts （同じ utility パターンの既存ファイル、style reference）
    - frontend/src/types.ts （ThreadInfo 型参照）
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §3 (L228-271 — 移行手順)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Example 4 (L944-966)
  </read_first>
  <action>
**Step A**: `frontend/src/utils/threadGroups.ts` を新規作成する。内容は **ThreadSidebar.tsx L61-86 からの 1:1 コピー** + `export` キーワード追加:

```typescript
// frontend/src/utils/threadGroups.ts
// Date-based grouping of threads — extracted from ThreadSidebar.tsx during Phase 35 (D-02).
// Shared by ThreadSidebar (existing consumer) and MenuScreen "最近のスレッド" section (Plan 06).

import type { ThreadInfo } from '../types';

export type DateGroup = '今日' | '昨日' | '今週' | '先週' | 'それ以前';

export const groupOrder: DateGroup[] = ['今日', '昨日', '今週', '先週', 'それ以前'];

export function getDateGroup(updatedAt?: string | null): DateGroup {
  if (!updatedAt) return 'それ以前';
  const now = new Date();
  const updated = new Date(updatedAt);
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffMs =
    todayStart.getTime() -
    new Date(updated.getFullYear(), updated.getMonth(), updated.getDate()).getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0 || diffDays === 0) return '今日';
  if (diffDays === 1) return '昨日';
  if (diffDays <= 7) return '今週';
  if (diffDays <= 14) return '先週';
  return 'それ以前';
}

export function groupThreads(threads: ThreadInfo[]): Map<DateGroup, ThreadInfo[]> {
  const groups = new Map<DateGroup, ThreadInfo[]>();
  for (const thread of threads) {
    const group = getDateGroup(thread.updated_at);
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(thread);
  }
  return groups;
}
```

**Step B**: `frontend/src/components/ThreadSidebar.tsx` を以下に書き換え:

1. 既存 L61-86 の `type DateGroup` / `const groupOrder` / `function getDateGroup` / `function groupThreads` の 4 宣言を**完全削除**
2. ファイル上部の import 群に以下を追加（既存 `import type { ThreadInfo } from '../types'` の隣あたり）:
   ```typescript
   import { getDateGroup, groupThreads, groupOrder, type DateGroup } from '../utils/threadGroups';
   ```
3. ThreadSidebar.tsx 本体コード（`groupThreads(filtered)` / `groupOrder.forEach(...)` 等の呼び出し）は**一切変更しない** — 名前が一致しているので import 後もそのまま動く

**重要な制約（ADR-0040 "スレッドサイドバー日付グループ" — 破壊しない）:**
- 5 ラベル（今日 / 昨日 / 今週 / 先週 / それ以前）は変更しない
- ロジック（`diffDays === 0` が "今日" など）は変更しない
- `groupOrder` の順序も変更しない

**isDark 三項の扱い:** ThreadSidebar.tsx 内の isDark 三項は**本 Plan では触らない**（Wave 1 Plan 04 が対処する）。本 Plan は L61-86 の削除 + import 追加のみ。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run build &amp;&amp; bun run lint</automated>
  </verify>
  <acceptance_criteria>
    - `test -f frontend/src/utils/threadGroups.ts` success
    - `grep -c 'export function getDateGroup' frontend/src/utils/threadGroups.ts` == 1
    - `grep -c 'export function groupThreads' frontend/src/utils/threadGroups.ts` == 1
    - `grep -c 'export const groupOrder' frontend/src/utils/threadGroups.ts` == 1
    - `grep -c 'export type DateGroup' frontend/src/utils/threadGroups.ts` == 1
    - `grep -c "from '../utils/threadGroups'" frontend/src/components/ThreadSidebar.tsx` == 1
    - `grep -cE '^(function getDateGroup|function groupThreads|type DateGroup|const groupOrder)' frontend/src/components/ThreadSidebar.tsx` == 0 （削除完了）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
  </acceptance_criteria>
  <done>
    threadGroups.ts が utils/ に存在し、ThreadSidebar.tsx は import して既存機能を破壊せず動く。build/lint 共に green。MenuScreen.tsx から同 import を使う準備が整う。
  </done>
</task>

<task type="auto">
  <name>Task 03: scripts/check-phase-35.sh 検証ハーネスを新規作成</name>
  <files>scripts/check-phase-35.sh</files>
  <read_first>
    - scripts/install-hooks.sh L1-40 （bash script preamble + `set -euo pipefail` + `REPO_ROOT` 取得の既存パターン）
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §4 (L275-317 — grep harness 本 script の 7 項目一覧)
    - .planning/phases/35-dashboard-design-system/35-VALIDATION.md §Per-Task Verification Map (L38-58)
  </read_first>
  <action>
`scripts/check-phase-35.sh` を新規作成する。内容は以下:

```bash
#!/usr/bin/env bash
# scripts/check-phase-35.sh — Phase 35 ダッシュボード化 + デザイン統一の grep-based 検証ハーネス
#
# 用途: phase gate 直前に 1 回手動実行する。CI 統合はしない（UI-SPEC §Registry Safety）。
# 検証対象: UX-03-1〜3（ダッシュボード構造）+ UX-04-1〜7（CSS 変数・レスポンシブ・InputBar 分離）

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

FAIL=0

check() {
  local label="$1"
  local actual="$2"
  local op="$3"
  local expected="$4"
  if [ "$op" = "ge" ] && [ "$actual" -ge "$expected" ]; then
    echo "  PASS: $label ($actual >= $expected)"
  elif [ "$op" = "eq" ] && [ "$actual" = "$expected" ]; then
    echo "  PASS: $label ($actual == $expected)"
  else
    echo "  FAIL: $label (got $actual, expected $op $expected)"
    FAIL=1
  fi
}

echo "=== Phase 35 Verification Harness ==="

echo
echo "--- UX-04: CSS 変数基盤 ---"
C1=$(grep -cE '^\s*--color-(bg|surface|border|text|accent|destructive|success|header)' frontend/src/theme.css || true)
check "UX-04-1 semantic color 変数 >= 13" "$C1" ge 13

C2=$(awk '/\[data-theme="dark"\]\s*{/,/^\}$/' frontend/src/theme.css | grep -cE '^\s*--color-' || true)
check "UX-04-2 dark ブロック内 semantic override >= 9" "$C2" ge 9

C3=$(grep -c '@media (max-width: 1024px)' frontend/src/theme.css || true)
check "UX-04-3 @media tablet >= 1" "$C3" ge 1

C4=$(grep -c '@media (max-width: 767px)' frontend/src/theme.css || true)
check "UX-04-4 @media mobile >= 1" "$C4" ge 1

echo
echo "--- UX-04: 4 対象ファイルの hardcode / isDark 排除 ---"
for FILE in frontend/src/components/MenuScreen.tsx frontend/src/components/MessageArea.tsx frontend/src/components/ThreadSidebar.tsx frontend/src/components/Header.tsx; do
  C=$(grep -c '#7c6ff7' "$FILE" || true)
  check "UX-04-5 #7c6ff7 in $(basename "$FILE") == 0" "$C" eq 0

  C=$(grep -cE 'isDark \?' "$FILE" || true)
  check "UX-04-6 isDark 三項 in $(basename "$FILE") == 0" "$C" eq 0
done

echo
echo "--- UX-04: InputBar 分離 ---"
if [ -f frontend/src/components/InputBar.tsx ]; then
  echo "  PASS: InputBar.tsx が存在"
  C=$(grep -cE 'toolbarSlot|previewSlot|onSend' frontend/src/components/InputBar.tsx || true)
  check "UX-04-7 InputBar に toolbarSlot/previewSlot/onSend >= 3" "$C" ge 3
else
  echo "  FAIL: frontend/src/components/InputBar.tsx が存在しない"
  FAIL=1
fi

echo
echo "--- UX-03: MenuScreen ダッシュボード構造 ---"
C=$(grep -c 'aria-labelledby="section-' frontend/src/components/MenuScreen.tsx || true)
check "UX-03-1 aria-labelledby=section-* >= 3" "$C" ge 3

C=$(grep -c 'slice(0, 5)' frontend/src/components/MenuScreen.tsx || true)
check "UX-03-2 slice(0, 5) >= 1" "$C" ge 1

C=$(grep -cE 'アプリケーション|最近のスレッド|その他' frontend/src/components/MenuScreen.tsx || true)
check "UX-03-3 日本語セクション見出し 3 種 >= 3" "$C" ge 3

echo
if [ "$FAIL" -eq 0 ]; then
  echo "=== All Phase 35 checks passed ==="
  exit 0
else
  echo "=== FAIL: Phase 35 verification failed ==="
  exit 1
fi
```

**実行権限:** 作成後 `chmod +x scripts/check-phase-35.sh` を実行する。

**重要な制約:**
- CI 統合しない（pre-commit hook 等に組み込まない）— D-01 方針「追加ツールなし」
- Wave 0 時点では InputBar.tsx 未存在・MenuScreen セクション化未完了なので**全 check PASS にはならない**（意図通り）。Wave 3 Plan 07 の phase gate で初めて全 PASS を期待する。
- 本 Task の acceptance はスクリプト**自体の存在と実行可能性**のみ。grep 結果の合否判定は後続 Wave の責務。
  </action>
  <verify>
    <automated>bash -n /home/parallels/workspaces/copilot-langgraph/scripts/check-phase-35.sh &amp;&amp; test -x /home/parallels/workspaces/copilot-langgraph/scripts/check-phase-35.sh</automated>
  </verify>
  <acceptance_criteria>
    - `test -f scripts/check-phase-35.sh` success
    - `test -x scripts/check-phase-35.sh` success （実行権限あり）
    - `bash -n scripts/check-phase-35.sh` exit 0 （syntax OK）
    - `grep -c 'set -euo pipefail' scripts/check-phase-35.sh` == 1
    - `grep -c 'UX-04-1' scripts/check-phase-35.sh` >= 1
    - `grep -c 'UX-03-1' scripts/check-phase-35.sh` >= 1
    - 実行しても Wave 0 時点では意図的に FAIL（InputBar 未存在 / MenuScreen 未セクション化）。**スクリプト自身が crash せず exit 1 で終わること**を確認: `bash scripts/check-phase-35.sh; echo "exit=$?"` → exit=1 は OK、crash(`command not found` 等)は NG
  </acceptance_criteria>
  <done>
    scripts/check-phase-35.sh が実行可能ファイルとして存在し、syntax OK。Wave 3 以降で全 check PASS する前提のハーネスとして commit 済。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| dev machine → repo | CSS 変数定義 / util 関数 / bash script は全て信頼済み開発者入力。untrusted input なし。 |
| browser runtime → CSS 変数 | Safari で未定義 var() は transparent 挙動（Pitfall 6）。primitive 名のタイプミスが発生すると本 phase 以降の UI 全体が崩れる。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-01 | Tampering | `theme.css` variable names | mitigate | UI-SPEC §Token 一覧の表を verbatim でコピー。Task 01 の acceptance で `grep -c '^\s*--color-purple-500:'` 等の固定値チェックで typo を検知する。 |
| T-35-02 | DoS (visual) | CSS `var()` fallback 未定義時の Safari 真っ黒/真っ白 (Pitfall 6) | accept | primitive は全て自己完結的（`#7c6ff7` 等の literal）、semantic は primitive 参照のみ。Wave 3 Plan 07 の manual cross-browser sweep で最終確認。Wave 0 時点では chain が完結していることを確認。 |
| T-35-03 | Information Disclosure | `threadGroups.ts` の ThreadInfo import | accept | ThreadInfo 型は既存公開型（types.ts）、内容 leak なし。PII は閾値判定に使わない（単純な日付差分のみ）。 |
| T-35-04 | Elevation of Privilege | `scripts/check-phase-35.sh` が git リポジトリへの書き込みをしない | mitigate | スクリプトは read-only grep のみ（`grep` / `awk` / `test` のみ、`git add` や `rm` を含まない）。Task 03 の action で writing 操作がないことを verify。 |
| T-35-05 | Repudiation | — | accept | ローカル dev-only 変更、audit log 不要。 |

すべて LOW severity。security_enforcement 閾値は high のみなので block しない。
</threat_model>

<verification>
- `cd frontend && bun run lint && bun run build` 両方 exit 0
- `test -f frontend/src/theme.css && test -f frontend/src/utils/threadGroups.ts && test -x scripts/check-phase-35.sh`
- `grep -cE '^\s*--color-(bg|surface|border|text|accent|destructive|success|header)' frontend/src/theme.css` >= 13
- `awk '/\[data-theme="dark"\]\s*{/,/^\}$/' frontend/src/theme.css | grep -cE '^\s*--color-'` >= 9
- `grep -c "from '../utils/threadGroups'" frontend/src/components/ThreadSidebar.tsx` == 1
</verification>

<success_criteria>
- Wave 0 完了時、後続 Plan は以下のファイル占有関係で並列/順次実行できる（B-4 明確化）:
  - **Plan 02 (wave 1)**: `frontend/src/theme.css` を**単独占有**（override 置換）
  - **Plan 03 (wave 1)**: `frontend/src/components/InputBar.tsx, frontend/src/components/MessageArea.tsx` を占有
  - **Plan 04 (wave 1)**: `frontend/src/components/ThreadSidebar.tsx` を占有
  - **Plan 05 (wave 1)**: `frontend/src/components/Header.tsx` を占有
  - → Plan 03/04/05 は互いに異なる tsx で並列可能。Plan 02 は theme.css を単独占有するので他の tsx 編集と並列可能だが theme.css に書き込むのは Plan 02 のみ。
  - **Plan 06 (wave 2)**: `frontend/src/theme.css` 末尾 @media block 追加 + `frontend/src/components/MenuScreen.tsx`。Plan 02 の完了後に theme.css を追記する（depends_on: [01, 02, 03, 04, 05]）。
- CSS 変数の primitive + semantic 2 層が定義され、`var(--color-bg)` 等が Wave 1 以降のコンポーネントで参照可能
- threadGroups.ts が utils/ に存在し、MenuScreen と ThreadSidebar が同じ関数を共有する準備ができる
- check-phase-35.sh が Phase 35 全体の grep verification gate として動作可能（本 Plan 時点では FAIL するが crash しない）
- ADR-0040（スレッドサイドバー日付グループ）を破壊していない（5 ラベル + 順序維持）
</success_criteria>

<output>
完了後、`.planning/phases/35-dashboard-design-system/35-01-foundation-setup-SUMMARY.md` を作成し、以下を記録:
- 追加した primitive / semantic 変数の正確な個数
- threadGroups.ts の import を使っている消費者（Phase 35 時点）
- check-phase-35.sh の初回実行結果（expected: 一部 FAIL、crash なし）
- Wave 1 plans が並列で進めるかの確認（files_modified 非重複チェック）
</output>
</content>
</invoke>