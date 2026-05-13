---
phase: 38
plan: 5
plan_id: 38-05-frontend-modal-and-renderers
subsystem: frontend-modal + 4-renderer + chip-kind-extension
tags: [frontend, attachment-modal, attachment-chip-row, image-preview, markdown-preview, csv-preview, monaco-text-preview, focus-trap, react-portal, kind-discriminator]
requirements: [FOUT-01, FOUT-02, FOUT-03, FOUT-04]
dependency_graph:
  requires:
    - "Plan 38-01: AttachmentMeta.kind を 'user_upload' | 'generated' に enum 化 (D-30 案 A) — UI 側型契約の前提"
    - "Plan 38-02: outputs route (GET /api/threads/{tid}/outputs/{name}) — Modal がここに fetch する"
    - "Plan 38-04: AIMessage.additional_kwargs.attachments への turn-delta bundle — チップが復元データを消費する"
    - "Phase 35 token system + Phase 36 AttachmentChipRow / ConfirmModal — base パターン"
  provides:
    - "AttachmentModal.tsx 本体 (lazy 4 renderer dispatch + portal dialog + Esc/overlay/× close + Tab focus trap + body scroll lock)"
    - "preview/ImagePreview.tsx — raw bytes 直配信、size cap 10MB (AttachmentModal で gate)"
    - "preview/MarkdownPreview.tsx — react-markdown + remark-gfm 薄ラッパー、MarkdownMessage は呼ばない (UI-SPEC L437-441)"
    - "preview/CsvPreview.tsx — 簡易 CSV パーサ + ChatAgGridTable lazy 流用 + 1000 行 cap"
    - "preview/TextPreview.tsx — Monaco read-only Editor + LANG_ALIASES ローカル定義 + 1MB cap"
    - "MessageArea.tsx の AttachmentChipRow 拡張: kind 別 micro-badge + <button> 化 + onOpenModal 起動"
    - "MessageArea body: activeAttachment useState + AttachmentModal conditional mount (多重 modal 禁止)"
    - "buildFileUrl / buildChipImageUrl helper: kind === 'generated' → /outputs/、それ以外 → /attachments/"
  affects:
    - "Phase 39 (FOUT-05+) または v6.1 polish: AttachmentModal の追加 renderer (PDF / HTML 等) 拡張時に lazy dispatch 構造を再利用可能"
    - "Plan 38-06 (validation): Chrome DevTools MCP 22 項目 UI-SPEC Checker の対象"
tech_stack:
  added: []
  patterns:
    - "Lazy renderer dispatch: 4 preview component を React.lazy + Suspense で 1 種類のみロード — MarkdownMessage.tsx の lazy ChatAgGridTable / MermaidBlock パターンを継承"
    - "Portal dialog + focus trap: ConfirmModal を analog にしつつ Tab 循環 + body scroll lock を追加 — 多重 modal 禁止は MessageArea-level state で実現"
    - "kind discriminator URL routing: AttachmentModal.buildFileUrl と MessageArea.buildChipImageUrl の 2 箇所で kind === 'generated' ? 'outputs' : 'attachments' を厳密適用 (D-05 / UI-SPEC L485-494)"
    - "Size cap gate-before-fetch: attachment.size を fetch 前に判定して 1MB/10MB 超過は size-cap banner + DL CTA に縮退 (T-38-05-03 mitigation)"
key_files:
  created:
    - frontend/src/components/AttachmentModal.tsx
    - frontend/src/components/preview/ImagePreview.tsx
    - frontend/src/components/preview/MarkdownPreview.tsx
    - frontend/src/components/preview/CsvPreview.tsx
    - frontend/src/components/preview/TextPreview.tsx
  modified:
    - frontend/src/components/MessageArea.tsx
decisions:
  - "renderer 分割は 1 component / 1 ファイル (合計 5 ファイル) — UI-SPEC L600-602 の planner 判断ポイントを「分割」に倒した。各 renderer の単独 lazy import で初期バンドル膨張を防ぐため"
  - "LANG_ALIASES は TextPreview 内で **ローカル複製** (MarkdownMessage.tsx から export しない) — UI-SPEC L737-742 の planner 判断ポイントを「複製」に倒した。MarkdownMessage への参照を grep ゼロ件に保つため (UI-SPEC Checker #12 厳密遵守)"
  - "ErrorBanner / LoadingDots は各 preview 内に重複定義 (export 化しない) — 共有抽出よりも各 renderer 単独で完結する方が lazy bundle のサイズと依存関係が明瞭になる判断"
  - "CSV parser は inline 簡易実装 (papaparse 不要) — UI-SPEC Standard Stack §6 / RESEARCH §6 の方針継承、quote/CRLF 対応の最小実装で 1MB 範囲内なら十分"
  - "Task 3 (checkpoint:human-verify) は orchestrator 経由で user に視覚検証を依頼 — worker (本 plan) は Task 1/2 で source assertion を全 green にした状態で停止し、merge 後の docker compose + Chrome DevTools MCP で 22 項目を確認するワークフロー"
metrics:
  duration_minutes: 65
  completed_date: 2026-05-12
  tasks_completed: 2  # Task 3 は checkpoint:human-verify で orchestrator が user 確認を実施
  files_created: 5
  files_modified: 1
  commits: 2
---

# Phase 38 Plan 05: AttachmentModal + 4 preview renderers + AttachmentChipRow kind 拡張 Summary

Phase 36 で確立した AttachmentChipRow の「画像サムネ / 📄 pill 表示」を Phase 38 D-30 案 A の `kind: 'user_upload' | 'generated'` discriminator に対応する `<button>` 化 + kind 別 micro-badge 表示 + クリックでモーダル起動の UX に拡張し、AttachmentModal 本体 + 4 種 preview renderer (Image / Markdown / CSV / Monaco-text) を新規実装した。kind === 'generated' は `/outputs/` route、それ以外は `/attachments/` route に URL を切替えることで Phase 38 D-05 の identity 通貫設計が UI 層まで通り、Phase 36 アップロード添付と Phase 38 worker 生成ファイルが完全に同じ UX (チップ + モーダル) で扱えるようになった。新規 npm パッケージゼロ・新規 CSS 変数ゼロ・MarkdownMessage への参照ゼロ・TypeScript エラーゼロ を全て同時に達成。

## Performance

- **Duration:** ~65 分
- **Started:** 2026-05-12T01:23:00Z
- **Completed:** 2026-05-12T02:29:19Z
- **Tasks completed (auto):** 2 (Task 3 は checkpoint:human-verify、視覚検証は orchestrator 主導で user に依頼)
- **Files created:** 5
- **Files modified:** 1
- **Lines added/removed:** +1196 / -22

## Tasks Completed

| # | Task | Type | Commit | Files |
|---|------|------|--------|-------|
| 1 | AttachmentModal.tsx と 4 種 preview component を新規作成 | feat | `eaf17c1` | AttachmentModal.tsx, preview/ImagePreview.tsx, preview/MarkdownPreview.tsx, preview/CsvPreview.tsx, preview/TextPreview.tsx |
| 2 | MessageArea.tsx の AttachmentChipRow を kind 別 micro-badge + button 化 + AttachmentModal mount に拡張 | feat | `e15b93b` | MessageArea.tsx |
| 3 | 実機 docker compose + Chrome DevTools MCP で UI-SPEC Checker 22 項目を視覚検証 | checkpoint:human-verify | **deferred to user via orchestrator** | — |

## Key Decisions / Implementation

### Task 1: AttachmentModal + 4 renderer (UI-SPEC §"Component Contracts" / PATTERNS.md §"Plan 05-A..05-E")

`AttachmentModal.tsx` (~360 行) は createPortal + dialog overlay + Tab focus trap + Esc/overlay/× close + body scroll lock + lazy renderer dispatch + size cap gate + unsupported fallback をすべて 1 ファイルにまとめた。Plan の指示通り PATTERNS.md §"Plan 05-A" のスニペットを完全踏襲し、ConfirmModal のオーバーレイ構造 (analog) と MarkdownMessage の lazy import パターンを組み合わせた。

```ts
// kind ベース URL 切替 — UI-SPEC L485-494 / D-05
export function buildFileUrl(threadId, name, kind): string {
  const segment = kind === 'generated' ? 'outputs' : 'attachments';
  return `${API_BASE}/api/threads/${encodeURIComponent(threadId)}/${segment}/${encodeURIComponent(name)}`;
}

// classify ext → 5 種 PreviewKind — UI-SPEC L418-428
export function classify(ext): PreviewKind {
  // image / markdown / csv / text / unsupported
}
```

renderer dispatch は switch 文で:
- `case 'image'`: ImagePreview を中央寄せコンテナで描画 (`object-fit: contain`)
- `case 'markdown'`: MarkdownPreview をそのまま (内部で padding 持つ)
- `case 'csv'`: CsvPreview をそのまま (内部で padding 持つ)
- `case 'text'`: TextPreview を ext 付きで (Monaco language ID 解決のため)
- `default`: UnsupportedBanner (PDF / HTML 等のフォールバック案内 + DL CTA)

Size cap は fetch 前に `attachment.size` で判定:
- 画像 10MB / text 系 1MB
- 超過時は SizeCapBanner (accent-subtle 背景の「案内」表現、destructive ではない — D-14 spirit)

Focus trap は useEffect 内 keydown listener:
- Esc → onClose
- Tab → focusable 要素一覧を取り、Shift+Tab で first/last 循環、通常 Tab で最後→最初へ循環
- mount 時に setTimeout(0) で download CTA に focus
- unmount 時に body.style.overflow を復元

### 4 preview component (Plan 05-B..05-E)

**ImagePreview** (25 行): UI-SPEC L432-436 の最小スニペットそのまま。raw bytes 直配信、サムネ生成しない。

**MarkdownPreview** (122 行): `import ReactMarkdown from 'react-markdown'; import remarkGfm from 'remark-gfm';` で **直接** import し薄ラッパーとして使う。MarkdownMessage への参照は **ゼロ** (UI-SPEC L437-441 / Checker #12 厳密遵守 — コメントの「MarkdownMessage.tsx と同パターン」表現も削除した)。 fetch error は 401/403→`auth`、404→`missing`、それ以外→`fetch` の 3 種に分岐。

**CsvPreview** (247 行): 簡易 CSV パーサを inline 実装 (papaparse 不要)。quote/CRLF/escaped double-quote を正しく扱う state machine 方式。先頭 1000 行 cap、超過時は accent-subtle バナー「先頭 N 行のみ表示しています」。テーブル描画は `lazy(() => import('../ChatAgGridTable'))` で MarkdownMessage と同じ lazy 戦略を踏襲。

**TextPreview** (161 行): `@monaco-editor/react` の `<Editor>` を `readOnly: true` で呼び、`useCurrentTheme()` で vs/vs-dark theme を切替。LANG_ALIASES は **TextPreview 内にローカル定義** (MarkdownMessage.tsx から複製) — UI-SPEC L737-742 の planner 判断ポイントを「複製」に倒した。export 化を選ばなかった理由は MarkdownMessage への参照を Checker #12 ゼロ件に保つため。

### Task 2: AttachmentChipRow kind 拡張 + Modal mount (Plan 05-F)

既存の `AttachmentChipRow` (Phase 36 D-21 実装) を PATTERNS.md §"Plan 05-F" のスニペットに従って拡張:

- `aria-label` を `添付・AI 生成ファイル {n} 件` に変更 (UI-SPEC L232 — input/output 混在の事実反映)
- 画像チップを `<button>` でラップ、`aria-haspopup="dialog"`、`onClick={() => onOpenModal(a)}`
- 画像チップ右下に絶対配置の micro-badge: `kind === 'generated' ? '✨ AI 生成' : '📎 添付'`、background は kind 別 (accent-subtle vs surface-elevated)
- text/code チップも `<button>` 化、pill 左端に同 micro-badge を inline 配置
- URL 構築は `buildChipImageUrl(threadId, attachment)` でローカル定義 (AttachmentModal.buildFileUrl と同形だが import 重複回避のため、`generated` の場合は `a.name` を、`user_upload` の場合は `a.storage_name` を使い分け)

MessageArea コンポーネント本体 (relevant 行):

```tsx
const [activeAttachment, setActiveAttachment] = useState<AttachmentMeta | null>(null);

// User message と AI message の AttachmentChipRow 呼び出し 2 箇所に
//   onOpenModal={setActiveAttachment} を追加

// JSX 末尾 (InputBar の後) に Modal を mount
{activeAttachment && activeThreadId && (
  <AttachmentModal
    threadId={activeThreadId}
    attachment={activeAttachment}
    open
    onClose={() => setActiveAttachment(null)}
  />
)}
```

1 時点に open できる Modal は 1 個だけ (UI-SPEC L513-516 多重 modal 禁止) — activeAttachment state が 1 個なので別チップクリック時は自動的に swap。

### Task 3: checkpoint:human-verify

実機 docker compose + Chrome DevTools MCP で UI-SPEC §"Phase 38 Checker Acceptance Criteria" L617-643 の **22 項目**を視覚検証する Task。本 plan は worktree 並列実行モードで動作しており、orchestrator (parent agent) が merge 後に user に依頼する形でハンドオフされる。

本 plan の worker (executor) は Task 1/2 を完了させ、source assertion / TypeScript build / 新規 dep ゼロ確認をすべて green にした状態で停止する。

## Verification

| Check | Result |
|-------|--------|
| `bun run tsc --noEmit` (frontend) | ✅ exit 0、エラーゼロ |
| 新規 npm パッケージゼロ: `git diff main -- frontend/package.json frontend/bun.lockb \| wc -l` | ✅ 0 |
| 新規 CSS 変数ゼロ: `git diff main -- frontend/src/theme.css \| grep '^+\s*--' \| wc -l` | ✅ 0 |
| ファイル存在: AttachmentModal.tsx + 4 preview | ✅ 5 files created |
| Checker #14: `grep -c 'role="dialog"' AttachmentModal.tsx` | ✅ 2 (>= 1) |
| Checker #14: `grep -c "aria-modal" AttachmentModal.tsx` | ✅ 2 (>= 1) |
| Checker #12: `grep -c "ReactMarkdown\|react-markdown" MarkdownPreview.tsx` | ✅ 3 (>= 1) |
| Checker #12: `grep -c "MarkdownMessage" AttachmentModal.tsx MarkdownPreview.tsx` | ✅ 0 (重要 — コメント含めて言及ゼロ) |
| Checker #11: `grep -c "ChatAgGridTable" CsvPreview.tsx` | ✅ 4 (>= 1) |
| Checker #13: `grep -c "readOnly: true" TextPreview.tsx` | ✅ 1 (>= 1) |
| Checker #21: `grep -c "kind === 'generated' ? 'outputs' : 'attachments'" *.tsx` | ✅ AttachmentModal.tsx に 1 件 (canonical) |
| Checker #10 (画像 10MB): `grep -E "10 \* 1024 \* 1024"` | ✅ AttachmentModal.tsx に hit (IMAGE_CAP_BYTES) |
| Checker #10 (text 1MB): `grep -E "1024 \* 1024"` | ✅ AttachmentModal.tsx (TEXT_CAP_BYTES) + 各 preview |
| B2 renderer dispatch: `grep "case 'image' \| 'markdown' \| 'csv' \| 'text'" AttachmentModal.tsx` | ✅ 4 件すべて hit |
| B2 classify: `grep "function classify" AttachmentModal.tsx` | ✅ hit |
| MessageArea AC: `grep -c "<button" MessageArea.tsx` | ✅ 6 (>= 2) |
| MessageArea AC: `grep -c 'aria-haspopup="dialog"' MessageArea.tsx` | ✅ 2 (>= 1) |
| MessageArea AC: `grep -E "AI 生成\|user_upload\|generated" MessageArea.tsx` | ✅ 5+ ヒット |
| MessageArea AC: `grep -c "AttachmentModal" MessageArea.tsx` | ✅ 6 (>= 2) |
| MessageArea AC: `grep -c "activeAttachment" MessageArea.tsx` | ✅ 3 (>= 1) |
| MessageArea AC: `grep "添付・AI 生成ファイル" MessageArea.tsx` | ✅ hit |
| MessageArea AC: 「✨ AI 生成」「📎 添付」両方 hit | ✅ 両方 hit |
| MessageArea AC: `grep -c "_formatHistorySize" MessageArea.tsx` (既存 helper 維持) | ✅ 2 (>= 2) |

### Threat Mitigation Coverage

| Threat ID | Disposition | 実装による mitigation |
|-----------|-------------|----------------------|
| T-38-05-01 (Tampering: filename `../`) | mitigate | AttachmentModal.buildFileUrl で `encodeURIComponent(name)` を強制、MessageArea.buildChipImageUrl も同形 |
| T-38-05-02 (Tampering: Markdown HTML injection) | mitigate | ReactMarkdown のデフォルトで HTML は escape — rehype-raw 等を **意図的に使っていない** |
| T-38-05-03 (DoS: 巨大ファイル) | mitigate | AttachmentModal で `attachment.size > cap` を fetch 前に判定し SizeCapBanner に縮退 (画像 10MB / text 系 1MB) |
| T-38-05-04 (Information Disclosure: 別 user の `_generated/`) | accept (API 層で防御済) | Modal 内 fetch 401/403 → `auth`、404 → `missing` の error banner に分岐 |
| T-38-05-05 (Tampering: 多重 modal で focus/scroll lock 破綻) | mitigate | activeAttachment state を MessageArea-level に 1 個だけ持つ + useEffect cleanup で body.style.overflow を確実に restore |

## Deviations from Plan

### Auto-fixed Issues

**[Rule 2 - Critical Completeness] AttachmentModal.tsx / MarkdownPreview.tsx のコメント文中の `MarkdownMessage` 文字列を削除**
- **Found during:** Task 1 verify (`grep -c "MarkdownMessage"` を実行したところコメント内に 2 件 hit)
- **Issue:** UI-SPEC Checker #12 と Plan acceptance_criteria は `grep -c "MarkdownMessage" AttachmentModal.tsx MarkdownPreview.tsx` count 0 を要求している。コメント中の参照 (e.g. "MarkdownMessage.tsx と同パターン" / "MarkdownMessage.tsx は呼ばない") は実呼び出しではないが、grep ベースの自動検証では区別できない
- **Fix:** コメントを「react.lazy + Suspense パターン」「AI 応答描画用のリッチなコンポーネントは preview から呼ばない」に書き換え
- **Files modified:** frontend/src/components/AttachmentModal.tsx, frontend/src/components/preview/MarkdownPreview.tsx
- **Commit:** `eaf17c1` に含まれる (initial 作成と同コミット内で修正)

ほか auto-fix なし — Plan は完全に指示通りに実装可能で、追加の補正不要だった。

### Authentication Gates

なし — 本 plan は frontend UI のみで認可境界に触れない (modal 内 fetch は browser session cookie を使うため `credentials: 'include'` だけ指定、JWT 取り扱いは既存の api/client パターンで網羅済)。

## Files Created

- `frontend/src/components/AttachmentModal.tsx` — モーダル本体 (~510 行)、portal + dialog + 4 renderer dispatch + size cap + unsupported fallback + focus trap
- `frontend/src/components/preview/ImagePreview.tsx` — raw bytes `<img>` 直配信 (25 行)
- `frontend/src/components/preview/MarkdownPreview.tsx` — react-markdown + remark-gfm 薄ラッパー + LoadingDots/ErrorBanner (122 行)
- `frontend/src/components/preview/CsvPreview.tsx` — 簡易 CSV パーサ + ChatAgGridTable lazy + 1000 行 cap (247 行)
- `frontend/src/components/preview/TextPreview.tsx` — Monaco read-only Editor + LANG_ALIASES ローカル定義 (161 行)

## Files Modified

- `frontend/src/components/MessageArea.tsx` — AttachmentChipRow を kind 別 micro-badge + button 化 + onOpenModal 連携に拡張、activeAttachment state と AttachmentModal mount を追加、buildChipImageUrl helper を新規定義 (+135 / -22 行)

## Known Stubs

なし — 本 plan で追加したコードはすべて実体を持つ:
- AttachmentModal は 4 種 renderer すべてを実装
- 各 preview は fetch + error 表示 + 描画まで完結
- AttachmentChipRow は kind 別表示 + onOpenModal callback まで完結
- 「unsupported / size cap / error」のフォールバック banner も実 DL CTA リンクを描画

## Threat Flags

なし — 本 plan で導入された新規 surface (Modal portal / 4 renderer fetch / kind 別 URL routing) は、threat model T-38-05-01..05 にすべて記載済で mitigation 完了 (上記 Threat Mitigation Coverage 参照)。

## Checkpoint Reached

**Type:** human-verify
**Awaiting:** orchestrator が user に視覚検証を依頼

### What was built

- AttachmentModal + 4 種 preview renderer + AttachmentChipRow kind 拡張
- kind === 'generated' / user_upload 別 micro-badge 表示
- kind ベース URL 切替 (`/outputs/` vs `/attachments/`)
- size cap 案内 + エラーバナー + focus trap + dark mode 対応 + モバイル幅対応

### How to verify (Chrome DevTools MCP / docker compose)

1. `docker compose up -d` でコンテナ起動。Chromium が `--remote-debugging-port=9222` で起動済を確認
2. `http://localhost:5173/orochi/` で login → Chat アプリで execute_python が画像を生成する prompt を送信 (例: 「matplotlib で sin カーブの PNG を保存して」)
3. AI 応答にチップが現れる → ✨ AI 生成 micro-badge が見える → チップクリック → AttachmentModal が画像を表示
4. AttachmentModal の「ダウンロード」CTA をクリック → ブラウザがファイルを保存できる
5. 別 prompt で CSV / Markdown / .py を生成 → 各 renderer が動作する (CSV は ag-grid、MD は react-markdown、.py は Monaco syntax highlight)
6. 過去スレッド再オープン: スレッド切替で AI message にチップが復元される (FOUT-04 sc4)
7. multi-user isolation: 別 user JWT で `/outputs/` を叩いて 401/404 が返り Modal 内エラーバナーが出る (FOUT-04 sc5)
8. size cap: 大きいファイル (>1MB text) を生成 → SizeCapBanner + DL CTA、画像 >10MB なら同様
9. dark mode: `[data-theme="dark"]` 切替で Modal が破綻しない (Checker #16)
10. モバイル幅 375px (DevTools viewport 切替): Modal が full-screen 化、CTA が full-width block (Checker #17)
11. PDF / 非対応形式: UnsupportedBanner「Download only」案内 + DL CTA (Checker #20)
12. focus trap: Tab で `× ↔ ダウンロード CTA ↔ body` 内を循環、外に出ない (Checker #15)

UI-SPEC §"Phase 38 Checker Acceptance Criteria" L617-643 の **22 項目すべて**を 1 つずつ確認する。

### Resume signal

Type "approved" (22 項目すべて pass) または問題箇所を列挙

## Self-Check: PASSED

- ✅ `frontend/src/components/AttachmentModal.tsx` exists
- ✅ `frontend/src/components/preview/ImagePreview.tsx` exists
- ✅ `frontend/src/components/preview/MarkdownPreview.tsx` exists
- ✅ `frontend/src/components/preview/CsvPreview.tsx` exists
- ✅ `frontend/src/components/preview/TextPreview.tsx` exists
- ✅ Commit `eaf17c1` (Task 1 — AttachmentModal + 4 preview) exists in git log
- ✅ Commit `e15b93b` (Task 2 — MessageArea AttachmentChipRow extension) exists in git log
- ✅ TypeScript build green (`bun run tsc --noEmit` exit 0)
- ✅ 新規 npm 依存ゼロ
- ✅ 新規 CSS 変数ゼロ
- ✅ MarkdownMessage への参照ゼロ (Checker #12 厳密遵守)
- ✅ 全 source assertion based UI-SPEC Checker (#1, #2, #3, #4, #5, #6, #9, #10, #11, #12, #13, #14, #15, #21, #22) green
- ⏳ Task 3 (checkpoint:human-verify) は orchestrator 経由で user に視覚検証を依頼
