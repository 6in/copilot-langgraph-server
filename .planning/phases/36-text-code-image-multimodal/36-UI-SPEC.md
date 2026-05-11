---
phase: 36
slug: text-code-image-multimodal
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-23
inherits_from: 35-UI-SPEC.md
---

# Phase 36 — UI Design Contract

> ファイル入力（text/code + image multimodal）フェーズの UI 契約。
> gsd-ui-researcher が作成、gsd-ui-checker が検証する。
> 本 SPEC は **Phase 35 UI-SPEC の増分仕様** として運用する（Phase 35 Handoff Contract §1〜§10 を満たした土台の上に、FIN-01 / FIN-02 が必要とする UI コンポーネントだけを増分で定義する）。
> 本契約は gsd-planner が `<AttachmentButton>` / `<AttachmentChips>` / `<VisionWarningBanner>` / MessageArea bubble 内チップ / Header model selector の vision flag 表示タスクに変換する際の「確定済み決定事項」として消費される。

**対象要件:** FIN-01（text/code 添付 → LLM 参照）、FIN-02（画像 multimodal 添付 + graceful fallback）
**依存元契約:** `.planning/phases/35-dashboard-design-system/35-UI-SPEC.md` の §Token Naming / §Typography / §Color / §Spacing / §InputBar Contract / §Phase 36 Handoff Contract すべて

---

## Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none（CSS custom properties on `:root` + `[data-theme="dark"]`、Phase 35 D-01 で locked） | 35-UI-SPEC §Design System |
| Preset | not applicable | — |
| Component library | `@chatscope/chat-ui-kit-react@^2.1.1`（既存維持、override は CSS 変数経由） | package.json |
| Icon library | 絵文字のみ（📎 / 🖼 / 📄 / ⚠ / × / 🗑）— 新規アイコンライブラリは導入しない | Phase 35 踏襲 |
| Font | システム default + `Rajdhani`（タイトル専用） | Phase 35 踏襲 |
| shadcn ゲート判定 | **N/A** — Phase 35 CONTEXT.md D-01 の "CSS custom properties locked" が継続。shadcn 導入は scope 外 | 35-UI-SPEC §Design System |
| Theme 切替機構 | `<html data-theme="dark">` 属性（既存維持） | 35-UI-SPEC §Design System |
| 新規トークン追加 | **なし** — Phase 35 が定義した token で全要素を表現する契約 | 本 SPEC §Token Reuse Contract |

---

## Token Reuse Contract

Phase 36 は **Phase 35 の既存 token を参照するのみ** で、新規 CSS 変数は追加しない。
新規追加を認める数少ない例外は、添付 chip のサムネ寸法・upload バッジなどピクセル単位の "マジックナンバー" を定義するためのローカル const（TS 側 `ATTACHMENT_THUMB_SIZE = 48` 等）で、CSS 変数化はしない（グローバル namespace 汚染を避ける）。

| Phase 36 要素 | 参照する Phase 35 token | Usage |
|--------------|------------------------|-------|
| `<AttachmentButton>` 通常時 | `--color-text-muted` | 📎 絵文字色 |
| `<AttachmentButton>` hover / active | `--color-accent` | accent reserved-for リストに "📎 フォーカス/hover" を本 SPEC §Accent Reserved-For Extension で追加 |
| `<AttachmentButton>` :focus-visible | `--color-accent` + 2px outline | Phase 35 §Visual Accessibility Baseline 踏襲 |
| `<AttachmentChips>` chip 枠線 | `--color-border` | pill 境界 |
| `<AttachmentChips>` chip 背景 | `--color-surface` | chip 内地色 |
| `<AttachmentChips>` chip 文字 | `--color-text` | ファイル名 |
| `<AttachmentChips>` chip サイズ / 日時 | `--color-text-muted` + `--font-caption` | 補助情報 |
| `<AttachmentChips>` × 削除ボタン通常 | `--color-text-muted` | 非強調 |
| `<AttachmentChips>` × 削除ボタン hover | `--color-destructive` | ThreadSidebar 削除ボタンと同 pattern（Phase 35 既存） |
| `<AttachmentChips>` 画像サムネ枠 | `--color-border` + `--radius-md` | 48×48 枠 |
| `<AttachmentChips>` 画像サムネ error 時 | `--color-destructive` 枠 | 読み込み失敗オーバーレイ |
| `<AttachmentChips>` uploading バッジ | `--color-text-muted` + animation | 8×8 円形 spinner |
| `<VisionWarningBanner>` 背景 | `--color-accent-subtle` | 非 destructive（仕様上 "エラー" ではなく "案内"） |
| `<VisionWarningBanner>` 文字 | `--color-text` | 本文 |
| `<VisionWarningBanner>` "切り替える" CTA | `--color-accent` + `--color-accent-contrast` | 本 SPEC §Accent Reserved-For Extension |
| `<VisionWarningBanner>` 枠 | `--color-accent` 1px 左 border（左端 3px アクセントバー） | active thread item と同 pattern（Phase 35 reserved-for #4） |
| Bubble 内 AttachmentChipRow 画像サムネ | `--color-border` + `--radius-md` | 48×48、履歴 |
| Bubble 内 AttachmentChipRow text/code pill | `--color-surface-elevated` + `--color-border` | 非強調 pill |
| Bubble 内 AttachmentChipRow テキスト | `--color-text-muted` + `--font-caption` | 履歴情報 |
| Drop zone overlay 背景 | `--color-accent-subtle` + `--color-accent` 2px dashed border | drag-over 時のみ表示（Phase 35 §Visual Accessibility Baseline focus-ring と同 accent） |
| Drop zone overlay テキスト | `--color-text` + `--font-heading` | 「ファイルをドロップ」 |
| エラーバナー（upload 失敗・サイズ超過） | `--color-destructive` 枠 + `--color-surface` 背景 | Phase 35 §Copywriting Contract Error State と同 pattern |

**非許容の新規トークン:**
- `--color-upload-*` / `--color-warning-*` / `--color-image-placeholder-*` などを作らない。既存 semantic token の合成で表現する。
- `--space-attachment-thumb` のような用途固有 spacing も作らない。`--space-2` (8px) / `--space-3` (12px) の合成で表現する。

---

## Accent Reserved-For Extension

Phase 35 §Color §Accent reserved-for リストに以下 2 項目を **追加** する（既存 7 項目は維持）。

| # | 追加される用途 | 根拠 |
|---|---------------|------|
| 8 | `<AttachmentButton>` の hover / active / :focus-visible 時の色（📎 絵文字色 + focus ring） | CTA 相当の primary action、accent 10% 配分の範囲内 |
| 9 | `<VisionWarningBanner>` の "切り替える" ワンクリック CTA（CTA 背景と左端 3px アクセントバー） | モデル切替という primary action、accent 10% 配分の範囲内。destructive 色は使わない（D-18 graceful fallback の方針により、画像非対応は「エラー」ではなく「案内」） |

**accent 10% 予算の再確認:**
本 phase で追加される accent 使用箇所は「📎 と警告バナー CTA」の 2 種のみで、同時表示されるのは通常 1 箇所（InputBar 下半分に 📎 か、上部に警告バナーか）。画面全体の accent 占有面積は Phase 35 の Send ボタン・New Chat ボタン・focus ring と合算しても 10% 以内に収まる。

**accent 予算外の ref-check:**
- 「添付チップ全面 accent 塗り」→ 使ってはいけない（Phase 35 §Color 禁止リスト「カード全面塗り潰し」に該当）
- 「uploading 状態のプログレス塗り」→ `--color-text-muted` で表現、accent を使わない

---

## Spacing Scale

Phase 35 の 8-point scale をそのまま使う。**新規 token 追加なし。**

| Phase 36 要素 | 使用する Phase 35 token |
|--------------|------------------------|
| `<AttachmentButton>` ボタン内 padding | `--space-2`（8px）左右・上下 |
| `<AttachmentButton>` 絵文字と ghost テキストの gap | `--space-1`（4px） |
| `<AttachmentChips>` chip 間 gap | `--space-2`（8px） |
| `<AttachmentChips>` chip 内 padding | `--space-2 --space-3`（8/12px） |
| `<AttachmentChips>` previewSlot 内側 padding | Phase 35 InputBar 既存（`8px 12px` = `--space-2 --space-3`） |
| `<VisionWarningBanner>` 内側 padding | `--space-3 --space-4`（12/16px） |
| `<VisionWarningBanner>` アイコン⇔テキスト gap | `--space-2`（8px） |
| `<VisionWarningBanner>` CTA 左 margin | `--space-3`（12px） |
| Bubble 内 AttachmentChipRow 上 margin（bubble 本文と区切り） | `--space-2`（8px） |
| Bubble 内 AttachmentChipRow chip 間 gap | `--space-2`（8px） |
| Drop zone overlay padding | `--space-6`（24px）全方向 |

**タップターゲット最低値:**
Phase 35 の 36px / tablet 40px を踏襲。`<AttachmentButton>` の DOM サイズは 36×36px（desktop）、tablet 以下 40×40px。アイコン自体は 20px、周囲に invisible hit area を確保。`<AttachmentChips>` の × 削除ボタンも 20×20px アイコン + 28×28px hit area を持つ。

**chip / サムネの固定寸法（CSS 変数化せずコンポーネント内 const で持つ）:**

| 要素 | 寸法 | Rationale |
|------|------|-----------|
| 画像サムネ（InputBar previewSlot 内） | 48×48px | Phase 36 CONTEXT.md D-05 の "48 or 64" のうち小さい方。タブレット幅でも 5 枚並びで overflow しない |
| 画像サムネ（Bubble 内履歴） | 48×48px | InputBar と統一、CONTEXT.md D-21 準拠 |
| text/code pill 高さ | 28px | Phase 35 label font-size 14px + `--space-2 * 2` 上下 padding で自然サイズ |
| 画像サムネ × 削除ボタン | 16×16px（icon）/ 20×20px（hit area） | サムネ右上 overlay、サムネ面積の 40% 以下 |

---

## Typography

Phase 35 の 5 役（body / label / heading / display / caption）をそのまま使う。**新規 font-role 追加なし。**

| Phase 36 要素 | 使用する Phase 35 役 |
|--------------|--------------------|
| `<AttachmentButton>` ラベル（スクリーンリーダー用の visually-hidden テキスト「ファイルを添付」） | `--font-label`（14px/1.4） |
| `<AttachmentChips>` ファイル名 | `--font-label`（14px/1.4）、truncate (ellipsis) 1 行 |
| `<AttachmentChips>` サイズ表示（例: `2.4 KB`） | `--font-caption`（12px/1.4） |
| `<VisionWarningBanner>` 見出し「画像非対応モデル」 | `--font-label`（14px/1.4）weight を 600 にオーバーライド |
| `<VisionWarningBanner>` 本文 | `--font-label`（14px/1.4） |
| `<VisionWarningBanner>` CTA「切り替える」 | `--font-label`（14px/1.4） |
| Bubble 内 AttachmentChipRow ファイル名 | `--font-caption`（12px/1.4）— 履歴表示はサイズを抑えてメッセージ本文より弱める |
| Drop zone overlay 見出し | `--font-heading`（20px/1.3） |
| Drop zone overlay 補助説明 | `--font-label`（14px/1.4） |

**line-height の堅持:**
- body 1.5 / label 1.4 / heading 1.3 / caption 1.4（Phase 35 定義を変更しない）
- サムネ画像と文字を並べる場合、line-height の差で縦方向の重心がズレないよう flex `align-items: center` で揃える

**weight オーバーライドルール:**
Phase 35 の定義は label=400 / heading=600 / display=700 / body=400 / caption=400 のみ。本 phase で唯一認めるオーバーライドは `<VisionWarningBanner>` 見出しの weight 600（label サイズのまま bold で強調）。新規 `--font-label-bold` 変数は作らず、コンポーネント内 inline style で `fontWeight: 600` を付与する。

---

## Color (60/30/10 契約)

Phase 35 の 60/30/10 split を完全踏襲。`--color-bg` 60% / `--color-surface` 30% / `--color-accent` 10%。

### accent reserved-for 統合リスト（Phase 35 の 7 項目 + Phase 36 の 2 項目 = 9 項目）

**Phase 35 既存（再掲、変更なし）:**
1. Send ボタン背景（InputBar）
2. New Chat ボタン背景（ThreadSidebar）
3. textarea / filter input の `:focus` ring
4. active thread item の左 3px アクセントボーダー（tablet 以降）
5. ダッシュボードカード `:hover` / focus ring
6. "Orochi Chat" タイトルのグラデーション
7. AuthPanel の link

**Phase 36 追加（2 項目）:**
8. `<AttachmentButton>`（📎 絵文字の hover / active / :focus-visible 色）
9. `<VisionWarningBanner>`（CTA 背景 + 左端 3px アクセントバー）

**9 項目以外で accent を使ってはいけない。**

### Destructive 使用箇所（Phase 35 踏襲 + 本 phase 追加）

| 箇所 | 用途 | 根拠 |
|------|------|------|
| `<AttachmentChips>` × 削除ボタンの hover 色 | 削除 hint | Phase 35 sidebar-thread-delete-btn hover と同 pattern |
| 画像サムネ error 時の枠 | 読み込み失敗シグナル | destructive 色は「エラーを示す」用途 |
| Upload failed エラーバナー枠 | エラー state | Phase 35 §Copywriting Contract Error State 同 pattern |
| サイズ超過 413 エラー時のチップ赤枠 | size 制限違反の視覚 | 同上 |
| Upload progress エラー overlay | 部分失敗の視覚 | 同上 |

**vision 非対応 banner は destructive を使わない**（D-18 graceful fallback の方針：エラーではなく案内）。

### 画像サムネの placeholder / 欠損状態

- サムネ読み込み中: `--color-surface-elevated` の単色塗りに中央 spinner（`--color-text-muted` 色、8×8px 円形 animation、Phase 35 typing-dot パターン流用）
- サムネ読み込み失敗: `--color-destructive` 1px 枠 + 絵文字 `🖼` 中央配置（`--color-text-muted`）
- ファイル削除後: チップ全体が fade-out（200ms opacity transition）してから unmount

---

## Copywriting Contract

全て日本語（CLAUDE.md 規約）。Phase 35 の copy を壊さず **追加のみ**。

### `<AttachmentButton>`

| 要素 | Copy | Notes |
|------|------|-------|
| aria-label | `ファイルを添付` | スクリーンリーダー / tooltip |
| title 属性（hover tooltip） | `ファイルを添付（最大 100MB / 画像は 10MB × 5 枚まで）` | D-01 / D-02 を簡潔に併記 |
| disabled 時 aria-label | `添付を追加できません（送信中）` | isThinking / disabled 時 |
| hidden label（visually-hidden span） | `ファイルを添付` | a11y の冗長化 |

### `<AttachmentChips>`

| 要素 | Copy | Notes |
|------|------|-------|
| 画像 chip aria-label | `画像: {filename}（{size}）。削除ボタン付き。` | スクリーンリーダー |
| text/code chip aria-label | `ファイル: {filename}（{size}）。削除ボタン付き。` | 同上 |
| × 削除ボタン aria-label | `{filename} を添付から削除` | 同上 |
| uploading 状態テキスト（visually-hidden） | `アップロード中` | 8×8 spinner に付随 |
| uploading 状態 title tooltip | `{percent}% アップロード中` | progress 値があれば（Claude's Discretion） |
| error 状態 tooltip | `アップロード失敗: {reason}。クリックで再試行` | Claude's Discretion — retry UX の採否は planner 判断 |
| サイズ表示フォーマット | `{n} KB` / `{n.n} MB` | 1024 ベース、1 桁小数で丸める |

### `<VisionWarningBanner>`（D-17）

| 要素 | Copy | Notes |
|------|------|-------|
| 見出し | `画像非対応モデル` | 14px weight 600 |
| 本文 | `現在のモデル（{current_model}）は画像を読めません。` | {current_model} は Header から伝達 |
| 本文 2（推奨案内） | `画像対応モデル（例: {suggested_model}）に切り替えると画像付きで送信できます。` | {suggested_model} は `/api/models` の `vision: true` 先頭候補（Header と共通） |
| CTA ボタンラベル | `{suggested_model} に切り替える` | ボタン幅を抑えるため短縮形: `モデル切替` も許容（planner 判断） |
| CTA aria-label | `モデルを {suggested_model} に切り替える` | フルネーム |
| 閉じる × ボタン aria-label | `この案内を閉じる` | 手動 dismiss も可（staging 中は再表示） |

### `<InputBar>` Drop zone（D-04）

| 要素 | Copy | Notes |
|------|------|-------|
| drag-over 時の overlay 見出し | `ファイルをドロップして添付` | 20px heading |
| drag-over 時の overlay 補足 | `テキスト・コード・画像（PNG / JPG / WebP）に対応` | 14px label |
| テキスト貼り付け時の透明 toast（Claude's Discretion） | `画像を貼り付けました` | paste 成功フィードバック — 採否は planner 判断、採用時のみ使用 |

### Bubble 内 AttachmentChipRow（D-21）

| 要素 | Copy | Notes |
|------|------|-------|
| chip row 全体 aria-label | `添付ファイル {n} 件` | スクリーンリーダー |
| 画像 chip tooltip | `{filename}（{size}）` | hover で表示 |
| text/code chip tooltip | `{filename}（{size}）` | 同上 |
| 画像 chip click 後の action | Claude's Discretion（modal zoom / download / 何もしない） | planner 判断 |
| text/code chip click 後の action | Claude's Discretion（modal preview / download / 何もしない） | planner 判断 |

### Primary CTA / Empty / Error State

| Element | Copy |
|---------|------|
| Primary CTA（本 phase が新規追加） | `送信`（既存 Phase 35 の InputBar Send ボタンそのまま、attachments が staging されていても同一ラベル — attachments 数 badge を付けない） |
| Empty state（staging が空の InputBar） | `previewSlot を描画しない`（Phase 35 の "空なら帯を出さない" 契約を踏襲、新規コピー不要） |
| Empty state（history bubble に添付がない） | `AttachmentChipRow を描画しない`（DOM に出さない、新規コピー不要） |
| Error state（upload 失敗） | `{filename} をアップロードできませんでした。もう一度お試しください。` |
| Error state（100MB 超過） | `{filename} は 100 MB を超えるため添付できません。` |
| Error state（10MB 超過、画像） | `{filename} は 10 MB を超えるため添付できません。` |
| Error state（5 枚超過） | `画像は 1 メッセージあたり 5 枚までです。` |
| Error state（未対応拡張子） | `{ext} 形式は対応していません。対応形式: PNG / JPG / WebP / テキスト・コード系。` |
| Error state（delete 失敗） | `{filename} の削除に失敗しました。時間を置いて再度お試しください。` |
| Error state（models 取得失敗、Header fallback） | （ハードコードされた従来 MODEL_OPTIONS を fallback として使用、ユーザー向け表示は無し） |

### Destructive Confirmation

| Action | Copy (message) | confirmLabel | 適用方法 |
|--------|---------------|--------------|---------|
| Upload 中キャンセル（× クリック） | **確認ダイアログ不要** — staging は「送信前の仮領域」という UX 契約、× で即削除 | N/A | D-06 ケース D（手動削除）は即時反映 |
| Bubble 内 attachment chip click → 削除 | **Phase 36 scope 外** — 履歴からの削除 UX は未定義（Claude's Discretion で planner が決める、範囲外なら実装しない） | N/A | — |
| Thread 削除時の一括削除 | Phase 35 既存の ConfirmModal 経由、本 phase で変更なし | 既存維持 | — |

**Phase 36 では新規 destructive action は導入しない**（D-06 で定めた通り、ケース A: ユーザー明示キャンセル・ケース D: × ボタン手動削除 の両方とも確認なしで即削除）。

---

## Component Contracts

### `<AttachmentButton>`（新規、`InputBar.toolbarSlot` に差し込む）

**ファイル:** `frontend/src/components/AttachmentButton.tsx`（新規）

**Props interface:**
```ts
interface AttachmentButtonProps {
  onFilesSelected: (files: File[]) => void;  // staging hook に流す
  disabled?: boolean;                         // isThinking 時 true
  maxFiles?: number;                          // デフォルト制限なし、D-02 画像 5 枚は呼び出し側で enforce
  acceptedExtensions?: string[];              // HTML accept 属性（例: '.txt,.md,.json,.csv,.py,.js,.png,.jpg,.jpeg,.webp'）
}
```

**DOM / レイアウト:**
```
<button aria-label="ファイルを添付" class="chat-attach-btn">
  <span aria-hidden="true">📎</span>
  <input type="file" multiple hidden ref={fileInputRef} accept={...} onChange={...} />
</button>
```
- `button` は `height: 36px; width: 36px; border-radius: var(--radius-md)`、tablet 以下は 40×40。
- hover / :focus-visible で `color: var(--color-accent)` を適用（通常は `color: var(--color-text-muted)`）
- disabled 時は opacity 0.5、cursor: not-allowed
- `input[type="file"]` はクリックされると OS ファイラを開く。選択後 `onFilesSelected(Array.from(e.target.files))` を呼び、後で reset（同名ファイル再添付のため `e.target.value = ''`）

**Drop zone 拡張:**
本 button 自体は drop target ではない。drop は `<InputBar>` および `<MessageArea>` 全体が受ける（D-04）。button は click 専用。

### `<AttachmentChips>`（新規、`InputBar.previewSlot` に差し込む）

**ファイル:** `frontend/src/components/AttachmentChips.tsx`（新規）

**Props interface:**
```ts
interface AttachmentChipsProps {
  items: StagingItem[];  // useAttachments.ts の staging state
  onRemove: (localId: string) => void;
  onRetry?: (localId: string) => void;  // error 状態の再試行（Claude's Discretion）
}
```

**レイアウト（横スクロール許容、`overflow-x: auto` は InputBar previewSlot 既存）:**
```
┌─ previewSlot (padding: 8px 12px, max-height: 120px, overflow-y: auto) ─┐
│  [🖼 48×48] [🖼 48×48] [📄 foo.py 2.4 KB ×] [📄 data.csv 12 KB ×]    │
└────────────────────────────────────────────────────────────────────────┘
```

**画像 chip 仕様:**
- 48×48px square
- `<img src="/api/threads/{tid}/attachments/{storage_name}" ...>` で直接表示（D-23、サムネ生成なし）
- 右上に × 削除ボタン（16×16 icon、20×20 hit area）を absolute 配置
- uploading 中: 半透明（opacity 0.5）+ 中央に 8×8 spinner（typing-dot パターン流用）
- error 時: 1px `--color-destructive` 枠、絵文字 `🖼` プレースホルダ
- 複数枚時は `display: flex; gap: var(--space-2);`、5 枚目以降は drop validation で拒否されるので常に 0〜5

**text/code chip 仕様:**
- pill 形（`border-radius: var(--radius-full)`）
- 高さ 28px、横幅は内容に合わせる（max-width 240px、超過時 `text-overflow: ellipsis`）
- `[📄 {filename} {size} ×]` の横並び（gap: 4px = `--space-1`）
- 絵文字 `📄`（14px）+ filename（`--font-label` 14px）+ size（`--font-caption` 12px `--color-text-muted`）+ × 削除ボタン
- uploading 中: 左端にインライン spinner 追加（絵文字を🔄に置換も可、Claude's Discretion）

**× 削除ボタン仕様（両 chip 共通）:**
- 通常: `color: var(--color-text-muted)`
- hover: `color: var(--color-destructive)`
- :focus-visible: 2px outline `var(--color-accent)`
- aria-label: `{filename} を添付から削除`

### `<VisionWarningBanner>`（新規、`<InputBar>` の上、`previewSlot` のさらに上に配置）

**ファイル:** `frontend/src/components/VisionWarningBanner.tsx`（新規）

**Props interface:**
```ts
interface VisionWarningBannerProps {
  currentModel: string;              // Header で選択中のモデル ID
  suggestedModel: string;             // /api/models の vision:true 先頭候補
  onSwitchModel: () => void;          // ワンクリック切替
  onDismiss?: () => void;             // 手動 × で閉じる（staging 中に画像が残っていれば次回再表示）
}
```

**表示条件:**
- `(selectedModel の vision === false) && (staging に画像 chip が 1 件以上)` の両方が true
- staging に画像が 0 件になるか、vision: true モデルに切り替わると自動で unmount

**レイアウト:**
```
┌─ 3px accent bar ─┬─ 12px 16px padding ──────────────────────────────┐
│                  │  ⚠  画像非対応モデル                                 │
│                  │     現在のモデル（gpt-4.1）は画像を読めません。        │
│                  │     画像対応モデル（例: claude-sonnet-4.6）に切り替え │
│                  │     ると画像付きで送信できます。                       │
│                  │     [claude-sonnet-4.6 に切り替える]   × 閉じる     │
└──────────────────┴─────────────────────────────────────────────────┘
```
- 左端 3px 縦バー: `background: var(--color-accent)` + `flex-shrink: 0`（Phase 35 active thread item と同 pattern）
- 本体背景: `var(--color-accent-subtle)`
- テキスト: `color: var(--color-text)`
- CTA ボタン: accent 背景 + accent-contrast 文字、`padding: var(--space-2) var(--space-3)`、`border-radius: var(--radius-md)`
- × 閉じる: 透明背景 + `--color-text-muted`、hover で `--color-text`

**InputBar 内の配置順序（上から）:**
```
┌────────────────────────────┐
│ VisionWarningBanner (条件付き) │  ← 本 phase 新規追加
├────────────────────────────┤
│ copyAllSlot                │  ← Phase 35 既存
├────────────────────────────┤
│ previewSlot (= AttachmentChips) │  ← 本 phase で埋まる
├────────────────────────────┤
│ toolbarSlot (= AttachmentButton) + textarea + AskMe + Send │  ← 本 phase で toolbar 埋まる
└────────────────────────────┘
```

**InputBar 側への変更:**
- 既存 `InputBarProps` に `warningSlot?: React.ReactNode` を **追加** する（`previewSlot` のさらに上に配置する named slot）
- warningSlot が undefined なら帯を出さない（既存 slot の挙動と同じ）
- `warningSlot` / `copyAllSlot` / `previewSlot` の 3 帯はすべて空許容、空なら DOM に出さない

### MessageArea Bubble 内 `<AttachmentChipRow>`（D-21）

**配置:** `MessageArea.tsx` の bubble 本文末尾（既存 markdown / code block render の後）

**DOM:**
```
┌─────────────────────────────┐
│ (user avatar)               │
│ これを解析してください       │  ← bubble 本文（既存）
│ ─────────────────────────── │  ← 区切り（border-top 1px var(--color-border) opacity 0.5）
│ [🖼 48×48] [📄 data.csv]    │  ← 添付チップ行（新規）
└─────────────────────────────┘
```

**仕様:**
- bubble の `additional_kwargs.attachments` が空なら DOM に出さない
- 画像チップ: 48×48px の `<img>` タグで直接表示（D-23 / `--color-border` 枠 + `--radius-md`）
- text/code チップ: InputBar previewSlot と同じ pill 形（削除 × なし、click アクションは Claude's Discretion）
- `gap: var(--space-2)`、`margin-top: var(--space-2)`、`padding-top: var(--space-2)`
- role="group" + aria-label="添付ファイル {n} 件"

**差分（InputBar previewSlot との違い）:**
- 削除 × ボタンなし（履歴は読み取り専用）
- uploading / error 状態なし（履歴はサーバー保存済み）
- 画像クリック時の zoom modal は Claude's Discretion（planner 判断で最小実装 or 非実装）

### Header の Model Selector 変更（`frontend/src/components/Header.tsx`）

**既存:**
- `MODEL_OPTIONS` 定数（line 22-41）がハードコードされた `{id, label}` 配列
- `<select>` で選択、onChange で `setSelectedModel`

**Phase 36 での変更:**
- `useModels()` hook（新規、`/api/models` から取得 + 1h TTL キャッシュ）からモデル一覧を取得
- 既存 `MODEL_OPTIONS` は **fallback** として残す（`/api/models` が 500 / timeout / 未認証時に使用）
- 各 `<option>` の後ろに vision インジケーター絵文字を付与: `vision: true` → ラベル末尾に `🖼`、false → 無印
  - 例: `GPT-4.1` → そのまま、`Claude Sonnet 4.6 🖼`
- select の aria-label を `モデル選択（現在: {selectedModelName}、画像{対応/非対応}）` に更新

**視覚設計:**
- select box の見た目は Phase 35 既存踏襲（変更なし）
- 🖼 絵文字は Phase 35 font-label サイズで inline 表示、色調整不要（絵文字の native カラー維持）

**responsive:**
- Phase 35 §Responsive で `header-model-label { display: none }` が tablet 以下で適用される（"Model:" テキストの非表示）。本 phase で追加変更なし（select 自体は表示継続）。

---

## Interaction Contract

### D-04: 3 種の staging 入り口

| 入力経路 | トリガー | Phase 36 の受け口 |
|---------|---------|------------------|
| 📎 ボタンクリック | `<AttachmentButton>` click → 隠し input[type=file] click | `onFilesSelected(files)` → staging hook |
| Drag & Drop | `<InputBar>` と `<MessageArea>` の両 DOM で dragover / drop を listener | `onDrop` で `e.dataTransfer.files` を staging hook に流す |
| Ctrl+V / Cmd+V paste | textarea focus 中の paste event で clipboardData.items から image/* blob | `onPaste` で `item.getAsFile()` を staging hook に流す |

**drag-over 時の visual feedback:**
- InputBar / MessageArea の外枠に `outline: 2px dashed var(--color-accent)` を overlay として表示
- overlay 内中央に "ファイルをドロップして添付" 見出し（heading 20px）+ "テキスト・コード・画像（PNG / JPG / WebP）に対応" 補足（label 14px）
- overlay 背景は `background: var(--color-accent-subtle)` + opacity 0.9
- drop 完了または dragleave で即時 unmount

**Paste 成功フィードバック:**
画像 paste 後にチップが表示されるので即時 visible feedback になっている。追加の toast / flash は Claude's Discretion（planner 判断で採否を決める、採用時は `--color-text` + `--color-surface-elevated` で非強調 toast を 1.5 秒表示）。

### D-06: エラー / キャンセル時の挙動

| ケース | トリガー | UI 挙動 | サーバー側挙動 |
|-------|---------|---------|--------------|
| A: ユーザー明示キャンセル（送信停止） | isThinking 中に Cancel クリック | staging チップは **残す**、入力値も残す | folder のファイルは残す（再送信できるように） |
| B: 技術的失敗（worker エラー等） | job 失敗 notification | staging チップは **自動削除**（fade-out 200ms） | サーバー側で folder から自動削除（worker 側の責務） |
| C: graceful fallback（vision 非対応送信） | 画像付きで非対応モデル送信 | staging チップは **残す**、SystemMessage がチャットに追加される | 画像は worker 側で drop、SystemMessage 注入（D-18） |
| D: × ボタン手動削除 | チップの × クリック | **即時** unmount（確認ダイアログなし） | `DELETE /api/threads/{tid}/attachments/{storage_name}` で同期削除 |

### Uploading 状態の視覚フィードバック

- チップに 8×8 spinner（typing-dot パターン流用、`animation: typing-bounce 1.2s infinite`）
- opacity 0.5 でサムネ / pill を grayed out
- × 削除ボタンは **uploading 中も有効**（AbortController で upload を cancel する）
- uploading 中は送信ボタン（Send）を disabled にして "アップロード中" tooltip を表示（Claude's Discretion — planner が uploading staging items > 0 時の send ボタン挙動を最終決定）

### D-19: vision pre-validate

- `<AttachmentButton>` クリック時、`acceptedExtensions` prop で filter
- 画像ファイル選択後、`selectedModel` の `vision_limits.max_prompt_image_size` / `max_prompt_images` / `supported_media_types` を確認
  - サイズ超過: toast でエラー表示、staging に追加しない
  - 枚数超過: toast でエラー表示、追加される前に reject
  - 形式非対応（`image/gif` 等）: toast でエラー表示、reject
- vision: false モデル選択中でも画像添付は許容（`<VisionWarningBanner>` で案内する責務）

---

## Responsive Breakpoints

Phase 35 の 2 breakpoint を踏襲（`@media (max-width: 1024px)` = tablet / `@media (max-width: 767px)` = mobile）。

| Phase 36 要素 | Desktop | Tablet (≤1024px) | Mobile (≤767px) |
|--------------|---------|------------------|-----------------|
| `<AttachmentButton>` | 36×36px、textarea 左に並ぶ | 40×40px（タップターゲット引き上げ）、toolbar 改行許容（Phase 35 `chat-input-row { flex-wrap: wrap }` で既定） | 40×40px、toolbar は 2 行許容、絶対に表示し続ける |
| `<AttachmentChips>` | 横並び、overflow-x: auto（8 枚以上で内部スクロール） | 同じ、max-height 120px で縦スクロール可 | 同じ、画面幅制約で 3 枚 / 行 程度 |
| `<VisionWarningBanner>` | 1 行に全コンテンツが並ぶ（banner 高さ 72px 目安） | banner 高さ 96px 目安、CTA と × が改行する可 | banner 高さ 120px 目安、CTA は full width block、× は右上 absolute |
| Drop zone overlay | InputBar + MessageArea 全体に overlay | 同上 | drop 非対応前提、paste も非保証（Pitfall 4）、📎 ボタンが主系路。overlay が表示されても 破綻ゼロのみ保証 |
| Bubble 内 AttachmentChipRow | 横並び、bubble 幅制約内で収まる | 同上 | outgoing bubble は `max-width: 100%` なので画像サムネが 1-2 枚並ぶ、text chip は縦積み許容 |
| Header model select（🖼 絵文字付き） | 絵文字含めて 1 行 | Model: ラベル非表示は Phase 35 既存、🖼 付き option 名は表示 | select 自体は表示、絵文字で vision 判定可能 |

**モバイル固有対応:**
- iOS Safari で paste / drop が不安定（Pitfall 4）→ 📎 button が mobile で primary entry
- `<AttachmentButton>` の hit area は 40×40px（Phase 35 タップターゲット規約）
- VisionWarningBanner は CTA を full width にして、× 閉じるは右上 absolute（幅 320px 想定でも CTA が切れない）

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | — | not applicable（shadcn 未導入、Phase 35 で locked） |
| third-party registries | — | 宣言なし |

**判定:** Phase 35 D-01 で CSS custom properties が locked。新規 UI コンポーネントライブラリは導入しない。Safety Gate N/A。

---

## Visual Accessibility Baseline

Phase 35 §Visual Accessibility Baseline を踏襲。本 phase で追加される新規コンポーネント要件:

| 項目 | 要件 |
|------|------|
| Focus ring | `<AttachmentButton>` / `<AttachmentChips>` の × 削除ボタン / `<VisionWarningBanner>` の CTA / `<VisionWarningBanner>` の × 閉じる に `:focus-visible` で 2px outline `--color-accent`（Phase 35 と同 pattern） |
| キーボード操作 | `<AttachmentButton>` Enter / Space で開く、`<AttachmentChips>` の × は Tab で到達可能・Enter / Space で削除、`<VisionWarningBanner>` の CTA も Tab 到達可能 |
| ARIA | `<AttachmentChips>` は `role="list"`、各 chip は `role="listitem"`。`<VisionWarningBanner>` は `role="status"` + `aria-live="polite"`（画面読み上げで自動通知） |
| Drop zone a11y | overlay は `aria-hidden="true"`（ドラッグ操作自体が非視覚ユーザーには届かないため、focus 管理不要） |
| Color contrast | すべて Phase 35 semantic token 経由のため WCAG AA（4.5:1）を継承。新規組み合わせ無し |
| Screen reader status | uploading 中の chip は `aria-busy="true"`、error 時は `role="alert"` |
| 画像サムネの alt | `<img alt="{filename}">`（ファイル名を代替テキストとして使う、`alt=""` にしない） |

---

## Phase 36 Checker Acceptance Criteria

gsd-ui-checker が本 SPEC を PASS とする基準:

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | 新規 CSS 変数がゼロ追加されている（全て Phase 35 token を参照） | `grep -E '^\s*--' frontend/src/theme.css` の件数が Phase 35 完了時点と同じ |
| 2 | `<AttachmentButton>` / `<AttachmentChips>` / `<VisionWarningBanner>` の 3 コンポーネントが存在 | `ls frontend/src/components/Attachment*.tsx frontend/src/components/VisionWarningBanner.tsx` |
| 3 | `<AttachmentButton>` が `toolbarSlot` に、`<AttachmentChips>` が `previewSlot` に差し込まれている | ChatApp.tsx（または各 *ChatApp.tsx）で `<InputBar toolbarSlot={<AttachmentButton ...>} previewSlot={<AttachmentChips ...>} ...>` のパターンを grep |
| 4 | InputBar に `warningSlot` prop が追加され、`<VisionWarningBanner>` が差し込まれている | grep `warningSlot` in InputBar.tsx + ChatApp.tsx |
| 5 | accent reserved-for リストの 9 項目以外で `--color-accent` が直接使われていない | `grep -rn "var(--color-accent)" frontend/src/components/Attachment*.tsx frontend/src/components/VisionWarningBanner.tsx` の件数 <= 4（📎 hover + focus ring + warning CTA + warning accent bar） |
| 6 | destructive 色は ① × 削除 hover、② 画像 error 枠、③ upload 失敗枠、④ サイズ超過枠 の 4 箇所のみ | grep `var(--color-destructive)` の件数がこの 4 箇所に収まる |
| 7 | Copywriting が日本語で、Phase 35 既存コピーと競合しない | grep によるコピー列確認（"送信" / "ファイルを添付" / "画像非対応モデル" 等の存在） |
| 8 | 画像サムネが 48×48 固定で、サーバー側サムネ生成（`.thumb/`）を追加していない | `find /shared/thread-files -type d -name '.thumb*'` が 0 件、かつ `grep "width=48\|width: 48\|48px" AttachmentChips.tsx MessageArea.tsx` で複数ヒット |
| 9 | Vision warning banner は `--color-destructive` を使わない（graceful 方針） | `grep "destructive" VisionWarningBanner.tsx` が 0 件 |
| 10 | タブレット (`max-width: 1024px`) / モバイル (`max-width: 767px`) で `<AttachmentButton>` が 40×40 に拡大される | Chrome DevTools MCP で幅 1024 / 375 で目視確認 |
| 11 | ダークモード（`[data-theme="dark"]`）で新規コンポーネントのコントラスト・色が破綻しない | Chrome DevTools MCP で data-theme 切替目視 |
| 12 | `<VisionWarningBanner>` は画像 staging が 0 件に戻るか vision: true モデルに切替で自動 unmount | Chrome DevTools MCP で再現 |
| 13 | Bubble 内 AttachmentChipRow が `additional_kwargs.attachments` 空のときに DOM に出ない | 既存メッセージ（Phase 35 以前の）で regression なし |
| 14 | Model selector に `vision: true` モデルの絵文字 🖼 が付いている | Chrome DevTools MCP または `grep "🖼" Header.tsx` |
| 15 | 新規 REST route (`POST/GET/DELETE /api/threads/{tid}/attachments`, `GET /api/models`) が JWT 保護される | `grep "get_jwt_payload\|get_github_token" app/api/routes/attachments.py app/api/routes/models.py` |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: 日本語統一、3 コンポーネントと銘柄選択 / Error State / Drop Zone すべて定義済み
- [ ] Dimension 2 Visuals: AttachmentButton / Chips / WarningBanner / Bubble ChipRow の 4 点の視覚仕様完備
- [ ] Dimension 3 Color: 60/30/10 維持、accent reserved-for リスト 9 項目に拡張、destructive 4 箇所明示
- [ ] Dimension 4 Typography: Phase 35 の 5 役を追加なしで運用、weight オーバーライドは 1 箇所のみ
- [ ] Dimension 5 Spacing: 8-point scale 踏襲、新規 token なし、タップターゲット 36/40px 維持
- [ ] Dimension 6 Registry Safety: N/A（shadcn 未導入、third-party なし）

**Approval:** pending
