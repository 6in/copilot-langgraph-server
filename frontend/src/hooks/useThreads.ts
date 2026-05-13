// frontend/src/hooks/useThreads.ts
// Thread list management: list, create, switch, delete.
// Thread list management: list, create, switch, delete.

import { useCallback, useEffect, useState } from 'react';
import {
  listThreads,
  createThread,
  deleteThread as apiDeleteThread,
  loadThreadMessages,
} from '../api/client';
import type { ThreadInfo, ChatMessage } from '../types';

interface UseThreadsReturn {
  threads: ThreadInfo[];
  activeThreadId: string | null;
  messages: ChatMessage[];
  isLoadingMessages: boolean;
  switchThread: (threadId: string) => Promise<void>;
  createNewThread: (gemId?: string | null) => Promise<string>;
  removeThread: (threadId: string) => Promise<void>;
  bulkRemoveThreads: (threadIds: string[]) => Promise<void>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  refreshThreads: () => Promise<void>;
}

export function useThreads(appId?: string, gemId?: string): UseThreadsReturn {
  const [threads, setThreads] = useState<ThreadInfo[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const refreshThreads = useCallback(async () => {
    try {
      const data = await listThreads(appId, gemId);
      setThreads(data);
    } catch {
      // DB may not be reachable if no messages have been sent yet
    }
  }, [appId, gemId]);

  // Load threads on mount
  useEffect(() => {
    refreshThreads();
  }, [refreshThreads]);

  const switchThread = useCallback(async (threadId: string) => {
    setActiveThreadId(threadId);
    setIsLoadingMessages(true);
    try {
      const msgs = await loadThreadMessages(threadId);
      setMessages(msgs);
    } catch {
      setMessages([]);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  const createNewThread = useCallback(async (gemId?: string | null): Promise<string> => {
    const { thread_id } = await createThread(gemId);
    setActiveThreadId(thread_id);
    setMessages([]);
    // Refresh thread list after a brief delay to let the first message register
    return thread_id;
  }, []);

  const removeThread = useCallback(async (threadId: string) => {
    await apiDeleteThread(threadId);
    setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
    if (activeThreadId === threadId) {
      setActiveThreadId(null);
      setMessages([]);
    }
  }, [activeThreadId]);

  const bulkRemoveThreads = useCallback(async (threadIds: string[]) => {
    await Promise.all(threadIds.map((id) => apiDeleteThread(id)));
    const idSet = new Set(threadIds);
    setThreads((prev) => prev.filter((t) => !idSet.has(t.thread_id)));
    if (activeThreadId && idSet.has(activeThreadId)) {
      setActiveThreadId(null);
      setMessages([]);
    }
  }, [activeThreadId]);

  return {
    threads,
    activeThreadId,
    messages,
    isLoadingMessages,
    switchThread,
    createNewThread,
    removeThread,
    bulkRemoveThreads,
    setMessages,
    refreshThreads,
  };
}
