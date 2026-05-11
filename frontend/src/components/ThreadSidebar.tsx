// frontend/src/components/ThreadSidebar.tsx
// Left sidebar: thread list + New Chat button + title filter.
// Per D-06: sidebar on left with thread list and New Chat button.
// Uses chatscope Sidebar component for layout compatibility.
// Features: collapse toggle, title filter, inline title editing, drag-to-resize (handle in ChatApp),
//           bulk select + bulk delete mode.
// Phase 35 Plan 04: isDark 三項排除 + CSS 変数移行 + drawer state 追加

import { useState, useEffect, useRef } from 'react';
import { Sidebar } from '@chatscope/chat-ui-kit-react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { ConfirmModal } from './ConfirmModal';
import type { ThreadInfo } from '../types';
import { groupThreads, groupOrder } from '../utils/threadGroups';

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
  drawerOpen?: boolean;
  onDrawerOpenChange?: (open: boolean) => void;
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
  drawerOpen: propDrawerOpen,
  onDrawerOpenChange,
}: ThreadSidebarProps) {
  const theme = useCurrentTheme();

  const [filter, setFilter] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState('');
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const cancelledRef = useRef<boolean>(false);

  // Bulk select mode
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false);

  // Collapsible "それ以前" group
  const [olderCollapsed, setOlderCollapsed] = useState(true);

  // Drawer state (uncontrolled mode 用 — controlled mode では propDrawerOpen が優先)
  const [internalDrawerOpen, setInternalDrawerOpen] = useState(false);

  // Drawer state resolver: controlled mode なら props を使用、uncontrolled なら内部 state
  const drawerOpen = propDrawerOpen ?? internalDrawerOpen;
  const setDrawerOpen = (next: boolean) => {
    if (onDrawerOpenChange) onDrawerOpenChange(next);
    else setInternalDrawerOpen(next);
  };

  // Escape キーで drawer を閉じる
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setDrawerOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  const filtered = filter.trim()
    ? threads.filter((t) => t.label.toLowerCase().includes(filter.toLowerCase()))
    : threads;

  // Group threads by date (logic extracted to utils/threadGroups.ts — Phase 35 D-02)
  const grouped = groupThreads(filtered);

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
      <>
        {drawerOpen && (
          <div
            className="sidebar-backdrop"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
        )}
        <aside
          className={`sidebar-drawer${drawerOpen ? ' open' : ''}`}
          role={drawerOpen ? 'dialog' : undefined}
          aria-modal={drawerOpen ? 'true' : undefined}
          aria-label={drawerOpen ? 'スレッド一覧' : undefined}
        >
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
                  color: 'var(--color-text-muted)',
                  padding: '4px',
                }}
              >
                ▶
              </button>
            </div>
          </Sidebar>
        </aside>
      </>
    );
  }

  return (
    <>
      {drawerOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setDrawerOpen(false)}
          aria-hidden="true"
        />
      )}
      <aside
        className={`sidebar-drawer${drawerOpen ? ' open' : ''}`}
        role={drawerOpen ? 'dialog' : undefined}
        aria-modal={drawerOpen ? 'true' : undefined}
        aria-label={drawerOpen ? 'スレッド一覧' : undefined}
      >
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
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-accent)',
                  color: 'var(--color-accent-contrast)',
                  fontWeight: 'bold',
                  fontSize: '0.9rem',
                }}
              >
                + 新しいチャット
              </button>
              <button
                onClick={() => selectMode ? exitSelectMode() : setSelectMode(true)}
                title={selectMode ? 'Exit select mode' : 'Select mode'}
                className="sidebar-collapse-btn"
                style={{
                  background: selectMode ? 'var(--color-accent-subtle)' : 'none',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  color: selectMode ? 'var(--color-accent)' : 'var(--color-text-muted)',
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
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  color: 'var(--color-text-muted)',
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
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    color: 'var(--color-text-muted)',
                    padding: '2px 6px',
                  }}
                >
                  {selectedIds.size === filtered.length && filtered.length > 0 ? '全解除' : '全選択'}
                </button>
                {selectedIds.size > 0 && (
                  <button
                    onClick={() => setBulkDeleteConfirm(true)}
                    style={{
                      background: 'var(--color-destructive)',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      color: 'var(--color-accent-contrast)',
                      padding: '2px 8px',
                      fontWeight: 600,
                    }}
                  >
                    {selectedIds.size}件削除
                  </button>
                )}
                <span style={{ color: 'var(--color-text-muted)', marginLeft: 'auto' }}>
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
                placeholder="会話を絞り込む..."
                className="sidebar-filter-input"
                style={{
                  width: '100%',
                  padding: '0.35rem 1.6rem 0.35rem 0.5rem',
                  fontSize: '0.8rem',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  outline: 'none',
                  boxSizing: 'border-box',
                  background: 'var(--color-surface)',
                  color: 'var(--color-text)',
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
                    color: 'var(--color-text-muted)',
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
              <p className="sidebar-filter-count" style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                {filtered.length} / {threads.length} 件一致
              </p>
            )}

            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {filtered.length === 0 && (
                <p className="sidebar-empty-text" style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', padding: '0.5rem 0' }}>
                  {threads.length === 0 ? 'まだ会話がありません' : '一致する会話がありません'}
                </p>
              )}
              {groupOrder.map((groupLabel) => {
                const groupThreads = grouped.get(groupLabel);
                if (!groupThreads || groupThreads.length === 0) return null;

                const isOlder = groupLabel === 'それ以前';
                const isCollapsed = isOlder && olderCollapsed;

                return (
                  <div key={groupLabel}>
                    {/* Group header */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 4px 4px',
                        fontSize: '0.7rem',
                        color: 'var(--color-text-muted)',
                        ...(isOlder ? { cursor: 'pointer' } : {}),
                      }}
                      onClick={isOlder ? () => setOlderCollapsed((v) => !v) : undefined}
                    >
                      <div style={{ flex: 1, height: '1px', background: 'var(--color-border)' }} />
                      <span style={{ whiteSpace: 'nowrap' }}>
                        {isOlder
                          ? (isCollapsed ? `▶ ${groupLabel} (${groupThreads.length}件)` : `▼ ${groupLabel}`)
                          : groupLabel}
                      </span>
                      <div style={{ flex: 1, height: '1px', background: 'var(--color-border)' }} />
                    </div>

                    {/* Thread items (hidden when collapsed) */}
                    {!isCollapsed && groupThreads.map((thread) => (
                      <div
                        key={thread.thread_id}
                        className={`sidebar-thread-item${activeThreadId === thread.thread_id ? ' active' : ''}`}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '0.4rem 0.5rem',
                          borderRadius: 'var(--radius-sm)',
                          cursor: 'pointer',
                          background: activeThreadId === thread.thread_id ? 'var(--color-accent-subtle)' : 'transparent',
                          fontWeight: activeThreadId === thread.thread_id ? 'bold' : 'normal',
                          color: 'var(--color-text)',
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
                              border: '1px solid var(--color-accent)',
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
                                  color: 'var(--color-text-muted)',
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
                              color: 'var(--color-text-muted)',
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
                );
              })}
            </div>
          </div>

          {/* Single delete confirm */}
          <ConfirmModal
            isOpen={deleteTargetId !== null}
            message={`「${threads.find((t) => t.thread_id === deleteTargetId)?.label ?? ''}」を削除しますか？`}
            confirmLabel="削除"
            isDark={theme === 'dark'}
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
            isDark={theme === 'dark'}
            onConfirm={handleBulkDelete}
            onCancel={() => setBulkDeleteConfirm(false)}
          />
        </Sidebar>
      </aside>
    </>
  );
}
