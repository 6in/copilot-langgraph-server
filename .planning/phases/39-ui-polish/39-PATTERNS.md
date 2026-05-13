# Phase 39: UI バグ潰し + Polish 枠 - Pattern Map

**Mapped:** 2026-05-13
**Files analyzed:** 15 (修正 12 / 新規 3)
**Analogs found:** 14 / 15

D-12 上限ポリシーで scope freeze 済み。analog 探索は確定リスト分のみ。

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/adr/0053-mermaid-source-default-rationale.md` (新規) | adr-doc | docs | `docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md` | exact (同カテゴリ Frontend・UI、同類 UI/UX rationale ADR) |
| `frontend/src/components/MermaidBlock.tsx` (修正) | component | request-response | `frontend/src/components/MermaidBlock.tsx:1-7` 自身の冒頭コメント | exact (in-place rewrite) |
| `frontend/src/theme.css` (修正) | styles | static-css | `frontend/src/theme.css:147-169` (Phase 35 既存 `.cs-message--incoming` override 群) | exact (同レイヤー / 同ブロック追補) |
| `app/jobs/job_store.py` (修正) | service | CRUD + dead-code-removal | `app/jobs/job_store.py:25-31, 39-78` 自身の現役メソッド (`save_result` / `push_turn` / `get_tokens` 等) | exact (in-place trim) |
| `app/jobs/notifier.py` (温存 / 確認のみ) | service | event-driven | 既存呼び出し元 `app/jobs/notifier.py:28,37` | exact (no-change verification) |
| `tests/test_sse.py::test_sse_done_signal` (書き直し or 削除) | test | request-response | `tests/test_sse.py:9-32` (`test_sse_already_done`) | exact (重複候補) |
| `tests/test_job_store.py` (テスト 2 件削除) | test | CRUD | `tests/test_job_store.py:17-48` (残す `test_save_and_get` / `test_get_missing` / `test_notify_no_queue`) | exact (同 file 内の生存テスト) |
| `frontend/src/components/{ChatApp,SuperChatApp,GemChatApp,CanvasChatApp,DebateChatApp}.tsx` (5 files, 1 行追加) | component | prop-passing | `frontend/src/components/MessageArea.tsx:36, 53, 379-386` (props 受け取り + `handleAskMeWrapped`) | exact (callback wiring) |
| `frontend/src/hooks/useThreads.ts` (interface 1 行追加) | hook-types | type-export | `frontend/src/hooks/useThreads.ts:14-24` 自身の `UseThreadsReturn` interface | exact (interface 追補) |
| `frontend/src/contexts/ThemeContext.ts` (1 word 追加) | types | type-export | `frontend/src/contexts/ThemeContext.ts:8` 自身の `export const ThemeContext` | exact (同 file 内に既存 export pattern) |
| `frontend/src/components/AttachmentButton.tsx` (props 追加 + tooltip 出し分け) | component | request-response | 自 file L7-11 (`AttachmentButtonProps`) + L45-46 (`aria-label / title`) | exact (in-place interface 拡張) |
| `frontend/src/hooks/useAttachments.ts` (validation 文言 props 受け渡し) | hook | event-driven | `frontend/src/hooks/useAttachments.ts:87-93` (`upload` early-return) | exact (in-place) |
| `tests/test_mcp_server.py` (cwd= 引数削除 6 件) | test | static-fix | 同 file 内既存修正後シグネチャ呼び出し (例 L293 削除後の `await claude_code(prompt="test")`) | exact (6 行同一 pattern) |
| `tests/test_generate_mcp_artifacts.py` (assert 数値 6→8) | test | static-fix | 同 file 内 `test_load_tools_has_six_tools` (L37-49) | exact (in-place) |
| Phase 36 由来 pre-existing 27 failures (D-10 / 5-6 パターン) | test | mock pattern 更新 | `tests/conftest.py:8-12` (`jwt_cookie` fixture)、`tests/test_graph.py:10-15` (mock llm) | role-match (パターンは既存、適用 site が複数) |
| `.planning/phases/39-ui-polish/deferred-items.md` (新規空 file) | doc | docs | `.planning/phases/38-worker-dl/deferred-items.md` / `.planning/phases/36-text-code-image-multimodal/deferred-items.md` | exact (同形式) |

---

## Pattern Assignments

### `docs/adr/0053-mermaid-source-default-rationale.md` (新規 ADR / Frontend・UI)

**Analog:** `docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md`

**ヘッダー pattern** (Analog L1-5 から踏襲):
```markdown
# 0053. Mermaid View デフォルトを Source 固定とする (UIFIX-01)

**Date:** 2026-05-13
**Status:** Accepted
```

**カテゴリ pattern:** `docs/adr/INDEX.md` の Frontend・UI セクション (現在 17 件) に追加される番号 0053。INDEX.md は pre-commit hook (`scripts/generate_adr_index.py`) で自動再生成されるため手書き不要。

**典型 ADR 構造** (Analog 0040 から踏襲):
- `## Context` — 現象 + 根本原因候補列挙
- `## Decision` — `'source'` default 恒久化 / View 復帰の defer / コメント参照ルール
- `## Alternatives Considered` — iframe srcdoc / Web Worker / queue 制御 / mermaid.renderAsync
- `## Consequences` (Positive / Trade-offs) — UX 影響 / 安定性 / 技術負債
- `## Related` — ADR-0037 / ADR-0040 / `.planning/todos/pending/2026-04-16-mermaid-view-os.md`

**Note:** CLAUDE.md D-15 ルール — ADR 起票後の `.planning/patterns.md` 追記は **手動判断**。Phase 39 では「Mermaid 既存 pattern (L231-236) を再強調するだけ」のため追記不要、ADR への pointer のみで十分。

---

### `frontend/src/components/MermaidBlock.tsx` (修正: 冒頭コメント 1-2 行追加)

**Analog:** 自 file `MermaidBlock.tsx:1-7` (現状コメントブロック)

**Imports pattern** (L9-13、変更しない):
```typescript
import { useState, useCallback, useRef, useEffect, memo } from 'react';
import Editor from '@monaco-editor/react';
import mermaid from 'mermaid';
import { toPng } from 'html-to-image';
import type { Theme } from '../contexts/ThemeContext';   // ← D-08 の Theme export 修正でこの行が通る
```

**Core pattern — 冒頭コメント形式** (L1-7 現状):
```typescript
// frontend/src/components/MermaidBlock.tsx
// Renders Mermaid diagram from code block with View/Source toggle.
// Lazy-loaded from MarkdownMessage to avoid loading mermaid (~1MB) upfront.
//
// Default: Source mode with editable Monaco Editor.
// View mode renders on demand using dangerouslySetInnerHTML.
// Source edits are local only — not persisted to chat messages.
```

**追加方針 (Phase 39):** Pitfall 6 (RESEARCH L337-342) に従い **1-2 行 + ADR-0053 link** に厳格に収める。下記の通り 2 行のみを末尾 (現状 L7 直後) に追加:
```typescript
// Why source-default: View-default で複数 mermaid ブロック同時 render が OS-level hang を
// 起こすため (Phase 39 / UIFIX-01)。恒久修正候補は ADR-0053 参照、v6.1+ spike 予定。
```

---

### `frontend/src/theme.css` (修正: CSS override 1-3 行追加)

**Analog:** 同 file L147-169 (Phase 35 既存「Monaco editor — break out of chatscope bubble width constraint」ブロック)

**Imports pattern:** N/A (CSS).

**Auth pattern:** N/A.

**Core pattern — 既存 chatscope override ブロック** (L147-169):
```css
/* ============================================================
   Monaco editor — break out of chatscope bubble width constraint
   ============================================================ */

/* Incoming messages: stretch to full available width so Monaco isn't constrained by text width */
.cs-message--incoming {
  max-width: 100% !important;
  width: 100% !important;
}

.cs-message--incoming .cs-message__content-wrapper,
.cs-message--incoming .cs-message__content,
.cs-message--incoming .cs-message__custom-content {
  max-width: 100% !important;
  width: 100% !important;
  box-sizing: border-box;
}

/* pre elements inside incoming messages must also stretch so CollapsibleCodeBlock fills the bubble */
.cs-message--incoming pre {
  width: 100%;
  max-width: 100%;
}
```

**Phase 39 追補候補 (RESEARCH L230-236 / Code Examples L401-409):**
```css
/* CollapsibleCodeBlock の最外 div が必ず親バルーンの幅を引き継ぐ担保。
   chatscope の .cs-message__custom-content の display:flex / fit-content 子要素として
   潰れる現象を防ぐ。 */
.cs-message--incoming .cs-message__custom-content > div {
  width: 100%;
}
```

**重要な制約 (D-02 / Pitfall 1-2):**
- `!important` は **既存ルールと同じ程度に据え置き**。新規 selector で抗争しない (specificity が足りなければ `.cs-message--single` / `--first` / `--last` を AND で書き足す方が先)。
- **`.cs-message--incoming` prefix を必ず付ける** (outgoing バルーンを巻き込まない、Pitfall 2)。
- 値は 100% / max-width 100% のみ、CollapsibleCodeBlock 単体に `min-width` / `max-width` を打ち込まない (D-02)。
- Wave 1 冒頭で chrome-devtools (`http://127.0.0.1:9222`) reality-check → 1 行か複数 selector かを確定 (A1 / Open Question 1)。

---

### `app/jobs/job_store.py` (修正: dead code 削除 + notify() no-op stub 化)

**Analog:** 自 file L25-31 (`save_result` の最小 async method) + L39-78 (`push_turn` / `get_tokens` 等の生存メソッド)

**Imports pattern** (L1-5、`asyncio` 削除を検討):
```python
import asyncio   # ← self.queues / asyncio.Queue 撤去後は不要、削除候補
import json
from typing import Optional

from redis.asyncio import Redis
```

**Core pattern — 削除対象** (L13, 15-23, 33-37):
```python
class JobStore:
    """Stores job results in Redis and manages asyncio.Queue signals for SSE."""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.queues: dict[str, asyncio.Queue] = {}   # ← 削除

    def register_sse(self, job_id: str) -> asyncio.Queue:   # ← 削除
        queue: asyncio.Queue = asyncio.Queue()
        self.queues[job_id] = queue
        return queue

    def unregister_sse(self, job_id: str) -> None:   # ← 削除
        self.queues.pop(job_id, None)

    async def notify(self, job_id: str, status: str, **extra) -> None:
        """Put a status event onto the SSE queue if one is registered."""
        if job_id in self.queues:   # ← この枝を削除、body を no-op stub に
            event = {"status": status, **extra}
            await self.queues[job_id].put(event)
```

**Phase 39 修正後形 (D-06 推奨 = no-op stub 残置 / Pitfall 3):**
```python
class JobStore:
    """Stores job results in Redis. SSE は Redis polling 経路に統一済 (Phase 39 / UIFIX-03)。
    notify() / register_sse / unregister_sse は in-memory queue 用の dead code として削除。
    notify() のみ notifier.py 経由の呼び出し互換のため no-op stub で残置。"""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def notify(self, job_id: str, status: str, **extra) -> None:
        """No-op stub (Phase 39 UIFIX-03 D-06)。in-memory queue 経路は廃止済。
        notifier.py が表面 API 維持のため呼び出しているが、production SSE は Redis polling
        (app/api/routes/chat.py:219-251) で完結している。"""
        return None
```

**残す pattern (変更なし):**
- `save_result` (L25-31)
- `push_turn` / `push_token` (L39-48)
- `get_tokens` / `get_turns` (L50-58)
- `push_tool_event` / `clear_tool_event` / `get_tool_event` (L60-73)
- `get` (L75-78)

---

### `app/jobs/notifier.py` (温存 / 確認のみ)

**Analog:** 自 file 全体 (`BaseNotifier` / `WebNotifier` / `build_notifier`)

**唯一の保証ポイント** (L23-37、変更しない):
```python
class WebNotifier(BaseNotifier):
    """Notifier that signals the SSE queue via JobStore."""

    def __init__(self, job_id: str, job_store: JobStore):
        self.job_id = job_id
        self.job_store = job_store

    async def progress(self, status: str) -> None:
        await self.job_store.notify(self.job_id, status)   # ← no-op stub に変わるが signature 互換

    async def send_turn(self, name: str, content: str) -> None:
        await self.job_store.push_turn(self.job_id, name, content)

    async def send_token(self, token: str) -> None:
        await self.job_store.push_token(self.job_id, token)

    async def done(self) -> None:
        await self.job_store.notify(self.job_id, "done")   # ← no-op stub に変わる
```

**確認方法 (Validation):** `git diff main..HEAD -- app/jobs/notifier.py` の出力が 0 行であること。

---

### `tests/test_sse.py` (書き直し: test_sse_done_signal を Redis polling mock に / 401 治す)

**Analog:** 自 file L9-32 (`test_sse_already_done`)

**Imports pattern** (L1-6、変更しない):
```python
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
```

**Core pattern — 残るテストの形** (`test_sse_already_done` L9-32):
```python
async def test_sse_already_done(mock_job_store, mock_arq_redis):
    """SSE endpoint returns immediate done event if job already complete (ASYNC-06)."""
    from app.api.main import app

    mock_job_store.get = AsyncMock(return_value={"status": "done", "result": "done"})
    app.state.job_store = mock_job_store
    app.state.arq_redis = mock_arq_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/chat/j1/stream")

    assert resp.status_code == 200
    # ... SSE response 検証
```

**Phase 39 修正方針 (RESEARCH L448-477):**
- 両テストとも `auth_cookies` fixture を渡して 401 を解消 (production の `chat.py:198 Depends(get_jwt_payload)` を満たす)。
- `test_sse_done_signal` は Redis polling を mock する形に書き直す (`mock_job_store.get` に `side_effect=[None, done]`、`get_turns` / `get_tokens` / `get_tool_event` を空 list / None で AsyncMock)。
- `test_sse_already_done` と本質的に重複と判断すれば削除 (D-04)。本リサーチでは「side_effect 列で polling 経路もカバーする」差分があるため削除より「書き直し」を推奨。

**JWT cookie fixture pattern (新規 or `conftest.py` 既存利用):**
既存 `tests/conftest.py:8-12` に `jwt_cookie` fixture あり:
```python
@pytest.fixture
def jwt_cookie():
    """A valid JWT session cookie value for use in chat endpoint tests."""
    from app.auth.jwt_utils import create_jwt
    return create_jwt("ghu_test_token_for_chat")
```
これを再利用する (`AsyncClient(... , cookies={"session": jwt_cookie})`)。RESEARCH L256-266 の `auth_cookies` 提案は同等品 — 既存 fixture と整合させる方が D-12 上限ポリシーと一致。

---

### `tests/test_job_store.py` (削除: `test_register_and_notify` / `test_unregister_sse`)

**Analog:** 自 file L17-48 (残す `test_save_and_get` / `test_get_missing` / `test_notify_no_queue`)

**残すテストの形** (L43-48):
```python
@pytest.mark.asyncio
async def test_notify_no_queue(mock_redis):
    """JobStore.notify() with no registered SSE queue does not raise (ASYNC-05)."""
    store = JobStore(mock_redis)
    # Must not raise
    await store.notify("no-such-job", "done")
```

**Phase 39 修正方針:**
- L52-60 `test_register_and_notify` 削除 (`register_sse` 撤去のため意味喪失)
- L64-72 `test_unregister_sse` 削除 (同上)
- `test_notify_no_queue` は **「no-op stub が raise しない」契約のテスト**として残す (asserts simplified、文言は ASYNC-05 → UIFIX-03 stub に更新可)

---

### `frontend/src/components/{ChatApp,SuperChatApp,GemChatApp,CanvasChatApp,DebateChatApp}.tsx` (5 files, 1 行追加)

**Analog (callback wiring):** `frontend/src/components/MessageArea.tsx:53, 379-386` (`onAskMe` prop 受け取り + `handleAskMeWrapped`)

**InputBar 描画条件** (`InputBar.tsx:164-165`、変更しない):
```typescript
{/* AskMe ボタン: onAskMe prop が渡された時かつ thinking でない時のみ描画 */}
{onAskMe && !isThinking && (
  <button ...>AskMe</button>
)}
```

**MessageArea 内の callback 完結** (L377-386):
```typescript
// AUQ suffix 付与は MessageArea 側の責務（Pitfall 4）
// InputBar の onAskMe は opaque callback として受け取る
const handleAskMeWrapped = onAskMe
  ? () => {
      const text = inputValue.trim();
      if (!text) return;
      handleSendWrapped(text + AUQ_SUFFIX);
      setInputValue('');
    }
  : undefined;
```

**親 chat app の現状 (ChatApp.tsx L337-358 で確認):**
```tsx
<MessageArea
  messages={messages}
  isThinking={isThinking}
  streamPreview={streamPreview}
  onSend={handleSend}
  onCancel={cancelJob}
  pendingQuestion={pendingQuestion}
  onQuestionSubmit={handleQuestionSubmit}
  activeThreadId={activeThreadId}
  // ← ここに onAskMe={...} が無いため AskMe ボタンが常に消える
  inputToolbarSlot={...}
  inputPreviewSlot={...}
/>
```

**Phase 39 修正方針 (5 files 共通 / D-07):**
親側からは「ボタン表示意図」を伝える truthy callback で十分:
```tsx
onAskMe={() => { /* AUQ trigger flag — handler は MessageArea 内で完結 */ }}
```

**修正対象 file:line:**
- `ChatApp.tsx:337-358` の `<MessageArea>` props block
- `SuperChatApp.tsx:293-...`
- `GemChatApp.tsx:207-...`
- `CanvasChatApp.tsx:305-...`
- `DebateChatApp.tsx:782-...`

---

### `frontend/src/hooks/useThreads.ts` (interface 1 行追加)

**Analog:** 自 file L14-24 (`UseThreadsReturn` interface)

**Imports pattern** (L1-12、変更しない):
```typescript
import { useCallback, useEffect, useState } from 'react';
import {
  listThreads, createThread, deleteThread as apiDeleteThread, loadThreadMessages,
} from '../api/client';
import type { ThreadInfo, ChatMessage } from '../types';
```

**Core pattern — 現状の `UseThreadsReturn`** (L14-24):
```typescript
interface UseThreadsReturn {
  threads: ThreadInfo[];
  activeThreadId: string | null;
  messages: ChatMessage[];
  isLoadingMessages: boolean;
  switchThread: (threadId: string) => Promise<void>;
  createNewThread: (gemId?: string | null) => Promise<string>;
  removeThread: (threadId: string) => Promise<void>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  refreshThreads: () => Promise<void>;
}
```

**実装側は既に存在** (L76-84、変更しない / Pitfall 4):
```typescript
const bulkRemoveThreads = useCallback(async (threadIds: string[]) => {
  await Promise.all(threadIds.map((id) => apiDeleteThread(id)));
  const idSet = new Set(threadIds);
  setThreads((prev) => prev.filter((t) => !idSet.has(t.thread_id)));
  if (activeThreadId && idSet.has(activeThreadId)) {
    setActiveThreadId(null);
    setMessages([]);
  }
}, [activeThreadId]);
```

**Phase 39 修正方針 (D-08):**
interface に 1 行追加するだけ。実装側 (L76-84) と return block (L86-97) は既に整合しているため触らない:
```typescript
interface UseThreadsReturn {
  // ...既存プロパティ...
  removeThread: (threadId: string) => Promise<void>;
  bulkRemoveThreads: (threadIds: string[]) => Promise<void>;  // ← 1 行追加
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  refreshThreads: () => Promise<void>;
}
```

---

### `frontend/src/contexts/ThemeContext.ts` (1 word 追加)

**Analog:** 自 file L8 (`export const ThemeContext = createContext<Theme>('light');`) — 既存 export pattern

**現状 (全 13 行):**
```typescript
// frontend/src/contexts/ThemeContext.ts
// Provides current theme to deeply nested components without prop drilling.

import { createContext, useContext } from 'react';

type Theme = 'light' | 'dark';                                  // ← L6: export 無し

export const ThemeContext = createContext<Theme>('light');      // ← L8: 既存 export

export function useCurrentTheme(): Theme {
  return useContext(ThemeContext);
}
```

**Phase 39 修正方針 (D-08):**
L6 に `export` キーワード 1 個追加するだけ:
```typescript
export type Theme = 'light' | 'dark';   // ← MermaidBlock.tsx:13 の `import type { Theme }` が解決
```

---

### `frontend/src/components/AttachmentButton.tsx` (props 追加 + tooltip 出し分け)

**Analog:** 自 file L7-11 (`AttachmentButtonProps`) + L41-47 (`disabled` / `aria-label` / `title`)

**Imports pattern** (L1-5、変更しない):
```typescript
import { useRef, type ChangeEvent } from 'react';
```

**Core pattern — 現状の disabled state ロジック** (L41-47):
```tsx
<button
  type="button"
  onClick={handleClick}
  disabled={disabled}
  aria-label={disabled ? '添付を追加できません（送信中）' : 'ファイルを添付'}
  title="ファイルを添付（最大 100MB / 画像は 10MB × 5 枚まで）"
  className="chat-attach-btn"
  ...
>
```

**Phase 39 修正方針 (D-11 / RESEARCH L556-580):**
Props に `disabledReason?: 'thinking' | 'no-thread'` 追加、`aria-label` / `title` を 3 状態 (no-thread / thinking / enabled) で分岐:
```typescript
export interface AttachmentButtonProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
  disabledReason?: 'thinking' | 'no-thread';   // ← 追加
  acceptedExtensions?: string[];
}

// L45-46 周辺:
aria-label={
  disabled
    ? (disabledReason === 'no-thread'
        ? 'スレッドが未作成のため添付できません'
        : '添付を追加できません（送信中）')
    : 'ファイルを添付'
}
title={
  disabled
    ? (disabledReason === 'no-thread'
        ? 'スレッドを作成してから添付してください'
        : '送信中は添付できません')
    : 'ファイルを添付（最大 100MB / 画像は 10MB × 5 枚まで）'
}
```

---

### `frontend/src/hooks/useAttachments.ts` (validation 文言を props で受け渡し)

**Analog:** 自 file L87-93 (`upload` の thread guard early-return)

**Core pattern — 現状の validation 文言** (L87-93):
```typescript
const upload = useCallback(async (files: File[]) => {
  if (!threadId) {
    if (files.length > 0) {
      setValidationError({ file: files[0], reason: 'スレッドが未作成のため添付できません。' });
    }
    return;
  }
  // ...
```

**Phase 39 修正方針 (D-11):**
- 文言自体は既に揃っている (L90 の `'スレッドが未作成のため添付できません。'`)。
- 親 chat app から `AttachmentButton` に `disabledReason={!activeThreadId ? 'no-thread' : 'thinking'}` を渡すための props 経路追加が主タスク。
- `useAttachments` 自体の変更は最小 (反映先は AttachmentButton で完結する可能性大、planner 判断)。
- **重要 (Pitfall, security V5):** `upload` 内の `if (!threadId)` ガードを残すこと (UI 側を緩めても hook が backstop)。

---

### `tests/test_mcp_server.py` (cwd= 引数削除 6 件)

**Analog:** 同 file 内修正後の呼び出し pattern (例 L293 を修正した後):
```python
await claude_code(prompt="test")   # 修正後
```

**現状 grep 実測 6 行 (RESEARCH L549 / D-09):**
- L293: `await claude_code(prompt="test", cwd="/tmp")`
- L316: `result = await claude_code(prompt="test", cwd="/tmp")`
- L341: `result = await claude_code(prompt="test", cwd="/tmp")`
- L372: `result = await claude_code(prompt="test", cwd="/tmp")`
- L394: `result = await claude_code(prompt="test", cwd="/tmp")`
- L410: `result = await claude_code(prompt="test", cwd="/tmp")`

**Phase 39 修正方針 (D-09 / Pitfall 5):**
6 行で `, cwd="/tmp"` を削除するのみ。`fastmcp` 非 install 環境では skip されるため、validation は `grep -c 'cwd=' tests/test_mcp_server.py` で 0 確認すれば足りる (RESEARCH Open Question 3)。

**Note:** CONTEXT.md D-09 / Phase 38 deferred-items.md は「7 件」と主張、grep 実測 6 件で ±1 件の乖離あり (RESEARCH Summary 確認済)。planner は実測 6 件を採用。

---

### `tests/test_generate_mcp_artifacts.py` (assert 数値 6→8)

**Analog:** 自 file L37-49 (`test_load_tools_has_six_tools`)

**Core pattern — 現状の assertion** (L37-49):
```python
def test_load_tools_has_six_tools():
    """実 YAML を読み込んで 6 ツールが返る。"""
    tools = gen.load_tools()
    assert len(tools) == 6   # ← 8 に更新
    names = [t["name"] for t in tools]
    assert names == [
        "ping", "web_search", "db_query",
        "claude_code", "execute_python", "get_current_datetime",
    ]   # ← attachments_list / attachments_extract を追加 (実際の YAML 順を要確認)
```

**Phase 39 修正方針 (D-09):**
- L40 の `== 6` を `== 8` に更新
- L41-49 の `names` list に `attachments_list` / `attachments_extract` を追加 (`config/mcp_tools.yaml` の宣言順を確認して挿入)
- **planner 注意:** 同 file L65-82 (`test_build_helper_has_four_functions`)、L121-135 (`test_build_js_order`)、L143-158 (`test_build_docs_header_and_table`) も同 6 件 list を持つため、3-4 件の数値 drift が**連鎖修正対象**。RESEARCH L544-545 で「実測で確認」と注記、planner で実行必須。

---

### Phase 36 由来 pre-existing 27 failures (D-10) — 5 パターン分類

**Analog (パターン別):**

#### Pattern A: JWT cookie 不足 (test_api_chat 3 / test_api_jobs 2 / test_sse 2 = 7 件)

**Analog:** `tests/conftest.py:8-12` (既存 `jwt_cookie` fixture) + `tests/test_api_jobs.py:1-23` (現状の `api_client` fixture 経由テスト)

**`jwt_cookie` fixture** (`tests/conftest.py:8-12`):
```python
@pytest.fixture
def jwt_cookie():
    """A valid JWT session cookie value for use in chat endpoint tests."""
    from app.auth.jwt_utils import create_jwt
    return create_jwt("ghu_test_token_for_chat")
```

**修正適用 pattern:** AsyncClient に `cookies={"session": jwt_cookie}` を渡す、または `api_client` fixture に同 cookie を初期化時に bake in。

#### Pattern B: psycopg AsyncMock パターン (test_api_chat 3 / test_worker 1 = 4 件)

**Analog:** Phase 36 deferred-items.md の説明 "DB mock 不整合 (psycopg AsyncConnection の AsyncMock パターンが現在の実装と不一致)"。具体的 analog として `tests/test_api_chat.py` 内で動いている既存の AsyncConnection mock を planner が grep で特定する。

#### Pattern C: LLM mock `astream` AsyncMock (test_graph 3 / test_worker 3 = 6 件)

**Analog:** `tests/test_graph.py:10-15` (現状の `mock_llm` fixture)
```python
@pytest.fixture
def mock_llm():
    """Mock BaseChatModel that returns a fixed AIMessage."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="mocked response"))
    return llm
```

**修正適用 pattern:** `astream` を AsyncMock ではなく async generator として mock する (`async for` 互換、Phase 31 token streaming 経路の標準パターン):
```python
async def _astream_gen(*args, **kwargs):
    yield AIMessage(content="chunk1")
    yield AIMessage(content="chunk2")
llm.astream = _astream_gen   # NOT AsyncMock
```

#### Pattern D: mock 経路 (test_debate_handler 1 / test_rpc_integration 1 / test_tool_enabled_subagent 1 / test_worker 1 = 4 件)

**Analog:** ファイル横断、planner は実測 27 failures の error message を Wave 0 で再分類しなおす (RESEARCH Wave 0 Gaps L708)。

#### Pattern E: tool catalog drift (test_tool_catalog_js 1 / test_tool_registry 1 / test_generate_mcp_artifacts 4 = 6 件)

**Analog:** D-09 と同じ — `config/mcp_tools.yaml` SSoT に対する assertion 値更新。test_generate_mcp_artifacts は D-09 で扱う 4 件と同根。test_tool_catalog_js / test_tool_registry は 6→8 同様の数値 drift か、`attachments_list` / `attachments_extract` を含めた整合性テスト更新。

**Note (RESEARCH A4):** hook scaffold env (`test_install_hooks` 4 errors) は CONTEXT.md D-10 では 4 errors と記載されているが、**実測で 4 passed (もう壊れていない)**。Phase 39 で扱う必要なし、planner は 5 パターンで進める (RESEARCH Summary L25, A4)。

---

### `.planning/phases/39-ui-polish/deferred-items.md` (新規空 file)

**Analog:** `.planning/phases/38-worker-dl/deferred-items.md` (Phase 38 で同形式採用済)

**Core pattern — Phase 38 deferred-items.md L1-6 ヘッダー:**
```markdown
# Phase 38 — Deferred Items

本 phase の plan 実行中に発見された、scope 外の pre-existing 問題を記録する。
ファイルは executor が出会った時点で書き加える。

---
```

**Phase 39 修正方針 (D-12):**
Phase 開始時に **空のヘッダーのみ**で作成 (実行中に executor が追記):
```markdown
# Phase 39 — Deferred Items

本 phase の plan 実行中に発見された、scope 外の小バグ・改善案を記録する。
D-12 上限ポリシーに従い、確定リスト (D-07..D-11) 以外で発見された項目は
ここに積み、v6.1+ で観察ベース再評価する。同一ファイル・同一テストスイートを
触る際の trivial fix も無条件で拾わず本ファイルに列挙してから判断する。

---
```

**追記 pattern (Phase 38 / 36 共通):** 各項目で「Plan XX-XX で発見された ...」見出し + 表形式 (File / Error / 由来) + 「本 plan で扱わない理由」 + 「いつ取り上げるか」を記載。

---

## Shared Patterns

### chatscope CSS override layer (Phase 35 base layer)

**Source:** `frontend/src/theme.css:147-169`
**Apply to:** UIFIX-02 (CollapsibleCodeBlock 横幅修正)

**Key rules:**
1. `!important` は既存ルールと同じ程度のみ。新規 selector で抗争しない (D-02)。
2. `.cs-message--incoming` prefix を必ず付ける (outgoing バルーンを巻き込まない / Pitfall 2)。
3. specificity 不足時は `.cs-message--single` / `--first` / `--last` を AND で書き足す (Pitfall 1)。
4. CSS variable (`--color-*` / `--radius-*` / `--space-*`) は Phase 35 base layer を再利用 — 新規 token 導入しない。
5. ※ `--cs-message-content-width` 系 token は **codebase に存在しない** (RESEARCH A6 で実測検証済、CONTEXT.md D-03 の言及は obsolete)。

---

### ADR + コード冒頭コメントの 2 段ドキュメント

**Source:** `patterns.md` "ADR + patterns.md + コード冒頭コメントの 3 段ドキュメント" + `MermaidBlock.tsx:1-7` 現状
**Apply to:** UIFIX-01

**Key rules:**
1. ADR (`docs/adr/NNNN-*.md`) で長文化、コード冒頭はポインタのみ (1-2 行 + ADR link)。
2. patterns.md 追記は **手動判断** (CLAUDE.md D-15)。Phase 39 では既存 Mermaid pattern (L231-236) で十分のため追記不要。
3. INDEX.md は `scripts/generate_adr_index.py` の pre-commit hook で自動再生成 (`scripts/install-hooks.sh` 済が前提)。
4. Pitfall 6: 冒頭コメント追記は 1-2 行に厳格に収める。ADR 要約のコピペ禁止。

---

### Pre-existing test failure を deferred-items.md に書く

**Source:** `.planning/phases/38-worker-dl/deferred-items.md` / `.planning/phases/36-text-code-image-multimodal/deferred-items.md`
**Apply to:** D-12 上限ポリシー全般 (Wave 実行中の新規発見)

**Key rules:**
1. 各項目に "本 plan で扱わない理由" + "いつ取り上げるか" を必ず書く (Phase 38 deferred L43-53 形式)。
2. 「同一ファイル / 同一テストスイートを触る際の trivial fix」も無条件で拾わず、deferred-items.md に列挙してから判断 (D-12)。
3. Pitfall 7: 10 項目を超えたら polish phase 自体が肥大化、書く粒度を再評価する。

---

### 既存 conftest.py fixture を再利用 (新規 fixture 追加抑制)

**Source:** `tests/conftest.py:8-12` (`jwt_cookie`) / L46-55 (`mock_job_store`) / L66-91 (`api_client`)
**Apply to:** D-10 Pattern A (JWT cookie 不足 7 件)

**Key rules:**
1. RESEARCH L256-266 で提案された `auth_cookies` fixture は **既存 `jwt_cookie` と機能等価** — 新規 fixture 追加せず既存を使う (D-12 上限ポリシーと一致)。
2. `mock_job_store` は L46-55 で既に存在、`register_sse` / `unregister_sse` / `notify` を MagicMock / AsyncMock で持つ — UIFIX-03 で `register_sse` / `unregister_sse` を JobStore から撤去した後は **conftest 側からも除去** (L53-54)。
3. `api_client` fixture (L66-91) は cookie 注入を持たないため、cookie 必要なテストは AsyncClient を別途立ち上げる現行パターンを継続。

---

### Cancel-safe / signature 互換契約 (notifier 不整合の予防)

**Source:** `patterns.md` "MCP ツールの Cancel-safe 例外処理" + `app/jobs/notifier.py:27-37`
**Apply to:** UIFIX-03 D-06 (notify() を no-op stub で残置)

**Key rules:**
1. `notify()` の signature を **完全互換** (`async def notify(self, job_id: str, status: str, **extra) -> None`) で残す (Pitfall 3)。
2. body は `return None` のみ — exception 投げない。`notifier.py` 4 経路 (langgraph / orchestrator / debate / iframe_rpc) からの呼び出しが silent success で通る。
3. handler 単体テストは mock で `JobStore.notify` を AsyncMock 化しているため (`conftest.py:52`)、stub 化の影響なし。

---

## No Analog Found

なし — 全 15 件で codebase 内に直接の analog が存在する。Phase 39 は新規未知要素ゼロの polish phase で、CONTEXT.md / RESEARCH.md がほぼ全ての file:line を特定済 (RESEARCH Summary 確認済)。

---

## Metadata

**Analog search scope:**
- `frontend/src/components/` (5 chat apps + InputBar / MessageArea / MermaidBlock / AttachmentButton / MarkdownMessage)
- `frontend/src/hooks/` (useThreads / useAttachments)
- `frontend/src/contexts/` (ThemeContext)
- `frontend/src/` (theme.css)
- `app/jobs/` (job_store / notifier)
- `app/api/routes/` (chat.py SSE generator)
- `tests/` (conftest / test_sse / test_job_store / test_api_chat / test_api_jobs / test_worker / test_graph / test_mcp_server / test_generate_mcp_artifacts)
- `docs/adr/` (0040 を Frontend・UI カテゴリ ADR の雛形として)
- `.planning/phases/{36, 38}/deferred-items.md`
- `.planning/patterns.md` (Mermaid / chatscope / Cancel-safe 関連 entry)

**Files scanned:** 約 25 (target files 15 + analog files 10)

**Pattern extraction date:** 2026-05-13
