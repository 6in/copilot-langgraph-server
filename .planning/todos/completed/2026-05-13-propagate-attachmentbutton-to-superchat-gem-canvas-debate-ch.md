---
created: 2026-05-13T13:45:00Z
title: AttachmentButton を SuperChat/Gem/Canvas/Debate にも展開
area: ui
files:
  - frontend/src/components/ChatApp.tsx:13,347-349
  - frontend/src/components/SuperChatApp.tsx:303
  - frontend/src/components/GemChatApp.tsx:215
  - frontend/src/components/CanvasChatApp.tsx:313
  - frontend/src/components/DebateChatApp.tsx:791
  - frontend/src/components/AttachmentButton.tsx
  - frontend/src/components/MessageArea.tsx:54,641
---

## Problem

ファイル添付用の 📎 クリップボタン (`AttachmentButton`) が **ChatApp.tsx でしか配線されていない**。SuperChat / Gem / Canvas / Debate の 4 つの chat app では UI に出ていない。

確認結果 (`grep AttachmentButton frontend/src/components/`):

- `ChatApp.tsx:13` — import 済 / `:347-349` で `<MessageArea>` の InputBar slot に挿入
- `SuperChatApp.tsx`, `GemChatApp.tsx`, `CanvasChatApp.tsx`, `DebateChatApp.tsx` — **import 0 件、配置なし**

Phase 36 (multimodal) で導入されたが ChatApp のみへの limited rollout だったらしく、Phase 39 Plan 39-05 (UIFIX-04 D-11) でも「事前 grep で AttachmentButton import が ChatApp.tsx のみと判明したため scope を 1 箇所に scope down」と SUMMARY に記録されている。結果として、SuperChat 等の chat app からファイルを添付できず、機能の存在が UI で発見不可能。

## Solution

TBD。検討案:

1. **MessageArea.tsx の InputBar slot 仕様 (L54, L641) はそのまま使えるはずなので、4 app の `<MessageArea>` 呼び出し箇所に `<AttachmentButton>` を差し込む** (推奨、ChatApp と対称化)
   - 各 app の `onAskMe={...}` の隣に `inputBarSlot` (もしくは Phase 36 で使った propキー) を渡す
   - `disabledReason` prop は Phase 39 で追加済 (`AttachmentButton.tsx`)。各 app で MODEL_SUPPORTS_ATTACHMENTS の判定があれば渡す
2. もしくは、`<AttachmentButton>` 自体を `<MessageArea>` の中に組み込み、各 app は `enableAttachments` flag だけ渡す。app 間でモデルやアプリ種別による有効/無効を切り替えやすい
3. Debate は 2 phase なので添付できる側 (人間の発言) と LLM 側で扱いを分けるか検討

関連:
- 既存 todo `2026-04-17-file-upload-download-chat-ui.md` — feature 全体の追跡 (一部 Phase 36 で実装済)
- Phase 39 Code Review WR-11 等 (もし関連指摘あれば)
- Phase 39 deferred-items.md にも記録されている可能性あり (要確認)

---

## Resolved 2026-05-13 — Phase 40 Plan 04

- Implemented in: .planning/phases/40-ui-polish-round-2-frontend-only/40-04-PLAN.md / 40-04-SUMMARY.md
- ROADMAP Success Criteria: 4 (UI-ATTACHBTN)
- Commits: bf61423, fcece63, aecf29d
- Note: Debate Chat は backend `debate_handler.py` が ChatRequest.attachments を読まないため意図的に除外 (Phase 41 Debate Document Review へ defer)
