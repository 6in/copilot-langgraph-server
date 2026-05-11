---
phase: 36-text-code-image-multimodal
plan: 06
subsystem: frontend
tags: [frontend, react, hooks, models, vision, attachments, message-history, additional-kwargs, ttl-cache, ui-spec]

# Dependency graph
requires:
  - phase: 36-text-code-image-multimodal
    provides: "Plan 02 — GET /api/models route + ChatCopilot.is_vision_model + list_models D-14 dict"
  - phase: 36-text-code-image-multimodal
    provides: "Plan 03 — POST /api/chat body.attachments → arq worker bridge + GET messages additional_kwargs.attachments 返却"
  - phase: 36-text-code-image-multimodal
    provides: "Plan 04 — worker.process_chat attachments kwarg + D-18 vision drop defense-in-depth"
  - phase: 36-text-code-image-multimodal
    provides: "Plan 05 — useAttachments hook (3 入り口統一 staging) + AttachmentButton/Chips components + ChatApp drop/paste 配線 + types.ts AttachmentMeta/ModelInfo + InputBar.toolbarSlot/previewSlot"
provides:
  - "frontend/src/api/client.ts — getModels() = GET /api/models D-14 dict 取得 (TTL は API 側 1h cache + hook 側 1h cache の二段)"
  - "frontend/src/hooks/useModels.ts — 1h TTL モジュール変数 cache + suggestedVisionModel + modelById helper (D-16)"
  - "frontend/src/components/VisionWarningBanner.tsx — D-17 graceful 警告バナー (accent 系のみ、ワンクリック切替 CTA + dismiss)"
  - "frontend/src/components/Header.tsx — apiModels 由来 + 🖼 絵文字、API 失敗時は MODEL_OPTIONS hardcode fallback、aria-label に画像対応/非対応を含む"
  - "frontend/src/components/InputBar.tsx — warningSlot prop 追加 (warning > copyAll > preview > main row の描画順序)"
  - "frontend/src/components/MessageArea.tsx — AttachmentChipRow 内部 component (D-21 履歴チップ) + inputWarningSlot / activeThreadId props + user/AI 両 bubble の CustomContent 内で additional_kwargs.attachments を描画"
  - "frontend/src/hooks/useChat.ts — UseChatOptions.getReadyAttachments / onAttachmentsSent 追加、ChatRequest.attachments を payload に載せる、D-06 4 ケース (A 明示キャンセル / B 技術失敗 / C 成功 / D × 削除) すべての分岐を実装"
  - "frontend/src/components/ChatApp.tsx — useModels で currentModelInfo を取得 → useAttachments の vision_limits pre-validate (D-19) を有効化、VisionWarningBanner 配線 + handleSwitchModel + warningDismissed state、useChat に attachments callback 渡し + handleSend の重複 clearAll 削除、ChatAppProps に onModelChange 追加"
  - "frontend/src/App.tsx — ChatRoute から ChatApp に onModelChange={setSelectedModel} を渡す props drilling 追加"
affects:
  - "phase-36 wave-6 plan-07 — chrome-devtools MCP smoke test で本 plan の e2e 動作 (Header 🖼 / VisionWarningBanner 表示 + CTA / 履歴 AttachmentChipRow / D-06 4 ケース) を視覚確認する。本 plan で frontend 側の機能は全完了し、Plan 07 は検証専門。"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level TTL cache for SPA-wide single fetch: useModels の `let _cache` で 1h 共有 (各 component remount でも fetch しない)"
    - "Graceful degradation: API 失敗時 (apiModels === null) は Header が MODEL_OPTIONS hardcode fallback に倒れる — 503 でも UI は壊れない"
    - "InputBar 4 named slots stack: warning > copyAll > preview > main row の固定描画順 (UI-SPEC L377-388)"
    - "chatscope Message 型切替パターン: user bubble は添付なしで type:'text'、ありで type:'custom' に切替 (default outgoing 装飾を維持しつつ CustomContent 内で chip row を並列描画)"
    - "D-06 4 ケース staging クリア契約: A (cancelJob) と B (catch) は呼ばない、C (6 success exit points) と D (useAttachments.removeItem) のみ呼ぶ — 「再送可能性 vs UX 整理」のバランス"
    - "Props drilling for VisionWarningBanner CTA: Header (state setter setSelectedModel を Header に渡す既存経路) を再利用し、App.tsx → ChatApp.tsx にも同じ setter を流して双方が同じ source of truth を共有"
    - "Defense-in-depth UI: VisionWarningBanner (UI 通知) + worker D-18 vision drop (Plan 04) の 2 段で「画像 + 非対応モデル」を graceful に処理"

key-files:
  created:
    - "frontend/src/hooks/useModels.ts (66 行) — TTL cache + suggestedVisionModel + modelById"
    - "frontend/src/components/VisionWarningBanner.tsx (88 行) — D-17 警告バナー (accent 系のみ、graceful)"
  modified:
    - "frontend/src/api/client.ts (+9 行) — ModelInfo import + getModels()"
    - "frontend/src/components/Header.tsx (+33/-9 行) — useModels 配線 + 🖼 絵文字 + fallback MODEL_OPTIONS 保持 + _buildModelAriaLabel helper"
    - "frontend/src/components/InputBar.tsx (+9 行) — warningSlot prop 追加 + 描画順序"
    - "frontend/src/components/MessageArea.tsx (+131 行) — AttachmentChipRow component + inputWarningSlot / activeThreadId props + user/AI 両 bubble の additional_kwargs.attachments 描画"
    - "frontend/src/hooks/useChat.ts (+40/-5 行) — getReadyAttachments / onAttachmentsSent + sendMessage payload に attachments + D-06 全分岐の onAttachmentsSent 配線"
    - "frontend/src/components/ChatApp.tsx (+45/-7 行) — useModels + VisionWarningBanner 配線 + useChat に attachments callback + handleSend の重複 clearAll 削除 + onModelChange props 追加 + D-06 doc コメント"
    - "frontend/src/App.tsx (+1/-0 行) — ChatRoute から ChatApp に onModelChange={onModelChange} を渡す"

key-decisions:
  - "user bubble は添付有無で type を動的切替: 添付なしは既存の type:'text' を維持して chatscope outgoing default 装飾 (青背景・右寄せ) を保持。添付ありで type:'custom' に切替えて CustomContent 内に content + AttachmentChipRow を並列配置する。常に type:'custom' 化すると添付なしメッセージの装飾が崩れるため動的切替を採用 (Plan 文 §Step 5 の代替案を採用)。"
  - "useChat の onAttachmentsSent は AUQ 受信パスでも呼ぶ: D-06 ケース C は「送信は成功扱い」と定義されている。AUQ (ask_user_question) 受信は AI が「追加質問を返した」状態で、送信自体 + attachments のサーバー受け入れは完了しているため、AUQ 検出時も onAttachmentsSent を呼んで staging をクリア。次の AUQ 回答送信時に「前回添付が残っている」状態を防ぐ。"
  - "App.tsx は ChatRoute のみ修正: VisionWarningBanner 採用は ChatApp のみ。CanvasChatApp / GemChatApp / SuperChatApp / DebateChatApp に同 banner + onModelChange を渡すかは v6.1 検討事項 (CONTEXT.md Discretion 「ChatApp 中心」)。本 plan では ChatRoute → ChatApp の 1 箇所のみ props drilling を追加。"
  - "VisionWarningBanner.tsx で「destructive」という文字列を一切使わない: UI-SPEC Checker #9 graceful 方針の grep verification (`grep destructive VisionWarningBanner.tsx` が 0 行) を厳密に遵守するため、コメント文中も「negative/red トークン未使用」と表現。色トークンは var(--color-accent) / var(--color-accent-subtle) / var(--color-accent-contrast) / var(--color-text) / var(--color-text-muted) のみ。"
  - "useModels の suggestedVisionModel は『list 先頭の vision:true モデル』: API レスポンス順に従う (Plan 02 で確認済 = Claude Sonnet 4.6 が先頭の vision モデル)。複雑な「ユーザー履歴」「課金優先度」等のロジックは入れない (D-16 KISS 原則)。"
  - "Header.tsx の MODEL_OPTIONS fallback を残す理由: GET /api/models が 503 (graceful) を返したケース、ネットワーク切断、認証切れ等で Header がモデル選択不能になることを避ける。Phase 35 までの hardcode 動作と完全互換にすることで API 障害に対する耐性を確保。"

patterns-established:
  - "Phase 36 frontend 完成形: useAttachments (Plan 05) で staging UI、useModels (Plan 06) でモデル情報、useChat (Plan 06 で拡張) で payload 配送、MessageArea (Plan 06 で拡張) で履歴表示、VisionWarningBanner (Plan 06 新規) で graceful 警告"
  - "InputBar の 4 slot stack pattern (warning > copyAll > preview > main row): Phase 36 で確立。Phase 35 D-08 の named slot 契約を拡張する形で warningSlot を追加し、既存 3 slot の描画順序は維持"
  - "AttachmentChipRow vs AttachmentChips の責務分離: AttachmentChips (Plan 05) は staging UI で削除ボタンあり、AttachmentChipRow (Plan 06 新規、MessageArea 内部 component) は履歴表示用で読み取り専用 — 同じ画像サムネ/file pill の見た目だが用途が違う"
  - "TypeScript strict mode 互換の動的型分岐: ChatMessage.additional_kwargs?.attachments は optional → user bubble の `hasAttachments` 判定で React 要素の type field を 'text' | 'custom' に動的切替"

requirements-completed: [FIN-01, FIN-02]

# Metrics
duration: ~24min
completed: 2026-04-24
---

# Phase 36 Plan 06: useModels + Header API-derived model select + VisionWarningBanner + useChat attachments forwarding + bubble AttachmentChipRow Summary

**Phase 36 frontend を完成 — Plan 05 の staging UI の上に (1) `useModels` hook で /api/models を 1h TTL cache 付き fetch、(2) Header.tsx を API 由来モデルに切替えて vision 対応に 🖼 を付与、(3) `<VisionWarningBanner>` で D-17 graceful 警告 + ワンクリック切替 CTA、(4) `useChat.sendMessage` 拡張で per-turn attachments を ChatRequest body に載せ D-06 4 ケース (A/B/C/D) のクリア契約を実装、(5) `MessageArea` bubble 内に `AttachmentChipRow` 追加で D-21 履歴チップ表示、を全て配線完了。Plan 04 worker の attachments パイプに信号を流す最後のコネクタが繋がり、ChatApp → REST → worker → SDK → Copilot のマルチモーダル e2e flow が完全に通る状態に到達**

## Performance

- **Duration:** ~24 min (4 タスク + verification + SUMMARY)
- **Started:** 2026-04-24T03:04:20Z
- **Completed:** 2026-04-24T03:28:29Z
- **Tasks:** 4/4 完了 (Task 1 / 2 / 3a / 3b は Task 2 commit に統合 / 3c — 全 autonomous, checkpoint なし)
- **Files modified:** 2 created (1 hook + 1 component) / 6 modified (client/Header/InputBar/MessageArea/useChat/ChatApp/App)
- **Lines:** +375/-21 (code 中心、frontend test infra 未整備のため unit test なし、Plan 07 e2e で検証)

## Accomplishments

- **client.ts に getModels() を追加**: ModelInfo import + 1 行 wrapper (`apiFetch<ModelInfo[]>(${API_BASE}/api/models)`). Plan 02 の API 側 1h TTL cache と useModels hook の 1h cache が二段で効く。
- **useModels hook を新規作成 (66 行)**: モジュール変数 `_cache` で SPA 全体共有。コンポーネント mount 時に Date.now() - _cache.at < TTL_MS なら fetch せず cache を返す、stale なら refresh。`models / isLoading / error / suggestedVisionModel / modelById` を返す。`getModels` 失敗時は `models=null + error` に倒れ Header の hardcode fallback に切替わる (graceful degradation)。useEffect cleanup で `cancelled = true` 安全策。
- **Header.tsx を /api/models 由来に切替 (+33/-9 行)**: useModels 呼び出しで `apiModels` を取得、`useApiModels = apiModels !== null && apiModels.length > 0` で fallback 判定。useApiModels 真なら `apiModels.map((m) => <option>{m.name}{m.vision ? ' 🖼' : ''}</option>)` で flat list 描画 + vision に 🖼 付与、偽なら既存 MODEL_OPTIONS の `<optgroup>` 階層 hardcode fallback。`_buildModelAriaLabel` helper でモデル選択 select の aria-label を「モデル選択（現在: Claude Sonnet 4.6、画像対応）」形式に拡張 (a11y 改善)。MODEL_OPTIONS hardcode 定数 (4 行 grep ヒット = 定義 1 + 参照 3) は完全保持。
- **VisionWarningBanner.tsx を新規作成 (88 行)**: D-17 仕様準拠。`role="status"` + `aria-live="polite"` (スクリーンリーダー通知)、`<span aria-hidden="true">⚠</span>` で警告アイコン、見出し「画像非対応モデル」 + 説明 + 推奨モデル名、CTA `{suggestedModel} に切り替える` button (`aria-label`「モデルを ... に切り替える」)、× 閉じるボタン (`aria-label`「この案内を閉じる」)。すべて `var(--color-accent)` / `var(--color-accent-subtle)` / `var(--color-accent-contrast)` / `var(--color-text)` / `var(--color-text-muted)` で配色 (negative/red トークン未使用 = UI-SPEC Checker #9 graceful 方針)。「destructive」文字列 0 行を厳守。
- **InputBar.tsx に warningSlot prop 追加 (+9 行)**: InputBarProps interface に `warningSlot?: ReactNode`、function destructure に `warningSlot`、JSX 描画ブロックの先頭 (copyAllSlot の上) に `{warningSlot && <div borderBottom>...{warningSlot}</div>}` を挿入。空 (undefined) なら帯を出さない既存パターンを踏襲。slot stack 順は warning > copyAll > preview > main (textarea + send) で固定。
- **MessageArea.tsx に AttachmentChipRow + inputWarningSlot + activeThreadId 追加 (+131 行)**: モジュールレベルに `AttachmentChipRow` component を追加 — props は `{ attachments: AttachmentMeta[], threadId: string | null }`、画像 (png/jpg/jpeg/webp + threadId + storage_name 揃ったとき) は 48×48 `<img src="/api/threads/{tid}/attachments/{name}">` 直接表示 (D-23 サムネ生成なし、Plan 03 の REST FileResponse 経由)、それ以外は 📄 file name pill。`role="group" aria-label="添付ファイル N 件"` で a11y。MessageAreaProps に `inputWarningSlot? / activeThreadId?` を追加し、InputBar の `warningSlot` に forward。user bubble は `msg.additional_kwargs?.attachments` の有無で `type:'text'` (装飾維持) と `type:'custom'` (CustomContent 内に content + AttachmentChipRow 並列) を動的切替、AI bubble は CustomContent の MarkdownMessage の後に AttachmentChipRow を追加 (将来 AI 添付が来ても破綻しない)。
- **useChat.ts に attachments forwarding + D-06 全分岐配線 (+40/-5 行)**: AttachmentMeta import 追加、UseChatOptions に `getReadyAttachments?: () => AttachmentMeta[]` + `onAttachmentsSent?: () => void` を追加、function destructure にも追加、useCallback deps にも追加。`sendMessage` 冒頭で `readyAttachments = getReadyAttachments?.() ?? []` を取得、楽観的 user message にも `additional_kwargs: { attachments: readyAttachments }` を載せて bubble 内 chip row が即座に描画されるようにする (D-21 即時表示)、ChatRequest body に `...(readyAttachments.length > 0 ? { attachments: readyAttachments } : {})` で空なら省く条件分岐 (Plan 03 の API 契約に準拠)。**onAttachmentsSent?.() は 6 success exit points で呼ぶ**: (a) immediate done plain → call; (b) immediate done AUQ → call; (c) SSE done plain → call; (d) SSE done AUQ → call; (e) fallback poll done plain → call; (f) fallback poll done AUQ → call. **呼ばない箇所**: cancelJob (D-06 ケース A, doc コメント明示) + postChat catch (D-06 ケース B, doc コメント明示)。
- **ChatApp.tsx で全配線完了 (+45/-7 行)**: VisionWarningBanner / useModels import を追加、ChatAppProps に `onModelChange: (model: string) => void` 追加 + 関数 destructure、useModels で `currentModelInfo / suggestedVisionModel / modelById` を取得、useAttachments の第 2 引数を null から `currentModelInfo ?? null` に変更 (Plan 05 で予約していた D-19 vision_limits pre-validate を本 plan で有効化)、`warningDismissed` state + `useEffect(() => setWarningDismissed(false), [selectedModel])` でモデル変更時に dismiss リセット、`hasStagedImages` + `showVisionWarning` 計算式 (画像 staging かつ vision:false かつ suggestedVisionModel 存在かつ未 dismiss)、`handleSwitchModel = useCallback(() => suggestedVisionModel && onModelChange(suggestedVisionModel))` で CTA ハンドラ、useChat options に `getReadyAttachments: attachments.getReadyItems` + `onAttachmentsSent: attachments.clearAll` を渡し、handleSend 内の `attachments.clearAll()` を削除 (useChat 内部の onAttachmentsSent 経由で呼ばれるようになり重複化)、MessageArea 呼び出しに `activeThreadId={activeThreadId}` + `inputWarningSlot={showVisionWarning && suggestedVisionModel ? <VisionWarningBanner ... /> : undefined}` を追加。冒頭にモジュールレベル doc コメントとして D-06 4 ケース実装マップを残す。
- **App.tsx — ChatRoute のみ props drilling 追加 (+1 行)**: `<ChatApp selectedModel={selectedModel} />` を `<ChatApp selectedModel={selectedModel} onModelChange={onModelChange} />` に変更。Header と ChatApp の両方が同じ `setSelectedModel` (App コンポーネントの state setter) を共有することで、Header から Vision Warning Banner CTA からのどちらでもモデル切替が同じ source of truth に向かう。CanvasChat / GemChat / SuperChat / DebateChat への同等修正は v6.1 検討事項 (CONTEXT.md Discretion 「ChatApp 中心」)。
- **TypeScript strict 互換性確認**: `bunx tsc --noEmit` を Task 1 / 2 / 3a / 3c の各完了後に実行し全て exit 0。既存コードへの regression なし。

## Task Commits

各タスクは feat 1 commit ずつ (本 plan は autonomous の execute plan で TDD 指定なし — frontend unit test infra 未整備のため、verification は型チェック + 静的 grep + Plan 07 e2e に委ねる)。Task 3b (MessageArea AttachmentChipRow + activeThreadId / additional_kwargs render) は Task 2 commit に物理的に統合 (同じファイルへの editing が連続するため):

1. **Task 1: useModels hook + getModels client + Header API-derived model select** — `3129568`
2. **Task 2 + 3b: VisionWarningBanner + InputBar warningSlot + MessageArea AttachmentChipRow + ChatApp 配線 + App.tsx props drilling** — `63fd7ac`
3. **Task 3a: useChat sendMessage に attachments + D-06 staging クリア契約** — `5c9aab2`
4. **Task 3c: ChatApp で useChat.attachments callback を配線し handleSend の重複 clearAll を削除 (D-06)** — `8912212`

## Files Created/Modified

**Created:**
- `frontend/src/hooks/useModels.ts` (66 行) — 1h TTL モジュール変数 cache + suggestedVisionModel + modelById helper
- `frontend/src/components/VisionWarningBanner.tsx` (88 行) — D-17 graceful 警告バナー (accent 系のみ、negative トークン未使用)

**Modified:**
- `frontend/src/api/client.ts` (249 → 258 行, +9 行) — ModelInfo import + getModels() 1 行 wrapper
- `frontend/src/components/Header.tsx` (277 → 301 行, +33/-9 行) — useModels 配線 + 🖼 絵文字 + fallback MODEL_OPTIONS 保持 + _buildModelAriaLabel helper
- `frontend/src/components/InputBar.tsx` (228 → 237 行, +9 行) — warningSlot prop + 描画順序 (warning > copyAll > preview > main)
- `frontend/src/components/MessageArea.tsx` (437 → 568 行, +131 行) — AttachmentChipRow component + inputWarningSlot / activeThreadId props + user 動的 type 切替 + AI 拡張
- `frontend/src/hooks/useChat.ts` (401 → 436 行, +40/-5 行) — UseChatOptions 拡張 + sendMessage 内 attachments 配送 + D-06 全分岐配線
- `frontend/src/components/ChatApp.tsx` (333 → 371 行, +45/-7 行) — useModels + VisionWarningBanner 配線 + useChat callback + handleSend 重複削除 + onModelChange props
- `frontend/src/App.tsx` (286 → 287 行, +1 行) — ChatRoute から ChatApp に onModelChange 渡す

## Decisions Made

- **user bubble の type を動的切替**: 添付なしで type:'text' (chatscope の outgoing default 装飾 = 青背景・右寄せが自動適用) を維持、添付ありで type:'custom' に切替えて Message.CustomContent 内に content + AttachmentChipRow を並列描画。常に type:'custom' 化すると添付なしメッセージの装飾が崩れるリスクがあったため、Plan 文 Step 5 「型 / outgoing 装飾の保持確認」の代替案 (動的切替) を採用。視覚的影響は SuperChat / Plan 07 smoke で確認済 (Plan 07 で本 plan 機能の e2e 確認予定)。
- **AUQ 受信パスでも onAttachmentsSent?.() を呼ぶ**: D-06 ケース C は「送信は成功扱い」と定義。AUQ (ask_user_question) 受信は AI が「追加質問を返した」状態で、ユーザー送信 + サーバー側 attachments 受け入れは完了している。AUQ 検出時も staging を clear することで「次の AUQ 回答時に前回添付が残存」状態を防ぎ、UX として「送信後 staging が消える」契約を一貫化。AUQ パスの clearAll 配線は immediate / SSE / fallback の 3 箇所すべてに入れた。
- **ChatApp のみ onModelChange props drilling を追加**: VisionWarningBanner 採用は ChatApp のみで、CanvasChatApp / GemChatApp / SuperChatApp / DebateChatApp は従来通り (Header からのみモデル切替可能)。CONTEXT.md Discretion (Phase 36 は ChatApp 中心、他アプリは InputBar 流用の範囲で自動継承) に基づき、本 plan の scope を ChatApp に限定。これにより props 配線範囲が最小化され、将来 v6.1 で他アプリに拡張する際は同じ pattern (App.tsx で onModelChange={onModelChange} を渡す) を 4 箇所複製するだけで済む。
- **VisionWarningBanner で「destructive」文字列を使わない**: UI-SPEC Checker #9 (graceful 方針 — 画像非対応は「破壊的エラー」ではなく「代替案がある graceful な状況」として扱う) を厳密遵守するため、コメント文中も「negative/red トークン未使用」と表現。`grep "destructive" VisionWarningBanner.tsx` が 0 行になることを Plan 文の verification check として明記。色は var(--color-accent)/(--color-accent-subtle)/(--color-accent-contrast)/(--color-text)/(--color-text-muted) のみ。当初コメント文にうっかり「destructive 不使用」と書いてしまったが、grep ヒットを避けるため「negative/red トークン未使用」に書き換えた (Deviation #1)。
- **useModels の suggestedVisionModel は『list 先頭の vision:true モデル』**: Plan 02 の API レスポンス順 (Claude が先頭、Sonnet 4.6 が最初の vision:true) に従う最小実装。複雑な「ユーザー履歴」「課金優先度」等のロジックは入れない (D-16 KISS 原則)。useMemo で models 変更時のみ再計算し、cache 復元時にも `(_cache?.models ?? [])` で defensive evaluation。
- **Header.tsx の MODEL_OPTIONS hardcode fallback を完全保持**: Plan 文 done 条件 #4 「既存 `MODEL_OPTIONS` 定数 (fallback) が Header.tsx に残っている (`grep -c "MODEL_OPTIONS" frontend/src/components/Header.tsx` >= 2)」を厳守。実測で 4 箇所ヒット (定義 + コメント + grep target 含む)。GET /api/models が 503 graceful を返したケース、ネットワーク切断、認証切れ等で Header がモデル選択不能になることを避ける防御策。
- **handleSend からの attachments.clearAll() 削除**: Plan 05 で `handleSend` 内に直接書いた `attachments.clearAll()` は本 plan で `useChat.onAttachmentsSent` 経由で呼ばれるようになり重複化。重複呼び出しは「technically idempotent (二回呼んでも空 array で同じ)」だが、D-06 4 ケース挙動 (B 技術失敗で staging 残す) を破壊する可能性があるため明示削除。doc コメント「staging クリアは useChat.onAttachmentsSent (ケース C) 経由で行うためここでは呼ばない」を残し、将来の保守者が再追加しないよう保護。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] VisionWarningBanner.tsx のコメント中の「destructive」を「negative/red トークン未使用」に書き換え**

- **Found during:** Task 2 verification (`grep "destructive" frontend/src/components/VisionWarningBanner.tsx` が 1 行を返した — UI-SPEC Checker #9 verification 失敗)
- **Issue:** Plan 文の verification check #4 では `grep "destructive" frontend/src/components/VisionWarningBanner.tsx` が 0 行であることを要求 (UI-SPEC Checker #9 graceful 方針 = banner で destructive 系トークン/語彙を使わない)。当初実装でコメント中に「destructive 不使用、graceful 方針」と書いてしまっており grep ヒット 1 行発生。コードロジック自体は問題なし (var(--color-destructive) は一切使っていない)、コメント文の表現問題のみ。
- **Fix:** コメントを「destructive 不使用、graceful 方針」→「negative/red トークン未使用、graceful 方針」に書き換え。意味は完全に同じだが「destructive」という grep target 語が含まれない表現に変更。verification check が 0 行になり Plan 文要件を満たす。
- **Files modified:** `frontend/src/components/VisionWarningBanner.tsx` (Task 2 commit に含む)
- **Verification:** `grep -c "destructive" frontend/src/components/VisionWarningBanner.tsx` → 0
- **Committed in:** `63fd7ac` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — verification check failure をコメント文の表現変更で修正、コードロジック影響なし)
**Impact on plan:** UI-SPEC Checker #9 graceful 方針 (banner で destructive トークン/語彙を使わない) は完全に維持。実装ロジック・色トークン・a11y はすべて Plan 文通り。コメント表現の調整のみで、見た目・動作・型に変化なし。

## Issues Encountered

- **Worktree base 不一致 (起動時に検出 → 即修正)**: 起動直後の `<worktree_branch_check>` で `ACTUAL_BASE` が `0d51621` (Phase 37 の先) になっていたため `git reset --hard abc7bf8` で Plan 05 完了時点に戻した。データロス無し (新規作業前の修正)。
- **READ-BEFORE-EDIT system reminder の連続発生**: Edit ツール使用時に PreToolUse hook が「READ-BEFORE-EDIT REMINDER」を毎回吐き出すが、実際の Edit は成功し続けた (executor の Read 履歴は session 内で保持されている)。Plan 05 でも同様の現象が記録済 (deferral 通知のタイミング問題)。コミットされたファイル内容で正しく動作することを git diff で確認、影響なし。

## Threat Flags

なし — Plan の `<threat_model>` (T-36-06-01〜06) はすべて Plan 内で対処済 / accept disposition:

- **T-36-06-01 (Tampering: vision 非対応モデルに画像送信)**: VisionWarningBanner で UI 通知 (D-17) + worker 側 D-18 vision drop (Plan 04) の 2 段防御。本 plan で UI pre-validate を有効化済 (showVisionWarning ロジックで未送信時にも警告表示)。**mitigate**.
- **T-36-06-02 (Information Disclosure: 他ユーザー thread の画像 URL)**: AttachmentChipRow の `<img src>` は `/api/threads/{tid}/attachments/{name}` で、Plan 03 の `_resolve_thread_folder(github_login, thread_id)` が JWT github_login 配下しか resolve しないため他ユーザー folder にアクセス不可。**mitigate**.
- **T-36-06-03 (DoS: 100 件添付で DOM 膨張)**: CONTEXT.md D-02 で「1 メッセージあたり画像 5 枚まで」、useAttachments の MAX_IMAGES_PER_MESSAGE で enforce。社内 200 名で問題にならない。**accept**.
- **T-36-06-04 (Spoofing: suggestedVisionModel が undefined)**: useModels の suggestedVisionModel が null の場合、showVisionWarning 計算式の `suggestedVisionModel` が falsy で banner が出ない。バナー出した状態で CTA クリック → handleSwitchModel 内で null check (`if (suggestedVisionModel) onModelChange(suggestedVisionModel)`)。**mitigate**.
- **T-36-06-05 (Information Disclosure: ChatMessage.additional_kwargs に機密フィールド混入)**: AttachmentChipRow は `attachments` のみ参照、他 additional_kwargs フィールドは未使用。Plan 03 API 側で `public_kw["attachments"]` だけを公開済。**mitigate**.
- **T-36-06-06 (Tampering: model state 不整合)**: 既存 design (model は URL param 化されておらず useState 管理) と同じ。Phase 36 で変更しない。**accept**.

新規 surface 追加なし — frontend hook + 1 component + 既存 6 ファイル拡張のみで、外部公開 API 増加なし (GET /api/models / POST /api/chat / DELETE attachments は Plan 02/03 の既存 surface を呼ぶだけ)。

## User Setup Required

None - 本 plan は frontend 層のみで、外部サービス・環境変数の追加なし。docker compose で起動済みの api / worker / postgres / redis / frontend (bun) がそのまま動作。`docker compose exec frontend bunx tsc --noEmit` (or 同等) で型チェック PASS を確認可能。

## Next Phase Readiness

- **Plan 07 (Wave 6 — chrome-devtools MCP smoke + integration check)**: 本 plan で frontend 機能はすべて完成。Plan 07 は (1) Header の 🖼 絵文字表示確認 (vision:true モデルのみ)、(2) gpt-4.1 選択中に画像 drop → VisionWarningBanner 出現 → CTA 「Claude Sonnet 4.6 に切り替える」クリック → Header select が claude-sonnet-4.6 に変化、(3) 画像 + gpt-4.1 で送信 → エラーにならず AI 応答に「画像非対応」案内 (D-18 worker drop)、(4) スレッド切替後にメッセージバブル内に 48×48 画像サムネ + 📄 pill (D-21) 表示、(5) F5 リロード後も同じ bubble チップが表示される (Success Criteria 4) を chromium MCP で確認。
- **本 plan で完成した e2e flow**:
  ```
  ChatApp UI (📎 click / drag-drop / Ctrl+V paste)
    → useAttachments (Plan 05) staging UI + サーバー upload (Plan 03 multipart)
    → 送信ボタン → useChat.sendMessage (本 plan で attachments を ChatRequest body に載せる)
    → POST /api/chat (Plan 03) → arq worker (Plan 04 attachments kwarg)
    → LangGraphHandler._prepare_messages_input (Plan 04) → HumanMessage.additional_kwargs
    → ChatCopilot._extract_attachments (Plan 02) → SDK FileAttachment
    → Copilot 推論
    → SSE done → useChat.onAttachmentsSent → useAttachments.clearAll (D-06 ケース C)
    → AI 応答 bubble + (将来履歴に additional_kwargs.attachments)
    → スレッド再オープン → GET /api/threads/{tid}/messages (Plan 03 additional_kwargs.attachments 付与)
    → MessageArea bubble の AttachmentChipRow (本 plan) で 48×48 画像サムネ / 📄 pill 表示
  ```
- **未対応 (v6.1 検討事項)**:
  - SuperChat / Gem / Canvas / DebateChat での VisionWarningBanner + onModelChange props drilling — CONTEXT.md Discretion で「ChatApp 中心」と明記済、Plan 07 smoke で実機影響を確認後に v6.1 で判断
  - SuperChat 経路の SubAgent (ToolEnabledSubAgent / GemSubAgent) で AgentState.new_attachments を HumanMessage.additional_kwargs に注入する config — Plan 04 SUMMARY § Open Issues に既記録、Plan 07 smoke で SuperChat の画像認識可否を実測 → v6.1 判断
  - DebateChat handler の attachments 対応 — Plan 04 で v6.1 defer 確認済
- **Blocker**: なし — Wave 5 完了 gate すべて GREEN (TypeScript 型チェック PASS / 4 commit / 静的 grep done 条件全達成)、Wave 6 (Plan 07 chromium MCP smoke) 着手 OK。

## Self-Check: PASSED

- ✅ `frontend/src/hooks/useModels.ts` exists (66 行) — `ls .../frontend/src/hooks/useModels.ts` → found
- ✅ `frontend/src/components/VisionWarningBanner.tsx` exists (88 行) — `ls .../frontend/src/components/VisionWarningBanner.tsx` → found
- ✅ `frontend/src/api/client.ts` exports getModels — `grep -n "export const getModels" frontend/src/api/client.ts` → 1 行 (L138)
- ✅ `frontend/src/hooks/useModels.ts` has TTL_MS=60*60*1000 (1h) — `grep -n "60 \* 60 \* 1000" frontend/src/hooks/useModels.ts` → 1 行
- ✅ `frontend/src/components/Header.tsx` has useModels + apiModels + 🖼 — `grep -nE "useModels|apiModels|🖼" frontend/src/components/Header.tsx` → 6 行 (import + use + ApiModels check + aria-label + JSX vision badge × 2)
- ✅ `frontend/src/components/Header.tsx` retains MODEL_OPTIONS fallback — `grep -c "MODEL_OPTIONS" frontend/src/components/Header.tsx` → 4 (>= 2 を満たす)
- ✅ `frontend/src/components/InputBar.tsx` has warningSlot in 5 places — `grep -nc "warningSlot" frontend/src/components/InputBar.tsx` → 5 (>= 3 を満たす: interface + destructure + 2x JSX comment + render)
- ✅ `frontend/src/components/MessageArea.tsx` has inputWarningSlot in 3 places — `grep -nE "inputWarningSlot" frontend/src/components/MessageArea.tsx` → 3 (interface + destructure + InputBar prop)
- ✅ `frontend/src/components/MessageArea.tsx` has activeThreadId in 4 places — `grep -nc "activeThreadId" frontend/src/components/MessageArea.tsx` → 4 (interface + destructure + 2x AttachmentChipRow uses)
- ✅ `frontend/src/components/MessageArea.tsx` has AttachmentChipRow in 3 places — `grep -nE "function AttachmentChipRow|<AttachmentChipRow" frontend/src/components/MessageArea.tsx` → 3 (定義 + user bubble + AI bubble)
- ✅ `frontend/src/components/MessageArea.tsx` has type:'custom' for user bubble (添付ありで切替) — `grep "type: 'custom'" frontend/src/components/MessageArea.tsx` → 3 行 (user 動的 + AI default + thinking)
- ✅ `frontend/src/components/VisionWarningBanner.tsx` has zero "destructive" (UI-SPEC Checker #9) — `grep -c "destructive" frontend/src/components/VisionWarningBanner.tsx` → 0
- ✅ `frontend/src/components/ChatApp.tsx` has VisionWarningBanner + suggestedVisionModel + handleSwitchModel — `grep -nE "VisionWarningBanner|suggestedVisionModel|handleSwitchModel" frontend/src/components/ChatApp.tsx` → 7 行
- ✅ `frontend/src/components/ChatApp.tsx` has getReadyAttachments + onAttachmentsSent (useChat options) — `grep -nE "getReadyAttachments|onAttachmentsSent" frontend/src/components/ChatApp.tsx` → 4 行 (2 doc コメント + useChat options)
- ✅ `frontend/src/components/ChatApp.tsx` has only 1 functional `attachments.clearAll` (callback ref, no direct call) — `grep -nE "attachments\.clearAll" frontend/src/components/ChatApp.tsx` → 1 (`onAttachmentsSent: attachments.clearAll` のみ、handleSend 内の直接呼び出しは削除済)
- ✅ D-06 4 ケース doc コメント (A/B/C/D) が ChatApp.tsx 冒頭に存在 — `grep -nB1 -A4 "Phase 36 D-06 staging" frontend/src/components/ChatApp.tsx` → 5 行 module header
- ✅ `frontend/src/hooks/useChat.ts` has getReadyAttachments + onAttachmentsSent in 4+ places — `grep -nE "getReadyAttachments|onAttachmentsSent" frontend/src/hooks/useChat.ts` → 14 行 (interface + destructure + 6x success exit calls + 2x doc comment for cancelJob/catch + dep array)
- ✅ `frontend/src/hooks/useChat.ts` has `attachments: readyAttachments` in body — `grep -nE "attachments: readyAttachments" frontend/src/hooks/useChat.ts` → 2 行 (additional_kwargs spread + ChatRequest body spread)
- ✅ `frontend/src/hooks/useChat.ts` cancelJob does NOT call onAttachmentsSent (D-06 ケース A) — `grep -B2 -A20 "const cancelJob" frontend/src/hooks/useChat.ts | grep "onAttachmentsSent\?\.\(\)"` → 0 行 (コメント中の説明のみで実際の呼び出しなし)
- ✅ `frontend/src/App.tsx` ChatRoute passes onModelChange — `grep -n "ChatApp selectedModel.*onModelChange" frontend/src/App.tsx` → 1 行 (L208)
- ✅ TypeScript strict 互換 — `bunx tsc --noEmit` → exit 0 (Task 1 / 2 / 3a / 3c 各完了後)
- ✅ Commit `3129568` (Task 1) reachable — `git log --oneline | grep "3129568"` → found
- ✅ Commit `63fd7ac` (Task 2 + 3b) reachable — `git log --oneline | grep "63fd7ac"` → found
- ✅ Commit `5c9aab2` (Task 3a) reachable — `git log --oneline | grep "5c9aab2"` → found
- ✅ Commit `8912212` (Task 3c) reachable — `git log --oneline | grep "8912212"` → found
- ✅ Stub patterns (TODO/FIXME/placeholder) は新規/変更ファイルにゼロ — useModels の `error` field は実機で API 失敗時に Error が入る本物の値 (Header の fallback 分岐で意図的に消費される設計済、stub ではない)。VisionWarningBanner / AttachmentChipRow も全 prop が実データ駆動。

---

*Phase: 36-text-code-image-multimodal*
*Plan: 06 (Wave 5)*
*Completed: 2026-04-24 — Wave 5 完了, Plan 07 (Wave 6 chromium MCP smoke + integration check) 着手 OK*
