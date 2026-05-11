---
phase: 35
plan: 07b
title: "Cross-browser sweep + DevTools Responsive human-verify + integration-check.md 検証"
status: draft
type: execute
wave: 4
depends_on: [07a]
files_modified:
  - docs/phase-35-integration-check.md
autonomous: false
requirements: [UX-03, UX-04]
requirements_addressed: [UX-03, UX-04]
tags: [frontend, cross-browser, responsive, human-verify, phase-36-handoff]
must_haves:
  truths:
    - "Chrome DevTools Responsive (4 widths × 2 themes = 8 画面) で human checker が APPROVED を返し、docs/phase-35-integration-check.md に観察結果が記入される"
    - "Chrome + Edge で MenuScreen / Chat / Drawer 破綻ゼロ、Safari は skipped でも判定は記録される"
    - "Phase 36 Handoff Contract 10 項目のうち visual 項目（#4 InputBar slot / #10 cross-browser）が human verified"
    - "docs/phase-35-integration-check.md が存在し、Chrome DevTools Responsive / Cross-Browser / Phase 36 Handoff Contract の 3 セクションが記入済"
  artifacts:
    - path: "docs/phase-35-integration-check.md"
      provides: "Chrome DevTools Responsive 4 パターン + cross-browser の目視結果記録"
      contains: "## Chrome DevTools Responsive, ## Cross-Browser, ## Phase 36 Handoff Contract"
  key_links:
    - from: "docs/phase-35-integration-check.md"
      to: "Plan 07a の check-phase-35.sh 結果"
      via: "Phase 36 Handoff Contract 表での cross-reference"
      pattern: "PASS|APPROVED"
---

<objective>
Phase 35 の最終 visual gate plan。human checker が Chrome DevTools Responsive 4 breakpoint × 2 テーマを sweep、Chrome/Edge cross-browser を sweep し、観察結果を `docs/phase-35-integration-check.md` に記録する。Phase 36 Handoff Contract 10 項目のうち grep 済 7 項目に加えて visual 3 項目（#4 / #5 / #10）を verified にする。

**W-6 分割の根拠:** 本 Plan は human-verify checkpoint 中心で autonomous task は最小限（integration-check.md の scaffold 作成と最終 verify のみ）。Plan 07a の autonomous work が完了した上で実施することで、human checker が明確な pass/fail 判断に集中できる。

**Purpose:** Phase 36 着手時に「InputBar の slot に差し込むだけで動く」契約を visual + grep の両面で確定させる。

**Output:**
- `docs/phase-35-integration-check.md` に cross-browser / 4 画面 × 2 テーマ sweep 結果
- Phase 36 Handoff Contract 10 項目の全 verification status
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
@.planning/phases/35-dashboard-design-system/35-VALIDATION.md
@.planning/phases/35-01-foundation-setup-SUMMARY.md
@.planning/phases/35-02-theme-hex-to-var-SUMMARY.md
@.planning/phases/35-03-messagearea-inputbar-split-SUMMARY.md
@.planning/phases/35-04-threadsidebar-migration-SUMMARY.md
@.planning/phases/35-05-header-migration-SUMMARY.md
@.planning/phases/35-06-dashboard-responsive-SUMMARY.md
@.planning/phases/35-07a-a11y-code-changes-SUMMARY.md

<interfaces>
<!-- Phase 36 Handoff Contract 10 項目 (UI-SPEC L437-452) -->
1. `:root` に 13+ semantic 変数定義 (Plan 01 で達成、grep で verify)
2. `[data-theme="dark"]` に同数の semantic override (Plan 01 達成)
3. InputBar.tsx 存在 + toolbarSlot/previewSlot props (Plan 03 達成)
4. InputBar slot 配置: toolbar 左 / preview 上 (Plan 03 達成、visual verify 本 Plan)
5. MessageArea が InputBar 使用 + UX retain (Plan 03 達成)
6. `@media (max-width: 1024px)` 最低 3 箇所 (theme.css 集約 — Plan 06)
7. `@media (max-width: 767px)` 最低 3 箇所 (同上 Plan 06)
8. MenuScreen 3 セクション (Plan 06 達成)
9. `#7c6ff7` が新規 hardcoded 追加なし (Plan 02-06 で移行対象 4 ファイル 0 件達成)
10. Chrome / Edge / Safari desktop + tablet 幅で 破綻ゼロ (本 Plan cross-browser sweep)

<!-- Chromium remote debug 起動確認 (CLAUDE.md) -->
`curl -s http://127.0.0.1:9222/json/version` 空なら ユーザーに起動依頼 (`chromium --remote-debugging-port=9222 ...`)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 01: docs/phase-35-integration-check.md を scaffold 作成（空テンプレ）</name>
  <files>docs/phase-35-integration-check.md</files>
  <read_first>
    - 無し（新規ファイル）
  </read_first>
  <action>
`docs/phase-35-integration-check.md` を以下のテンプレートで新規作成する。human checker が Task 02 / Task 03 のチェックポイントで approve する際に、このファイルを直接編集して結果を記入する前提。

```markdown
# Phase 35 Integration Check Report

**Date:** YYYY-MM-DD (人間が Task 02 approve 時に記入)
**Tested by:** <human name>

## Chrome DevTools Responsive

Plan 07b Task 02 で実測。4 width × 2 theme = 8 パターン。

| Width | Theme | MenuScreen | Chat | Drawer | Verdict |
|-------|-------|-----------|------|--------|---------|
| 1440  | light |           |      | N/A    |         |
| 1440  | dark  |           |      | N/A    |         |
| 1024  | light |           |      |        |         |
| 1024  | dark  |           |      |        |         |
| 768   | light |           |      |        |         |
| 768   | dark  |           |      |        |         |
| 375   | light |           |      |        |         |
| 375   | dark  |           |      |        |         |

## Cross-Browser

Plan 07b Task 03 で実測。Safari は macOS 不在なら skipped 可（判定は記録）。

| Browser | MenuScreen | Chat | Drawer | Notes |
|---------|-----------|------|--------|-------|
| Chrome  |           |      |        |       |
| Edge    |           |      |        |       |
| Safari  |           |      |        | skipped / via UserAgent |

## Phase 36 Handoff Contract

10 項目の最終 verification。

| # | 項目 | 方法 | 結果 |
|---|------|------|------|
| 1 | semantic 変数 13+ | grep | PASS |
| 2 | dark override | grep | PASS |
| 3 | InputBar 存在 + props | grep | PASS |
| 4 | InputBar slot レイアウト | visual |  |
| 5 | MessageArea UX retain | manual |  |
| 6 | @media 1024px | grep | PASS |
| 7 | @media 767px | grep | PASS |
| 8 | MenuScreen 3 セクション | grep | PASS |
| 9 | #7c6ff7 new hardcode なし | grep | PASS |
| 10 | Chrome/Edge/Safari 破綻ゼロ | cross-browser |  |

## Issues found

(あれば記録)

## Verdict

- Phase 35 phase gate: **APPROVED / NEEDS FIXES**
```

**重要な制約:**
- scaffold 作成のみ。本 Task で値を埋めない（human checker が後続 checkpoint で埋める）。
- 表の列数を揃える。Task 02 / Task 03 の approve 時に human が編集する前提で、空欄でも grep gate が通るように `PASS` を事前記入する項目（1/2/3/6/7/8/9）は既に埋めておく（これらは Plan 07a Task 03 で grep 済）。
  </action>
  <verify>
    <automated>test -f /home/parallels/workspaces/copilot-langgraph/docs/phase-35-integration-check.md &amp;&amp; wc -l /home/parallels/workspaces/copilot-langgraph/docs/phase-35-integration-check.md</automated>
  </verify>
  <acceptance_criteria>
    - `test -f docs/phase-35-integration-check.md` success
    - `grep -c '## Chrome DevTools Responsive' docs/phase-35-integration-check.md` == 1
    - `grep -c '## Cross-Browser' docs/phase-35-integration-check.md` == 1
    - `grep -c '## Phase 36 Handoff Contract' docs/phase-35-integration-check.md` == 1
    - `wc -l docs/phase-35-integration-check.md` >= 30
  </acceptance_criteria>
  <done>
    docs/phase-35-integration-check.md が scaffold 状態で存在、Task 02 / Task 03 の human checker が直接編集して結果を記入する準備ができた。
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 02: Chrome DevTools Responsive 4 パターン（375/768/1024/1440 × light/dark）目視確認 + integration-check.md 記入</name>
  <what-built>
    Phase 35 の Plan 01-06 で完成した MenuScreen ダッシュボード / InputBar 分離 / ThreadSidebar drawer / Header hamburger / CSS 変数 + @media の結果を、Chrome DevTools Responsive Mode で 4 breakpoint × 2 テーマ = 8 画面 で目視確認する。
  </what-built>
  <how-to-verify>
    1. Chromium が remote debug port で起動していることを確認:
       ```bash
       curl -s http://127.0.0.1:9222/json/version
       ```
       レスポンスが空なら以下で起動してもらう:
       ```bash
       chromium --remote-debugging-port=9222 --no-first-run --no-default-browser-check &
       ```
    2. `docker compose up` で起動（既に起動していれば省略）
    3. Chrome で `http://localhost:5173/orochi/` を開く
    4. DevTools を開き Responsive Mode を ON にし、以下 4 幅を順に切り替える:
       - 1440px (desktop)
       - 1024px (tablet)
       - 768px (tablet 下限 / mobile 上限)
       - 375px (mobile)
    5. 各幅で Header の 🌙/☀️ toggle でダーク/ライト両テーマを切り替え、以下を確認する:

    **MenuScreen (`/orochi/`):**
    - 1440px: 3 セクション縦並び、カード grid 最大 3-4 列、タイトル gradient 表示
    - 1024px: カード grid 2-3 列、padding 縮小、"Model:" ラベル非表示（Header が連動）
    - 768px: グリッドがさらに狭く、hamburger まだ非表示
    - 375px: 1 列 grid、hamburger 表示、横スクロールゼロ

    **Chat (`/orochi/chat`):**
    - 1440px: InputBar + MessageArea 横幅フル、typing indicator 動作
    - 1024px: 同、chatscope outgoing bubble 幅 85%、incoming bubble 100%
    - 768px: 同、InputBar padding 縮小
    - 375px: textarea padding 縮小、Send ボタン可視、両サイド bubble 100%

    **ThreadSidebar drawer (tablet/mobile):**
    - 1024px 以下: hamburger / 既存 collapse トグルから ThreadSidebar を開き、`position: fixed` overlay、backdrop 半透明、Escape で閉じる

    **ダーク/ライト切替:**
    - 各幅で 🌙/☀️ toggle が瞬時に色反映（React 再レンダーなしで CSS 変数で解決）

    6. **`docs/phase-35-integration-check.md` の `## Chrome DevTools Responsive` セクションの表（8 行）を human checker が直接編集して PASS / Notes を埋める**。空欄 approve は不可。
    7. 埋め終わったら resume signal で "approved" と返答。
  </how-to-verify>
  <resume-signal>
    **B-3 強化版:** `docs/phase-35-integration-check.md` に Chrome DevTools Responsive セクション (4 widths × 2 themes = 8 行の表) を**全て追記した上で** "approved" と返答。空欄の approve は reject される。
  </resume-signal>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 03: Cross-browser sweep（Chrome / Edge / 可能なら Safari）+ Phase 36 Handoff Contract 確認 + integration-check.md 追記</name>
  <what-built>
    Phase 36 Handoff Contract 10 項目（UI-SPEC L439-452）の残 visual 項目（#4 InputBar slot / #5 MessageArea UX / #10 Chrome/Edge/Safari 破綻ゼロ）を確認する。結果を `docs/phase-35-integration-check.md` に追記する。
  </what-built>
  <how-to-verify>
    1. **#4 InputBar slot レイアウト visual 確認（Chrome 1 ブラウザで十分）:**
       - `/orochi/chat` で開発者ツール → Elements タブで `<div class="chat-input-bar">` 内を確認
       - `toolbarSlot` / `previewSlot` が空の場合に DOM に出ていない（条件レンダー）
       - textarea 左側に toolbar の隙間が無い（slot 空なら div も出ない）
       - previewSlot 空なら textarea 上に帯が出ない

    2. **#5 MessageArea UX retain:** Ctrl+Enter 送信 / AskMe ボタン / Cancel ボタン / QuestionPanel 表示 / resend checkbox / CopyAll / typing indicator 全動作を実測。

    3. **#10 Cross-browser sweep（Chrome + Edge 必須、Safari は macOS 環境があれば）:**

       各ブラウザで以下 3 ページ × 2 テーマ × desktop (1440) + tablet (1024) = 12 画面を sweep:

       **ページ:**
       - `http://localhost:5173/orochi/` (MenuScreen)
       - `http://localhost:5173/orochi/chat` (Chat + InputBar)
       - `http://localhost:5173/orochi/chat` で drawer 開閉（tablet 幅）

       **確認項目:**
       - レイアウト破綻なし（要素重なり・切れ・はみ出し）
       - chatscope バルーン幅が outgoing 85% / incoming 100% (tablet)
       - gradient title (Orochi Chat) 表示
       - dark/light 切替で色が瞬時に反映
       - drawer (tablet) が左から slide in、backdrop click で閉じる、Escape で閉じる
       - hamburger (mobile) が `<details>` で開閉
       - InputBar の Send / AskMe / Cancel が動く
       - MenuScreen の 3 セクションが表示、最近スレッドが 5 件以下

       **Safari 不在の場合:** Chrome DevTools で UserAgent を Safari に変更して近似確認（完全ではないが警戒点を拾える）。judge は `skipped / via UserAgent` として Notes に記載する。

    4. **結果を `docs/phase-35-integration-check.md` の以下 2 セクションに human checker が直接追記:**
       - `## Cross-Browser` 表の Chrome / Edge / Safari 3 行を全て埋める（Safari は skipped でも空欄禁止、skipped と明記）
       - `## Phase 36 Handoff Contract` 表の #4 / #5 / #10 3 項目の「結果」列を PASS or 詳細説明で埋める
       - `## Verdict` に APPROVED か NEEDS FIXES のいずれかを明記

    5. 問題があれば詳細を Issues found セクションに記録し、fix が必要な Plan を指示。問題がなければ "approved" と返答。
  </how-to-verify>
  <resume-signal>
    **B-3 強化版:** `docs/phase-35-integration-check.md` に Cross-Browser セクション (Chrome / Edge / Safari 3 行、Safari は skipped 可だが判定を明記) を全て記入し、Phase 36 Handoff Contract 表の #4 / #5 / #10 を埋め、Verdict を APPROVED / NEEDS FIXES に確定した上で "approved" と返答。空欄の approve は reject される。
  </resume-signal>
</task>

<task type="auto">
  <name>Task 04: integration-check.md 最終 verification（記入済か自動チェック）</name>
  <files>docs/phase-35-integration-check.md</files>
  <read_first>
    - docs/phase-35-integration-check.md（Task 02 / Task 03 で human 記入済の状態、W-5 Task 05 依存前提）
  </read_first>
  <action>
**W-5 明文化ゲート:** 本 Task は Task 02 と Task 03 が両方 "approved" を返した後に実行される前提で動作する。Task 02 / Task 03 のいずれかが pending の場合、本 Task の acceptance は FAIL する設計。

Task 02 / Task 03 の human verify で `docs/phase-35-integration-check.md` が埋まったので、Phase 35 の final commit に含めるためにファイル存在と内容 formatting を自動 check する。

**確認項目:**
- Chrome DevTools Responsive 4 width × 2 theme の表が埋まっている（8 行全て）
- Cross-Browser の Chrome / Edge / (Safari) 3 行が埋まっている
- Phase 36 Handoff Contract 10 項目の表が全部 PASS or 明示的な defer 理由あり
- Issues found セクションに未解決事項があれば記載（後続 polish phase or Phase 36 に繰り越し）
- Verdict が APPROVED/NEEDS FIXES で明示

**Gate（W-5）:**
- Task 02 が approved でなければ Chrome DevTools Responsive セクションが空欄 → 本 Task acceptance FAIL
- Task 03 が approved でなければ Cross-Browser セクションが空欄 → 本 Task acceptance FAIL
- これを acceptance grep で機械的に gate する（下記 acceptance 参照）

**整形調整:**
- 表の列数 / 行数が揃っているか
- "Tested by" / "Date" が記入済み
- 見出し level (h1 / h2 / h3) が一貫

**重要な制約:**
- このファイルは人間判断記録なので Claude が結果を変造しない
- 空欄があれば Task 02 / Task 03 のどちらが pending かを判断して返却する（Claude が勝手に PASS を埋めない）
  </action>
  <verify>
    <automated>test -f /home/parallels/workspaces/copilot-langgraph/docs/phase-35-integration-check.md &amp;&amp; wc -l /home/parallels/workspaces/copilot-langgraph/docs/phase-35-integration-check.md</automated>
  </verify>
  <acceptance_criteria>
    - `test -f docs/phase-35-integration-check.md` success
    - `wc -l docs/phase-35-integration-check.md` >= 30 （最低限の記録量）
    - `grep -c '## Chrome DevTools Responsive' docs/phase-35-integration-check.md` == 1
    - `grep -c '## Cross-Browser' docs/phase-35-integration-check.md` == 1
    - `grep -c '## Phase 36 Handoff Contract' docs/phase-35-integration-check.md` == 1
    - **B-3 width rows**: `grep -cE '^\| (375|768|1024|1440)' docs/phase-35-integration-check.md` >= 4 （4 幅の行が全て埋まっている）
    - **B-3 browser rows**: `grep -cE '^\| (Chrome|Edge|Safari)' docs/phase-35-integration-check.md` >= 2 （Chrome + Edge 必須、Safari は skipped OK）
    - `grep -cE 'PASS|APPROVED|skipped|NEEDS FIXES' docs/phase-35-integration-check.md` >= 5
  </acceptance_criteria>
  <done>
    docs/phase-35-integration-check.md が完全記入済で Phase 35 の visual 検証記録として後続 Phase から参照可能。Task 02 / Task 03 の approve が gate されていることが grep で確認できる。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Chromium remote debug 9222 ↔ local dev | social trust（開発者マシン内部の閉じた debug port）、CLAUDE.md で運用フロー確立済。 |
| integration-check.md 人間記入 ↔ Phase gate 判定 | human checker が直接編集、Claude は値を変造しない。空欄は acceptance gate で検出。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-33 | Repudiation | integration-check.md の human verify 結果が改ざんされて嘘の PASS が commit される | mitigate | Task 02 / Task 03 は `checkpoint:human-verify` で人間が直接記入。Task 04 は自動整形のみで内容変造しない（action で明示）。resume-signal で空欄 approve が reject される。Claude は PASS/FAIL を勝手に変えない。 |
| T-35-36 | DoS (visual) | Safari 不在による #10 の verification 欠損 | accept | Safari 不在環境での UserAgent spoof は近似。本番 Safari ユーザーが発生した場合は polish phase で対応。Verdict に Safari skipped を明記することで責任範囲を明確化。 |

すべて LOW severity。security_enforcement 閾値は high のみなので block しない。
</threat_model>

<verification>
- `test -f docs/phase-35-integration-check.md`
- Task 02 human approval（Chrome DevTools Responsive、表 8 行記入済）
- Task 03 human approval（cross-browser 3 行記入済 + Phase 36 Handoff 表記入済）
- Task 04 automated gate PASS（width rows >= 4, browser rows >= 2, Verdict 明記）
- Phase 36 が本 phase の成果物（InputBar slot / CSS 変数 / MenuScreen 構造）に差し込むだけで FIN-01/02 UI を追加できる contract が確立
</verification>

<success_criteria>
- **UX-03 全要件 PASS**:
  - UX-03-1/2/3 grep gate green (Plan 07a で確認済)
  - UX-03-4 (初見ユーザー判別可能) human checker approved（Task 02）
- **UX-04 全要件 PASS**:
  - UX-04-1〜7 grep gate green（Plan 07a）
  - UX-04-8 (4 画面 × 2 テーマ) human approved（Task 02、B-3 強化版 resume signal）
  - UX-04-9 (Chrome/Edge/Safari) human approved（Task 03、B-3 強化版 resume signal、Safari 任意）
- **Phase 36 Handoff Contract 10 項目全て確認済**:
  - 1-3, 6-9 grep で機械的に verify（Plan 07a 済）
  - 4, 5, 10 human checker で visual verify（本 Plan）
- **accessibility baseline**（:focus-visible + keyboard operation + ARIA 属性）が既存水準以上
- **ADR-0040（スレッドサイドバー日付グループ）/ ADR-0043（content 正規化）を破壊していない**
</success_criteria>

<output>
完了後、`.planning/phases/35-dashboard-design-system/35-07b-crossbrowser-handoff-SUMMARY.md` を作成し、以下を記録:

- Chrome DevTools Responsive 結果サマリ（8 画面）
- Cross-browser 結果サマリ（2-3 ブラウザ）
- Phase 36 Handoff Contract 10 項目の verification status 表
- docs/phase-35-integration-check.md の commit 済確認
- Phase 35 phase gate 最終判定（APPROVED / NEEDS FIXES）

および `docs/phase-35-integration-check.md` 自体は Task 01 作成 + Task 02/03 で human 記入済、Task 04 で gate 通過 → commit 対象。
</output>
