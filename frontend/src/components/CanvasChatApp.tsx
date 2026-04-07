// frontend/src/components/CanvasChatApp.tsx
// CanvasChatApp: Canvas App 専用チャット画面。
// 左右分割レイアウト: ThreadSidebar + sidebar drag handle + MessageArea + canvas drag handle + CanvasPane
// GemChatApp.tsx を参照実装として、CanvasPane 常時表示（D-01〜D-04, D-14, D-15, D-17）を追加。

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
  canvasGemId: string;              // Canvas 専用 Gem の gem_id（App.tsx から渡す）
  selectedModel: string;
  onBack: () => void;
  initialThreadId?: string | null;  // D-10: 既存アプリから起動時にスレッドを復元
}

export function CanvasChatApp({ canvasGemId, selectedModel, onBack, initialThreadId }: CanvasChatAppProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const cardBg = isDark ? '#2a2a3e' : '#ffffff';
  const textColor = isDark ? '#e0e0e0' : '#333333';

  // D-17: gem_id でスレッドを分離（app_id に依存しない）
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

  // initialThreadId が渡された場合は起動時にスレッドを復元（D-10）
  const initialSwitchDone = useRef(false);
  if (initialThreadId && !initialSwitchDone.current) {
    initialSwitchDone.current = true;
    // useEffect は hooks 内のものを使うため、ここでは ref フラグで初回のみ実行
    setTimeout(() => switchThread(initialThreadId), 0);
  }

  // サイドバー幅
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const dragStartX = useRef<number | null>(null);
  const dragStartWidth = useRef<number>(SIDEBAR_DEFAULT);

  // Canvas ペイン幅
  const [canvasPaneWidth, setCanvasPaneWidth] = useState(CANVAS_PANE_DEFAULT);
  const canvasDragStartX = useRef<number | null>(null);
  const canvasDragStartWidth = useRef<number>(CANVAS_PANE_DEFAULT);

  // Canvas 状態管理
  const { canvasApp, setCanvasApp, isSaving, isDeploying, deployUrl, deployError, saveCanvas, deployCanvas, loadCanvasForThread } = useCanvas();

  // スレッド切り替え時に最新の canvas app を復元（Todo #2）
  useEffect(() => {
    if (!activeThreadId) {
      setCanvasApp(null);
      return;
    }
    loadCanvasForThread(activeThreadId);
  }, [activeThreadId, loadCanvasForThread, setCanvasApp]);

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

  // D-14: gemId と onCanvasResponse を useChat に渡す
  // app_id: 'canvas' を明示することで通常の ChatApp スレッドと混在しないようにする
  const { isThinking, sendMessage } = useChat({
    activeThreadId,
    selectedModel,
    appId: 'canvas',
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

  // サイドバー drag handle（GemChatApp と同パターン）
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

  // CanvasPane drag handle（RESEARCH.md Pitfall 1: delta の符号が逆）
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
      {/* Canvas ヘッダーバー (UI-SPEC: "🎨 Canvas") */}
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
        <style>{`button:focus-visible { outline: 2px solid #7c6ff7; outline-offset: 2px; }`}</style>
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
        <span style={{ fontSize: '1rem', fontWeight: 600, color: textColor }}>🎨 Canvas</span>
      </div>

      {/* MainContainer: ThreadSidebar | sidebar handle | MessageArea | canvas handle | CanvasPane */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <MainContainer style={{ overflow: 'hidden' }}>
          {/* サイドバー: UI-SPEC collapse width 32px（GemChatApp の 40px を修正） */}
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

          {/* サイドバー drag handle — 展開時のみ表示（UI-SPEC: 4px） */}
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

          {/* CanvasPane drag handle（UI-SPEC: 4px） */}
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

          {/* D-02: canvasApp=null でもプレースホルダーとして常時表示 */}
          {canvasApp ? (
            <CanvasPane
              canvasApp={canvasApp}
              isSaving={isSaving}
              isDeploying={isDeploying}
              deployUrl={deployUrl}
              deployError={deployError}
              onSave={saveCanvas}
              onDeploy={deployCanvas}
              onClose={() => {}}
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
