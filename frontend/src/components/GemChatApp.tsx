// frontend/src/components/GemChatApp.tsx
// GemChatApp: Gem 専用チャット画面。
// ChatApp.tsx と同構造（ThreadSidebar + drag handle + MessageArea）だが
// CanvasPane / GemSelector / selectedGemId を持たないシンプル構成（D-17）。
// Gem ヘッダーバーを内部実装（UI-SPEC.md 3b 準拠）。

import { useCallback, useRef, useState } from 'react';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { renameThread } from '../api/client';
import type { GemInfo } from '../types';

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;

interface GemChatAppProps {
  gem: GemInfo;
  selectedModel: string;
  onBack: () => void;
}

export function GemChatApp({ gem, selectedModel, onBack }: GemChatAppProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const cardBg = isDark ? '#2a2a3e' : '#ffffff';
  const textColor = isDark ? '#e0e0e0' : '#333333';

  // D-15: Gem 単位のスレッド分離 — gem_id で直接フィルタ（app_id に依存しないため既存スレッドも取得できる）
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
  } = useThreads(undefined, gem.gem_id);

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

  // D-16: gem_id を useChat に渡す。appId も合わせて渡し、threads.app_id を 'gem-{id}' で統一する（Todo 8）
  const { isThinking, sendMessage } = useChat({
    activeThreadId,
    selectedModel,
    gemId: gem.gem_id,
    appId: `gem-${gem.gem_id}`,
    setMessages,
    refreshThreads,
  });

  const handleSend = async (text: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
    }
    await sendMessage(text, threadId);
    await refreshThreads();
  };

  // Drag-to-resize handlers (ChatApp.tsx と同パターン)
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Gem ヘッダーバー (UI-SPEC.md 3b) */}
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
        {/* Pitfall 4 対策: このボタンで GemsScreen に戻る。App.tsx Header の onBackToMenu は渡さない */}
        <button
          onClick={onBack}
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
        <span
          style={{
            fontSize: '1rem',
            fontWeight: 600,
            color: textColor,
          }}
        >
          💎 {gem.name}
        </span>
      </div>

      {/* MainContainer (ChatApp.tsx と同パターン) */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
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

          {/* Drag handle — sidebar 展開時のみ表示 */}
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
    </div>
  );
}
