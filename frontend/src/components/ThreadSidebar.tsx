// frontend/src/components/ThreadSidebar.tsx
// Left sidebar: thread list + New Chat button + title filter.
// Per D-06: sidebar on left with thread list and New Chat button.
// Uses chatscope Sidebar component for layout compatibility.
// Features: collapse toggle, title filter, inline title editing, drag-to-resize (handle in ChatApp),
//           bulk select + bulk delete mode.

import { useState, useRef } from 'react';
import { Sidebar } from '@chatscope/chat-ui-kit-react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { ConfirmModal } from './ConfirmModal';
import type { ThreadInfo } from '../types';

interface ThreadSidebarProps {
  threads: ThreadInfo[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewChat: () => void;
  onDeleteThread: (threadId: string) => void;
  onBulkDeleteThreads?: (threadIds: string[]) => void;
  onRenameThread: (threadId: string, label: string) => Promise<void>;
  collapsed: boolean;
  onToggleCollapse: () => void;
  width: number;
}

export function ThreadSidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onNewChat,
  onDeleteThread,
  onBulkDeleteThreads,
  onRenameThread,
  collapsed,
  onToggleCollapse,
  width,
}: ThreadSidebarProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const [filter, setFilter] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState('');
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const cancelledRef = useRef<boolean>(false);

  // Bulk select mode
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false);

  const filtered = filter.trim()
    ? threads.filter((t) => t.label.toLowerCase().includes(filter.toLowerCase()))
    : threads;

  const startEdit = (thread: ThreadInfo, e: React.MouseEvent) => {
    e.stopPropagation();
    cancelledRef.current = false;
    setEditingId(thread.thread_id);
    setEditLabel(thread.label);
  };

  const commitEdit = async (threadId: string) => {
    if (cancelledRef.current) {
      cancelledRef.current = false;
      return;
    }
    const trimmed = editLabel.trim();
    if (trimmed) {
      await onRenameThread(threadId, trimmed);
    }
    setEditingId(null);
  };

  const cancelEdit = () => {
    cancelledRef.current = true;
    setEditingId(null);
  };

  const toggleSelect = (threadId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(threadId)) next.delete(threadId);
      else next.add(threadId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map((t) => t.thread_id)));
    }
  };

  const exitSelectMode = () => {
    setSelectMode(false);
    setSelectedIds(new Set());
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    if (onBulkDeleteThreads) {
      onBulkDeleteThreads(Array.from(selectedIds));
    } else {
      // Fallback: delete one by one
      selectedIds.forEach((id) => onDeleteThread(id));
    }
    exitSelectMode();
    setBulkDeleteConfirm(false);
  };

  if (collapsed) {
    return (
      <Sidebar position="left" style={{ width: `${width}px`, flexBasis: `${width}px`, flexShrink: 0, minWidth: `${width}px`, maxWidth: `${width}px` }}>
        <div className="sidebar-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '0.5rem 0', height: '100%' }}>
          <button
            onClick={onToggleCollapse}
            title="Expand sidebar"
            className="sidebar-collapse-btn"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '1.1rem',
              color: '#555',
              padding: '4px',
            }}
          >
            ▶
          </button>
        </div>
      </Sidebar>
    );
  }

  return (
    <Sidebar position="left" style={{ width: `${width}px`, flexBasis: `${width}px`, flexShrink: 0, minWidth: `${width}px`, maxWidth: `${width}px` }}>
      <div className="sidebar-content" style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', height: '100%' }}>

        {/* Header row: New Chat + select mode toggle + collapse button */}
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <button
            onClick={onNewChat}
            className="sidebar-new-chat-btn"
            style={{
              flex: 1,
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
          <button
            onClick={() => selectMode ? exitSelectMode() : setSelectMode(true)}
            title={selectMode ? 'Exit select mode' : 'Select mode'}
            className="sidebar-collapse-btn"
            style={{
              background: selectMode ? (isDark ? '#3a3a52' : '#e8f0fe') : 'none',
              border: '1px solid #ddd',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              color: selectMode ? (isDark ? '#e8e8f0' : '#0366d6') : '#555',
              padding: '4px 6px',
              flexShrink: 0,
            }}
          >
            ☑
          </button>
          <button
            onClick={onToggleCollapse}
            title="Collapse sidebar"
            className="sidebar-collapse-btn"
            style={{
              background: 'none',
              border: '1px solid #ddd',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              color: '#555',
              padding: '4px 6px',
              flexShrink: 0,
            }}
          >
            ◀
          </button>
        </div>

        {/* Select mode controls */}
        {selectMode && (
          <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', fontSize: '0.78rem' }}>
            <button
              onClick={toggleSelectAll}
              style={{
                background: 'none',
                border: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem',
                color: isDark ? '#9090a8' : '#555',
                padding: '2px 6px',
              }}
            >
              {selectedIds.size === filtered.length && filtered.length > 0 ? '全解除' : '全選択'}
            </button>
            {selectedIds.size > 0 && (
              <button
                onClick={() => setBulkDeleteConfirm(true)}
                style={{
                  background: '#e05252',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  color: '#fff',
                  padding: '2px 8px',
                  fontWeight: 600,
                }}
              >
                {selectedIds.size}件削除
              </button>
            )}
            <span style={{ color: isDark ? '#9090a8' : '#888', marginLeft: 'auto' }}>
              {selectedIds.size}/{filtered.length}
            </span>
          </div>
        )}

        {/* Title filter input */}
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter conversations..."
            className="sidebar-filter-input"
            style={{
              width: '100%',
              padding: '0.35rem 1.6rem 0.35rem 0.5rem',
              fontSize: '0.8rem',
              border: '1px solid #d1dbe3',
              borderRadius: '4px',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
          {filter && (
            <button
              onClick={() => setFilter('')}
              title="Clear filter"
              className="sidebar-filter-clear"
              style={{
                position: 'absolute',
                right: '4px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#999',
                fontSize: '0.8rem',
                padding: '0 2px',
                lineHeight: 1,
              }}
            >
              ✕
            </button>
          )}
        </div>

        {filter && (
          <p className="sidebar-filter-count" style={{ margin: 0, fontSize: '0.75rem', color: '#888' }}>
            {filtered.length} / {threads.length} matches
          </p>
        )}

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {filtered.length === 0 && (
            <p className="sidebar-empty-text" style={{ color: '#888', fontSize: '0.8rem', padding: '0.5rem 0' }}>
              {threads.length === 0 ? 'No conversations yet' : 'No matches'}
            </p>
          )}
          {filtered.map((thread) => (
            <div
              key={thread.thread_id}
              className={`sidebar-thread-item${activeThreadId === thread.thread_id ? ' active' : ''}`}
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
              onClick={() => {
                if (selectMode) {
                  toggleSelect(thread.thread_id);
                } else if (editingId !== thread.thread_id) {
                  onSelectThread(thread.thread_id);
                }
              }}
            >
              {/* Checkbox in select mode */}
              {selectMode && (
                <input
                  type="checkbox"
                  checked={selectedIds.has(thread.thread_id)}
                  onChange={() => toggleSelect(thread.thread_id)}
                  onClick={(e) => e.stopPropagation()}
                  style={{ marginRight: '6px', flexShrink: 0, cursor: 'pointer' }}
                />
              )}

              {editingId === thread.thread_id ? (
                <input
                  autoFocus
                  value={editLabel}
                  onChange={(e) => setEditLabel(e.target.value)}
                  onBlur={() => commitEdit(thread.thread_id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') { e.preventDefault(); commitEdit(thread.thread_id); }
                    if (e.key === 'Escape') cancelEdit();
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="sidebar-thread-edit-input"
                  style={{
                    flex: 1,
                    fontSize: '0.82rem',
                    border: '1px solid #0366d6',
                    borderRadius: '3px',
                    padding: '1px 4px',
                    outline: 'none',
                    minWidth: 0,
                  }}
                />
              ) : (
                <div
                  style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}
                  onDoubleClick={(e) => !selectMode && startEdit(thread, e)}
                  title={selectMode ? undefined : 'Double-click to rename'}
                >
                  <span
                    className="sidebar-thread-label"
                    style={{
                      fontSize: '0.82rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {thread.label}
                  </span>
                  {thread.updated_at && (
                    <span
                      className="sidebar-thread-date"
                      style={{
                        fontSize: '0.7rem',
                        color: '#999',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {new Date(thread.updated_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              )}

              {!selectMode && editingId !== thread.thread_id && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteTargetId(thread.thread_id);
                  }}
                  className="sidebar-thread-delete-btn"
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
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Single delete confirm */}
      <ConfirmModal
        isOpen={deleteTargetId !== null}
        message={`「${threads.find((t) => t.thread_id === deleteTargetId)?.label ?? ''}」を削除しますか？`}
        confirmLabel="削除"
        isDark={isDark}
        onConfirm={() => {
          if (deleteTargetId) onDeleteThread(deleteTargetId);
          setDeleteTargetId(null);
        }}
        onCancel={() => setDeleteTargetId(null)}
      />

      {/* Bulk delete confirm */}
      <ConfirmModal
        isOpen={bulkDeleteConfirm}
        message={`${selectedIds.size}件のスレッドを削除しますか？`}
        confirmLabel={`${selectedIds.size}件削除`}
        isDark={isDark}
        onConfirm={handleBulkDelete}
        onCancel={() => setBulkDeleteConfirm(false)}
      />
    </Sidebar>
  );
}
