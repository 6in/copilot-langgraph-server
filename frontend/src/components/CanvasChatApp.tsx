// frontend/src/components/CanvasChatApp.tsx
// Canvas chat app: split layout (ThreadSidebar + MessageArea | CanvasPane).
// Phase 16: D-01 (split layout), D-02 (CanvasPane always visible), D-03 (drag handle),
//           D-04 (CanvasPane min width), D-14 (useChat gemId), D-15 (useCanvas hook), D-17 (gem_id thread filter).

import { useCallback, useEffect, useRef, useState } from 'react';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { CanvasPane } from './CanvasPane';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useCanvas } from '../hooks/useCanvas';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { renameThread } from '../api/client';

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;
const CANVAS_PANE_MIN = 320;    // UI-SPEC: CanvasPane 最小幅
const CANVAS_PANE_DEFAULT = 400; // 初期幅（ピクセル）

interface CanvasChatAppProps {
  canvasGemId: string;
  selectedModel: string;
  onBack: () => void;
  initialThreadId?: string | null;  // D-10: 既存アプリから起動時にスレッドを復元
}

export function CanvasChatApp({
  canvasGemId,
  selectedModel,
  onBack,
  initialThreadId,
}: CanvasChatAppProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const cardBg = isDark ? '#2a2a3e' : '#ffffff';
  const textColor = isDark ? '#e0e0e0' : '#333333';

  // D-17: Canvas 専用 Gem の gem_id でスレッドをフィルタ
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
  } = useThreads(undefined, canvasGemId);

  // D-10: initialThreadId が指定されている場合、マウント後にスレッドを復元
  const hasInitialized = useRef(false);
  useEffect(() => {
    if (!hasInitialized.current && initialThreadId) {
      hasInitialized.current = true;
      switchThread(initialThreadId);
    }
  }, [initialThreadId, switchThread]);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const [canvasPaneWidth, setCanvasPaneWidth] = useState(CANVAS_PANE_DEFAULT);

  const dragStartX = useRef<number | null>(null);
  const dragStartWidth = useRef<number>(SIDEBAR_DEFAULT);
  const canvasDragStartX = useRef<number | null>(null);
  const canvasDragStartWidth = useRef<number>(CANVAS_PANE_DEFAULT);

  // D-15: useCanvas フック
  const { canvasApp, setCanvasApp, isSaving, isDeploying, deployUrl, deployError, saveCanvas, deployCanvas } =
    useCanvas();

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

  // D-14: useChat に gemId と onCanvasResponse を渡す
  const { isThinking, sendMessage } = useChat({
    activeThreadId,
    selectedModel,
    gemId: canvasGemId,
    setMessages,
    refreshThreads,
    onCanvasResponse: setCanvasApp,
  });

  const handleSend = async (text: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
    }
    await sendMessage(text, threadId);
    await refreshThreads();
  };

  // Sidebar drag handle
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

  // D-03: Canvas drag handle — delta の符号が逆（右から左への drag で CanvasPane が拡大）
  const handleCanvasDividerMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    canvasDragStartX.current = e.clientX;
    canvasDragStartWidth.current = canvasPaneWidth;

    const onMouseMove = (ev: MouseEvent) => {
      if (canvasDragStartX.current === null) return;
      const delta = ev.clientX - canvasDragStartX.current;
      // 右から左への drag で CanvasPane が拡大 → delta を反転
      const newWidth = Math.max(CANVAS_PANE_MIN, canvasDragStartWidth.current - delta);
      setCanvasPaneWidth(newWidth);
    };

    const onMouseUp = () => {
      canvasDragStartX.current = null;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }, [canvasPaneWidth]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* Canvas ヘッダーバー */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '8px 16px',
          height: '48px',
          borderBottom: '1px solid #d1dbe3',
          background: cardBg,
          flexShrink: 0,
        }}
      >
        <style>{`
          button:focus-visible {
            outline: 2px solid #7c6ff7;
            outline-offset: 2px;
          }
        `}</style>
        <button
          onClick={onBack}
          aria-label="Back to Canvas screen"
          style={{
            padding: '0.25rem 0.75rem',
            borderRadius: '4px',
            border: '1px solid #555',
            background: 'transparent',
            color: textColor,
            cursor: 'pointer',
            fontSize: '0.875rem',
          }}
        >
          ← Back
        </button>
        <span style={{ fontSize: '1rem', fontWeight: 600, color: textColor }}>
          🎨 Canvas
        </span>
      </div>

      {/* MainContainer: ThreadSidebar | drag | MessageArea | canvas-drag | CanvasPane */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <MainContainer style={{ overflow: 'hidden' }}>
          {/* ThreadSidebar — collapse width 32px（UI-SPEC: 32px, GemChatApp の 40px を修正） */}
          <ThreadSidebar
            threads={threads}
            activeThreadId={activeThreadId}
            onSelectThread={handleSelectThread}
            onNewChat={handleNewChat}
            onDeleteThread={removeThread}
            onRenameThread={handleRenameThread}
            collapsed={sidebarCollapsed}
            onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
            width={sidebarCollapsed ? 32 : sidebarWidth}
          />

          {/* Sidebar drag handle — 4px（UI-SPEC 準拠） */}
          {!sidebarCollapsed && (
            <div
              onMouseDown={handleDividerMouseDown}
              style={{
                width: '4px',
                cursor: 'col-resize',
                background: 'transparent',
                flexShrink: 0,
                zIndex: 10,
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

          {/* Canvas drag handle — 4px（UI-SPEC 準拠） */}
          <div
            onMouseDown={handleCanvasDividerMouseDown}
            style={{
              width: '4px',
              cursor: 'col-resize',
              background: 'transparent',
              flexShrink: 0,
              zIndex: 10,
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = '#b0c4d8'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
          />

          {/* D-02: CanvasPane は canvasApp=null でも常時表示（プレースホルダー） */}
          {canvasApp ? (
            <CanvasPane
              canvasApp={canvasApp}
              isSaving={isSaving}
              isDeploying={isDeploying}
              deployUrl={deployUrl}
              deployError={deployError}
              onSave={saveCanvas}
              onDeploy={deployCanvas}
              onClose={() => {}}  // Pitfall 4: 常時表示のためダミー
            />
          ) : (
            <div
              style={{
                minWidth: `${CANVAS_PANE_MIN}px`,
                width: `${canvasPaneWidth}px`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                gap: '8px',
                background: '#ffffff',
                borderLeft: '1px solid #d1dbe3',
                color: '#666666',
                textAlign: 'center',
                padding: '24px',
                flexShrink: 0,
              }}
            >
              <div style={{ fontSize: '2rem' }}>🎨</div>
              <div style={{ fontSize: '1rem', fontWeight: 600 }}>アプリがここに表示されます</div>
              <div style={{ fontSize: '0.875rem', color: '#666666', lineHeight: 1.5 }}>
                チャットで HTML アプリを生成してください
              </div>
            </div>
          )}
        </MainContainer>
      </div>
    </div>
  );
}
