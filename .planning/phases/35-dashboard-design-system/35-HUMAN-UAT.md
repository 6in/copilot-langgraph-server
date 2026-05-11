---
status: partial
phase: 35-dashboard-design-system
source: [35-VERIFICATION.md]
started: 2026-04-23T12:00:00Z
updated: 2026-04-23T12:00:00Z
---

## Current Test

[awaiting human testing — 3 cross-browser / drawer-trigger items]

## Tests

### 1. Edge ブラウザで 4 幅 × 2 テーマ sweep
expected: 1440/1024/768/375px 各幅で Edge (Chromium base) での MenuScreen / Chat / drawer CSS overlay / chatscope バルーン幅 / gradient title が Chrome と視覚的差異なし
result: [pending]

### 2. Safari (WebKit) で同 sweep
expected: Safari 固有の transform / flex / `background-clip: text` / `:focus-visible` / `var()` fallback が正常動作。Chrome/Edge と視覚的差異なし
result: [pending]

### 3. Drawer UI trigger 未配線の取り扱い確認（Issue 2）
expected: Phase 36 early fix で Header に drawer open button を追加、mobile hamburger menu にも drawer open item を追加。それまでは tablet/mobile ユーザーは thread 一覧にアクセス不能（既知の機能ギャップとして記録済）
result: [pending — Phase 36 着手時の early fix で closure]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
