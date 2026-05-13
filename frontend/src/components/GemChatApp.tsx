// frontend/src/components/GemChatApp.tsx
// GemChatApp: Gem 専用チャット画面。
// ChatApp.tsx と同構造（ThreadSidebar + drag handle + MessageArea）だが
// CanvasPane / GemSelector / selectedGemId を持たないシンプル構成（D-17）。
// Gem ヘッダーバーを内部実装（UI-SPEC.md 3b 準拠）。

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { AttachmentButton } from './AttachmentButton';
import { AttachmentChips } from './AttachmentChips';
import { VisionWarningBanner } from './VisionWarningBanner';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useAttachments } from '../hooks/useAttachments';
import { useModels } from '../hooks/useModels';
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
  // Phase 40-04: VisionWarningBanner CTA でモデルを切り替えるために onModelChange を受ける
  onModelChange?: (model: string) => void;
}

export function GemChatApp({ gem, selectedModel, onBack, onModelChange }: GemChatAppProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const cardBg = isDark ? '#2a2a3e' : '#ffffff';
  const textColor = isDark ? '#e0e0e0' : '#333333';

  const { gemId, threadId: urlThreadId } = useParams<{ gemId: string; threadId?: string }>();
  const navigate = useNavigate();

  // D-15: Gem 単位のスレッド分離 — gem_id で直接フィルタ（app_id に依存しないため既存スレッドも取得できる）
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
  } = useThreads(undefined, gem.gem_id);

  // Phase 25: URL を single source of truth として switchThread と同期
  useEffect(() => {
    if (urlThreadId && urlThreadId !== activeThreadId) {
      switchThread(urlThreadId);
    }
  }, [urlThreadId, activeThreadId, switchThread]);

  // Phase 40 UI-INIT-THREAD (#10 拡張): Gem Chat も Chat/SuperChat と同形の初回 mount auto-create。
  // Menu → Gems → Gem 選択で /gemchat/{gemId} (thread ID なし) に遷移したとき、
  // AttachmentButton を即座に有効化するため自動で新規 thread を作成する。
  const initThreadInFlightRef = useRef<boolean>(false);
  useEffect(() => {
    if (initThreadInFlightRef.current) return;
    if (urlThreadId !== undefined) return; // URL に既に thread がある
    if (activeThreadId !== null) return; // 既存 thread がアクティブ
    if (messages.length !== 0) return; // 既存メッセージが残っている
    if (!gemId) return; // gemId が URL params から取れる前は待機
    initThreadInFlightRef.current = true;
    (async () => {
      try {
        const tid = await createNewThread();
        navigate(`/gemchat/${gemId}/${tid}`, { replace: true });
      } finally {
        initThreadInFlightRef.current = false;
      }
    })();
  }, [urlThreadId, activeThreadId, messages.length, gemId, createNewThread, navigate]);

  // Phase 40-04: model info を /api/models から取得し、useAttachments の vision_limits pre-validate を有効化
  const { modelById, suggestedVisionModel } = useModels();
  const currentModelInfo = modelById(selectedModel);

  // Phase 40-04: staging attachments
  const attachments = useAttachments(activeThreadId, currentModelInfo ?? null);

  // Phase 40-04: vision 警告バナー dismiss state (モデル変更時にリセット)
  const [warningDismissed, setWarningDismissed] = useState(false);
  useEffect(() => {
    setWarningDismissed(false);
  }, [selectedModel]);

  const hasStagedImages = attachments.items.some(
    (it) => ['png', 'jpg', 'jpeg', 'webp'].includes(it.ext.toLowerCase()),
  );
  const showVisionWarning = !!(
    hasStagedImages
    && currentModelInfo
    && currentModelInfo.vision === false
    && suggestedVisionModel
    && !warningDismissed
  );

  const handleSwitchModel = useCallback(() => {
    if (suggestedVisionModel && onModelChange) {
      onModelChange(suggestedVisionModel);
    }
  }, [suggestedVisionModel, onModelChange]);

  // Phase 40-04: drop zone overlay state + paste listener
  const [dragOver, setDragOver] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const onDragOver = useCallback((e: React.DragEvent) => {
    if (e.dataTransfer.types.includes('Files')) {
      e.preventDefault();
      setDragOver(true);
    }
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    if (e.currentTarget === e.target) setDragOver(false);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) attachments.upload(files);
  }, [attachments]);

  // Ctrl+V / Cmd+V で image blob を paste する (document level listener)
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      if (!e.clipboardData) return;
      const imageFiles: File[] = [];
      for (let i = 0; i < e.clipboardData.items.length; i++) {
        const item = e.clipboardData.items[i];
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          const f = item.getAsFile();
          if (f) imageFiles.push(f);
        }
      }
      if (imageFiles.length > 0) {
        e.preventDefault();
        attachments.upload(imageFiles);
      }
    };
    document.addEventListener('paste', onPaste);
    return () => document.removeEventListener('paste', onPaste);
  }, [attachments]);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);

  const dragStartX = useRef<number | null>(null);
  const dragStartWidth = useRef<number>(SIDEBAR_DEFAULT);

  const handleNewChat = async () => {
    const tid = await createNewThread();
    navigate(`/gemchat/${gemId}/${tid}`, { replace: true });
  };

  const handleSelectThread = async (threadId: string) => {
    navigate(`/gemchat/${gemId}/${threadId}`);
  };

  const handleRenameThread = async (threadId: string, label: string) => {
    await renameThread(threadId, label);
    await refreshThreads();
  };

  // D-16: gem_id を useChat に渡す。appId は送らない（applications FK 制約があるため 'gem-xxx' は無効）
  // スレッドは app_id='chat' で保存されるが gem_id で絞り込めるため問題なし（Todo 8）
  const { isThinking, streamPreview, sendMessage, cancelJob, pendingQuestion, handleQuestionSubmit } = useChat({
    activeThreadId,
    selectedModel,
    gemId: gem.gem_id,
    setMessages,
    refreshThreads,
    // Phase 40-04: attachments pipeline
    getReadyAttachments: attachments.getReadyItems,
    onAttachmentsSent: attachments.clearAll,
  });

  const handleSend = async (text: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
      navigate(`/gemchat/${gemId}/${threadId}`, { replace: true });
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
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
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
      <div
        ref={rootRef}
        style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' }}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        {/* Phase 40-04: drop overlay (drag-over 中のみ表示) */}
        {dragOver && (
          <div
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: 0,
              zIndex: 100,
              background: 'var(--color-accent-subtle)',
              border: '2px dashed var(--color-accent)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-2)',
              pointerEvents: 'none',
              opacity: 0.9,
            }}
          >
            <div style={{
              fontFamily: "'Rajdhani', sans-serif",
              fontSize: '20px',
              fontWeight: 600,
              color: 'var(--color-text)',
            }}>ファイルをドロップして添付</div>
            <div style={{ fontSize: 14, color: 'var(--color-text-muted)' }}>
              テキスト・コード・画像（PNG / JPG / WebP）に対応
            </div>
          </div>
        )}

        {/* Phase 40-04: validation error banner */}
        {attachments.validationError && (
          <div style={{
            padding: 'var(--space-2) var(--space-3)',
            borderBottom: '1px solid var(--color-destructive)',
            background: 'var(--color-surface)',
            fontSize: 14,
            color: 'var(--color-destructive)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            position: 'relative',
            zIndex: 50,
          }}>
            <span aria-hidden="true">⚠</span>
            <span style={{ flex: 1 }}>{attachments.validationError.reason}</span>
            <button
              onClick={attachments.dismissValidationError}
              aria-label="エラーを閉じる"
              style={{
                border: 'none', background: 'transparent',
                color: 'var(--color-text-muted)', cursor: 'pointer',
                fontSize: '16px', lineHeight: 1, padding: 0,
              }}
            >×</button>
          </div>
        )}

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
              streamPreview={streamPreview}
              onSend={handleSend}
              onCancel={cancelJob}
              pendingQuestion={pendingQuestion}
              onQuestionSubmit={handleQuestionSubmit}
              onAskMe={() => { /* AUQ trigger flag — handler は MessageArea/InputBar 内で完結 */ }}
              activeThreadId={activeThreadId}
              // Phase 40-04: AttachmentButton / AttachmentChips を InputBar slot に差し込む
              inputToolbarSlot={
                <AttachmentButton
                  onFilesSelected={(files) => attachments.upload(files)}
                  disabled={isThinking || !activeThreadId}
                  disabledReason={!activeThreadId ? 'no-thread' : 'thinking'}
                />
              }
              inputPreviewSlot={
                <AttachmentChips
                  items={attachments.items}
                  onRemove={attachments.removeItem}
                />
              }
              // Phase 40-04: vision 非対応モデル選択中に画像 staging があれば警告 + ワンクリック切替 CTA
              inputWarningSlot={
                showVisionWarning && suggestedVisionModel ? (
                  <VisionWarningBanner
                    currentModel={currentModelInfo!.name}
                    suggestedModel={modelById(suggestedVisionModel)?.name ?? suggestedVisionModel}
                    onSwitchModel={handleSwitchModel}
                    onDismiss={() => setWarningDismissed(true)}
                  />
                ) : undefined
              }
            />
          )}
        </MainContainer>
      </div>
    </div>
  );
}
