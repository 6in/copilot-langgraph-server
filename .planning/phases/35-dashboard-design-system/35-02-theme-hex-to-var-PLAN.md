---
phase: 35
plan: 02
title: "theme.css hex → var() 機械置換 + chatscope override 変数駆動化"
status: draft
type: execute
wave: 1
depends_on: [01]
files_modified:
  - frontend/src/theme.css
autonomous: true
requirements: [UX-04]
requirements_addressed: [UX-04]
tags: [frontend, theme, css-variables, chatscope]
must_haves:
  truths:
    - "theme.css の既存 [data-theme=\"dark\"] .cs-* / .sidebar-* / .chat-* / .auth-* / md-table / typing-dot ブロックが CSS 変数を参照する"
    - "chatscope override の !important は据え置かれている（specificity 勝負は変えない）"
    - "primitive 宣言行を除き、theme.css に生の hex 値が残っていない（対象 override ブロック内で残っていない）"
  artifacts:
    - path: "frontend/src/theme.css"
      provides: "chatscope / app-class の dark override が全て semantic 変数経由で解決される状態"
      contains: "var(--color-bg), var(--color-surface), var(--color-accent), var(--color-text), var(--color-border), var(--color-destructive)"
  key_links:
    - from: "frontend/src/theme.css [data-theme=\"dark\"] .cs-main-container"
      to: "--color-bg / --color-border / --color-text (semantic)"
      via: "background/border-color/color property で var() 参照"
      pattern: "background:\\s*var\\(--color-bg\\)\\s*!important"
---

<objective>
theme.css の既存 L82-396 にわたる `[data-theme="dark"]` chatscope + app-class override ブロック群の hex 値を機械的に `var(--...)` 参照へ置換する。`!important` は据え置き（chatscope specificity 勝負のため）、値のみ変数化する。

**Purpose:** Wave 0 Plan 01 で追加した semantic 変数を theme.css 側で実際に消費させ、dark mode 切替が 1 箇所の semantic 値変更で伝播する状態にする。

**Output:** theme.css が primitive/semantic を source of truth として持ち、既存 override はその値を参照するだけの構造に移行する（行数はほぼ変わらない）。
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
@.planning/phases/35-01-foundation-setup-SUMMARY.md

<interfaces>
<!-- Semantic 変数対応表 (Plan 01 で追加済、UI-SPEC §Semantic Token 一覧) -->
hex → var() 対応:
- `#1e1e2e` → `var(--color-bg)`
- `#2a2a3e` → `var(--color-surface)`
- `#313145` → `var(--color-surface-elevated)`
- `#3a3a52` → `var(--color-border)` (dark border)
- `#e8e8f0` → `var(--color-text)` (dark text)
- `#9090a8` → `var(--color-text-muted)` (dark muted)
- `#7c6ff7` → `var(--color-accent)` (brand purple)
- `#ffffff` / `#fff` → `var(--color-accent-contrast)` (accent 上のテキスト) もしくは surface light の場合は `var(--color-surface)` (文脈依存)
- `#0366d6` → `var(--color-accent)` (ただし accent 統一: UI-SPEC §Accent reserved-for リスト参照、Send/NewChat は accent 化)
- `#e05252` → `var(--color-destructive)`
- `#22c55e` → `var(--color-success)`
- `#24292e` → `var(--color-header-bg)` (Header light bg)
- `#d1dbe3` → `var(--color-border)` (light border、ただし [data-theme="dark"] ブロック内の dark border 用ではない)
- `#e8f0fe` → `var(--color-accent-subtle)` (active thread 背景)
- `#a78bfa` + `#38bdf8` → gradient リテラルのまま（theme 不変、`--gradient-title` 経由で使う文脈は Wave 1 Plan 05 Header で移行）

<!-- 既存構造 (verified by Read: theme.css 現行 397 行) -->
主要ブロック:
- L82-117 (cs-main-container / cs-message-list / cs-sidebar--left 等)
- L119-203 (sidebar-new-chat-btn / sidebar-filter-input / sidebar-thread-item.active / sidebar-thread-delete-btn)
- L209-252 (chat-input-bar / chat-textarea / chat-send-btn)
- L256-302 (auth-container / auth-button 等)
- L306-320 (typing-dot アニメーション)
- L325-395 (md-table 系)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 01: chatscope + sidebar + chat-input-bar の hex を var() に機械置換</name>
  <files>frontend/src/theme.css</files>
  <read_first>
    - frontend/src/theme.css 全行 （Plan 01 で追加された新変数ブロック L4-100 付近 + 既存 override L100-397）
    - .planning/phases/35-dashboard-design-system/35-UI-SPEC.md §chatscope `cs-*` クラス override との共存 (L100-106)
    - .planning/phases/35-dashboard-design-system/35-RESEARCH.md §Pattern 2 (L305-330)
    - .planning/phases/35-dashboard-design-system/35-PATTERNS.md §5 (L320-388)
  </read_first>
  <action>
theme.css の既存 `[data-theme="dark"]` ブロック内の hex 値を、以下の置換規則で机械的に `var(--...)` に置き換える。

**置換規則（UI-SPEC §Semantic Token 一覧 verbatim）:**

| 旧 hex | 新 var() | 注意 |
|-------|---------|------|
| `#1e1e2e` | `var(--color-bg)` | dark primary surface |
| `#2a2a3e` | `var(--color-surface)` | dark secondary surface |
| `#313145` | `var(--color-surface-elevated)` | active thread 背景 |
| `#3a3a52` | `var(--color-border)` | dark border （[data-theme="dark"] ブロック内のみ） |
| `#e8e8f0` | `var(--color-text)` | dark primary text |
| `#9090a8` | `var(--color-text-muted)` | dark muted text |
| `#7c6ff7` | `var(--color-accent)` | brand accent |
| `#0366d6` | `var(--color-accent)` | UI-SPEC Accent reserved-for 統一（Send/New Chat ボタン） |
| `#ffffff` / `#fff` | 文脈依存：accent 上の文字なら `var(--color-accent-contrast)`、surface として背景色なら primitive のまま（:root では `#ffffff` のリテラルが正しい）、dark モード内で文字色なら `var(--color-accent-contrast)` |
| `#e05252` | `var(--color-destructive)` |
| `#22c55e` | `var(--color-success)` |
| `#e8f0fe` | `var(--color-accent-subtle)` | active thread 背景 (light mode) |

**変更対象ブロック（既存 L82-395 の override 群。Plan 01 で追加した L4-100 付近の**primitive/semantic 宣言ブロックは変更しない**）:**

1. **chatscope containers (既存 L82-117 付近):**
   ```css
   /* BEFORE */
   [data-theme="dark"] .cs-main-container,
   [data-theme="dark"] .cs-chat-container,
   [data-theme="dark"] .cs-message-list {
     background: #1e1e2e !important;
     border-color: #3a3a52 !important;
     color: #e8e8f0 !important;
   }
   /* AFTER */
   [data-theme="dark"] .cs-main-container,
   [data-theme="dark"] .cs-chat-container,
   [data-theme="dark"] .cs-message-list {
     background: var(--color-bg) !important;
     border-color: var(--color-border) !important;
     color: var(--color-text) !important;
   }
   ```

2. **sidebar-* (既存 L119-203 付近):**
   - `sidebar-new-chat-btn`: `#7c6ff7` → `var(--color-accent)`、`#ffffff` → `var(--color-accent-contrast)`
   - `sidebar-filter-input`: `#1e1e2e` → `var(--color-bg)`、`#e8e8f0` → `var(--color-text)`、`#3a3a52` → `var(--color-border)`
   - `sidebar-thread-item.active`: `#313145` → `var(--color-surface-elevated)`
   - `sidebar-thread-delete-btn:hover`: `#e05252` → `var(--color-destructive)`

3. **chat-input-bar (既存 L209-252 付近):**
   - `.chat-input-bar`: `#2a2a3e` → `var(--color-surface)`、`#3a3a52` → `var(--color-border)`
   - `.chat-textarea:focus`: `#7c6ff7` → `var(--color-accent)`
   - `.chat-send-btn`: `#7c6ff7` → `var(--color-accent)`、`#ffffff` → `var(--color-accent-contrast)`

4. **auth-* (既存 L256-302 付近):** 同パターンで dark bg / text / border を semantic に置換

5. **typing-dot (既存 L306-320 付近):** dot の色 `#7c6ff7` があれば `var(--color-accent)`

6. **md-table (既存 L325-395 付近):** dark mode 内の hex を semantic に置換（header bg は `var(--color-surface)`、border は `var(--color-border)`、text は `var(--color-text)`）

**Pitfall 1 対策（既存 inline style と片側だけ変数化しない）:** 本 Plan は theme.css のみを対象。tsx 側は Wave 1 Plan 03/04/05 が並行して対処する。**theme.css 側の既存 hex を残さない**ことに集中する。

**Pitfall 2 対策（chatscope `.cs-message--incoming` を弄らない）:** 本 Plan は dark override のみ。`@media` 内の bubble width 調整は Wave 2 Plan 06 の責務。incoming bubble の既存 `max-width: 100%` ルール（L59-76 付近）は触らない。

**重要:**
- `!important` は**一切外さない**（UI-SPEC §chatscope 共存方針）
- 各ブロックの外枠・セレクタ・コメント・プロパティ名は一切変更しない（値のみ変更）
- Plan 01 で追加した primitive/semantic 宣言ブロック内の hex 値（`#7c6ff7` 等）は**そのまま残す**（これらは source of truth）
- `#ffffff` / `#fff` は複数の役割を持つため、UI-SPEC §Semantic Token 一覧の Light 値 `--color-surface: #ffffff` を参照して文脈判定する。dark モード内で文字色なら `var(--color-accent-contrast)`、背景としての `#ffffff` は dark モード内に出てくる場合はほぼ `var(--color-surface)` ではなく `var(--color-accent-contrast)`（アクセント上の文字）として出ているはず。

**置換漏れ検出のセルフチェック:**
```bash
# [data-theme="dark"] chatscope / sidebar / chat / auth / md-table override の中に hex が残っていないか
awk '/\[data-theme="dark"\]\s*\.(cs-|sidebar-|chat-|auth-|md-)/,/^\}$/' frontend/src/theme.css \
  | grep -cE '#[0-9a-fA-F]{6}\b'
# 期待: 0 (override ブロック内に 6-digit hex が残らない。primitive/semantic 宣言 `[data-theme="dark"] { --color-*: ... }` は対象外)
```
ただし primitive/semantic 宣言ブロック (`:root` / `[data-theme="dark"]` の**変数宣言のみ**の大ブロック) は awk パターンに `.cs-|sidebar-|chat-|auth-|md-` を絞り込むことで除外される — Plan 01 で追加した 2 ブロック内の hex は source of truth なので残る。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/frontend &amp;&amp; bun run build &amp;&amp; bun run lint</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'var(--color-bg) !important' frontend/src/theme.css` >= 1
    - `grep -c 'var(--color-surface) !important' frontend/src/theme.css` >= 1
    - `grep -c 'var(--color-accent) !important' frontend/src/theme.css` >= 2 （Send ボタンと New Chat ボタン相当）
    - `grep -c 'var(--color-border) !important' frontend/src/theme.css` >= 2
    - `grep -c 'var(--color-text) !important' frontend/src/theme.css` >= 1
    - `grep -c 'var(--color-destructive)' frontend/src/theme.css` >= 1
    - `grep -c '!important' frontend/src/theme.css` >= 20 （既存 `!important` 宣言が据え置かれている — 減っていないこと）
    - 既存 `[data-theme="dark"] .cs-main-container` 等のセレクタは削除されていない: `grep -c '.cs-main-container' frontend/src/theme.css` >= 1
    - **置換漏れ検出 (W-1)**: `awk '/\[data-theme="dark"\]\s*\.(cs-|sidebar-|chat-|auth-|md-)/,/^\}$/' frontend/src/theme.css | grep -cE '#[0-9a-fA-F]{6}\b'` == 0 （override ブロック内に 6-digit hex が残っていない）
    - `cd frontend && bun run build` exit 0
    - `cd frontend && bun run lint` exit 0
    - 機能目視（integration check で判定）: ダーク/ライト切替で chatscope main container / thread sidebar / chat input が正しく再描画される
  </acceptance_criteria>
  <done>
    theme.css の `[data-theme="dark"]` 配下の override ブロック群が全て CSS 変数経由で色を解決する。`!important` は据え置き。dark mode 機能の retro regression なし（build/lint green、目視 integration check で確認）。置換漏れ awk チェックが 0 件。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| theme.css ↔ browser CSS engine | 未定義の var() は Safari で transparent になる（Pitfall 6）。variable 名の typo が伝播しないことが前提。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-06 | Tampering | hex → var() 置換の scope（primitive 宣言ブロックに及んでしまう） | mitigate | Task 01 の action で「Plan 01 で追加した primitive/semantic 宣言ブロック内の hex 値はそのまま残す」を明示。acceptance で `grep -c '^\s*--color-purple-500: #7c6ff7' frontend/src/theme.css` == 1 を確認（後続 Plan 07 gate で再確認）。 |
| T-35-07 | DoS (visual) | typo による var() 未定義 (Pitfall 6) | mitigate | `bun run build` + manual dark/light toggle で dark mode の chatscope container / sidebar / input の表示を目視（integration check）。Safari での確認は Plan 07 の cross-browser sweep へ委譲。 |
| T-35-08 | Tampering | chatscope `!important` の意図せぬ除去 | mitigate | acceptance で `grep -c '!important' frontend/src/theme.css` >= 20 を確認（元の `!important` 数から減らない）。`!important` を外すと chatscope specificity に負ける。 |
| T-35-09 | Information Disclosure | — | accept | CSS ファイル、秘密情報なし。 |
| T-35-10 | Repudiation | — | accept | ローカル変更のみ、audit 不要。 |

すべて LOW severity。security_enforcement 閾値は high のみなので block しない。
</threat_model>

<verification>
- `cd frontend && bun run lint && bun run build` 両方 exit 0
- 目視: `docker compose up` → `http://localhost:5173/orochi/` → Header の ☀️/🌙 toggle でダーク/ライト切替し、chatscope 本体（MessageList 背景）・ThreadSidebar 背景 / New Chat ボタン色・chat-input-bar 背景が破綻なく反映される
- `grep -c 'var(--color-' frontend/src/theme.css` >= 15 （override 全体で変数参照している）
- `grep -c '#1e1e2e' frontend/src/theme.css` <= 2 （primitive `--color-dark-bg: #1e1e2e` 宣言 1 + dark override block 内の semantic `--color-bg: var(--color-dark-bg)` 参照 = 0） — **0 もしくは primitive 宣言行のみ**
- `grep -c '#7c6ff7' frontend/src/theme.css` <= 1 （primitive `--color-purple-500: #7c6ff7` の 1 行のみ）
- **置換漏れ awk gate**: `awk '/\[data-theme="dark"\]\s*\.(cs-|sidebar-|chat-|auth-|md-)/,/^\}$/' frontend/src/theme.css | grep -cE '#[0-9a-fA-F]{6}\b'` == 0
</verification>

<success_criteria>
- theme.css の override ブロック群から生 hex が排除され、semantic 変数経由で解決される
- ダーク/ライト切替が 1 箇所（semantic 変数の dark override）で完結し、切替時に React 再レンダーが発生しない
- chatscope との specificity 勝負は変わらない（`!important` 数は減らない）
- Phase 36 が `--color-accent` を参照して添付ボタンを追加できる基盤が確立される
</success_criteria>

<output>
完了後、`.planning/phases/35-dashboard-design-system/35-02-theme-hex-to-var-SUMMARY.md` を作成し、以下を記録:
- 置換した hex の個数（カテゴリ別: chatscope / sidebar / chat-input / auth / md-table）
- `!important` 数の before/after
- 残存 hex の箇所（primitive 宣言行のみであることの verify）
- 置換漏れ awk gate の結果（W-1）
- integration check（docker compose + dark/light toggle）の結果
</output>
</content>
</invoke>
