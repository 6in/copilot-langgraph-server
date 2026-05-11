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
import { AttachmentButton } from './AttachmentButton';
import { AttachmentChips } from './AttachmentChips';
import { VisionWarningBanner } from './VisionWarningBanner';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useCanvas } from '../hooks/useCanvas';
import { useAttachments } from '../hooks/useAttachments';
import { useModels } from '../hooks/useModels';
import { renameThread } from '../api/client';

// Phase 36 D-06 staging クリア契約 (4 ケース):
// A. ユーザー明示キャンセル (cancelJob 経路) -> staging 残す (useChat.cancelJob は onAttachmentsSent を呼ばない)
// B. 技術失敗 (postChat 例外 / SSE error fallback) -> staging 残す (ユーザーが再送できる)
// C. graceful fallback (vision 非対応での text 応答含む、送信は成功扱い) -> useChat.onAttachmentsSent -> attachments.clearAll()
// D. ユーザー手動 × 削除 -> useAttachments.removeItem -> DELETE /api/threads/{tid}/attachments/{name}
//
// Task 3a で実装する useChat.onAttachmentsSent コールバックがケース C を扱う。

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;

interface ChatAppProps {
  selectedModel: string;
  // Phase 36 D-17: VisionWarningBanner CTA でモデルを切り替えるために onModelChange を受ける
  onModelChange: (model: string) => void;
}

export function ChatApp({ selectedModel, onModelChange }: ChatAppProps) {
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

  // Phase 36 D-16: model info を /api/models から取得し、useAttachments の vision_limits pre-validate を有効化
  const { modelById, suggestedVisionModel } = useModels();
  const currentModelInfo = modelById(selectedModel);

  // Phase 36: staging attachments — selectedModelInfo を渡すと vision_limits pre-validate (D-19) が有効化される
  const attachments = useAttachments(activeThreadId, currentModelInfo ?? null);

  // Phase 36 D-17: vision 警告バナー dismiss state
  // モデル変更時にリセット (新しい選択で再評価)
  const [warningDismissed, setWarningDismissed] = useState(false);
  useEffect(() => {
    setWarningDismissed(false);
  }, [selectedModel]);

  // 画像 staging アイテムがあるかつモデルが vision=false なら表示
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
    if (suggestedVisionModel) {
      onModelChange(suggestedVisionModel);
    }
  }, [suggestedVisionModel, onModelChange]);

  // Phase 36 D-04: drop zone overlay state + paste listener
  const [dragOver, setDragOver] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const onDragOver = useCallback((e: React.DragEvent) => {
    if (e.dataTransfer.types.includes('Files')) {
      e.preventDefault();
      setDragOver(true);
    }
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    // 子要素に移った dragleave を無視
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
    // Phase 36 D-14: useChat.sendMessage が attachments を ChatRequest body に載せる
    getReadyAttachments: attachments.getReadyItems,
    // Phase 36 D-06 ケース C: 送信成功時 useChat 内部から staging クリアを呼ぶ
    onAttachmentsSent: attachments.clearAll,
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
    // Phase 36 D-06: staging クリアは useChat.onAttachmentsSent (ケース C) 経由で
    // 行うためここでは呼ばない。重複呼び出しすると D-06 の 4 ケース挙動が崩れる。
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
    <div
      ref={rootRef}
      style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' }}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* Phase 36: drop overlay (drag-over 中のみ表示) */}
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

      {/* Phase 36: validation error banner (D-04 で reject された file の表示) */}
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
              activeThreadId={activeThreadId}
              // Phase 36: AttachmentButton / AttachmentChips を InputBar slot に差し込む
              inputToolbarSlot={
                <AttachmentButton
                  onFilesSelected={(files) => attachments.upload(files)}
                  disabled={isThinking || !activeThreadId}
                />
              }
              inputPreviewSlot={
                <AttachmentChips
                  items={attachments.items}
                  onRemove={attachments.removeItem}
                />
              }
              // Phase 36 D-17: vision 非対応モデル選択中に画像 staging があれば警告 + ワンクリック切替 CTA
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
