// frontend/src/components/ChatApp.tsx
// MainContainer layout root: Sidebar (left) + ChatContainer (main).
// CRITICAL: outer div must have height: 100vh (Pitfall 1 in 07-RESEARCH.md).
// Header is rendered ABOVE the MainContainer in App.tsx, not inside it.
// Phase 25: useParams/useNavigate で URL を single source of truth にする。

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { CanvasPane } from './CanvasPane';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useCanvas } from '../hooks/useCanvas';
import { renameThread } from '../api/client';

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;

interface ChatAppProps {
  selectedModel: string;
}

export function ChatApp({ selectedModel }: ChatAppProps) {
  const { threadId: urlThreadId } = useParams<{ threadId?: string }>();
  const navigate = useNavigate();

  const {
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
  } = useThreads('chat');

  // 25-RESEARCH.md Pitfall 5 対策: URL を single source of truth とする
  // URL の threadId が変わったら useThreads の activeThreadId を同期する
  useEffect(() => {
    if (urlThreadId && urlThreadId !== activeThreadId) {
      switchThread(urlThreadId);
    }
    // urlThreadId が undefined(/chat) の場合は activeThreadId をクリアしない
    // (新規スレッド作成時に /chat → /chat/:tid の遷移で消えないように)
  }, [urlThreadId, activeThreadId, switchThread]);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);

  const {
    canvasApp,
    setCanvasApp,
    isSaving,
    isDeploying,
    deployUrl,
    deployError,
    saveCanvas,
    deployCanvas,
    dismissCanvas,
  } = useCanvas();
  const dragStartX = useRef<number | null>(null);
  const dragStartWidth = useRef<number>(SIDEBAR_DEFAULT);

  const handleNewChat = async () => {
    const tid = await createNewThread();
    // 新規スレッドは履歴を汚染しないよう replace
    navigate(`/chat/${tid}`, { replace: true });
  };

  const handleSelectThread = async (threadId: string) => {
    navigate(`/chat/${threadId}`);
  };

  const handleRenameThread = async (threadId: string, label: string) => {
    await renameThread(threadId, label);
    await refreshThreads();
  };

  const { isThinking, streamPreview, sendMessage, cancelJob, pendingQuestion, handleQuestionSubmit } = useChat({
    activeThreadId,
    selectedModel,
    setMessages,
    refreshThreads,
    onCanvasResponse: (app) => setCanvasApp(app),
  });

  const handleSend = async (text: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
      navigate(`/chat/${threadId}`, { replace: true });
    }
    // Pass threadId explicitly: sendMessage's closure may still capture the
    // stale activeThreadId=null value if createNewThread() just set it and
    // the component hasn't re-rendered yet.
    await sendMessage(text, threadId);
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
          onBulkDeleteThreads={bulkRemoveThreads}
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
          <>
            <MessageArea
              messages={messages}
              isThinking={isThinking}
              streamPreview={streamPreview}
              onSend={handleSend}
              onCancel={cancelJob}
              pendingQuestion={pendingQuestion}
              onQuestionSubmit={handleQuestionSubmit}
            />
            {canvasApp && (
              <CanvasPane
                canvasApp={canvasApp}
                isSaving={isSaving}
                isDeploying={isDeploying}
                deployUrl={deployUrl}
                deployError={deployError}
                onSave={saveCanvas}
                onDeploy={deployCanvas}
                onClose={dismissCanvas}
              />
            )}
          </>
        )}
      </MainContainer>
    </div>
  );
}
