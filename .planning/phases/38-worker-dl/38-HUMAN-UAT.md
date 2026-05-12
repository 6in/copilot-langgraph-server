---
status: partial
phase: 38-worker-dl
source: [38-VERIFICATION.md]
started: 2026-05-12T02:30:00Z
updated: 2026-05-12T02:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. FOUT-03 — チャット画面プレビュー (画像 / Markdown / CSV / text の各 renderer dispatch 実機動作)
expected: AttachmentModal で kind 別 renderer (image=`<img>`, markdown=react-markdown, csv=ag-grid, text=Monaco) が破綻なく描画され、PDF/unsupported はフォールバック案内 + DL CTA を出す
result: [pending]
how: `docker compose up -d` → `http://localhost:5173/orochi/` → Chat で execute_python に `matplotlib で sin カーブの PNG を保存` → AttachmentChipRow → モーダル → 各 renderer 動作確認

### 2. Dark mode 視覚整合性
expected: ダーク/ライト切替で Modal overlay / 4 renderer 全てがコントラスト破綻なく表示される
result: [pending]
how: ヘッダーのダーク/ライト切替を 2 回トグルしながら Modal を開き、overlay・テキスト・border のコントラストを目視確認 (UI-SPEC Checker #16)

### 3. Mobile 375px viewport の Modal full-screen 化
expected: DevTools viewport を 375×667 にすると Modal が full-screen に展開、ダウンロード CTA が full-width 化
result: [pending]
how: Chrome DevTools で device toolbar → 375×667 (iPhone SE) → Modal を開いて full-screen 化 + CTA full-width を目視確認 (UI-SPEC Checker #17)

### 4. Multi-user isolation (FOUT-04 sc5)
expected: 別 user の JWT で `/api/threads/{tid}/outputs/{name}` を curl → 401 or 404、Modal を別 user session で開くとエラーバナー「このファイルにはアクセスできません」表示
result: [pending]
how: 2 つの GitHub アカウントで login → User A で生成ファイル発生 → User B JWT cookie で curl 直接叩き + Modal で開く (UI-SPEC Checker #18)

### 5. Size cap UX
expected: >1MB text / >10MB image で size cap 案内 + DL CTA、accent-subtle banner、destructive 色なし
result: [pending]
how: execute_python で 11MB 画像 / 2MB CSV を出力 → モーダルで size cap banner を目視 (UI-SPEC Checker #19)

### 6. PDF / unsupported フォールバック
expected: PDF を Modal で開くと「Download only」案内 + DL CTA を表示しプレビューは実行されない
result: [pending]
how: execute_python で reportlab 等で PDF 生成 → Modal で開く → フォールバック描画確認 (UI-SPEC Checker #20)

### 7. Accent reserved-for / destructive 色限定
expected: AttachmentChipRow / AttachmentModal で `--color-accent` の使用箇所が UI-SPEC L173-192 の用途内に収まり、destructive はエラーバナーのみで使われる
result: [pending]
how: DevTools で AttachmentChipRow / Modal / preview の各要素を選択し computed style の color/border-color が `--color-accent` を使っている箇所を UI-SPEC L173-192 と照合 (Checker #7, #8)

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
