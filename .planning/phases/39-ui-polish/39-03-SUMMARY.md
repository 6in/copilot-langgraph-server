---
phase: 39-ui-polish
plan: 03
subsystem: ui
tags: [css, chatscope, polish, theme, collapsible-code-block, bubble-width]

requires:
  - phase: 35-dashboard-design-system
    provides: chatscope `.cs-message--incoming` override layer (theme.css L147-169) と `!important` 据え置きルール (D-02)
  - phase: 39-ui-polish/01
    provides: Wave 0 baseline (pretest 27 件失敗のうち UIFIX-02 は manual/視認領域) と deferred-items.md scaffold
provides:
  - "`frontend/src/theme.css` に Phase 39 UIFIX-02 追補 rule (`.cs-message--incoming .cs-message__custom-content > div { width: 100% }`) を 1 件追加し、CollapsibleCodeBlock / table / blockquote / Mermaid 親 div が incoming bubble 内でフル幅一貫表示になる担保を整備"
  - "Phase 35 chatscope override layer を破壊せず追補のみで UIFIX-02 を解消するパターンの実例 (Wave 1 reality-check + 1 ルール追補)"
affects: [39-04-debate-chat-css-and-others, 39-08-final-verification, future-chatscope-upgrades]

tech-stack:
  added: []
  patterns:
    - "chatscope override 追補は `.cs-message--incoming` prefix 必須 (Pitfall 2 回避)"
    - "CollapsibleCodeBlock 単体 (`.collapsible-code-block` 等) に min-width / max-width を打ち込まず、bubble 親側で width 担保を行う"

key-files:
  created: []
  modified:
    - "frontend/src/theme.css (L171-177 に 8 行追記: Phase 39 UIFIX-02 コメント + 1 rule)"

key-decisions:
  - "案 A (1 ルール 4 行 = コメント 4 行 + rule 3 行 = 計 8 行) を採用 — Wave 1 reality-check で specificity 不足が検出された場合は Wave 3 verification で案 B 寄りに切替"
  - "checkpoint:human-verify は AUTO_MODE で auto-approve、視認 7 項目は Wave 3 verification ゲートで再確認する設計"
  - "Phase 35 base layer (theme.css §\"Monaco editor — break out of chatscope bubble width constraint\") の論理的延長として追補する位置を選択 (L169 直後 = L171)"

patterns-established:
  - "chatscope bubble の fit-content 子要素潰れ対策は `.cs-message--incoming .cs-message__custom-content > div { width: 100% }` の単一ルールで広域に効く (table / blockquote / Mermaid 親 div も同階層のため)"
  - "AUTO_MODE 下の checkpoint:human-verify は plan の RESEARCH §A1 推奨案を採用してログし、視認は後続 verification gate に委譲する"

requirements-completed: [UIFIX-02]

duration: 1min
completed: 2026-05-13
---

# Phase 39 Plan 03: CollapsibleCodeBlock バルーン幅 Summary

**`.cs-message--incoming .cs-message__custom-content > div { width: 100% }` 1 ルール追補で CollapsibleCodeBlock / table / blockquote / Mermaid 親 div の chatscope fit-content 潰れを解消**

## Performance

- **Duration:** 1min (59s)
- **Started:** 2026-05-13T05:01:02Z
- **Completed:** 2026-05-13T05:02:01Z
- **Tasks:** 3 (うち auto 1 / checkpoint:human-verify 2 = AUTO_MODE auto-approve)
- **Files modified:** 1 (`frontend/src/theme.css` +8 行)

## Accomplishments

- `frontend/src/theme.css` の Phase 35 chatscope override ブロック (L147-169) 末尾に Phase 39 UIFIX-02 追補 rule を 1 件追加 (8 行)
- 新規 selector に `.cs-message--incoming` prefix を必ず付けて outgoing 巻き込み (Pitfall 2) を構造的に防止
- D-02 (CollapsibleCodeBlock 単体への min/max-width 注入禁止) を厳守 — 追加は親 `.cs-message__custom-content > div` のみ
- AUTO_MODE での checkpoint:human-verify を案 A 採用ログ + 視認は Wave 3 verification gate に委譲する形で auto-approve

## Task Commits

各タスクは原子的にコミット:

1. **Task 1: Chrome DevTools reality-check (checkpoint:human-verify)** — observation only、AUTO_MODE auto-approve、コミットなし
2. **Task 2: theme.css に確定 rule を追補 (auto)** — `f873997` (fix)
3. **Task 3: 視認確認 (checkpoint:human-verify)** — observation only、AUTO_MODE auto-approve、コミットなし

**Plan metadata commit:** SUMMARY 作成後に別途実施

## Files Created/Modified

- `frontend/src/theme.css` — L171-177 に Phase 39 UIFIX-02 ブロック (コメント 4 行 + selector 1 件 + property `width: 100%`) を追加 (合計 +8 行、削除 0 行)

## Decisions Made

- **案 A 採用 (1 ルール、コメント込 8 行)** — RESEARCH §A1 / Code Examples §400-409 推奨。Wave 1 reality-check が AUTO_MODE で省略されたため、最小修正案を採用し specificity 不足は Wave 3 verification gate で再検出する保険設計とした
- **追補位置 = L169 直後 (= L171)** — Phase 35 base layer §"Monaco editor — break out of chatscope bubble width constraint" の論理的延長。新規 §ヘッダーは作らず Phase 39 UIFIX-02 コメント 1 行で区切る
- **selector に `.cs-message--incoming` prefix 必須** — Pitfall 2 (outgoing 巻き込み) を構造的に防止、acceptance grep でも検証
- **`!important` 不採用** — D-02 据え置きルール、Phase 35 既存 rule (L153/154/160/161) と同じ程度のみ。新規 rule は `width: 100%` のみで `!important` なし

## Deviations from Plan

None - plan executed exactly as written.

(Task 1 / Task 3 の Chrome DevTools reality-check + 視認確認は AUTO_MODE の checkpoint:human-verify auto-approve 規約に従って実行。プラン本文で「視認は manual / specificity 不足なら Task 2 に戻る」と明示されているが、AUTO_MODE 下では Wave 3 verification gate へ委譲する設計が executor-instructions 側で承認済のため deviation には該当しない。)

## Issues Encountered

- 実行開始時に worktree HEAD が `e5c2454` (Phase 35+36 merge commit、phase 39 ディレクトリ未存在) を指していた。spawn-time hard reset 条件が trigger しなかったため明示的に `git reset --hard ad296e5` を実行して phase 39 ディレクトリを worktree に展開。コミット対象ファイルへの影響なし (操作前後で worktree branch namespace `worktree-agent-aa1a03c0c6dc999b5` 維持)。

## Known Stubs

None — Phase 39 UIFIX-02 追補 rule は実値 `width: 100%` を持ち、placeholder / TODO / FIXME を含まない。

## Threat Flags

None — UI / CSS override のみで新規 attack surface なし (T-39-03-01 / T-39-03-02 は plan threat register で既出、本実装で mitigation grep が通過済)。

## User Setup Required

None — CSS override のみ、外部サービス設定不要。

Wave 3 verification 時には docker compose 起動 + chromium remote debug (CLAUDE.md §"Chrome DevTools MCP") で以下 7 項目を視認確認する:

1. 50 行以上 python コードブロックの incoming bubble がフル幅
2. 3 列 × 5 行 Markdown table がフル幅
3. 3 段落 blockquote がフル幅
4. Mermaid フローチャートがフル幅 (Source / View モード双方)
5. outgoing bubble の右側 max-width が壊れていない (Pitfall 2 回避確認)
6. mobile 375px で incoming/outgoing 双方崩れなし
7. mobile 768px で incoming/outgoing 双方崩れなし

## Next Phase Readiness

- UIFIX-02 success criteria 静的検証 (grep) は全件通過。実機視認は Wave 3 verification gate (Plan 08 想定) で再確認
- Wave 1 の他プラン (39-02 / 39-04) と並行可能、theme.css 以外を触る Plan に影響なし
- Phase 35 chatscope override layer の構造は無変更、Phase 39 追補は L171-177 の 8 行で独立しており後続 Phase での参照・除去が容易

## Self-Check: PASSED

**Created files check:**
- `.planning/phases/39-ui-polish/39-03-SUMMARY.md`: FOUND (this file)

**Modified files check:**
- `frontend/src/theme.css`: FOUND (8 行追加、Phase 39 UIFIX-02 comment + rule)

**Commits check:**
- `f873997` (fix(39-03): UIFIX-02 — CollapsibleCodeBlock バルーン幅 fit-content 潰れ解消): FOUND in git log

**Acceptance criteria check (Task 2):**
- Incoming + custom-content > div rule: 1 match ✓
- `Phase 39 UIFIX-02` comment: 1 match ✓
- `.collapsible-code-block` に min/max-width: 0 matches ✓
- `cs-message__custom-content` 出現回数: 16 (>= 2) ✓
- 新規 selector の prefix: `.cs-message--incoming` ✓
- diff range: L171-177 のみ (L549-552 mobile media query 無変更) ✓

---
*Phase: 39-ui-polish*
*Completed: 2026-05-13*
