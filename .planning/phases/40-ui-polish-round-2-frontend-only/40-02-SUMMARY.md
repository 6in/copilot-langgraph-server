---
phase: 40
plan: 02
subsystem: Frontend / UI
tags: [frontend, ui, css, chatscope, debate-chat, theme]
requires:
  - frontend/src/theme.css (Phase 39 UIFIX-02 既存 override の cascade)
  - @chatscope/chat-ui-kit-react の `.cs-message--incoming .cs-message__content` DOM 構造
provides:
  - chatscope デフォルト薄青 bubble (light mode rgb(198,227,250)) の透明化
  - Debate Chat / SuperChat 等 senderName 付き message の agentBgColor wrapper 単独表示
affects:
  - frontend/src/components/MessageArea.tsx (L486-491 wrapper レイアウトに依存変化なし — margin: -8px -12px は padding=0 の外側 contents に対しても同じ視覚効果になる)
  - dark mode override (theme.css L197-200) は specificity 同等＋後置のため後勝ち維持
tech_stack:
  added: []
  patterns:
    - "CSS cascade ordering — light mode 既定の chatscope bubble を透明化する rule を dark mode override より前に置き、specificity 同等 / 後勝ちで data-theme=\"dark\" 時のみ暗色背景に切替"
key_files:
  created:
    - .planning/phases/40-ui-polish-round-2-frontend-only/40-02-SUMMARY.md
  modified:
    - frontend/src/theme.css
decisions:
  - todo の Option A (theme.css への global override 1 か所追加) を採用。chunked override (senderName ありの message のみへ scope 絞る) は副作用確認次第で revert 経由切替予定 (本 plan の手動 verification 項目)
metrics:
  duration: "1 task / 単一 CSS rule 追加"
  completed: 2026-05-13T09:07:44Z
  tasks_completed: 1
  files_changed: 1
  insertions: 11
  deletions: 0
---

# Phase 40 Plan 02: Debate Chat エージェントメッセージの 2 層 bubble 解消 Summary

`frontend/src/theme.css` に `.cs-message--incoming .cs-message__content { background: transparent !important; padding: 0 !important; }` を追加し、Debate Chat で観察されていた "chatscope デフォルト薄青 bubble と Phase 35 エージェント別カラー wrapper の 2 層重ね" を CSS 1 ルール追加のみで解消。

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | theme.css に Phase 40 UIFIX rule を追加し、dark mode override が後勝ちで残ることを確認 | `9029c77` | `frontend/src/theme.css` |

## Implementation Notes

### Cascade ordering
- 新規 rule 位置: theme.css **L179-187** (Phase 39 UIFIX-02 block L171-177 直下)
- dark mode override 位置: **L208-211** (`[data-theme="dark"] .cs-message--incoming .cs-message__content`)
- 結論: Phase 40 rule が先に定義され、dark mode rule が後勝ちで `--color-surface` を再適用 → 暗色テーマで regression なし

### 影響範囲
- **Debate Chat** (senderName 付き): 外側 chatscope bubble 透明化により、agentBgColor wrapper が単独表示。todo の主目的を達成
- **SuperChat** (senderName 付き): 同上
- **Chat / Gem / Canvas** (senderName 無し): wrapper の `style` が `undefined` のため agentBgColor も適用されない。外側透明化で MessageList の `--color-bg` がそのまま見える形に切替わる (本 plan の `<verification>` で目視確認必要)

### outgoing は touch しない
- `[data-theme="dark"] .cs-message--outgoing .cs-message__content` (L213-216) と `[data-theme="light"]` 既定の outgoing bubble は **未変更**。外向き message の見た目変化なし

## Acceptance Criteria (all met)

- [x] Source assertion: `grep -A1 'Phase 40 UIFIX' frontend/src/theme.css | grep -c 'background: transparent !important'` ≥ 1 (取得: 1)
- [x] Source assertion: `grep -B0 -A3 'Phase 40 UIFIX' frontend/src/theme.css | grep -c 'padding: 0 !important'` ≥ 1 (取得: 1)
- [x] Source assertion: 新規 rule のセレクタが `.cs-message--incoming .cs-message__content` を含む (grep ヒット 4 件 — 既存 box-sizing rule・dark override・本 plan 追加分を含む)
- [x] Source ordering: Phase 40 UIFIX 行 (L179) < dark mode override 行 (L208) → cascade 上 dark mode が後勝ち
- [x] Test command: lint regression を新規発生させない (本 plan は CSS のみ変更で TS/TSX 0 件 → eslint 対象外)
- [x] Source negation: `[data-theme="dark"] .cs-message--outgoing` を含む既存 rule (現 L213-216) は本 plan で変更しない (差分 0 行)
- [x] Done criteria: "Phase 40 UIFIX" コメント付き rule が dark mode override より前 (cascade 上後勝ち) に配置されている

## Deviations from Plan

None - plan executed exactly as written.

## Deferred Issues (pre-existing, out of scope)

Frontend lint (`bun run lint` in docker container against main worktree) reports **17 errors / 1 warning** in pre-existing TS/TSX files:
- `frontend/src/components/MarkdownMessage.tsx` (多数の `no-empty` 等)
- `frontend/src/hooks/useModels.ts` (`react-hooks/purity` — `Date.now()` 呼び出し)
- 他複数ファイル

本 plan の変更は `frontend/src/theme.css` (CSS) のみで TS/TSX に 0 行触っていないため、これら lint エラーは本 plan の責任範囲外 (SCOPE BOUNDARY: 既存の警告)。Phase 40 の別 Plan または将来の保守タスクで扱う候補。

## Manual Verification Required (post-merge)

Plan の `<verification>` 節に記載されている手動確認:

1. **Debate Chat (light mode)**: `http://localhost:5173/orochi/debate/{thread}` でエージェントバブルの上下から薄青がはみ出していないこと
2. **Debate Chat (dark mode)**: Header の 🌙 トグル後、incoming バブル背景が暗色 (`--color-surface`) で表示され透明にならないこと
3. **Chat / SuperChat / Gem / Canvas**: incoming AI バブルが「白背景に黒テキスト」になり読みづらくならないこと
4. Fallback: もし Chat/Gem/Canvas でコントラスト低下が顕著な場合、本 plan を revert し chunked override (senderName 付き message に scope 絞る方針) を別途検討 — revert 手順は theme.css の L179-187 を削除するのみ

## Known Stubs

None.

## Threat Flags

None — CSS 表示属性の変更のみで、ネットワーク endpoint / 認証 / ファイルアクセス / スキーマに影響なし。

## Self-Check: PASSED

- frontend/src/theme.css: FOUND (modified)
- .planning/phases/40-ui-polish-round-2-frontend-only/40-02-SUMMARY.md: FOUND (this file)
- Commit `9029c77`: FOUND in git log (verified before SUMMARY commit)
