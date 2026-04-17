// frontend/src/hooks/useChat.ts
// sendMessage with SSE completion + polling fallback.
// sendMessage with SSE completion + polling fallback.

import { useCallback, useEffect, useRef, useState } from 'react';
import { postChat, getJob, streamJob } from '../api/client';
import type { AskUserQuestionPayload, CanvasAppInfo, CanvasResult, ChatMessage, ContextMessage } from '../types';
import { parseAUQ } from '../components/QuestionPanel';

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
  sendMessage: (text: string, threadId?: string, contextMessages?: ContextMessage[]) => Promise<void>;
  cancelJob: () => void;
  pendingQuestion: AskUserQuestionPayload | null;
  handleQuestionSubmit: (answers: Record<string, string>) => void;
}

// Phase 15/17: Parse job result — detect AUQ / Canvas / debate_result / orchestrator_result JSON payload vs plain text.
function parseJobResult(raw: string): { text: string; canvas: CanvasResult | null; debate: DebateResult | null; agentName: string | null; askUserQuestion: AskUserQuestionPayload | null } {
  // AUQ check FIRST — before any JSON.parse attempt.
  // The AI may return <ask_user_question> as plain text or wrapped in other content.
  if (raw.includes('<ask_user_question>')) {
    const auq = parseAUQ(raw);
    if (auq) {
      // Strip the AUQ tag portion; keep any surrounding text as the message
      const textWithout = raw.replace(/<ask_user_question>[\s\S]*?<\/ask_user_question>/g, '').trim();
      return { text: textWithout, canvas: null, debate: null, agentName: null, askUserQuestion: auq };
    }
  }
  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.type === 'canvas') {
      const c = parsed as CanvasResult;
      const name = (parsed as { name?: string }).name ?? 'HTMLアプリ';
      const html = c.html ?? '';
      // canvashtml: custom language tag → CollapsibleCodeBlock in MarkdownMessage
      const text = `🎨 **${name}**\n\n\`\`\`canvashtml\n${html}\n\`\`\``;
      return { text, canvas: c, debate: null, agentName: null, askUserQuestion: null };
    }
    if (parsed && parsed.type === 'debate_result') {
      return { text: parsed.debate_text as string, canvas: null, debate: parsed as DebateResult, agentName: null, askUserQuestion: null };
    }
    if (parsed && parsed.type === 'orchestrator_result') {
      const content = parsed.content as string;
      if (content.includes('<ask_user_question>')) {
        const auq = parseAUQ(content);
        if (auq) {
          const textWithout = content.replace(/<ask_user_question>[\s\S]*?<\/ask_user_question>/g, '').trim();
          return { text: textWithout, canvas: null, debate: null, agentName: parsed.agent_name ?? null, askUserQuestion: auq };
        }
      }
      return { text: content, canvas: null, debate: null, agentName: parsed.agent_name ?? null, askUserQuestion: null };
    }
  } catch {
    // plain text — not JSON; already checked for AUQ above
  }
  return { text: raw, canvas: null, debate: null, agentName: null, askUserQuestion: null };
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
  const [pendingQuestion, setPendingQuestion] = useState<AskUserQuestionPayload | null>(null);
  const fallbackTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Cleanup fallback polling timer on unmount
  useEffect(() => {
    return () => {
      if (fallbackTimerRef.current) {
        clearInterval(fallbackTimerRef.current);
        fallbackTimerRef.current = null;
      }
    };
  }, []);

  const sendMessage = useCallback(async (text: string, threadId?: string, contextMessages?: ContextMessage[]) => {
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
        // 過去の会話コンテキスト（SuperChat用）
        ...(contextMessages && contextMessages.length > 0 ? { context_messages: contextMessages } : {}),
        // Phase 17: 討論チャットフィールド
        ...(participants && participants.length > 0 ? { participants } : {}),
        ...(pattern ? { pattern } : {}),
        ...(maxTurns !== undefined ? { max_turns: maxTurns } : {}),
        ...(currentTurn !== undefined ? { current_turn: currentTurn } : {}),
      });

      // Helper: handle result raw string (Canvas / debate_result / AUQ / plain text)
      const handleResult = (raw: string) => {
        const { text: resultText, canvas, debate, agentName, askUserQuestion } = parseJobResult(raw);
        if (askUserQuestion) {
          setPendingQuestion(askUserQuestion);
          return;
        }
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
        // Unwrap orchestrator_result then check AUQ
        let immContent = immediate.result;
        try { const o = JSON.parse(immediate.result); if (o?.type === 'orchestrator_result' && typeof o.content === 'string') immContent = o.content; } catch {}
        if (immContent.includes('<ask_user_question>')) {
          const auq = parseAUQ(immContent);
          if (auq) {
            setPendingQuestion(auq);
            setIsThinking(false);
            await refreshThreads?.();
            return;
          }
        }
        handleResult(immediate.result);
        setIsThinking(false);
        await refreshThreads?.();
        return;
      }

      // 3. Open SSE stream for real-time completion notification
      const es = streamJob(job_id);
      eventSourceRef.current = es;
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
              // Unwrap orchestrator_result if present, then check for AUQ
              let rawContent = result.result;
              try {
                const outer = JSON.parse(result.result);
                if (outer?.type === 'orchestrator_result' && typeof outer.content === 'string') {
                  rawContent = outer.content;
                }
              } catch { /* not JSON — use as-is */ }
              if (rawContent.includes('<ask_user_question>')) {
                const auq = parseAUQ(rawContent);
                if (auq) {
                  setStreamPreview('');
                  setPendingQuestion(auq);
                  setIsThinking(false);
                  await refreshThreads?.();
                  return;
                }
              }
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
              // Unwrap orchestrator_result then check AUQ
              let pollContent = job.result;
              try { const o = JSON.parse(job.result); if (o?.type === 'orchestrator_result' && typeof o.content === 'string') pollContent = o.content; } catch {}
              if (pollContent.includes('<ask_user_question>')) {
                const auq = parseAUQ(pollContent);
                if (auq) {
                  setPendingQuestion(auq);
                  setIsThinking(false);
                  await refreshThreads?.();
                  return;
                }
              }
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

  const handleQuestionSubmit = useCallback((answers: Record<string, string>) => {
    setPendingQuestion(null);
    const text = Object.entries(answers)
      .filter(([, v]) => v)
      .map(([q, a]) => `${q}：${a}`)
      .join('\n');
    sendMessage(text);
  }, [sendMessage]);

  const cancelJob = useCallback(() => {
    // Close SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    // Clear fallback polling
    if (fallbackTimerRef.current) {
      clearInterval(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
    // Finalize partial streaming text if any
    if (streamPreview) {
      setMessages((prev) => [...prev, { role: 'ai', content: streamPreview + '\n\n_(中断されました)_' }]);
    }
    setStreamPreview('');
    setCurrentTool(null);
    setIsThinking(false);
  }, [streamPreview, setMessages]);

  return { isThinking, currentTool, streamPreview, sendMessage, cancelJob, pendingQuestion, handleQuestionSubmit };
}
