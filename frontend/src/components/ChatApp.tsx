// frontend/src/components/ChatApp.tsx
// MainContainer layout root: Sidebar (left) + ChatContainer (main).
// CRITICAL: outer div must have height: 100vh (Pitfall 1 in 07-RESEARCH.md).
// Header is rendered ABOVE the MainContainer in App.tsx, not inside it.

import { useCallback, useRef, useState } from 'react';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { renameThread } from '../api/client';

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;

interface ChatAppProps {
  selectedModel: string;
}

export function ChatApp({ selectedModel }: ChatAppProps) {
  const {
    threads,
    activeThreadId,
    messages,
    isLoadingMessages,
    switchThread,
    createNewThread,
    removeThread,
    setMessages,
    refreshThreads,
  } = useThreads();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const dragStartX = useRef<number | null>(null);
  const dragStartWidth = useRef<number>(SIDEBAR_DEFAULT);

  const handleNewChat = async () => {
    await createNewThread();
  };

  const handleSelectThread = async (threadId: string) => {
    await switchThread(threadId);
  };

  const handleRenameThread = async (threadId: string, label: string) => {
    await renameThread(threadId, label);
    await refreshThreads();
  };

  const { isThinking, sendMessage } = useChat({
    activeThreadId,
    selectedModel,
    setMessages,
    refreshThreads,
  });

  const handleSend = async (text: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
    }
    await sendMessage(text);
    await refreshThreads();
  };

  // Drag-to-resize handlers
  const handleDividerMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragStartX.current = e.clientX;
    dragStartWidth.current = sidebarWidth;

    const onMouseMove = (ev: MouseEvent) => {
      if (dragStartX.current === null) return;
      const delta = ev.clientX - dragStartX.current;
      const newWidth = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, dragStartWidth.current + delta));
      setSidebarWidth(newWidth);
    };

    const onMouseUp = () => {
      dragStartX.current = null;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }, [sidebarWidth]);

  return (
    // CRITICAL: This div must have an explicit height.
    // chatscope MainContainer/ChatContainer use height: 100% internally.
    // Without this, the entire chat UI collapses to 0px.
    // Per Pitfall 1 in 07-RESEARCH.md.
    // min-height: 0 prevents flex item from expanding beyond available space
    // (default min-height: auto allows unbounded growth in flex columns)
    <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
      {/* overflow:hidden overrides chatscope's default overflow:auto on cs-main-container */}
      <MainContainer style={{ overflow: 'hidden' }}>
        <ThreadSidebar
          threads={threads}
          activeThreadId={activeThreadId}
          onSelectThread={handleSelectThread}
          onNewChat={handleNewChat}
          onDeleteThread={removeThread}
          onRenameThread={handleRenameThread}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
          width={sidebarCollapsed ? 40 : sidebarWidth}
        />

        {/* Drag handle — only shown when sidebar is expanded */}
        {!sidebarCollapsed && (
          <div
            onMouseDown={handleDividerMouseDown}
            style={{
              width: '5px',
              cursor: 'col-resize',
              background: 'transparent',
              flexShrink: 0,
              zIndex: 10,
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = '#b0c4d8'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
          />
        )}

        {isLoadingMessages ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
            <p>Loading messages...</p>
          </div>
        ) : (
          <MessageArea
            messages={messages}
            isThinking={isThinking}
            onSend={handleSend}
          />
        )}
      </MainContainer>
    </div>
  );
}
