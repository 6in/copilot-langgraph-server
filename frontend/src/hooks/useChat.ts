// frontend/src/hooks/useChat.ts
// sendMessage with SSE completion + polling fallback.
// Mirrors static/app.js sendMessage (lines ~370-450).

import { useCallback, useEffect, useRef, useState } from 'react';
import { postChat, getJob, streamJob } from '../api/client';
import type { CanvasAppInfo, CanvasResult, ChatMessage } from '../types';

// Phase 17: 討論チャット結果
interface DebateTurn {
  name: string;
  content: string;
}
interface DebateResult {
  type: 'debate_result';
  debate_text: string;
  turns?: DebateTurn[];
  final_turn: number;
  max_turns: number;
  is_complete: boolean;
}

interface UseChatOptions {
  activeThreadId: string | null;
  selectedModel: string;
  selectedTaskType?: string;
  selectedMode?: 'simple' | 'super';
  agents?: string[];
  appId?: string;
  gemId?: string | null;           // Phase 15: Gem ID for chat request payload
  gemIds?: string[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  _onThreadCreated?: (threadId: string) => void;
  refreshThreads?: () => Promise<void>;
  onCanvasResponse?: (app: CanvasAppInfo) => void;  // Phase 15: Canvas response callback
  // Phase 17: 討論チャット
  participants?: string[];
  pattern?: string;
  maxTurns?: number;
  currentTurn?: number;
  onDebateResult?: (result: { debate_text: string; turns?: DebateTurn[]; final_turn: number; max_turns: number; is_complete: boolean }) => void;
}

interface UseChatReturn {
  isThinking: boolean;
  currentTool: {tool: string; query: string} | null;
  streamPreview: string;
  sendMessage: (text: string, threadId?: string) => Promise<void>;
}

// Phase 15/17: Parse job result — detect Canvas / debate_result / orchestrator_result JSON payload vs plain text.
function parseJobResult(raw: string): { text: string; canvas: CanvasResult | null; debate: DebateResult | null; agentName: string | null } {
  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.type === 'canvas') {
      const c = parsed as CanvasResult;
      const name = (parsed as { name?: string }).name ?? 'HTMLアプリ';
      const html = c.html ?? '';
      // canvashtml: custom language tag → CollapsibleCodeBlock in MarkdownMessage
      const text = `🎨 **${name}**\n\n\`\`\`canvashtml\n${html}\n\`\`\``;
      return { text, canvas: c, debate: null, agentName: null };
    }
    if (parsed && parsed.type === 'debate_result') {
      return { text: parsed.debate_text as string, canvas: null, debate: parsed as DebateResult, agentName: null };
    }
    if (parsed && parsed.type === 'orchestrator_result') {
      return { text: parsed.content as string, canvas: null, debate: null, agentName: parsed.agent_name ?? null };
    }
  } catch {
    // plain text — not JSON
  }
  return { text: raw, canvas: null, debate: null, agentName: null };
}

export function useChat({
  activeThreadId,
  selectedModel,
  selectedTaskType = 'langgraph',
  selectedMode = 'simple',
  agents,
  appId,
  gemId,
  gemIds,
  setMessages,
  refreshThreads,
  onCanvasResponse,
  participants,
  pattern,
  maxTurns,
  currentTurn,
  onDebateResult,
}: UseChatOptions): UseChatReturn {
  const [isThinking, setIsThinking] = useState(false);
  const [currentTool, setCurrentTool] = useState<{tool: string; query: string} | null>(null);
  const [streamPreview, setStreamPreview] = useState<string>('');
  const fallbackTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup fallback polling timer on unmount
  useEffect(() => {
    return () => {
      if (fallbackTimerRef.current) {
        clearInterval(fallbackTimerRef.current);
        fallbackTimerRef.current = null;
      }
    };
  }, []);

  const sendMessage = useCallback(async (text: string, threadId?: string) => {
    if (!text.trim() || isThinking) return;

    // Prefer explicitly passed threadId (avoids stale closure when caller just
    // created a new thread and the state update hasn't re-rendered yet).
    const resolvedThreadId = threadId ?? activeThreadId;
    if (!resolvedThreadId) return;

    // Optimistically add user message
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setStreamPreview('');
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
        // Phase 15: Pass gem_ids when multiple Gems are selected
        ...(gemIds && gemIds.length > 0 ? { gem_ids: gemIds } : {}),
        // Phase 17: 討論チャットフィールド
        ...(participants && participants.length > 0 ? { participants } : {}),
        ...(pattern ? { pattern } : {}),
        ...(maxTurns !== undefined ? { max_turns: maxTurns } : {}),
        ...(currentTurn !== undefined ? { current_turn: currentTurn } : {}),
      });

      // Helper: handle result raw string (Canvas / debate_result / plain text)
      const handleResult = (raw: string) => {
        const { text: resultText, canvas, debate, agentName } = parseJobResult(raw);
        if (canvas && onCanvasResponse) {
          // Canvas response: show raw text in chat + open Canvas pane
          setMessages((prev) => [...prev, { role: 'ai', content: resultText }]);
          onCanvasResponse({
            app_id: canvas.app_id,
            thread_id: resolvedThreadId,
            name: (canvas as unknown as { name?: string }).name ?? 'Canvas App',
            thread_label: null,
            html: canvas.html,
            source: 'canvas',
            deployed: false,
            deployed_at: null,
            created_at: new Date().toISOString(),
          });
        } else if (debate && onDebateResult) {
          // Phase 17: debate_result — 各エージェントの発言を個別バブルで表示
          if (debate.turns && debate.turns.length > 0) {
            setMessages((prev) => [
              ...prev,
              ...debate.turns!.map((t) => ({
                role: 'ai' as const,
                content: t.content,
                senderName: t.name,
              })),
            ]);
          } else {
            setMessages((prev) => [...prev, { role: 'ai', content: resultText }]);
          }
          onDebateResult({
            debate_text: debate.debate_text,
            turns: debate.turns,
            final_turn: debate.final_turn,
            max_turns: debate.max_turns,
            is_complete: debate.is_complete,
          });
        } else {
          setMessages((prev) => [...prev, { role: 'ai', content: resultText, ...(agentName ? { senderName: agentName } : {}) }]);
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
      // SSE で表示済みのターン数を追跡（done 時の重複防止）
      let streamedTurnCount = 0;

      es.onmessage = async (e: MessageEvent) => {
        try {
          const event = JSON.parse(e.data as string) as { status: string; turn?: { name: string; content: string }; tool?: string; query?: string; token?: string };
          if (event.status === 'token') {
            // SDK streaming=True による real-time delta（1〜4 文字/chunk）を蓄積。
            // 末尾 200 文字のみ保持して DOM 肥大化を防ぐ。
            const incoming = event.token ?? '';
            setStreamPreview((prev) => {
              const next = prev + incoming;
              return next.length > 200 ? next.slice(-200) : next;
            });
            return;
          }
          if (event.status === 'message' && event.turn) {
            // リアルタイムで各エージェントの発言を表示
            streamedTurnCount++;
            setMessages((prev) => [...prev, {
              role: 'ai' as const,
              content: event.turn!.content,
              senderName: event.turn!.name,
            }]);
          } else if (event.status === 'tool_executing') {
            const ev = event as { status: string; tool: string; query: string };
            setCurrentTool({ tool: ev.tool, query: ev.query || '' });
          } else if (event.status === 'done') {
            setCurrentTool(null);
            es.close();
            const result = await getJob(job_id);
            if (result.result) {
              const parsed = (() => { try { return JSON.parse(result.result); } catch { return null; } })();
              if (parsed?.type === 'debate_result') {
                // SSE で未表示のターンを result から補完（ストリーム失敗時のフォールバック）
                setStreamPreview('');
                const allTurns: DebateTurn[] = parsed.turns ?? [];
                if (allTurns.length > streamedTurnCount) {
                  const remaining = allTurns.slice(streamedTurnCount);
                  setMessages((prev) => [...prev, ...remaining.map((t) => ({
                    role: 'ai' as const,
                    content: t.content,
                    senderName: t.name,
                  }))]);
                }
                if (onDebateResult) {
                  onDebateResult({
                    debate_text: parsed.debate_text,
                    turns: parsed.turns,
                    final_turn: parsed.final_turn,
                    max_turns: parsed.max_turns,
                    is_complete: parsed.is_complete,
                  });
                }
              } else {
                // 通常応答: 真のストリーミング（SDK streaming=True）により streamPreview は
                // 既に応答末尾が表示されている。プレビューを消して完成メッセージに切替える。
                setStreamPreview('');
                handleResult(result.result);
              }
            } else {
              setStreamPreview('');
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
        fallbackTimerRef.current = setInterval(async () => {
          try {
            const job = await getJob(job_id);
            if (job.status === 'done' && job.result) {
              clearInterval(fallbackTimerRef.current!);
              fallbackTimerRef.current = null;
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
  }, [activeThreadId, selectedModel, selectedTaskType, selectedMode, agents, appId, gemId, gemIds, isThinking, setMessages, refreshThreads, onCanvasResponse, participants, pattern, maxTurns, currentTurn, onDebateResult]);

  return { isThinking, currentTool, streamPreview, sendMessage };
}
