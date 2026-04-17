---
phase: 27-askuserquestion-ai-ui
reviewed: 2026-04-17T12:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - app/jobs/handlers/langgraph_handler.py
  - app/utils/system_prompt.py
  - frontend/src/components/CanvasChatApp.tsx
  - frontend/src/components/ChatApp.tsx
  - frontend/src/components/DebateChatApp.tsx
  - frontend/src/components/GemChatApp.tsx
  - frontend/src/components/MessageArea.tsx
  - frontend/src/components/QuestionPanel.tsx
  - frontend/src/components/SuperChatApp.tsx
  - frontend/src/hooks/useChat.ts
  - frontend/src/types.ts
findings:
  critical: 0
  warning: 5
  info: 2
  total: 7
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-04-17T12:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 27 adds AskUserQuestion (AUQ) protocol support: an AI-to-user question flow using `<ask_user_question>` XML tags parsed from AI responses. The backend injects the AUQ protocol instructions into system prompts, the frontend parses the tag, renders a `QuestionPanel` component in the input area, and sends answers back as structured text.

The core flow is well-structured. The new `QuestionPanel` component handles single/multi/text question types with free-text fallback. `parseAUQ` in `QuestionPanel.tsx` correctly extracts and parses the JSON payload. `useChat.ts` integrates AUQ detection into the existing `parseJobResult` pipeline and exposes `pendingQuestion` / `handleQuestionSubmit` to all chat app components.

Key concerns: (1) `QuestionPanel` hardcodes dark-theme colors for several style elements, causing poor contrast in light mode; (2) `handleQuestionSubmit` relies on stale closure for `activeThreadId` instead of passing it explicitly; (3) backend handlers silently swallow exceptions during Gem info lookup and canvas upsert.

## Warnings

### WR-01: handleQuestionSubmit does not pass threadId explicitly

**File:** `frontend/src/hooks/useChat.ts:328`
**Issue:** `handleQuestionSubmit` calls `sendMessage(text)` without an explicit `threadId` argument. The `sendMessage` function then falls back to `activeThreadId` captured in its closure. While in practice `activeThreadId` should be set when a question is pending (questions only appear during active conversations), this pattern is inconsistent with how every other caller in the codebase passes `threadId` explicitly to avoid stale closure bugs. The codebase already has comments explaining this pattern (e.g., ChatApp.tsx:99-102).
**Fix:**
```typescript
const handleQuestionSubmit = useCallback((answers: Record<string, string>) => {
  setPendingQuestion(null);
  const text = Object.entries(answers)
    .filter(([, v]) => v)
    .map(([q, a]) => `${q}：${a}`)
    .join('\n');
  sendMessage(text, activeThreadId ?? undefined);
}, [sendMessage, activeThreadId]);
```

### WR-02: QuestionPanel headerBadge hardcodes dark-theme colors

**File:** `frontend/src/components/QuestionPanel.tsx:248-256`
**Issue:** The `headerBadge` style uses hardcoded dark-theme colors (`background: '#1e2a3a'`, `border: '1px solid #2a3a4a'`, `color: '#60a5fa'`) regardless of the `isDark` parameter. In light mode, this renders a dark blue badge on a white background, which is visually inconsistent with the rest of the UI.
**Fix:**
```typescript
headerBadge: {
  background: isDark ? '#1e2a3a' : '#e8f0fe',
  border: `1px solid ${isDark ? '#2a3a4a' : '#b0c4de'}`,
  color: isDark ? '#60a5fa' : '#0366d6',
  fontSize: 10,
  fontWeight: 600,
  padding: '4px 8px',
  borderRadius: 4,
  letterSpacing: '0.05em',
} satisfies CSSProperties,
```

### WR-03: QuestionPanel optionSelected hardcodes dark-theme background

**File:** `frontend/src/components/QuestionPanel.tsx:304-306`
**Issue:** `optionSelected` uses `background: '#0f1f0f'` (very dark green) and `border: '1px solid #22c55e'`. In light mode, this dark green background creates poor readability against light-colored text.
**Fix:**
```typescript
optionSelected: {
  background: isDark ? '#0f1f0f' : '#f0fdf4',
  border: '1px solid #22c55e',
} satisfies CSSProperties,
```

### WR-04: QuestionPanel submitDisabled hardcodes dark-theme colors

**File:** `frontend/src/components/QuestionPanel.tsx:378-381`
**Issue:** `submitDisabled` uses `background: '#1a2a1a'` and `color: '#2a4a2a'`, both dark-theme-only values. In light mode the disabled button will appear as a nearly black rectangle.
**Fix:**
```typescript
submitDisabled: {
  background: isDark ? '#1a2a1a' : '#e5e7eb',
  color: isDark ? '#2a4a2a' : '#9ca3af',
  cursor: 'default',
} satisfies CSSProperties,
```

### WR-05: Silent exception swallowing in _get_gem_info

**File:** `app/jobs/handlers/langgraph_handler.py:41-42`
**Issue:** The `_get_gem_info` function catches all exceptions with a bare `except: pass`, returning None values. Database connection failures, query syntax errors, or permission issues are completely hidden. This makes production debugging very difficult when Gem-related features silently degrade.
**Fix:**
```python
import logging

logger = logging.getLogger(__name__)

async def _get_gem_info(...):
    try:
        ...
    except Exception as e:
        logger.warning("Failed to fetch gem info for thread %s: %s", thread_id, e)
    return None, None, None, None, None
```

## Info

### IN-01: Non-null assertion on optional prop

**File:** `frontend/src/components/MessageArea.tsx:386`
**Issue:** `onQuestionSubmit!` uses a TypeScript non-null assertion operator, but `onQuestionSubmit` is declared as optional in `MessageAreaProps`. All current callers provide both `pendingQuestion` and `onQuestionSubmit` together (from `useChat` hook), so this is safe in practice. However, a future caller could provide `pendingQuestion` without `onQuestionSubmit`, causing a runtime crash.
**Fix:** Add a guard or make the prop required when `pendingQuestion` is provided:
```typescript
onSubmit={onQuestionSubmit ?? (() => {})}
```

### IN-02: Duplicate comment line

**File:** `frontend/src/hooks/useChat.ts:2-3`
**Issue:** Lines 2 and 3 are identical: `// sendMessage with SSE completion + polling fallback.`
**Fix:** Remove the duplicate line.

---

_Reviewed: 2026-04-17T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
