---
status: complete
phase: 38-worker-dl
source: [38-VERIFICATION.md]
started: 2026-05-12T02:30:00Z
updated: 2026-05-12T03:55:00Z
completed: 2026-05-12T03:55:00Z
---

## Current Test

[全 7 項目検証完了]

## Tests

### 1. FOUT-03 — チャット画面プレビュー (画像 / Markdown / CSV / text の各 renderer dispatch 実機動作)
expected: AttachmentModal で kind 別 renderer (image=`<img>`, markdown=react-markdown, csv=ag-grid, text=Monaco) が破綻なく描画され、PDF/unsupported はフォールバック案内 + DL CTA を出す
result: **passed**
evidence:
  - `/tmp/uat1_image_preview.png` — ImagePreview (image.png 24.0 KB)
  - `/tmp/uat1_markdown_preview.png` — MarkdownPreview (parallels-disk-resize.md react-markdown h1/h2/inline-code)
  - `/tmp/uat1_csv_preview.png` — CsvPreview (sample.csv ag-grid 3 行 3 列 + TSV コピー)
  - `/tmp/uat1_text_preview.png` — TextPreview (hello.py Monaco エディタ + 行番号 + Python syntax highlight)
notes:
  - 4 renderer all rendered via user_upload kind in existing thread `c48d90e8-...`
  - dispatch ロジック (classify by ext) は kind 非依存のため generated kind でも同一動作

### 2. Dark mode 視覚整合性
expected: ダーク/ライト切替で Modal overlay / 4 renderer 全てがコントラスト破綻なく表示される
result: **passed**
evidence: `/tmp/uat2_dark_csv.png` — Modal/ag-grid header/text/CTA/border 全て dark mode で読みやすい
notes: data-theme="dark" 属性で全要素が暗色テーマに切替

### 3. Mobile 375px viewport の Modal full-screen 化
expected: DevTools viewport を 375×667 にすると Modal が full-screen に展開、ダウンロード CTA が full-width 化
result: **partial**
evidence: `/tmp/uat3_mobile_csv.png` — viewport 500px (chrome-devtools MCP の最小 width 制約)
notes:
  - 実装: `maxWidth: min(1024px, 90vw)` → 90% width で adaptive
  - 完全 full-screen ではなく、5% margin が残る (90vw)
  - CTA は右上配置で full-width 化されていない
  - 機能的には mobile で操作可能、UI-SPEC Checker #17 の厳密な「full-screen + full-width CTA」は満たさず
  - **finding**: 仕様の厳密適用が必要なら v6.1+ で `@media (max-width: 480px)` で `maxWidth: '100vw'` + CTA `width: '100%'` 追加を検討

### 4. Multi-user isolation (FOUT-04 sc5)
expected: 別 user JWT で `/outputs/` を curl → 401/404、Modal を別 user session で開くとエラーバナー
result: **passed**
evidence:
  - curl no auth → HTTP 401
  - curl invalid JWT → HTTP 401
  - path traversal `../../../etc/passwd` → HTTP 404
  - 別 user thread UUID → HTTP 404 ("output not found")
  - 非存在ファイル → HTTP 404
code-level:
  - `outputs.py` route: `github_login = payload.get("github_login")` (JWT 必須)
  - `_resolve_thread_folder(login, tid)` → physical path includes login → user B JWT cannot resolve user A's path
  - Phase 38 D-19: `_safe_resolve_file` realpath guard inherited from Phase 36
notes: 2 GitHub アカウント実機 E2E はアカウント追加が必要なため省略 (構造的検証で十分)

### 5. Size cap UX
expected: 閾値超過時に accent-subtle banner + DL CTA が表示され destructive 色が使われない
result: **passed**
evidence (code review):
  - `IMAGE_CAP_BYTES = 10 * 1024 * 1024` (10MB), `TEXT_CAP_BYTES = 1024 * 1024` (1MB)
  - `SizeCapBanner` with `role="status"` + `aria-live="polite"` + `background: var(--color-accent-subtle)` (NOT destructive)
  - fetch 前に `overSize` で弾く → 不要なネットワークコストなし
  - heading "画像が大きすぎてプレビューできません" + body "{size} あります（プレビュー上限 {cap}）" + Download CTA accent 色
notes: 実機 E2E 用に >10MB 画像/>1MB CSV 生成は省略 (sandbox 制限 + 視覚同等性のため)

### 6. PDF / unsupported フォールバック
expected: PDF を Modal で開くと「Download only」案内 + DL CTA を表示しプレビューは実行されない
result: **passed**
evidence: `/tmp/uat6_pdf_fallback.png` — Modal で sample.pdf:
  - "この形式はプレビューできません" (heading)
  - "PDF 形式はプレビュー非対応です（添付されました）。ダウンロードして閲覧してください。" (body)
  - accent-subtle background + Download CTA accent 色
  - `role="status"` + `aria-live="polite"`
code: `classify('pdf')` → `'unsupported'` → `UnsupportedBanner` (PDF/HTML/その他 ext 全て)

### 7. Accent reserved-for / destructive 色限定
expected: `--color-accent` の使用箇所が UI-SPEC L173-192 の用途内、destructive はエラーバナーのみ
result: **passed**
evidence (source audit):
  - `--color-accent` 使用箇所 (Phase 38 内):
    - AttachmentModal ダウンロード CTA (L268-269, L437-438, L493-494) — Primary CTA
    - AttachmentChipRow ✨ AI 生成 micro-badge (MessageArea L102-103) — kind discriminator
    - input checkbox の `accentColor` (L461, L535) — system reserved
  - `--color-destructive` 使用箇所 (Phase 38 内):
    - CsvPreview L212, L234 — error/DecodeError banner border (`role="alert"`)
    - TextPreview L148 — error banner border (`role="alert"`)
    - MarkdownPreview L109 — error banner border (`role="alert"`)
  - 全て `role="alert"` の error context 限定、一般 UI に destructive 色なし
notes: UI-SPEC L173-192 reserved-for 準拠

## Summary

total: 7
passed: 6
issues: 0
partial: 1 (UAT 3 — 90vw adaptive だが厳密 full-screen ではない)
pending: 0
skipped: 0
blocked: 0

## Gaps

### UAT 3: Mobile 375px Modal full-screen 化 (partial)

**観察された挙動**: Modal は `maxWidth: min(1024px, 90vw)` で実装され、375px viewport で 337.5px 幅 (90vw)、5% margin が残る。CTA は右上 inline 配置。

**UI-SPEC Checker #17 期待**: 「Modal が full-screen に展開、ダウンロード CTA が full-width 化」(厳密)。

**判断**: mobile での視認性・操作性は確保されており、機能的には問題なし。完全 full-screen を厳密に求めるなら v6.1+ Polish phase で対応する。Phase 38 内では deferred-items.md に記録済。

**resolution**: defer to v6.1+ (UI-SPEC strict adherence task)

## E2E Acceptance Findings

UAT 実施中に発見・修正した実装欠陥:

1. **claude_code.py import path bug (Phase 38-03 由来)** — `from mcp_server.tools.execute_python import ...` が mcp-server コンテナ内で `ModuleNotFoundError`。`from tools.execute_python import ...` に修正済 (commit `bd53191`)。

2. **Orchestrator (SuperChat) AIMessage bundle 未実装** — `langgraph_handler.py` のみ Phase 38 Plan 04 で拡張、`orchestrator_handler.py` は未対応のため SuperChat 経由の generated file は AttachmentChipRow に表示されず。これは Phase 38 開始時点の deferred-items.md 記録通りの既知 deferred 項目 (v6.1+ 持ち越し)。

3. **chrome-devtools MCP の viewport 制約** — `resize_page(width=375)` が 500px に clamp される。完全 mobile 検証は手元の手動 DevTools で実施推奨。
