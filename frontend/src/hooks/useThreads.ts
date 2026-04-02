// frontend/src/hooks/useThreads.ts
// Thread list management: list, create, switch, delete.
// Mirrors static/app.js loadThreads, createNewThread, switchThread, deleteThread.

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
  createNewThread: () => Promise<string>;
  removeThread: (threadId: string) => Promise<void>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  refreshThreads: () => Promise<void>;
}

export function useThreads(): UseThreadsReturn {
  const [threads, setThreads] = useState<ThreadInfo[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const refreshThreads = useCallback(async () => {
    try {
      const data = await listThreads();
      setThreads(data);
    } catch {
      // DB may not be reachable if no messages have been sent yet
    }
  }, []);

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

  const createNewThread = useCallback(async (): Promise<string> => {
    const { thread_id } = await createThread();
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

  return {
    threads,
    activeThreadId,
    messages,
    isLoadingMessages,
    switchThread,
    createNewThread,
    removeThread,
    setMessages,
    refreshThreads,
  };
}
