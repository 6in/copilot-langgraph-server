---
phase: 36-text-code-image-multimodal
plan: 05
subsystem: frontend
tags: [frontend, react, hooks, attachments, multipart, drag-drop, paste, typescript, ui-spec, additional-kwargs]

# Dependency graph
requires:
  - phase: 36-text-code-image-multimodal
    provides: "Plan 03 — POST/GET/DELETE /api/threads/{tid}/attachments multipart routes + ChatRequest.attachments + GET messages additional_kwargs.attachments 返却"
  - phase: 36-text-code-image-multimodal
    provides: "Plan 04 — worker.process_chat に attachments kwarg + LangGraphHandler/OrchestratorHandler additional_kwargs / state 配線 + D-18 vision drop"
  - phase: 35-dashboard-design-system
    provides: "InputBar.toolbarSlot / previewSlot 予約 + chat-attach-btn 配置位置 + theme.css CSS 変数 (--color-accent / --color-destructive / --color-accent-subtle / --color-text-muted)"
provides:
  - "frontend/src/types.ts — AttachmentMeta (D-14 統一スキーマ) / ModelInfo (D-16) / ChatMessage.additional_kwargs / ChatRequest.attachments 型追加"
  - "frontend/src/api/client.ts — postAttachments (multipart + AbortSignal) / deleteAttachment (204 idempotent)"
  - "frontend/src/hooks/useAttachments.ts — 3 入り口 (click/drop/paste) 統一 staging hook + サーバー連動 CRUD + AbortController キャンセル + D-19 vision_limits pre-validate"
  - "frontend/src/components/AttachmentButton.tsx — 📎 button + hidden input[type=file multiple] + a11y aria-label/title/visually-hidden span"
  - "frontend/src/components/AttachmentChips.tsx — 画像 48×48 サムネ / text/code pill / × 削除 / uploading typing-dot spinner / error 時 destructive 枠"
  - "frontend/src/components/ChatApp.tsx — useAttachments 配線 + drop zone overlay + document level paste listener + validation error banner + InputBar slot 差し込み + handleSend で clearAll"
  - "frontend/src/components/MessageArea.tsx — inputToolbarSlot / inputPreviewSlot props を InputBar の toolbarSlot / previewSlot に forward"
  - "frontend/src/theme.css — .chat-attach-btn hover/focus + .chat-attach-remove-btn hover/focus を追加 (新規 CSS 変数追加なし)"
affects:
  - "phase-36 wave-5 plan-06 — useAttachments.getReadyItems() を useChat の sendMessage payload に載せ、Bubble 内 AttachmentChipRow を MessageArea に追加。ModelInfo 型と useModels hook (新規) で selectedModelInfo を本 hook の第 2 引数に流すと vision_limits pre-validate が有効化される。"
  - "phase-36 wave-6 plan-07 — chrome-devtools MCP smoke で 3 入り口動作 (📎 click / drag-drop overlay / Ctrl+V paste) + chip 表示 + × 削除 → DELETE → サーバーから消える、を E2E 検証する。"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "3 入り口 (click/drop/paste) 統一 upload pattern: 1 つの useAttachments.upload(files) で OS file picker / DataTransfer / ClipboardData の 3 経路を統一 (D-04)"
    - "AbortController per item: StagingItem.abortCtrl で uploading 中の × クリックが abort() し、AbortError 検出時に staging から消す"
    - "楽観削除 + best-effort DELETE: removeItem で UI から先に消し、その後 DELETE 失敗しても restore しない (UX 優先)"
    - "Document level paste listener: clipboardData.items から image/* blob を拾う pattern (textarea focus 中も外も拾える、Pitfall 4 mobile 対策と分離)"
    - "InputBar slot pattern (Phase 35 D-08): MessageArea が inputToolbarSlot / inputPreviewSlot を named slot として forward し、ChatApp 側で AttachmentButton / AttachmentChips を差し込む"
    - "Drop zone overlay pattern: ChatApp 全体 (rootRef div) で onDragOver/onDrop を捕捉し、dragOver state で overlay を absolute 表示 (pointer-events: none で透過)"
    - "Validation error banner pattern: useAttachments の validationError state を ChatApp 側で表示 (× 閉じるあり、destructive 枠で警告)"

key-files:
  created:
    - "frontend/src/hooks/useAttachments.ts (182 行) — 3 入り口統一 staging hook"
    - "frontend/src/components/AttachmentButton.tsx (83 行) — 📎 button + hidden file input"
    - "frontend/src/components/AttachmentChips.tsx (154 行) — staging chip 描画 (画像/text/uploading/error)"
  modified:
    - "frontend/src/types.ts (+32 行) — AttachmentMeta / ModelInfo 型 + ChatMessage.additional_kwargs + ChatRequest.attachments"
    - "frontend/src/api/client.ts (+34 行) — postAttachments / deleteAttachment + AttachmentMeta import"
    - "frontend/src/components/ChatApp.tsx (+131/-3 行) — useAttachments 配線 + drop overlay + paste listener + validation banner + slot 差し込み + handleSend.clearAll"
    - "frontend/src/components/MessageArea.tsx (+7/-2 行) — inputToolbarSlot / inputPreviewSlot props を InputBar に forward"
    - "frontend/src/theme.css (+22 行) — .chat-attach-btn / .chat-attach-remove-btn の hover/focus style"

key-decisions:
  - "× 削除ボタンに dedicated class .chat-attach-remove-btn を付与: 当初 plan 案の `[role=\"listitem\"] button[aria-label$=\"を添付から削除\"]` セレクタは既存 ThreadSidebar 等の `role=\"listitem\"` 要素と CSS 上競合する恐れがあったため、明示的な class 名で隔離。CSS セレクタの specificity 安定性を優先。Plan 文の「衝突する場合は class 名付与の代案も可」に従った。"
  - "ChatApp 内 useAttachments の selectedModelInfo は null 固定: 本 plan scope では vision_limits pre-validate (D-19) は無効化。useModels hook と Header 連携は Plan 06 で実装するため、本 plan では size/ext のみの validate に留める。useAttachments の API は ModelInfo を受ける形で先行設計しておき、Plan 06 で第 2 引数に流すだけで有効化される。"
  - "useChat に attachments を載せない: 本 plan は staging UI 完成までの責務に限定。useChat への payload 拡張は Plan 06 (frontend → REST → worker への e2e 連動) で行う。ChatApp.handleSend では送信成功時に clearAll を呼ぶだけで、attachments.getReadyItems() の sendMessage 引数 forwarding は Plan 06 に移譲。"
  - "drop zone listener は ChatApp root div に集約: InputBar / MessageArea ではなく ChatApp の最外殻 div に onDragOver/onDrop を付与した。これにより MessageArea のスクロール領域や InputBar の textarea focus 状態に依らず drop が拾える。InputBar 単体には drop を付けない (Phase 35 slot 契約を壊さない)。"
  - "paste listener は document level: textarea focus 中に限定せず document.addEventListener('paste', ...) で常時拾う。これにより画像コピー直後にどの要素が focus でも upload が動く。useEffect cleanup で removeListener を確実に外す。"
  - "validationError state を useAttachments hook 内に保持: validation 失敗 (例: 画像 6 枚目 / 100MB 超 / 未対応 ext) は staging に入れずに reason 文字列を hook 側で保持し、ChatApp 側で banner として描画。Plan 文の Step 1 では「validation reject は staging に入れない」を明記済。dismissValidationError で × 閉じるが可能。"

patterns-established:
  - "Phase 36 frontend staging 層 = useAttachments がサーバーと UI 状態の唯一の真実源、AttachmentButton/Chips は dumb component、ChatApp は drop/paste listener + validation banner + slot 配線の責務"
  - "新規 CSS 変数ゼロ追加 (UI-SPEC Checker #1) を実装段階で厳格適用: Phase 35 token (--color-accent / --color-destructive / --color-accent-subtle / --color-border / --color-text / --color-text-muted / --color-surface / --space-* / --radius-*) のみで全要素を表現"
  - "a11y baseline: visually-hidden span (clip:rect(0,0,0,0)) + aria-label + aria-busy + role=\"list\"/\"listitem\" + alt=filename を全 chip に適用"
  - "TypeScript strict mode 互換: 全 props を明示型 + AttachmentMeta dict を spread (...served) で StagingItem に統合する pattern"

requirements-completed: [FIN-01, FIN-02]

# Metrics
duration: ~12min
completed: 2026-04-24
---

# Phase 36 Plan 05: frontend staging + upload 経路 (useAttachments hook + AttachmentButton/Chips + ChatApp 配線) Summary

**Phase 36 の frontend staging 層を完成 — 3 入り口 (📎 click / drag-drop / Ctrl+V paste) で File を 1 つの `useAttachments.upload(files)` に集約し、即時 multipart upload + AbortController キャンセル + サーバー連動 CRUD を実現。`<AttachmentButton>` / `<AttachmentChips>` 2 components を UI-SPEC 仕様完全準拠で新規作成し、ChatApp.tsx で InputBar の toolbarSlot / previewSlot に差し込み + drop zone overlay + validation error banner + 送信成功時の clearAll を配線した。新規 CSS 変数追加ゼロを厳守 (UI-SPEC Checker #1)**

## Performance

- **Duration:** ~12 min (3 タスク + verification + SUMMARY)
- **Started:** 2026-04-24 (worktree base reset 後)
- **Tasks:** 3/3 完了 (全 autonomous, checkpoint なし)
- **Files:** 3 created (1 hook + 2 components) / 5 modified (types/client/ChatApp/MessageArea/theme)
- **Lines:** +648 / -2 (code 中心、test なし — RESEARCH §Wave 0 「frontend unit は Claude's Discretion」+ Plan 07 e2e で検証)

## Accomplishments

- **types.ts に Phase 36 型定義群を追加**: `AttachmentMeta` (D-14 統一 dict スキーマ: kind/name/storage_name/path/size/mime_type/ext/modified_at)、`ModelInfo` (D-16 vision_limits 含む、Plan 06 で消費)、`ChatMessage.additional_kwargs.attachments` (D-22 履歴連携)、`ChatRequest.attachments` (per-turn 添付)。既存 import path を破壊しない (新フィールドは全て optional)。
- **client.ts に multipart 対応 endpoint を追加**: `postAttachments(threadId, files, signal?)` は FormData + 直接 fetch (Content-Type を明示しない — browser が boundary 付きで自動設定)、AbortSignal を受けるので useAttachments 側でキャンセル可能。`deleteAttachment(threadId, name)` は 204 期待 (idempotent)、deleteThread と同 pattern で apiFetch を経由しない直接 fetch。
- **useAttachments hook が 3 入り口統一 staging を実現**: `upload(files)` 1 つの関数で OS file picker / DataTransfer / ClipboardData の 3 経路を統一処理。各 file 毎に StagingItem (localId=crypto.randomUUID() + status='uploading'|'done'|'error' + abortCtrl) を作り、postAttachments の Promise が done で server-side メタデータ (storage_name/path/mime_type) を merge、AbortError なら staging から削除、それ以外の error なら status='error' に遷移。`removeItem` は楽観削除 (UI から先に消す) + uploading なら abort() / done なら DELETE / error なら何もしない。`clearAll()` は staging を全消去 (送信成功時に呼ばれる)。`getReadyItems()` は status==='done' のみを AttachmentMeta dict のリストとして返す (Plan 06 で useChat の payload に乗せる)。
- **D-01/D-02 pre-validate を hook 内で enforce**: 画像 (png/jpg/jpeg/webp) は 10MB 超で reject、5 枚を超えると reject、text/code (text/* MIME or extension allowlist) は 100MB 超で reject、それ以外の extension は「対応していません」で reject。失敗時は validationError state に reason 文字列を入れる (staging には入れない)。
- **D-19 model vision_limits 連携を hook 内に組み込み**: 第 2 引数 `selectedModelInfo: ModelInfo | null` の `vision_limits.max_prompt_image_size` / `max_prompt_images` / `supported_media_types` を見て size 制限・枚数 cap・MIME allowlist を追加適用 (より厳しい方を優先)。本 plan では ChatApp が null 固定で渡すので無効化、Plan 06 で useModels hook 完成後に有効化される予定。
- **AttachmentButton 完成**: 📎 emoji + visually-hidden span (clip:rect(0,0,0,0))。aria-label を `disabled ? '添付を追加できません（送信中）' : 'ファイルを添付'` で切り替え、title tooltip は「ファイルを添付（最大 100MB / 画像は 10MB × 5 枚まで）」。隠し input[type=file multiple] が click 時に OS dialog を開き、選択後 onFilesSelected(Array.from(files)) → useAttachments.upload に流す。同名ファイル再添付のため input.value='' で reset。
- **AttachmentChips 完成**: items.length===0 で何も描画しない (InputBar slot 契約)。画像 (IMAGE_EXTS={png,jpg,jpeg,webp}) は 48×48 ImageChip で `<img src="/api/threads/{tid}/attachments/{storage_name}">` 直接表示 (D-23 サムネ生成なし)、status==='uploading' は半透明+typing-dot、status==='error' は destructive 枠+🖼 placeholder。text/code は FileChip で pill (border-radius: --radius-full + 28px height + max-width 240px ellipsis) で `[📄 filename size ×]`。両 chip の × 削除ボタンは .chat-attach-remove-btn class 付与で hover destructive、aria-label `{filename} を添付から削除`、role="list"/"listitem" + aria-busy="uploading 中" を付与。
- **ChatApp.tsx 配線完了**: useAttachments(activeThreadId, null) で hook を呼び、root div (position: relative) に `onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}` を付与。dragOver state を見て drop overlay (var(--color-accent-subtle) + 2px dashed var(--color-accent) + 中央「ファイルをドロップして添付」見出し + 「テキスト・コード・画像（PNG / JPG / WebP）に対応」補助) を absolute zIndex:100 で表示、pointer-events:none で透過。document level paste listener で clipboardData.items から image/* を抽出 → upload。validation error banner (destructive 枠 + ⚠ + reason + × 閉じる) を root 上部に表示。MessageArea に `inputToolbarSlot=<AttachmentButton onFilesSelected={(f) => attachments.upload(f)} disabled={isThinking || !activeThreadId} />` / `inputPreviewSlot=<AttachmentChips items={attachments.items} onRemove={attachments.removeItem} />` を差し込み。handleSend 成功時に attachments.clearAll() を呼ぶ。
- **MessageArea.tsx forwarding**: props に `inputToolbarSlot? / inputPreviewSlot?: React.ReactNode` を追加し、InputBar の `toolbarSlot={inputToolbarSlot} previewSlot={inputPreviewSlot}` に forward。InputBar 自体は変更不要 (Phase 35 で予約済の toolbarSlot / previewSlot を消費するだけ)。
- **theme.css 拡張**: `.chat-attach-btn:hover:not(:disabled) { color/border-color: var(--color-accent) }` + `.chat-attach-btn:focus-visible { outline: 2px solid var(--color-accent) }` (UI-SPEC §Accent Reserved-For Extension #8)、`.chat-attach-remove-btn:hover { color: var(--color-destructive) }` + `:focus-visible` (UI-SPEC §Color §Destructive #1)。**新規 CSS 変数追加なし** (UI-SPEC Checker #1 厳守)。
- **TypeScript strict 互換性確認**: `bunx tsc --noEmit` を Task 1/2/3 各完了後に実行し全て exit 0。既存コードへの regression なし (ChatMessage の新フィールドは optional、ChatRequest の attachments も optional)。

## Task Commits

各タスクは feat 1 commit ずつ (本 plan は TDD 指定なし — frontend unit test infra 未整備のため、verification は型チェック + 静的 grep + Plan 07 e2e に委ねる):

1. **Task 1: types.ts + client.ts** — `83641a5` (feat: AttachmentMeta / ModelInfo types and postAttachments / deleteAttachment client wrappers)
2. **Task 2: useAttachments hook + AttachmentButton + AttachmentChips + theme.css** — `24ca9b4` (feat: useAttachments hook + AttachmentButton / AttachmentChips components + theme hover/focus styles)
3. **Task 3: ChatApp.tsx + MessageArea.tsx 配線** — `fb90c1d` (feat: wire useAttachments + AttachmentButton/Chips into ChatApp; forward InputBar slots through MessageArea; add drop overlay + paste listener + validation banner)

## Files Created/Modified

**Created:**
- `frontend/src/hooks/useAttachments.ts` (182 行) — 3 入り口統一 staging hook
- `frontend/src/components/AttachmentButton.tsx` (83 行) — 📎 button + hidden file input
- `frontend/src/components/AttachmentChips.tsx` (154 行) — staging chip 描画

**Modified:**
- `frontend/src/types.ts` (165 → 197 行, +32 行) — AttachmentMeta + ModelInfo + ChatMessage.additional_kwargs + ChatRequest.attachments
- `frontend/src/api/client.ts` (215 → 249 行, +34 行) — AttachmentMeta import + postAttachments + deleteAttachment
- `frontend/src/components/ChatApp.tsx` (201 → 332 行, +131/-3 行) — 全配線 (詳細は Accomplishments §)
- `frontend/src/components/MessageArea.tsx` (430 → 437 行, +7/-2 行) — inputToolbarSlot / inputPreviewSlot props 追加 + InputBar への forward
- `frontend/src/theme.css` (614 → 636 行, +22 行) — .chat-attach-btn / .chat-attach-remove-btn の hover/focus style

## Decisions Made

- **× 削除ボタンに class .chat-attach-remove-btn を付与**: 当初 plan 案では `[role="listitem"] button[aria-label$="を添付から削除"]:hover` というセレクタを theme.css に追加する案だったが、既存 ThreadSidebar 等の `role="listitem"` 要素と specificity 上競合する恐れがあったため、`.chat-attach-remove-btn` という dedicated class 名で隔離した。Plan 文の「セレクタ衝突の場合は class 名付与の代案も可」に明記された通り。AttachmentChips.tsx の ImageChip / FileChip 両方の × ボタンに同じ class を付与し、theme.css 側で `:hover { color: var(--color-destructive) }` / `:focus-visible { outline: 2px solid var(--color-accent) }` を定義。
- **selectedModelInfo は本 plan で null 固定**: useAttachments の第 2 引数 `selectedModelInfo: ModelInfo | null` は将来 useModels hook (Plan 06) で実装される予定の vision_limits pre-validate 用。本 plan では Header からの伝達経路がまだないため null を渡し、size/ext の最小 validate のみ適用。Plan 06 で useModels の戻り値を ChatApp で取得 → useAttachments の第 2 引数に流すだけで vision_limits 連携が有効化される後方互換設計とした。
- **useChat への attachments 引き渡しは Plan 06 へ**: 本 plan では handleSend 内で attachments.clearAll() を呼ぶのみ。useChat の sendMessage 引数を拡張して getReadyItems() を payload に乗せる責務は Plan 06 (frontend → REST → worker への e2e 連動) に明示的に分離。これにより本 plan の scope が「staging UI 完成」に収束し、各 plan の責務境界が明確になった。
- **drop zone listener は ChatApp root div に集約**: 当初 plan 案でも明記されているが、実装時にも InputBar / MessageArea の中ではなく ChatApp の最外殻 div (rootRef) に onDragOver/onDrop を付与した。これにより MessageArea のスクロール領域や InputBar の textarea focus 状態に依らず drop が拾える。InputBar 単体には drop を付けず Phase 35 slot 契約を壊さない (Plan 文 Step 3「InputBar.tsx は本 plan で修正しない」を厳守)。
- **paste listener は document level**: textarea focus 中に限定せず document.addEventListener('paste', ...) で常時拾う。これにより画像コピー直後に focus が他要素にあっても upload が動く。useEffect cleanup で removeListener を確実に外し、コンポーネント unmount 時の memory leak を回避。
- **validationError state を useAttachments hook 内に保持**: validation 失敗 (例: 画像 6 枚目 / 100MB 超 / 未対応 ext) は staging に入れず、{file, reason} を hook 側で保持。ChatApp 側で banner として描画 + dismissValidationError で × 閉じる。複数同時失敗時は最後の reason のみ表示 (Plan 07 で UX 確認 → 必要なら Plan 06 以降で配列化)。
- **新規 CSS 変数追加ゼロを厳格適用**: UI-SPEC Checker #1 (`grep -E '^\s*--' frontend/src/theme.css` の件数が Phase 35 完了時点と同じ) を遵守。すべての色は Phase 35 既存 semantic token (--color-accent / --color-destructive / --color-accent-subtle / --color-border / --color-text / --color-text-muted / --color-surface)、すべての spacing は --space-1/2/3、すべての radius は --radius-md/full で表現。`grep "^\+.*--color-" frontend/src/theme.css | grep -v "var(--color-"` が 0 行を確認 (新規 token 定義行がないこと)。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] × 削除ボタンの CSS セレクタ衝突を class 名付与で解決**

- **Found during:** Task 2 GREEN (theme.css への追加時)
- **Issue:** Plan 文の Step 4 では `[role="listitem"] button[aria-label$="を添付から削除"]:hover { color: var(--color-destructive); }` という属性セレクタを使う案だったが、既存 ThreadSidebar 等で `role="listitem"` を持つ要素が複数あり、specificity 上の意図しない競合の恐れがあった。Plan 文側でも「セレクタが既存 [role=\"listitem\"] と衝突する場合は class 名付与の代案も可」と明記されていた。
- **Fix:** AttachmentChips.tsx の ImageChip / FileChip 両方の × ボタンに `className="chat-attach-remove-btn"` を付与し、theme.css 側のセレクタを `.chat-attach-remove-btn:hover { color: var(--color-destructive) }` + `.chat-attach-remove-btn:focus-visible { outline: 2px solid var(--color-accent) }` に変更。dedicated class 名で specificity が安定し、既存セレクタと完全に独立。
- **Files modified:** frontend/src/components/AttachmentChips.tsx + frontend/src/theme.css (Task 2 commit に含む)
- **Verification:** `grep -n "chat-attach-remove-btn" frontend/src/components/AttachmentChips.tsx` → 2 行 (ImageChip + FileChip 両方)
- **Committed in:** `24ca9b4` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — CSS セレクタ衝突を class 化で解決)
**Impact on plan:** UI-SPEC § × 削除ボタン仕様は完全に維持 (hover destructive + focus-visible accent + aria-label)。class 名追加は theme.css の specificity 安定化のための実装最適化のみで、見た目・動作・a11y に変化なし。

## Issues Encountered

- **bunx tsc 初回実行時の依存解決**: `bunx tsc --noEmit` を Task 1 完了直後に実行した時、bun が typescript パッケージを resolve/download するため初回は出力が `Resolving dependencies / Resolved, downloaded and extracted [2] / Saved lockfile` のみで停止。2 回目以降は通常通り型チェック実行。これは bun の仕様 (依存物の lazy install) によるもので、Plan の verification gate には影響なし。
- **Edit tool の system-reminder で複数回 Read 要求**: types.ts / client.ts / MessageArea.tsx / ChatApp.tsx に対する複数の Edit 操作中に、READ-BEFORE-EDIT reminder が送られたが、実際にはすべての編集が反映されていた (grep / Read で確認済)。reminder は遅延通知の可能性があり、実際の編集成功と矛盾していた。コミットされたファイル内容で正しく動作することを git diff で確認。

## Threat Flags

なし — Plan の `<threat_model>` (T-36-05-01〜08) はすべて Plan 内で対処済 / accept disposition:

- **T-36-05-01 (Tampering: 実行可能ファイル受け入れ)**: AttachmentButton.tsx の DEFAULT_ACCEPT で extension allowlist + サーバー側 (Plan 03) で extension allowlist。SPA 内 fetch のみで browser 実行は起きない。**mitigate**.
- **T-36-05-02 (Information Disclosure: validationError が path 露出)**: useAttachments の validation reason は filename + 理由のみ、path を含めない。**mitigate**.
- **T-36-05-03 (DoS: 大量ファイル一括 upload)**: useAttachments の MAX_IMAGES_PER_MESSAGE=5 + IMAGE_MAX_BYTES=10MB / TEXT_MAX_BYTES=100MB を hook 内で enforce。サーバー側 (Plan 03) も 100MB cap。**mitigate**.
- **T-36-05-04 (Spoofing: activeThreadId 差し替え)**: useParams (URL) → activeThreadId のみ受け付ける。サーバー側 (Plan 03) で github_login と thread 所有者 mismatch なら 404 / 403 を返す realpath guard 二段防御済。**mitigate**.
- **T-36-05-05 (Tampering: 同一 file 複数 upload)**: localId=crypto.randomUUID() で各 staging item を独立扱い、既存 chip と衝突しない。**mitigate**.
- **T-36-05-06 (XSS: filename に <script> 等)**: AttachmentChips の filename render は React text node (auto-escape)、dangerouslySetInnerHTML 未使用。`alt={item.name}` も React が escape。**mitigate**.
- **T-36-05-07 (Info Disclosure: 別ユーザー thread 画像取得)**: ImageChip の src URL は `/api/threads/{threadId}/attachments/{storage_name}` で、サーバー側 (Plan 03) が JWT payload の github_login 配下しか resolve しない realpath guard 済。**mitigate**.
- **T-36-05-08 (Tampering: src URL を browser 外で取得)**: credentials:include が要るので JWT cookie を持つブラウザからのみアクセス可能。社内 200 名環境で追加リスク低い。**accept**.

新規 surface 追加なし — frontend hook + 2 components + ChatApp 配線のみで、外部公開 API 増加なし (POST/GET/DELETE は Plan 03 の既存 surface を呼ぶだけ)。

## User Setup Required

None - 本 plan は frontend 層のみで、外部サービス・環境変数の追加なし。docker compose で起動済みの api / worker / postgres / redis / frontend (bun) がそのまま動作。`docker compose exec frontend bun run typecheck` (or `bunx tsc --noEmit`) で型チェック PASS を確認可能。

## Next Phase Readiness

- **Plan 06 (Wave 5 — useModels + Header model selector + useChat attachments forwarding + bubble AttachmentChipRow + VisionWarningBanner)**: 本 plan で staging UI が完成し、useAttachments.getReadyItems() で送信可能な D-14 dict の配列が取得可能。Plan 06 は (1) useModels hook 新規作成、(2) ChatApp で useModels の戻り値から selectedModelInfo を取得 → useAttachments の第 2 引数に流す → vision_limits pre-validate が有効化、(3) useChat の sendMessage 引数に attachments を追加 → ChatRequest.attachments に乗せる → 既に Plan 03/04 で配線済の REST → worker → SDK e2e フローが完成、(4) MessageArea bubble 内 AttachmentChipRow を追加 (additional_kwargs.attachments を見て読み取り専用 chip 描画)、(5) VisionWarningBanner を InputBar warningSlot (Plan 06 で InputBar に追加) に差し込み、を実装する。
- **Plan 07 (Wave 6 — chrome-devtools MCP smoke + integration check)**: 本 plan の 3 入り口 (📎 click / drag-drop overlay / Ctrl+V paste) + chip 表示 + × 削除 → DELETE → サーバーから消える、を chromium MCP で目視確認し、UI-SPEC Checker Acceptance Criteria 全 15 項目を検証する。
- **Blocker**: なし — Wave 4 完了 gate すべて GREEN (TypeScript 型チェック PASS / 3 commit / 静的 grep done 条件全達成)、Wave 5 (Plan 06) 着手 OK。
- **Open Issues**: useChat への attachments 引き渡しは Plan 06 で実装。SuperChat / Gem / Canvas / DebateChat の各アプリでの useAttachments 採用は CONTEXT.md Claude's Discretion (ChatApp 中心) に従い、Plan 06/07 段階で必要に応じて planner が判断。

## Self-Check: PASSED

- ✅ `frontend/src/hooks/useAttachments.ts` exists (182 行) — `ls /home/parallels/workspaces/copilot-langgraph/.claude/worktrees/agent-a5d8848e/frontend/src/hooks/useAttachments.ts` → found
- ✅ `frontend/src/components/AttachmentButton.tsx` exists (83 行) — `ls ...AttachmentButton.tsx` → found
- ✅ `frontend/src/components/AttachmentChips.tsx` exists (154 行) — `ls ...AttachmentChips.tsx` → found
- ✅ `frontend/src/types.ts` has AttachmentMeta + ModelInfo + ChatMessage.additional_kwargs + ChatRequest.attachments — `grep -n "export interface AttachmentMeta\|export interface ModelInfo\|additional_kwargs\|attachments?: AttachmentMeta" frontend/src/types.ts` → 4 定義検出
- ✅ `frontend/src/api/client.ts` exports postAttachments + deleteAttachment — `grep -n "export const postAttachments\|export const deleteAttachment\|AttachmentMeta" frontend/src/api/client.ts` → 4 行
- ✅ `frontend/src/components/ChatApp.tsx` wires useAttachments + AttachmentButton + AttachmentChips — `grep -n "useAttachments\|AttachmentButton\|AttachmentChips" frontend/src/components/ChatApp.tsx` → 6 行 (import 3 + use 1 + JSX 2)
- ✅ `frontend/src/components/ChatApp.tsx` has drop/paste listeners — `grep -n "onDragOver\|onDrop\|addEventListener('paste'" frontend/src/components/ChatApp.tsx` → 5 行
- ✅ `frontend/src/components/MessageArea.tsx` forwards inputToolbarSlot / inputPreviewSlot to InputBar — `grep -n "toolbarSlot=\|previewSlot=" frontend/src/components/MessageArea.tsx` → 2 行 (InputBar の toolbarSlot={inputToolbarSlot} / previewSlot={inputPreviewSlot})
- ✅ `frontend/src/components/MessageArea.tsx` has inputToolbarSlot / inputPreviewSlot props in interface + destructure — `grep -n "inputToolbarSlot\|inputPreviewSlot" frontend/src/components/MessageArea.tsx` → 4 行
- ✅ `frontend/src/theme.css` has chat-attach-btn hover/focus + chat-attach-remove-btn hover/focus — `grep -n "chat-attach" frontend/src/theme.css` → 5 行
- ✅ 新規 CSS 変数追加ゼロ — `git diff ed1637c..HEAD frontend/src/theme.css | grep "^+" | grep -E "^\+\s*--color-" | grep -v "var(--color-"` → 0 行
- ✅ TypeScript strict 互換 — `cd frontend && bunx tsc --noEmit` → exit 0
- ✅ Commit `83641a5` (Task 1 feat) reachable — `git log --oneline | grep "83641a5"` → found
- ✅ Commit `24ca9b4` (Task 2 feat) reachable — `git log --oneline | grep "24ca9b4"` → found
- ✅ Commit `fb90c1d` (Task 3 feat) reachable — `git log --oneline | grep "fb90c1d"` → found
- ✅ Stub patterns (TODO/FIXME/placeholder) は新規/変更ファイルにゼロ — useAttachments hook の `selectedModelInfo: null` 固定は明示的に Plan 06 で有効化される設計済 (stub ではなく後方互換 API)

---

*Phase: 36-text-code-image-multimodal*
*Plan: 05 (Wave 4)*
*Completed: 2026-04-24 — Wave 4 完了, Plan 06 (Wave 5 useModels + useChat attachments forwarding + bubble chip + VisionWarningBanner) 着手 OK*
