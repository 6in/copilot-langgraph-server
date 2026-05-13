---
phase: 38
slug: worker-dl
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-12
inherits_from:
  - 35-UI-SPEC.md
  - 36-UI-SPEC.md
---

# Phase 38 — UI Design Contract

> ファイル出力（worker 生成 DL + プレビュー + ユーザー別保持）フェーズの UI 契約。
> gsd-ui-researcher が作成、gsd-ui-checker が検証する。
> 本 SPEC は **Phase 35 / Phase 36 UI-SPEC の増分仕様** として運用する。
> 既存の `<AttachmentChipRow>`（`MessageArea.tsx` 内）と `<AttachmentChips>` を `kind` 対応に拡張し、
> 新規 `<AttachmentModal>` でプレビューを担う。
> AI 応答テキスト内への inline 描画はしない（D-13）。

**対象要件:** FOUT-01（DL）、FOUT-02（claude_code workspace 取得）、FOUT-03（チャット内プレビュー）、FOUT-04（過去スレッド再取得 + multi-user isolation）
**依存元契約:**
- `.planning/phases/35-dashboard-design-system/35-UI-SPEC.md` の §Token Naming / §Color / §Spacing / §Typography / §Responsive すべて
- `.planning/phases/36-text-code-image-multimodal/36-UI-SPEC.md` の §Token Reuse Contract / §Component Contracts（`<AttachmentChips>` / Bubble 内 `<AttachmentChipRow>` 仕様）

---

## Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none（CSS custom properties on `:root` + `[data-theme="dark"]`、Phase 35 D-01 で locked） | 35-UI-SPEC |
| Preset | not applicable | — |
| Component library | `@chatscope/chat-ui-kit-react@^2.1.1`（既存維持、override は CSS 変数経由） | package.json |
| Icon library | 絵文字のみ（📎 / 🖼 / 📄 / ✨ / 📥 / ⚠ / ×）— 新規アイコンライブラリは導入しない | Phase 35/36 踏襲 |
| Font | システム default + `Rajdhani`（タイトル専用） | Phase 35 踏襲 |
| shadcn ゲート判定 | **N/A** — Phase 35 D-01 の "CSS custom properties locked" が継続 | 35-UI-SPEC |
| Theme 切替機構 | `<html data-theme="dark">` 属性（既存維持） | 35-UI-SPEC |
| 新規トークン追加 | **なし** — Phase 35 が定義した token で全要素を表現 | 本 SPEC §Token Reuse Contract |
| 新規 npm パッケージ | **ゼロ** — `@monaco-editor/react@4.7.0` / `ag-grid-community@35.2.1` / `react-markdown@10.1.0` / `remark-gfm@4.0.1` はすべて Phase 35/36 で導入済 | 38-RESEARCH §Standard Stack |

---

## Token Reuse Contract

Phase 38 は **Phase 35 の既存 token を参照するのみ** で、新規 CSS 変数は追加しない。
新規追加を認める数少ない例外は、AttachmentModal のサイズ・renderer 内 const（TS 側 `MODAL_MAX_VW = 90`、`PREVIEW_TEXT_SIZE_CAP_BYTES = 1024 * 1024` 等）で、CSS 変数化はしない。

| Phase 38 要素 | 参照する Phase 35 token | Usage |
|--------------|------------------------|-------|
| `<AttachmentChipRow>` チップ全体 background（kind=user_upload） | `--color-surface` | Phase 36 と同一（変更なし） |
| `<AttachmentChipRow>` チップ全体 background（kind=generated） | `--color-surface` | 同一の地色（kind は左肩 micro-badge で区別） |
| `<AttachmentChipRow>` チップ枠（共通） | `--color-border` | Phase 36 と同一 |
| `<AttachmentChipRow>` kind=user_upload micro-badge background | `--color-surface-elevated` | 「添付」ラベル — 弱い強調 |
| `<AttachmentChipRow>` kind=user_upload micro-badge text | `--color-text-muted` | 同上 |
| `<AttachmentChipRow>` kind=generated micro-badge background | `--color-accent-subtle` | 「AI 生成」ラベル — accent 系の弱い面、本 SPEC §Accent Reserved-For Extension で追加 |
| `<AttachmentChipRow>` kind=generated micro-badge text | `--color-accent` | accent の文字色、reserved-for に追加 |
| `<AttachmentChipRow>` チップ hover/focus | `--color-accent` 1px focus ring | 押下可能性のアフォーダンス、reserved-for に追加 |
| `<AttachmentModal>` overlay 背景 | `rgba(0,0,0,0.5)` | hex/RGB 直書き許容（既存 ConfirmModal と同パターン） |
| `<AttachmentModal>` dialog 背景 | `--color-surface-elevated` | カード状の地色 |
| `<AttachmentModal>` dialog 枠 | `--color-border` | 1px |
| `<AttachmentModal>` ヘッダー文字 | `--color-text` | filename 表示 |
| `<AttachmentModal>` ヘッダー meta（size, timestamp, kind） | `--color-text-muted` + `--font-caption` | 補助情報 |
| `<AttachmentModal>` 「ダウンロード」CTA | `--color-accent` + `--color-accent-contrast` | primary action、reserved-for に追加 |
| `<AttachmentModal>` 「閉じる」× ボタン通常 | `--color-text-muted` | 非強調 |
| `<AttachmentModal>` 「閉じる」× ボタン hover | `--color-text` | 弱い hover、destructive ではない |
| `<AttachmentModal>` body 区切り | `--color-border` 1px top | ヘッダー / preview の境界 |
| Image preview 枠 | `--color-border` + `--radius-md` | サムネと同じ枠 |
| Markdown preview コンテナ | `--color-surface` | render 内地色、`MarkdownMessage` 系の bubble 内挙動とは独立した薄ラッパー |
| CSV preview コンテナ | ag-grid `themeQuartz` で `--color-*` を引き渡し | `ChatAgGridTable` の theme パラメータと同パターン |
| Monaco text preview 枠 | `--color-border` | エディタ全体 |
| Monaco text preview theme | `vs` / `vs-dark`（`useCurrentTheme` 経由） | Phase 35 既存と同パターン |
| エラーバナー（401/404/サイズ超過/decode 失敗） | `--color-destructive` 1px 枠 + `--color-surface` 背景 | Phase 36 §Color §Destructive 4 箇所の延長 |
| Size cap 超過時の "DL のみ" 案内 | `--color-accent-subtle` 背景 + `--color-text` 本文 + `--color-accent` CTA | non-error な「案内」（vision warning と同 spirit） |

**非許容の新規トークン:**
- `--color-generated-*` / `--color-preview-*` / `--color-modal-*` などを作らない。
- `--space-modal-*` のような用途固有 spacing も作らない。`--space-3` / `--space-4` / `--space-6` の合成で表現する。
- `--radius-modal` も作らない。`--radius-lg` (12px) を流用する。

---

## Accent Reserved-For Extension

Phase 35 / 36 §Color §Accent reserved-for リストに以下 2 項目を **追加** する（既存 9 項目は維持）。

| # | 追加される用途 | 根拠 |
|---|---------------|------|
| 10 | `<AttachmentChipRow>` kind=generated チップの micro-badge（「AI 生成」ラベル）と、チップ hover/focus ring | input vs output の semantic 識別。accent を単純なクリック誘導ではなく「AI 生成というコンテンツ属性」のシグナルとして使う |
| 11 | `<AttachmentModal>` の「ダウンロード」CTA + サイズ超過時案内の CTA | モーダル内 primary action。1 つのモーダルにつき 1 CTA、accent 10% 配分の範囲内 |

**accent 10% 予算の再確認:**
本 phase で追加される accent 使用箇所は「kind=generated のチップ micro-badge」と「Modal CTA」の 2 種。
チップ micro-badge は 11px × 36px 程度（バッジ 1 個）× 数件で、画面 accent 面積として Phase 36 の AttachmentButton / VisionWarningBanner と同等以下。
Modal は同時に開けるのは 1 つだけのため accent CTA も同時に 1 個。
合算で Phase 35 / 36 の 9 用途と合わせて 10% 以内に収まる。

**accent 予算外の ref-check:**
- 「kind=generated チップ全面 accent 塗り」→ 使ってはいけない。micro-badge と focus ring のみ accent、地色は user_upload と同じ `--color-surface`。
- 「Modal body 内に accent 多用」→ 使ってはいけない。1 モーダル内の accent は CTA ボタン 1 個 + サイズ超過時の案内 CTA 1 個まで。
- 「kind ラベルを destructive 色で表現」→ 使ってはいけない（D-14 / Phase 36 D-18 と同じ spirit：エラーではない属性表示）。

---

## Spacing Scale

Phase 35 の 8-point scale をそのまま使う。**新規 token 追加なし。**

| Phase 38 要素 | 使用する Phase 35 token |
|--------------|------------------------|
| `<AttachmentChipRow>` チップ間 gap | `--space-2`（8px、Phase 36 既存） |
| `<AttachmentChipRow>` チップ内 padding | `--space-2 --space-3`（8/12px、Phase 36 既存） |
| `<AttachmentChipRow>` micro-badge と filename の gap | `--space-1`（4px） |
| `<AttachmentChipRow>` micro-badge 内 padding | `2px var(--space-1)`（縦 2px 横 4px — 0.5 段例外、根拠は下記注記） |
| `<AttachmentModal>` overlay 中央寄せ padding | `--space-4`（16px、画面端からの余白） |
| `<AttachmentModal>` dialog 内 padding | `--space-4`（16px、ヘッダー・body・footer 共通） |
| `<AttachmentModal>` ヘッダー要素間 gap | `--space-3`（12px） |
| `<AttachmentModal>` ヘッダー / body 間の border-top margin | `--space-3`（12px、border + margin で視覚分離） |
| `<AttachmentModal>` size cap 案内バナーの内側 padding | `--space-3 --space-4`（12/16px、VisionWarningBanner と同形） |
| Image preview の最大寸法 padding | `--space-2`（8px、preview コンテナと画像の間） |
| Monaco preview コンテナの内 padding | 0（エディタ自体が padding を持つ） |

**0.5 段例外（2px）の根拠:**
micro-badge は font-caption 12px の文字を pill 形で囲む小さい要素で、4px 縦 padding だと badge 全体高さが 22px となりチップ高 28px の中で過剰。2px とすると badge 高さ 18px となりチップ高 28px の縦中央配置で自然に収まる。
他に 2px 単位は出さない（micro-badge 専用例外）。

**タップターゲット最低値:**
Phase 35 の 36px / tablet 40px を踏襲。
- `<AttachmentChipRow>` チップ自体: 28px 高（Phase 36 既存）。ただし本 phase で **チップ全体がクリック可能 = モーダルを開く** ボタン挙動になるため、`<button>` 要素として包み、hit area は親要素含めて 28×min 120px（filename 最小幅）= 概ね 28×120px。28px はモバイルタップターゲット 36px を下回るが、Phase 36 で既に 28px チップが導入されており、本 phase で hit area を変えない方が UX 連続性が高い（Phase 35 D-08 タップターゲット規約には抵触するが、Phase 36 で承認済の継続）。
- `<AttachmentModal>` の × 閉じる: 24×24 icon + 36×36 hit area（Phase 35 §Visual Accessibility Baseline の最低値準拠）。
- 「ダウンロード」CTA: 36×min 120px（desktop）、40×min 120px（tablet/mobile）。

---

## Typography

Phase 35 の 5 役（body / label / heading / display / caption）をそのまま使う。**新規 font-role 追加なし。**

| Phase 38 要素 | 使用する Phase 35 役 |
|--------------|--------------------|
| `<AttachmentChipRow>` filename | `--font-label`（14px/1.4）、truncate 1 行（Phase 36 既存） |
| `<AttachmentChipRow>` size 表示 | `--font-caption`（12px/1.4、Phase 36 既存） |
| `<AttachmentChipRow>` micro-badge ラベル（「AI 生成」/「添付」） | `--font-caption`（12px/1.4）weight を 600 にオーバーライド |
| `<AttachmentModal>` ヘッダー filename | `--font-label`（14px/1.4）weight 600 |
| `<AttachmentModal>` ヘッダー meta（size, timestamp, kind） | `--font-caption`（12px/1.4） |
| `<AttachmentModal>` 「ダウンロード」CTA ラベル | `--font-label`（14px/1.4） |
| `<AttachmentModal>` × 閉じる aria-label | （視覚要素なし、スクリーンリーダー専用） |
| エラーバナー見出し | `--font-label`（14px/1.4）weight 600 |
| エラーバナー本文 | `--font-label`（14px/1.4） |
| サイズ超過時の案内 見出し | `--font-label`（14px/1.4）weight 600 |
| サイズ超過時の案内 本文 | `--font-label`（14px/1.4） |
| Markdown preview 本文 | react-markdown が自前で h1〜h6/p/code を出す。`--font-body`（16px/1.5）を `.attachment-modal-md` コンテナに適用し、内部 h1〜h6 は CSS で `--font-heading` (20px/1.3) 相当に縮約 |
| Monaco preview コンテンツ | Monaco の monospace デフォルト（new font-role 追加なし） |

**weight オーバーライドルール:**
本 phase で認めるオーバーライドは 2 箇所:
1. `<AttachmentChipRow>` micro-badge ラベル: `fontWeight: 600`（caption 12px のまま強調）
2. `<AttachmentModal>` ヘッダー filename: `fontWeight: 600`（label 14px のまま強調）

新規 `--font-label-bold` 変数は作らず、コンポーネント内 inline style で `fontWeight: 600` を付与する（Phase 36 と同方針）。

**line-height の堅持:**
- body 1.5 / label 1.4 / heading 1.3 / caption 1.4（Phase 35 定義を変更しない）
- micro-badge は flex `align-items: center` で縦中央揃え、line-height による高さ揺らぎを吸収。

---

## Color (60/30/10 契約)

Phase 35 の 60/30/10 split を完全踏襲。`--color-bg` 60% / `--color-surface` 30% / `--color-accent` 10%。

### accent reserved-for 統合リスト（Phase 35 の 7 + Phase 36 の 2 + Phase 38 の 2 = 11 項目）

**Phase 35 既存（再掲、変更なし）:**
1. Send ボタン背景（InputBar）
2. New Chat ボタン背景（ThreadSidebar）
3. textarea / filter input の `:focus` ring
4. active thread item の左 3px アクセントボーダー（tablet 以降）
5. ダッシュボードカード `:hover` / focus ring
6. "Orochi Chat" タイトルのグラデーション
7. AuthPanel の link

**Phase 36 既存（再掲、変更なし）:**
8. `<AttachmentButton>`（📎 絵文字の hover / active / :focus-visible 色）
9. `<VisionWarningBanner>`（CTA 背景 + 左端 3px アクセントバー）

**Phase 38 追加（2 項目）:**
10. `<AttachmentChipRow>` kind=generated micro-badge（「AI 生成」ラベル text/background）+ チップ全体の hover/focus ring
11. `<AttachmentModal>` 「ダウンロード」CTA + サイズ超過時案内の CTA

**11 項目以外で accent を使ってはいけない。**

### Destructive 使用箇所（Phase 35/36 踏襲 + 本 phase 追加）

| 箇所 | 用途 | 根拠 |
|------|------|------|
| `<AttachmentChips>` × 削除ボタンの hover 色（Phase 36） | 削除 hint | 既存 |
| 画像サムネ error 時の枠（Phase 36） | 読み込み失敗シグナル | 既存 |
| Upload failed エラーバナー枠（Phase 36） | エラー state | 既存 |
| サイズ超過 413 エラー時のチップ赤枠（Phase 36） | size 制限違反 | 既存 |
| `<AttachmentModal>` body 内 エラーバナー（401 / 404 / decode 失敗）枠 | preview 取得失敗 | 本 phase 追加（Phase 36 のエラーバナーパターン延長） |

**追加されるのは 1 箇所のみ（モーダル内 エラーバナー）。**

**kind=generated を destructive 色で表現してはいけない**（D-14 / 36 D-18 と同じ spirit：エラーではなく属性表示）。
**サイズ超過案内（>1MB）も destructive ではなく accent-subtle で「案内」表現にする**（DL すれば見える＝エラーではない）。

### kind ラベル（最重要決定）

| 値 | 表示文言 | Badge 背景 | Badge 文字 | Badge アイコン |
|----|---------|-----------|-----------|---------------|
| `kind="user_upload"` | `添付` | `var(--color-surface-elevated)` | `var(--color-text-muted)` | （なし）または 📎 |
| `kind="generated"` | `AI 生成` | `var(--color-accent-subtle)` | `var(--color-accent)` | ✨ |

**設計判断:**
- 「AI 生成」は Phase 35/36 で確立済の語彙（CONTEXT.md `<decisions>` D-14 で `kind="user_upload" / "generated"` discriminator として宣言されている）。「自動生成」「出力」等のバリエーションは作らない。
- 「添付」は Phase 36 で既に AttachmentChip の意味として運用されているため、これに合わせる。
- アイコンは「✨ AI 生成」「📎 添付」の 2 トーンで pill 内に文字とともに表示。
- 色は accent-subtle vs surface-elevated の弱コントラストペアで、両者を「同じ重要度の属性タグ」として位置づける（generated を「より目立つ」表示にすると AI 生成物が常に視覚優位になり、ユーザー添付の地位が下がる UX 不均衡を生む）。

---

## Copywriting Contract

全て日本語（CLAUDE.md 規約）。Phase 35 / 36 の copy を壊さず **追加のみ**。

### `<AttachmentChipRow>` kind 拡張（既存ファイル: `MessageArea.tsx` 内）

| 要素 | Copy | Notes |
|------|------|-------|
| chip row 全体 aria-label（Phase 36 既存、改訂） | `添付・AI 生成ファイル {n} 件` | input / output 混在の事実を反映 |
| 画像 chip aria-label（kind=user_upload） | `添付画像: {filename}（{size}）` | Phase 36 既存維持 |
| 画像 chip aria-label（kind=generated） | `AI が生成した画像: {filename}（{size}）` | 新規 |
| 画像 chip click 後の action（kind 共通） | モーダルプレビューを開く | D-13 確定 |
| text/code chip aria-label（kind=user_upload） | `添付ファイル: {filename}（{size}）` | Phase 36 既存維持 |
| text/code chip aria-label（kind=generated） | `AI が生成したファイル: {filename}（{size}）` | 新規 |
| text/code chip click 後の action（kind 共通） | モーダルプレビューを開く | D-13 確定 |
| chip tooltip（hover、kind 共通） | `{filename}（{size}）— クリックでプレビュー` | hover で表示、Phase 36 既存に "— クリックでプレビュー" を追加 |
| micro-badge（kind=generated） | `✨ AI 生成` | accent 配色、必ず filename の前に配置 |
| micro-badge（kind=user_upload） | `📎 添付` | muted 配色、必ず filename の前に配置 |

**badge の表示判断:**
- 画像チップ: badge はサムネ上に絶対配置（右下、サムネ面積の 30% 以内）。サムネが小さくて隠れる場合は hover 時のみ表示でもよい（planner 判断、ただし aria-label には常に含める）。
- text/code チップ: pill の左端、絵文字 + 「AI 生成」/「添付」の順で表示。

### `<AttachmentModal>` 新規コンポーネント

| 要素 | Copy | Notes |
|------|------|-------|
| Modal aria-label | `{filename} のプレビュー` | dialog 全体 |
| Modal role | `dialog` + `aria-modal="true"` | focus trap 起点 |
| ヘッダー filename 表示 | `{filename}` | 重複情報は出さない |
| ヘッダー meta（kind=generated） | `✨ AI 生成 ・ {size} ・ {timestamp}` | 中黒区切り |
| ヘッダー meta（kind=user_upload） | `📎 添付 ・ {size} ・ {timestamp}` | 同上 |
| 「ダウンロード」CTA ラベル | `ダウンロード` | 最小限の動詞のみ |
| 「ダウンロード」CTA aria-label | `{filename} をダウンロード` | フルネーム |
| × 閉じる aria-label | `プレビューを閉じる` | スクリーンリーダー |
| × 閉じる title 属性 | `閉じる (Esc)` | キーボードヒント |
| キーボードヒント（footer、Claude's Discretion） | `Esc で閉じる` | footer 右下に薄く表示 |

### Empty / Error / Size-Cap States

| Element | Copy |
|---------|------|
| Empty state（チップ列に該当ファイルがない） | `AttachmentChipRow を描画しない`（DOM に出さない、Phase 36 と同方針） |
| Empty state（モーダル開いた瞬間のローディング） | `読み込み中...` + `--color-text-muted` の typing-dot アニメ |
| Error: 認可拒否（401） | `このファイルにはアクセスできません。再ログインしてからお試しください。` |
| Error: ファイル消失（404） | `このファイルは削除されたか、ストレージから取得できません。` |
| Error: フォーマット decode 失敗（CSV/MD のパースエラー） | `プレビューを表示できませんでした。ダウンロードして開いてください。` + 「ダウンロード」CTA（accent） |
| Error: ネットワーク失敗（fetch reject） | `ネットワークエラーで読み込めませんでした。時間を置いて再度お試しください。` |
| Size cap 超過案内（テキスト系 >1MB） | 見出し: `ファイルが大きすぎてプレビューできません` / 本文: `このファイルは {size} あります（プレビュー上限 1 MB）。ダウンロードして開いてください。` + 「ダウンロード」CTA（accent） |
| Size cap 超過案内（画像 >10MB） | 見出し: `画像が大きすぎてプレビューできません` / 本文: `この画像は {size} あります（プレビュー上限 10 MB）。ダウンロードして開いてください。` + 「ダウンロード」CTA |
| PDF / 非対応形式 | 見出し: `この形式はプレビューできません` / 本文: `{ext} 形式はプレビュー非対応です（{kind=generated ? "AI が生成しました" : "添付されました"}）。ダウンロードして閲覧してください。` + 「ダウンロード」CTA |
| CSV 行数上限（>1000 行） | preview 内の上部にバナー: `先頭 1000 行のみ表示しています（全 {n_rows} 行）。全データはダウンロードしてください。` + 「ダウンロード」CTA |

### Primary CTA

| Element | Copy |
|---------|------|
| Primary CTA（モーダル内） | `ダウンロード`（accent 背景 + accent-contrast 文字） |
| Primary CTA aria-label（モーダル内） | `{filename} をダウンロード` |

### Destructive Confirmation

| Action | Copy (message) | confirmLabel | 適用方法 |
|--------|---------------|--------------|---------|
| Modal 内 個別ファイル削除（× ボタン） | **Phase 38 scope 外** — 個別削除 UI は v6.1+ deferred（CONTEXT.md `<deferred>`） | N/A | — |
| Thread 削除時の `_generated/` 一括削除 | Phase 35 既存の ConfirmModal 経由 + Phase 37 D-03 の thread 削除 hook で `_generated/` も一括削除（透過的、UI 文言変更なし） | 既存維持 | — |

**Phase 38 では新規 destructive action を導入しない**（CONTEXT.md D-02: 個別削除 API は新設しない）。

---

## Component Contracts

### `<AttachmentChipRow>` kind 拡張（既存ファイル: `frontend/src/components/MessageArea.tsx` 内）

**変更内容:** Phase 36 で実装済の `AttachmentChipRow` 内部関数に以下の prop 追加と描画変更を施す。

**`AttachmentMeta` 型拡張（`frontend/src/types.ts` 内、本 SPEC の範囲外だが SPEC が前提とする型）:**
```ts
interface AttachmentMeta {
  // ... 既存フィールド
  kind: 'user_upload' | 'generated';   // 新規必須フィールド（CONTEXT.md D-06）
}
```

**DOM / レイアウト（kind による分岐）:**

画像チップ（kind=generated 例）:
```
┌──────────────┐
│ 48×48 image  │
│              │
│      ┌─────┐ │  ← 右下に micro-badge 絶対配置
│      │✨AI生成│ │     (kind=user_upload は📎 添付)
│      └─────┘ │
└──────────────┘
```

text/code チップ（kind=generated 例）:
```
[✨ AI 生成] [📄 result.csv  12 KB]   ← 横並び、gap: --space-1
```

**badge の絶対位置 (画像チップ):**
- 右下 absolute、`bottom: 2px; right: 2px`
- 高さ 18px、padding `2px var(--space-1)`、border-radius `var(--radius-sm)`
- font-caption 12px / weight 600
- 背景: kind に応じて `--color-accent-subtle` or `--color-surface-elevated`
- 文字色: kind に応じて `--color-accent` or `--color-text-muted`

**badge の inline 位置 (text/code チップ):**
- pill の最左、絵文字より前
- 高さ 18px、padding `2px var(--space-1)`、border-radius `var(--radius-sm)`
- 他は画像チップと同じ

**チップ全体のクリック挙動:**
- Phase 38 で **チップ全体がクリック可能なボタン要素になる**（モーダルを開く）
- `<button>` 要素にラップ、`aria-haspopup="dialog"`
- hover/focus: `outline: 1px solid var(--color-accent); outline-offset: 1px`（reserved-for #10）
- cursor: pointer
- Phase 36 の既存「画像チップ click 後の action: Claude's Discretion」が本 phase で確定 = モーダル開く

**× 削除ボタンの扱い:**
- bubble 内 chip は **削除ボタンなし**（Phase 36 既存、履歴は読み取り専用）
- staging チップ（InputBar `<AttachmentChips>`）の × は Phase 36 既存維持。Phase 38 では staging に generated ファイルは現れない（worker 出力なので post-process で一括 bundle される）。

**uploading / error 状態:**
- Phase 36 既存（uploading は staging 時のみ、bubble 内では出ない）
- bubble 内チップは「サーバー保存済」前提なので uploading 状態は描画しない

### `<AttachmentModal>` 新規コンポーネント

**ファイル:** `frontend/src/components/AttachmentModal.tsx`（新規）

**Props interface:**
```ts
interface AttachmentModalProps {
  threadId: string;
  attachment: AttachmentMeta;   // kind / storage_name / name / size / ext / mime_type を含む
  open: boolean;
  onClose: () => void;
}
```

**DOM 構造:**
```
<div role="dialog" aria-modal="true" aria-label="{filename} のプレビュー"
     class="attachment-modal-overlay">
  <div class="attachment-modal-dialog">
    <header class="attachment-modal-header">
      <div class="attachment-modal-title">{filename}</div>
      <div class="attachment-modal-meta">
        {✨ AI 生成 | 📎 添付} ・ {size} ・ {timestamp}
      </div>
      <div class="attachment-modal-actions">
        <a class="attachment-modal-download-btn" href={dl_url} download={filename}>
          ダウンロード
        </a>
        <button class="attachment-modal-close-btn" aria-label="プレビューを閉じる">×</button>
      </div>
    </header>
    <div class="attachment-modal-body">
      {renderer based on ext}
    </div>
  </div>
</div>
```

**Overlay:**
- 画面全体: `position: fixed; inset: 0; z-index: 100;`
- 背景: `rgba(0, 0, 0, 0.5)` 直書き許容（既存 ConfirmModal と同パターン）
- click で閉じる（dialog 外クリック）

**Dialog:**
- 中央寄せ: `display: flex; align-items: center; justify-content: center;`
- 最大寸法: `max-width: min(1024px, 90vw); max-height: 90vh;`
- 背景: `var(--color-surface-elevated)`
- 枠: `1px solid var(--color-border)`、`border-radius: var(--radius-lg)`（12px）
- overflow: `hidden`（内部 body 側で scroll を持つ）
- padding: なし（header / body 各々で持つ）

**Header (height: auto, 1 行 or 2 行):**
- padding: `var(--space-4)`（16px 全方向）
- border-bottom: `1px solid var(--color-border)`
- レイアウト: flex（filename を flex-grow、meta と actions を右寄せ）
- filename: `--font-label` 14px weight 600、truncate 1 行
- meta: `--font-caption` 12px `--color-text-muted`、中黒区切り
- actions: 「ダウンロード」CTA + × 閉じる、`gap: var(--space-3)`

**Body (flex-grow, overflow-y: auto):**
- padding: renderer により異なる（image は `var(--space-2)`、Markdown / CSV / Monaco は renderer 内で持つ or 0）
- max-height: `calc(90vh - {header-height})`
- 内側で scroll（外側 dialog は overflow: hidden）

**4 種 Renderer dispatch（mime_type / ext ベース、決定論的）:**

| 入力（ext lowercase） | mime_type ヒント | Renderer | Component / Library | Size cap |
|---------------------|------------------|----------|--------------------|----------|
| `png` / `jpg` / `jpeg` / `gif` / `webp` | `image/*` | `ImagePreview` | `<img>` raw bytes 直配信 | 10MB |
| `md` | `text/markdown` | `MarkdownPreview` | react-markdown + remark-gfm 直呼び（薄ラッパー） | 1MB |
| `csv` | `text/csv` | `CsvPreview` | `ChatAgGridTable` 流用 + CSV→`MarkdownTableData` 変換ヘルパー | 1MB |
| `txt` / `log` / `py` / `js` / `ts` / `tsx` / `jsx` / `json` / `yaml` / `yml` / `toml` / `sh` / `sql` / `html` / `css` / `xml` | `text/*` | `MonacoPreview` | `@monaco-editor/react` read-only、language は ext→Monaco language ID マッピング（既存 `MarkdownMessage.LANG_ALIASES` 流用） | 1MB |
| `pdf` | `application/pdf` | (なし) | フォールバック案内「PDF はプレビュー非対応です。ダウンロードして閲覧してください。」 | — |
| `html` | `text/html` | (なし) | 同上「HTML はプレビュー非対応です。」（Canvas との衝突回避） |  — |
| その他 | — | (なし) | 同上「{ext} 形式はプレビュー非対応です。」 | — |

**注意: `html` は上記の Monaco 対象に含めない**（D-12 で HTML は Canvas と衝突するため対象外）。

**ImagePreview:**
- `<img src={fetch_url} alt={filename} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />`
- raw bytes 直配信。サムネ生成しない（CONTEXT.md `<deferred>` 画像サムネ生成: やらない方針継承）。
- size cap: 10MB（Phase 36 IMAGE_MAX_BYTES と統一）。超過時は size cap 案内を表示。

**MarkdownPreview:**
- 1MB cap で fetch → text 取得 → `<ReactMarkdown remarkPlugins={[remarkGfm]}>` でレンダリング
- `MarkdownMessage.tsx` は **直接呼ばない**（Monaco code block / Mermaid 等の重い tree を含むため、preview 用には薄ラッパーが軽い — RESEARCH.md `Pitfall 7` 根拠）
- コンテナ: `padding: var(--space-4); --font-body; --color-text;`
- 内部 h1〜h6 は CSS で適度に縮小（既存 `.cs-message__custom-content` 系の縮約スタイルに準ずる薄い CSS を AttachmentModal 専用に追加）

**CsvPreview:**
- 1MB cap で fetch → text 取得 → CSV パーサ（split + 簡易 quote 処理、papaparse 不要 — RESEARCH.md `Standard Stack §6` 根拠）→ `MarkdownTableData` 形に整形（`{ headers: string[], rows: string[][] }`）
- `<ChatAgGridTable data={...} theme={...} />` をそのまま流用（lazy import）
- 行数上限: **UI 表示は先頭 1000 行**、超過時は preview 内 上部にバナー `先頭 1000 行のみ表示しています（全 {n_rows} 行）。全データはダウンロードしてください。`（ag-grid 自体は virtual scroll で 10k 行まで耐えるが、UX 整合性のため明示的に 1000 行 cap）
- size cap: 1MB（行数とは別。1MB 超は CSV パース前に弾く）

**MonacoPreview:**
- 1MB cap で fetch → text 取得 → Monaco read-only Editor で表示
- height: `calc(90vh - {header-height} - var(--space-4) * 2)` ≈ 70vh
- options: `readOnly: true, minimap: { enabled: false }, scrollBeyondLastLine: false, fontSize: 13, wordWrap: 'on'`
- language: ext から `LANG_ALIASES` 経由で Monaco language ID（既存 `MarkdownMessage.tsx` のテーブル流用）。未知 ext は `plaintext`。
- theme: `useCurrentTheme()` で `vs` / `vs-dark` 切替（既存パターン）

**Loading 状態:**
- fetch 中: body 中央に `読み込み中...` テキスト + typing-dot アニメ（Phase 35 既存パターン）
- 200ms 以下で完了する場合は表示しない（チラつき回避）

**Error 状態:**
- `--color-destructive` 1px 枠 + `--color-surface` 背景の banner を body 中央に表示
- 文言は §Copywriting Contract の Error states を使用

**Size-Cap 案内:**
- `--color-accent-subtle` 背景 + `--color-text` 本文 + `--color-accent` CTA の bordered card を body 中央に表示
- destructive ではない（D-14 / 36 D-18 同 spirit）
- CTA「ダウンロード」をクリックすると header の CTA と同じ URL に飛ぶ

**Keyboard / Focus 管理:**
- Esc キーで `onClose` 呼び出し
- Tab で `× 閉じる ↔ ダウンロード CTA ↔ body 内 focusable 要素` を循環（focus trap）
- 開いた瞬間に「× 閉じる」or「ダウンロード CTA」に focus（planner 判断、推奨は CTA）
- 閉じた後は元の chip にフォーカスを戻す（モーダルパターン標準）

**マウント / アンマウント:**
- `useEffect` で body の overflow を `hidden` にして背景スクロールを止める
- アンマウント時に元に戻す

### `useAttachments` hook 拡張（既存ファイル: `frontend/src/hooks/useAttachments.ts`）

本 SPEC は UI 側の決定のみを扱うが、planner / executor が consume できるよう以下を明示:

- 既存 `useAttachments` は staging（user input 側）専用なので、bubble 内表示には **使わない**
- bubble 内 `AttachmentChipRow` は `message.additional_kwargs.attachments`（型 `AttachmentMeta[]`、kind フィールド付き）を直接受け取る
- モーダルからの fetch URL ロジックは hook 化候補（`useAttachmentFetch`）—> planner 判断、最小実装なら AttachmentModal 内で直接 fetch でも OK

**URL 解決ルール（kind ベース、planner 確認用）:**

| kind | URL pattern |
|------|-------------|
| `user_upload` | `${API_BASE}/api/threads/{tid}/attachments/{storage_name}` （Phase 36 既存） |
| `generated` | `${API_BASE}/api/threads/{tid}/outputs/{name}` （Phase 38 新規、CONTEXT.md D-05） |

**Modal 内では kind に応じて URL を切り替える。** `attachment.kind` を if/switch で分岐させる薄い関数で十分。

---

## Interaction Contract

### チップクリック → モーダル開閉

| トリガー | 挙動 |
|---------|------|
| チップ click | モーダル open、対象 attachment を渡す |
| チップ keyboard Enter / Space | モーダル open（チップが `<button>` 要素なので default behavior） |
| Modal 内 Esc キー | モーダル close |
| Modal 外（overlay）click | モーダル close |
| Modal × 閉じる click | モーダル close |
| Modal 「ダウンロード」CTA click | `<a download>` の default behavior でブラウザがファイルを保存 — close しない（複数回 DL 可能） |
| Modal 内 keyboard Tab | focus trap で循環、外に出ない |

### 多重 modal 禁止

- 1 時点に開けるモーダルは 1 つだけ。ChatApp 側で modal state（`activeAttachment: AttachmentMeta | null`）を 1 個持つ。
- 別チップを click すると即時 swap（前の close → 新規 open）。confirm なし。

### 大きいファイルでのブラウザ DoS 防御（RESEARCH.md `Pitfall 7`）

- fetch 前に `attachment.size > cap` をチェック、超過時は fetch をスキップして size-cap 案内を表示
- 「ダウンロード」CTA は size cap に関係なく常に表示（DL は cap せず、サーバー側 `FileResponse` でストリーミング）
- text 系 1MB / 画像 10MB のキャップ理由は RESEARCH.md `Pitfall 7` / `Assumption A6` 参照

### Multi-user isolation の UX 表現

- 別 user JWT で fetch → サーバーが 401/404 を返す → モーダル内エラーバナー「このファイルにはアクセスできません」/「このファイルは削除されたか、ストレージから取得できません」を表示
- 「ダウンロード」CTA も同じく失敗するため、エラー時は CTA を disable + tooltip「アクセス権がありません」
- スレッドを別 user で開いた場合（v6.0 では起こらない想定だが防御）も同じパスでフォールバック

### Loading の即時性

- 200ms 以下で完了する fetch ではローディング表示を出さない（チラつき回避）
- 200ms 超: typing-dot + 「読み込み中...」を body 中央に表示

---

## Responsive Breakpoints

Phase 35 の 2 breakpoint を踏襲（`@media (max-width: 1024px)` / `@media (max-width: 767px)`）。

| Phase 38 要素 | Desktop | Tablet (≤1024px) | Mobile (≤767px) |
|--------------|---------|------------------|-----------------|
| `<AttachmentChipRow>` チップ列 | 横並び、flex-wrap | 同じ、tablet でも 1 行に収まらない場合は折り返し | 同じ、画面幅で 2 枚 / 行 程度 |
| Image chip micro-badge 位置 | 右下絶対配置 | 同じ | 同じ |
| text/code chip micro-badge 位置 | pill 左端 | 同じ | 同じ |
| `<AttachmentModal>` dialog 寸法 | `max-width: 1024px; max-height: 90vh` | `max-width: 90vw; max-height: 90vh` | `max-width: 100vw; max-height: 100vh; border-radius: 0`（full-screen 化） |
| `<AttachmentModal>` header layout | 1 行（filename / meta / actions 横並び） | 同じ | 2 行（上: filename、下: meta + actions） |
| `<AttachmentModal>` 「ダウンロード」CTA | inline button | 同じ | full-width block button at bottom |
| `<AttachmentModal>` × 閉じる hit area | 36×36 | 40×40 | 44×44（OS タップターゲット推奨） |
| Monaco preview height | `calc(90vh - 100px)` | 同じ | `calc(100vh - 120px)` |
| ImagePreview の maxWidth/Height | `100%` 各方向 | 同じ | 同じ |
| CSV preview ag-grid 行数 | 1000 行 cap、virtual scroll | 同じ | 同じ |

**モバイル固有対応:**
- Modal が full-screen 化するため overlay の rgba 背景は見えない（差分なし）
- × 閉じるは右上 absolute（44×44px hit area）、CTA は footer 固定

### +N more / collapse の判断

**結論: 採用しない。** flex-wrap で折り返しに任せる。

**理由:**
- 1 メッセージあたりの生成ファイル数は通常 1〜数件、執拗に大量生成するケースは tool 失敗のサイン（v6.1+ で GC 検討）
- Phase 36 の AttachmentChipRow も同方針で運用済み
- 「+N more」UI を入れると hover/click インタラクションが増えて UX 複雑度が上がる
- v6.1+ で観察次第、件数爆発が起きていれば導入を再検討（OUT-OF-SCOPE for v6.0）

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | — | not applicable（shadcn 未導入、Phase 35 で locked） |
| third-party registries | — | 宣言なし |

**判定:** Phase 35 D-01 で CSS custom properties が locked。新規 UI コンポーネントライブラリは導入しない。Safety Gate N/A。
**新規 npm パッケージもゼロ**（CONTEXT.md / RESEARCH.md で確認済）。

---

## Visual Accessibility Baseline

Phase 35 / 36 §Visual Accessibility Baseline を踏襲。本 phase で追加される新規・拡張コンポーネント要件:

| 項目 | 要件 |
|------|------|
| Focus ring | `<AttachmentChipRow>` チップ全体（hover / :focus-visible で 1px accent outline）、`<AttachmentModal>` × 閉じる・ダウンロード CTA に 2px outline `--color-accent`（Phase 35 と同 pattern） |
| キーボード操作 | チップは Enter / Space でモーダル open、Modal 内は Tab で focus trap、Esc で close |
| ARIA | `<AttachmentChipRow>` は `role="group"` + `aria-label="添付・AI 生成ファイル {n} 件"`、各チップは `<button>` 要素 + `aria-haspopup="dialog"` + `aria-label="{kind ラベル}: {filename}（{size}）"`。`<AttachmentModal>` は `role="dialog"` + `aria-modal="true"` + `aria-label="{filename} のプレビュー"` |
| Focus 管理 | Modal open 時は CTA か × 閉じるに focus 移動、close 時は元の chip に focus を戻す |
| Color contrast | すべて Phase 35 semantic token 経由のため WCAG AA（4.5:1）を継承。新規組み合わせ無し。kind=generated micro-badge は `--color-accent` × `--color-accent-subtle` のペアで AA 確認済（Phase 35 で検証済の組み合わせ） |
| Screen reader status | エラー時のバナーは `role="alert"`、Size-Cap 案内は `role="status"` + `aria-live="polite"` |
| 画像 preview の alt | `<img alt="{filename}">`（ファイル名を代替テキスト、`alt=""` にしない） |
| Reduced motion | `prefers-reduced-motion: reduce` 時は modal の fade-in/out アニメを無効化（Phase 35 既存方針継承） |

---

## File Inventory（参考 — planner が消費する）

**新規ファイル:**
- `frontend/src/components/AttachmentModal.tsx` — モーダル本体 + 4 種 renderer dispatch
- （任意分割）`frontend/src/components/preview/ImagePreview.tsx` / `MarkdownPreview.tsx` / `CsvPreview.tsx` / `MonacoPreview.tsx` — RESEARCH.md L288 のファイル構成案。**planner 判断で 1 ファイル or 5 ファイルに分割**。本 SPEC はインターフェースのみ確定、ファイル分割は executor 裁量。

**既存ファイル変更:**
- `frontend/src/components/MessageArea.tsx` — `AttachmentChipRow` 関数を kind 対応に拡張、チップを `<button>` 化、modal state（`useState<AttachmentMeta | null>`）と AttachmentModal の mount を bubble 表示と並列追加
- `frontend/src/types.ts` — `AttachmentMeta` に `kind: 'user_upload' | 'generated'` 必須フィールド追加
- `frontend/src/hooks/useAttachments.ts` — staging item は常に `kind: 'user_upload'` を埋め込む（既存 type 整合）
- `frontend/src/theme.css` — `chat-attach-chip-clickable:hover` 等の薄い CSS（planner が省略判断可、inline style で済むなら追加なし）

**変更されないファイル:**
- `frontend/src/components/MarkdownMessage.tsx` — D-13 により inline 描画はしないため、追加変更を入れない（CONTEXT.md `<decisions>` Claude's Discretion 明示）

---

## Phase 38 Checker Acceptance Criteria

gsd-ui-checker が本 SPEC を PASS とする基準:

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | 新規 CSS 変数がゼロ追加されている（全て Phase 35 token を参照） | `grep -E '^\s*--' frontend/src/theme.css` の `:root` ブロック内エントリ件数が Phase 36 完了時点と同じ |
| 2 | 新規 npm パッケージがゼロ追加されている | `git diff main -- frontend/package.json frontend/bun.lockb` で追加なしを確認 |
| 3 | `<AttachmentModal>` コンポーネントが存在し、4 種 renderer（image / markdown / csv / monaco-text）を内包する | `ls frontend/src/components/AttachmentModal.tsx` + grep で `ReactMarkdown` / `ChatAgGridTable` / `Editor`（Monaco）/ `<img` の 4 つすべてのヒット |
| 4 | `AttachmentMeta` に `kind: 'user_upload' \| 'generated'` フィールドが追加されている | `grep "kind:" frontend/src/types.ts` |
| 5 | `<AttachmentChipRow>` に kind による micro-badge 分岐が実装されている | `grep "AI 生成\|user_upload\|generated" frontend/src/components/MessageArea.tsx` |
| 6 | チップが `<button>` 要素化され、クリックで `<AttachmentModal>` を開く | `grep "<button" frontend/src/components/MessageArea.tsx` の AttachmentChipRow 周辺ヒット |
| 7 | accent reserved-for リストの 11 項目以外で `--color-accent` が直接使われていない | `grep -rn "var(--color-accent)" frontend/src/components/AttachmentModal.tsx frontend/src/components/MessageArea.tsx` の件数 ≦ 4（chip badge + chip hover ring + Modal CTA + size-cap CTA） |
| 8 | destructive 色は Modal 内 エラーバナーのみで使用（kind=generated badge には使われない） | `grep "destructive" frontend/src/components/AttachmentModal.tsx frontend/src/components/MessageArea.tsx` の件数を確認、AttachmentChipRow kind 分岐内に出現しないこと |
| 9 | Copywriting が日本語で、Phase 35/36 既存コピーと競合しない | grep `"AI 生成"` / `"添付"` / `"プレビューを閉じる"` / `"ダウンロード"` の存在 |
| 10 | Image preview の size cap が 10MB、text/CSV/Markdown の cap が 1MB に揃っている | grep `10 * 1024 * 1024` / `1024 * 1024` in `AttachmentModal.tsx` |
| 11 | CSV preview が `ChatAgGridTable` を流用している（重複実装なし） | grep `ChatAgGridTable` in `AttachmentModal.tsx` or preview/CsvPreview.tsx |
| 12 | Markdown preview が `MarkdownMessage` を呼ばず、react-markdown を直接呼んでいる | `grep "MarkdownMessage" frontend/src/components/AttachmentModal.tsx` が 0 件、かつ `import.*ReactMarkdown` がヒット |
| 13 | Monaco preview が read-only で、language ID を ext から正しくマップしている | `grep "readOnly: true" AttachmentModal.tsx`、`LANG_ALIASES` の参照 |
| 14 | Modal が role="dialog" + aria-modal="true"、Esc / overlay click / × で close する | `grep 'role="dialog"\|aria-modal\|onKeyDown.*Escape' AttachmentModal.tsx` |
| 15 | Focus trap が実装されている（Modal 内 Tab で循環、外に出ない） | コードレビューで focus trap の実装確認、または Chrome DevTools MCP で挙動再現 |
| 16 | ダークモード（`[data-theme="dark"]`）で Modal・preview 4 種 がコントラスト破綻しない | Chrome DevTools MCP で data-theme 切替目視、特に Monaco theme と ag-grid theme |
| 17 | モバイル幅（375px）で Modal が full-screen 化、CTA が full-width block 化 | Chrome DevTools MCP で 375×667 確認 |
| 18 | 別 user JWT で fetch → 401/404 時にモーダル内エラーバナーが表示される | smoke test または manual operation check |
| 19 | サイズ超過時（>1MB text / >10MB image）に size-cap 案内 + DL CTA が表示される | manual operation check |
| 20 | PDF や非対応形式は preview せずフォールバック案内 + DL CTA が表示される | manual operation check |
| 21 | URL 解決が kind に応じて `/attachments/` か `/outputs/` に正しく分岐する | grep `kind === 'generated'\|kind === "user_upload"` の URL ロジック確認 |
| 22 | chip 全体がクリック可能で、aria-haspopup="dialog" が設定されている | `grep 'aria-haspopup="dialog"' MessageArea.tsx` |

---

## Out-of-Scope Reaffirmation（v6.1+ で再検討）

本 SPEC では以下を **意図的に扱わない**（CONTEXT.md `<deferred>` と整合、UI 観点で再宣言）:

- 横断「My Files」画面 / Header dropdown
- 個別ファイル削除 UI（Modal 内に削除ボタンを置かない）
- PDF プレビュー（pdf.js / iframe）
- HTML プレビュー（Canvas との衝突）
- 画像サムネ生成（raw bytes 直配信のまま）
- AI 応答テキスト内 inline 描画（Markdown `![](...)` 経路、`session-state/files/...` パスの自動解決）
- 「+N more」collapse UI（flex-wrap で対応）
- AI 生成完了時の toast / 通知
- CSV 行数完全表示 / 大規模 (>10000 行) サポート
- generated ファイルの個別 DL の analytics
- staging 時に generated kind が混在する UX（worker 後付け bundle のみ想定）

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: 日本語統一、AttachmentModal / AttachmentChipRow kind ラベル / Error / Size-Cap / 非対応形式 すべて定義済み
- [ ] Dimension 2 Visuals: AttachmentChipRow kind 拡張 + AttachmentModal + 4 renderer の視覚仕様完備
- [ ] Dimension 3 Color: 60/30/10 維持、accent reserved-for リスト 11 項目に拡張、destructive 5 箇所明示（4 既存 + 1 新規 Modal エラーバナー）
- [ ] Dimension 4 Typography: Phase 35 の 5 役を追加なしで運用、weight オーバーライドは 2 箇所（micro-badge / Modal filename）
- [ ] Dimension 5 Spacing: 8-point scale 踏襲、新規 token なし、0.5 段例外（2px）は micro-badge 縦 padding のみで明示
- [ ] Dimension 6 Registry Safety: N/A（shadcn 未導入、third-party なし、新規 npm dep ゼロ）

**Approval:** pending
