// frontend/src/hooks/useChat.ts
// sendMessage with SSE completion + polling fallback.
// Mirrors static/app.js sendMessage (lines ~370-450).

import { useCallback, useState } from 'react';
import { postChat, getJob, streamJob } from '../api/client';
import type { CanvasAppInfo, CanvasResult, ChatMessage } from '../types';

interface UseChatOptions {
  activeThreadId: string | null;
  selectedModel: string;
  selectedTaskType?: string;
  selectedMode?: 'simple' | 'super';
  agents?: string[];
  appId?: string;
  gemId?: string | null;           // Phase 15: Gem ID for chat request payload
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  _onThreadCreated?: (threadId: string) => void;
  refreshThreads?: () => Promise<void>;
  onCanvasResponse?: (app: CanvasAppInfo) => void;  // Phase 15: Canvas response callback
}

interface UseChatReturn {
  isThinking: boolean;
  sendMessage: (text: string, threadId?: string) => Promise<void>;
}

// Phase 15: Parse job result — detect Canvas JSON payload vs plain text.
function parseJobResult(raw: string): { text: string; canvas: CanvasResult | null } {
  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.type === 'canvas') {
      return { text: raw, canvas: parsed as CanvasResult };
    }
  } catch {
    // plain text — not JSON
  }
  return { text: raw, canvas: null };
}

export function useChat({
  activeThreadId,
  selectedModel,
  selectedTaskType = 'langgraph',
  selectedMode = 'simple',
  agents,
  appId,
  gemId,
  setMessages,
  refreshThreads,
  onCanvasResponse,
}: UseChatOptions): UseChatReturn {
  const [isThinking, setIsThinking] = useState(false);

  const sendMessage = useCallback(async (text: string, threadId?: string) => {
    if (!text.trim() || isThinking) return;

    // Prefer explicitly passed threadId (avoids stale closure when caller just
    // created a new thread and the state update hasn't re-rendered yet).
    const resolvedThreadId = threadId ?? activeThreadId;
    if (!resolvedThreadId) return;

    // Optimistically add user message
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setIsThinking(true);

    try {
      // 1. POST /api/chat → { job_id, thread_id }
      const { job_id } = await postChat({
        message: text,
        thread_id: resolvedThreadId,
        model: selectedModel,
        task_type: selectedTaskType,
        mode: selectedMode,
        // Pass selected agents only in super mode; undefined in simple mode preserves all agents
        agents: selectedMode === 'super' ? agents : undefined,
        // Pass app_id when provided for thread scoping
        ...(appId ? { app_id: appId } : {}),
        // Phase 15: Pass gem_id when a Gem is selected
        ...(gemId ? { gem_id: gemId } : {}),
      });

      // Helper: handle result raw string (Canvas or plain text)
      const handleResult = (raw: string) => {
        const { text: resultText, canvas } = parseJobResult(raw);
        if (canvas && onCanvasResponse) {
          // Canvas response: show raw text in chat + open Canvas pane
          setMessages((prev) => [...prev, { role: 'ai', content: resultText }]);
          onCanvasResponse({
            app_id: canvas.app_id,
            thread_id: resolvedThreadId,
            name: 'Canvas App',
            html: canvas.html,
            source: 'canvas',
            deployed: false,
            deployed_at: null,
            created_at: new Date().toISOString(),
          });
        } else {
          setMessages((prev) => [...prev, { role: 'ai', content: resultText }]);
        }
      };

      // 2. Check if already done (reconnect / very fast response edge case)
      const immediate = await getJob(job_id);
      if (immediate.status === 'done' && immediate.result) {
        handleResult(immediate.result);
        setIsThinking(false);
        await refreshThreads?.();
        return;
      }

      // 3. Open SSE stream for real-time completion notification
      const es = streamJob(job_id);

      es.onmessage = async (e: MessageEvent) => {
        try {
          const { status } = JSON.parse(e.data as string) as { status: string };
          if (status === 'done') {
            es.close();
            const result = await getJob(job_id);
            if (result.result) {
              handleResult(result.result);
            }
            setIsThinking(false);
            await refreshThreads?.();
          }
          // status === 'thinking' → keep waiting
        } catch {
          // Malformed SSE data — ignore and keep listening
        }
      };

      es.onerror = () => {
        // SSE connection dropped — fall back to polling every 2 seconds
        es.close();
        const timer = setInterval(async () => {
          try {
            const job = await getJob(job_id);
            if (job.status === 'done' && job.result) {
              clearInterval(timer);
              handleResult(job.result);
              setIsThinking(false);
              await refreshThreads?.();
            }
          } catch {
            // Poll error — keep trying
          }
        }, 2000);
      };
    } catch (err) {
      // POST /api/chat failed (401 auth required, network error, etc.)
      setIsThinking(false);
      const errorMsg = err instanceof Error && err.message.includes('401')
        ? 'Session expired. Please log in again.'
        : 'Failed to send message. Please try again.';
      setMessages((prev) => [...prev, { role: 'ai', content: `⚠ ${errorMsg}` }]);
    }
  }, [activeThreadId, selectedModel, selectedTaskType, selectedMode, agents, appId, gemId, isThinking, setMessages, refreshThreads, onCanvasResponse]);

  return { isThinking, sendMessage };
}
