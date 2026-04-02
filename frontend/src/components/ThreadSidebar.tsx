// frontend/src/components/ThreadSidebar.tsx
// Left sidebar: thread list + New Chat button.
// Per D-06: sidebar on left with thread list and New Chat button.
// Uses chatscope Sidebar component for layout compatibility.

import { Sidebar } from '@chatscope/chat-ui-kit-react';
import type { ThreadInfo } from '../types';

interface ThreadSidebarProps {
  threads: ThreadInfo[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewChat: () => void;
  onDeleteThread: (threadId: string) => void;
}

export function ThreadSidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onNewChat,
  onDeleteThread,
}: ThreadSidebarProps) {
  return (
    <Sidebar position="left" style={{ width: '240px', flexShrink: 0 }}>
      <div style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', height: '100%' }}>
        <button
          onClick={onNewChat}
          style={{
            padding: '0.5rem',
            cursor: 'pointer',
            borderRadius: '6px',
            border: '1px solid #ddd',
            background: '#0366d6',
            color: '#fff',
            fontWeight: 'bold',
            fontSize: '0.9rem',
          }}
        >
          + New Chat
        </button>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {threads.length === 0 && (
            <p style={{ color: '#888', fontSize: '0.8rem', padding: '0.5rem 0' }}>
              No conversations yet
            </p>
          )}
          {threads.map((thread) => (
            <div
              key={thread.thread_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.4rem 0.5rem',
                borderRadius: '4px',
                cursor: 'pointer',
                background: activeThreadId === thread.thread_id ? '#e8f0fe' : 'transparent',
                fontWeight: activeThreadId === thread.thread_id ? 'bold' : 'normal',
              }}
              onClick={() => onSelectThread(thread.thread_id)}
            >
              <span style={{
                fontSize: '0.82rem',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                flex: 1,
              }}>
                {thread.label}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm('Delete this conversation?')) {
                    onDeleteThread(thread.thread_id);
                  }
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#999',
                  padding: '0 4px',
                  fontSize: '0.9rem',
                  flexShrink: 0,
                }}
                title="Delete thread"
                aria-label="Delete thread"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>
    </Sidebar>
  );
}
