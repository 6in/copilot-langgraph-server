---
phase: 35
plan: 07a
title: "Accessibility focus-visible + AuthPanel 変数化 + check-phase-35 実行 + PROJECT.md 更新（自動完結部分）"
status: draft
type: execute
wave: 3
depends_on: [01, 02, 03, 04, 05, 06]
files_modified:
  - frontend/src/theme.css
  - frontend/src/components/AuthPanel.tsx
  - .planning/PROJECT.md
autonomous: true
requirements: [UX-03, UX-04]
requirements_addressed: [UX-03, UX-04]
tags: [frontend, accessibility, auth-panel, project-md-update]
must_haves:
  truths:
    - "新規ボタン群（FeatureCard / RecentThreadCard / drawer hamburger / InputBar の各ボタン）が :focus-visible で 2px outline var(--color-accent) を持つ"
    - "AuthPanel.tsx の色値が CSS 変数参照に置換されている（構造変更なし、1-line diff 相当）"
    - "scripts/check-phase-35.sh が全 automated check PASS で exit 0 を返す"
    - "PROJECT.md の Out of Scope から「モバイル対応 — PC ブラウザのみ対象」が削除/修正されている（D-07）"
  artifacts:
    - path: "frontend/src/theme.css"
      provides: ":focus-visible ユーティリティ ルール"
      contains: ":focus-visible, outline-offset"
    - path: "frontend/src/components/AuthPanel.tsx"
      provides: "variable 経由の色参照（構造変更なし）"
    - path: ".planning/PROJECT.md"
      provides: "v6.0 UI/AI Experience の mobile policy 反転記録"
  key_links:
    - from: "theme.css :focus-visible"
      to: "全新規 button クラス（recent-thread-card / menu-card / header-hamburger summary / chat-send-btn 等）"
      via: "CSS セレクタ連鎖"
      pattern: ":focus-visible"
---

<objective>
Phase 35 の autonomous 完結部分。アクセシビリティ最低限（:focus-visible）、AuthPanel の変数差し替え（D-02 許容範囲）、check-phase-35.sh 全 PASS 化、PROJECT.md の mobile policy 反転（D-07）をこの plan で一括処理する。

**W-6 Plan 分割の根拠:** 旧 Plan 07 は autonomous 3 task + human-verify 2 task + autonomous 1 task + autonomous 1 task の 7 task 混在 plan で context 逼迫 & checkpoint 順序依存が複雑だった。Plan 07a (autonomous のみ、フル自動実行可能) と Plan 07b (human-verify gate 集中) に分割し、Plan 07a が完了してから Plan 07b に遷移する明確な境界を引く。

**Purpose:** Phase 35 の締めくくり前段階。grep / tsc / bun build で完結する要件を全部これで通す。visual 検証（Chrome DevTools Responsive / cross-browser）は Plan 07b へ委譲。

**Output:**
- `:focus-visible` ユーティリティが theme.css に追加
- AuthPanel の hex → var() 差し替え（構造変更なし）
- PROJECT.md から古い「PC ブラウザのみ対象」policy を削除/反転
- `scripts/check-phase-35.sh` 全 automated check green
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/PROJECT.md
@.planning/phases/35-dashboard-design-system/35-CONTEXT.md
@.planning/phases/35-dashboard-design-system/35-UI-SPEC.md
@.planning/phases/35-dashboard-design-system/35-RESEARCH.md
@.planning/phases/35-dashboard-design-system/35-PATTERNS.md
@.planning/phases/35-dashboard-design-system/35-VALIDATION.md
@.planning/phases/35-01-foundation-setup-SUMMARY.md
@.planning/phases/35-02-theme-hex-to-var-SUMMARY.md
@.planning/phases/35-03-messagearea-inputbar-split-SUMMARY.md
@.planning/phases/35-04-threadsidebar-migration-SUMMARY.md
@.planning/phases/35-05-header-migration-SUMMARY.md
@.planning/phases/35-06-dashboard-responsive-SUMMARY.md

<interfaces>
<!-- UI-SPEC §Visual Accessibility Baseline (L462-469) -->
| 項目 | 要件 |
|------|------|
| Focus ring | `:focus-visible` で 2px outline var(--color-accent) |
| キーボード操作 | Tab / Enter / Escape を破壊しない |
| ARIA | drawer `role="dialog"` + `aria-modal`、hamburger `aria-expanded` |
| Color contrast | WCAG AA (4.5:1) 既存値で満たしている想定 |

<!-- PROJECT.md Out of Scope の該当行 (CONTEXT.md D-07) -->
既存: 「モバイル対応 — PC ブラウザのみ対象」
→ v6.0 で policy 反転：「タブレット幅 (768-1024px) までは primary scope、スマホ幅 (375-767px) はレイアウト破綻しない保証」 or 単純に該当行を削除。
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 01: theme.css に :focus-visible ユーティリティを追加（accessibility baseline）</name>
  <files>frontend/src/theme.css</files>
  <read_first>
    - frontend/src/theme.css 末尾（Plan 06 で追加した @media block の後に追加）
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Visual Accessibility Baseline (L462-469)
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §Shared Patterns §Focus ring (L794-804)
  </read_first>
  <action>
theme.css の末尾（Plan 06 で追加した `@media (max-width: 767px)` ブロックの直後）に以下を追加する:

```css
/* ============================================================
   Phase 35: Accessibility — Focus Visible Utility
   新規追加ボタン群にキーボード操作時の焦点リングを付与
   (マウスクリック時は outline 表示しない — :focus-visible)
   ============================================================ */
.menu-card:focus-visible,
.recent-thread-card:focus-visible,
.chat-send-btn:focus-visible,
.chat-askme-btn:focus-visible,
.chat-cancel-btn:focus-visible,
.sidebar-new-chat-btn:focus-visible,
.header-hamburger summary:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

**注意:**
- `:focus-visible` は Chrome 86+ / Edge 86+ / Safari 15.4+ / Firefox 85+ で safe（UX-04 target browser 全対応、RESEARCH §State of the Art L978 [VERIFIED: caniuse.com/css-focus-visible]）
- 既存 FeatureCard に `className="menu-card"` を追加する必要があれば MenuScreen.tsx を最小限修正（1 line diff、`<button className="menu-card" ...>`）。もし Plan 06 時点で既に付いていれば本 Plan では theme.css のみで完結。
- `.cs-*` クラスへの `:focus-visible` は chatscope 内部処理があるため本 Plan では触らない（polish scope 外）
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph &amp;&amp; grep -c ':focus-visible' frontend/src/theme.css &amp;&amp; cd frontend &amp;&amp; bun run build</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c ':focus-visible' frontend/src/theme.css` >= 1
    - `grep -c 'outline: 2px solid var(--color-accent)' frontend/src/theme.css` >= 1
    - `grep -c 'outline-offset: 2px' frontend/src/theme.css` >= 1
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
  </acceptance_criteria>
  <done>
    theme.css 末尾に :focus-visible ユーティリティが追加され、キーボード Tab 操作時に新規ボタン群に accent outline が付与される。マウスクリック時は outline 非表示（UX 不変）。
  </done>
</task>

<task type="auto">
  <name>Task 02: AuthPanel.tsx の色値を CSS 変数参照に置換（構造変更なし）</name>
  <files>frontend/src/components/AuthPanel.tsx</files>
  <read_first>
    - frontend/src/components/AuthPanel.tsx 全行（Phase 35 scope 外だが変数差し替えは許容 — UI-SPEC §Component Migration Scope L352）
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Color (L163-189)
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §Accent reserved-for リスト #7 (L181)
  </read_first>
  <action>
AuthPanel.tsx の **inline style の hex 値のみ** を CSS 変数に置換する。**構造変更（JSX 改変 / 新規コンポーネント化 / isDark 三項除去）はしない**（D-02 scope 外、1-line diff 相当の変数差し替えのみ許容）。

置換規則（UI-SPEC §Accent reserved-for #7 に従い Device Flow URL リンクは accent を使う）:

| 既存 hex | 新 var() |
|---------|---------|
| `#7c6ff7` | `var(--color-accent)` |
| `#0366d6` | `var(--color-accent)` （UI-SPEC Accent reserved-for #7 — Device Flow link） |
| `#ffffff` / `#fff` (accent 上の文字) | `var(--color-accent-contrast)` |
| `#e05252` | `var(--color-destructive)` |
| `#1e1e2e` | `var(--color-bg)` |
| `#2a2a3e` | `var(--color-surface)` |
| `#3a3a52` | `var(--color-border)` |
| `#e8e8f0` | `var(--color-text)` |
| `#9090a8` | `var(--color-text-muted)` |
| `#333333` / `#333` | `var(--color-text)` |
| `#888888` / `#888` | `var(--color-text-muted)` |

**重要な制約:**
- **isDark 三項が AuthPanel 内にあっても残す**（D-02 scope 外）。本 Plan は**三項の分岐値の hex を var() に置換するだけ**（`isDark ? 'var(--color-bg)' : 'var(--color-bg)'` のように両辺が同じ var() になれば三項を **消してよい**、そうでないなら分岐を残す）。
  - 多くの場合、semantic 変数 (`--color-bg` 等) は light/dark で自動解決されるため、両辺を同じ var() に統合できる。結果として**isDark 削減の副次的な正の影響**が発生する（意図通り）。
- **新規コンポーネント分離・props 変更・JSX 構造変更は行わない**
- **日本語化などのコピー変更も本 Plan では行わない**（AuthPanel 内の文言はそのまま）
- Device Flow URL / user_code 表示 / 認証済みメッセージ等の機能を破壊しない
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run build &amp;&amp; bun run lint</automated>
  </verify>
  <acceptance_criteria>
    - `grep -cE '#(7c6ff7|0366d6|1e1e2e|2a2a3e|3a3a52|e8e8f0)' frontend/src/components/AuthPanel.tsx` == 0 （主要 hex が全置換）
    - `grep -c 'var(--color-' frontend/src/components/AuthPanel.tsx` >= 3
    - AuthPanel 全体の JSX 構造（props / component 名 / 関数分割）が変更されていない（`git diff --stat frontend/src/components/AuthPanel.tsx` で追加行 ≒ 削除行、差分は inline style 内のみ）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
  </acceptance_criteria>
  <done>
    AuthPanel.tsx の inline style hex が CSS 変数参照に置換された。構造変更なし。Device Flow 認証フロー regression は Plan 07b の human verify で最終確認。
  </done>
</task>

<task type="auto">
  <name>Task 03: scripts/check-phase-35.sh を実行して全 PASS を確認</name>
  <files>scripts/check-phase-35.sh</files>
  <read_first>
    - scripts/check-phase-35.sh (Plan 01 Task 03 で作成済)
    - .planning/phases/35-dashboard-design-system/35-VALIDATION.md §Per-Task Verification Map (L38-58)
  </read_first>
  <action>
Plan 01 Task 03 で作成した `scripts/check-phase-35.sh` を実行し、全 automated check が PASS することを確認する。

```bash
cd /home/parallels/workspaces/copilot-langgraph
bash scripts/check-phase-35.sh
echo "exit=$?"
```

**期待結果:**
- `exit=0`
- 全ての UX-04-1〜7 と UX-03-1〜3 が `PASS: ...` 表示

**FAIL が出る場合の対処:**
- どの要件が FAIL したかを SUMMARY に記録
- FAIL の原因が Plan 06 の漏れ（例: MenuScreen の section が 2 つ）等なら、該当 Plan を再実施（または本 Plan 内で最小限 fix）
- FAIL が Phase 35 scope 外の問題（例: 他の tsx に `#7c6ff7` が残存）なら、check script の scope が 4 対象ファイルに限定されているか確認（check-phase-35.sh L42-53 は明示的に 4 ファイルのみ対象）

**副次 automated check:**
```bash
cd frontend && bun run build
cd frontend && bun run lint
```
両者 exit 0。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph &amp;&amp; bash scripts/check-phase-35.sh</automated>
  </verify>
  <acceptance_criteria>
    - `bash scripts/check-phase-35.sh; echo "exit=$?"` → `exit=0`
    - スクリプト出力に `FAIL:` が含まれない
    - スクリプト末尾に `All Phase 35 checks passed` が含まれる
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
  </acceptance_criteria>
  <done>
    Phase 35 の全 grep-verifiable 要件（UX-03-1/2/3, UX-04-1/2/3/4/5/6/7）が green。Phase gate の automated 部分が通過。
  </done>
</task>

<task type="auto">
  <name>Task 04: PROJECT.md の Out of Scope を v6.0 policy 反転に合わせて更新（D-07）</name>
  <files>.planning/PROJECT.md</files>
  <read_first>
    - .planning/PROJECT.md 全行（特に Out of Scope セクションの既存表現を確認）
    - .planning/phases/35-dashboard-design-system/35-CONTEXT.md §D-07 (L41)
    - .planning/REQUIREMENTS.md §UX-04 (Phase 35 完了時点の責任範囲)
  </read_first>
  <action>
`.planning/PROJECT.md` を以下のように更新する:

**Step A**: `Out of Scope` セクション内で「モバイル対応 — PC ブラウザのみ対象」または同等の表現を**検索する**（文言は PROJECT.md の実際の内容に合わせる — 完全一致しないかもしれない）。

**Step B**: 該当行を以下のいずれかに置換:

- **案 A（削除）**: その bullet を削除し、Out of Scope リストから 1 項目減らす
- **案 B（反転して明記）**: 該当 bullet を以下に置換:
  ```markdown
  - **ネイティブモバイルアプリ** — タブレット幅（768-1024px）までは PC ブラウザでプライマリ scope、スマホ幅（375-767px）もレイアウト破綻ゼロは保証（Phase 35 で実施）。iOS/Android ネイティブアプリは非対象。
  ```

**推奨: 案 B**。なぜなら単に削除すると「何をしないか」がふわっとするため、「ネイティブアプリは非対象」を明示する方が contract として強い。

**Step C**: PROJECT.md の `Key Decisions` 表（もしあれば）に以下を追加:
```markdown
| Phase 35 | Mobile responsive policy 反転 | タブレット幅まで primary scope、スマホ幅は破綻ゼロのみ保証 | D-07 |
```

**Step D**: PROJECT.md の `Last updated` を今日の日付に更新。

**重要な制約:**
- **v6.0 の他の Out of Scope（`チャット以外からの UI 操作 API` / `AI による root 権限操作` 等）は変更しない** — 本 Task は mobile policy 反転のみ
- **Phase 36 Handoff Contract は PROJECT.md には書かない**（UI-SPEC / 本 Plan の SUMMARY で contract 化済み）
  </action>
  <verify>
    <automated>grep -cE 'PC ブラウザのみ対象' /home/parallels/workspaces/copilot-langgraph/.planning/PROJECT.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -cE 'PC ブラウザのみ対象' .planning/PROJECT.md` == 0 （削除または文言反転完了）
    - `grep -cE 'タブレット幅|ネイティブモバイルアプリ' .planning/PROJECT.md` >= 1 （新 policy が記述されている）
    - PROJECT.md の構造（セクション順・見出し）は変更されていない
    - Last updated 日付が更新されている
  </acceptance_criteria>
  <done>
    PROJECT.md の Out of Scope から古い mobile policy が削除 or 反転され、Phase 35 で policy 反転したことが記録された。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| AuthPanel 変数差し替え ↔ Device Flow 認証 | 変数化は純粋な color remapping、認証 API 呼び出しに影響なし。 |
| PROJECT.md 編集 ↔ milestone policy | v6.0 policy 反転は user decisions（D-07）で既に合意済、本 Plan は実装記録のみ。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-31 | Tampering | AuthPanel 変数差し替えで Device Flow 認証フローが regression（D-02 scope 外ファイル触る） | mitigate | Task 02 action で「構造変更なし、inline style hex のみ置換」を明示。acceptance で `git diff --stat AuthPanel.tsx` 差分が小さいことを確認。Plan 07b human verify で認証フロー実測。 |
| T-35-32 | DoS (visual) | `:focus-visible` が古いブラウザで無視され outline が出ない | accept | Chrome 86+ / Edge 86+ / Safari 15.4+ / Firefox 85+ で safe（RESEARCH §State of the Art L978）。社内利用の 200 名規模で古いブラウザ使用者は極少。 |
| T-35-34 | Information Disclosure | PROJECT.md 更新で historical decision が失われる | mitigate | Task 04 action で「Key Decisions 表に追記」と明示（削除ではなく追加）。old policy 行は削除してよいが、「Phase 35 で policy 反転した」という事実は Key Decisions 表で記録。 |
| T-35-35 | Elevation of Privilege | — | accept | 変更なし。 |

すべて LOW severity。security_enforcement 閾値は high のみなので block しない。
</threat_model>

<verification>
- `cd frontend && bun run lint && bun run build` 両方 exit 0
- `bash scripts/check-phase-35.sh` exit 0、全 `PASS:` 行
- `grep -cE 'PC ブラウザのみ対象' .planning/PROJECT.md` == 0
- 次段階（Plan 07b）への引き継ぎ: focus-visible / AuthPanel / PROJECT.md / check-phase-35 全て green の状態で human verify へ遷移可能
</verification>

<success_criteria>
- **grep-verifiable Phase 35 要件 全て PASS**:
  - UX-03-1/2/3 / UX-04-1〜7 grep gate green (check-phase-35.sh で確認)
  - UX-04-10 (tsc) / UX-04-11 (eslint) green
- **accessibility baseline**（:focus-visible）が theme.css に追加されている
- **D-07 policy 反転が PROJECT.md に記録済**
- Plan 07b (human-verify) への橋渡しが整っている
</success_criteria>

<output>
完了後、`.planning/phases/35-dashboard-design-system/35-07a-a11y-code-changes-SUMMARY.md` を作成し、以下を記録:
- 追加した :focus-visible セレクタ件数
- AuthPanel 変数置換後の diff size（追加 ≒ 削除の inline style hex のみ）
- scripts/check-phase-35.sh の最終実行結果（全 PASS）
- PROJECT.md diff サマリ
- Plan 07b 着手準備完了の旨
</output>
