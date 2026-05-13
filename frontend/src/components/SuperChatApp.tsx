// frontend/src/components/SuperChatApp.tsx
// SuperChat page — multi-agent orchestration with selectable agent chips.
// Always operates in 'super' mode (no mode toggle).
// Agent selection: horizontal chip row above input area.
// Layout mirrors ChatApp: sidebar + chat area.
// appId scopes threads; appAgents filters displayed agent chips.

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { CanvasPane } from './CanvasPane';
import { GemSelector } from './GemSelector';
import { AttachmentButton } from './AttachmentButton';
import { AttachmentChips } from './AttachmentChips';
import { VisionWarningBanner } from './VisionWarningBanner';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useAgents } from '../hooks/useAgents';
import { useCanvas } from '../hooks/useCanvas';
import { useAttachments } from '../hooks/useAttachments';
import { useModels } from '../hooks/useModels';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { agentAccentColor } from '../utils/agentColor';
import { renameThread } from '../api/client';
import { buildSuperChatPath, isUuidLike, DEFAULT_SUPERCHAT_SLUG } from '../App';
import type { AgentInfo, CanvasAppInfo, ContextMessage } from '../types';

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;

interface SuperChatAppProps {
  selectedModel: string;
  appId: string;
  appName: string;
  appAgents?: string[];
  // Phase 40-04: VisionWarningBanner CTA でモデルを切り替えるために onModelChange を受ける
  onModelChange?: (model: string) => void;
}

interface AgentChipProps {
  agent: AgentInfo;
  selected: boolean;
  onToggle: (name: string) => void;
  isDark: boolean;
}

function AgentChip({ agent, selected, onToggle, isDark }: AgentChipProps) {
  const accentColor = agentAccentColor(agent.name);
  return (
    <button
      onClick={() => onToggle(agent.name)}
      title={agent.description}
      style={{
        padding: '4px 12px',
        borderRadius: '16px',
        border: `1px solid ${selected ? accentColor : (isDark ? '#3a3a52' : '#d1dbe3')}`,
        background: selected ? accentColor : 'transparent',
        color: selected ? '#fff' : (isDark ? '#e8e8f0' : '#555'),
        fontSize: '0.82rem',
        fontWeight: selected ? 600 : 400,
        cursor: 'pointer',
        transition: 'all 0.15s',
        whiteSpace: 'nowrap',
        flexShrink: 0,
      }}
    >
      {agent.name}
    </button>
  );
}

interface AgentSelectorProps {
  agents: AgentInfo[];
  selectedAgents: string[];
  onToggle: (name: string) => void;
  isLoading: boolean;
  isDark: boolean;
}

function AgentSelector({ agents, selectedAgents, onToggle, isLoading, isDark }: AgentSelectorProps) {
  const selectedSet = new Set(selectedAgents);
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 12px',
        borderBottom: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,
        background: isDark ? '#2a2a3e' : '#f8f9fa',
        overflowX: 'auto',
        flexShrink: 0,
        minHeight: '38px',
      }}
    >
      <span
        style={{
          fontSize: '0.78rem',
          color: isDark ? '#9090a8' : '#777',
          whiteSpace: 'nowrap',
          flexShrink: 0,
          marginRight: '4px',
        }}
      >
        Agents:
      </span>
      {isLoading ? (
        <span style={{ fontSize: '0.78rem', color: isDark ? '#9090a8' : '#aaa' }}>Loading...</span>
      ) : agents.length === 0 ? (
        <span style={{ fontSize: '0.78rem', color: '#f0a500' }}>No agents found</span>
      ) : (
        agents.map((agent) => (
          <AgentChip
            key={agent.name}
            agent={agent}
            selected={selectedSet.has(agent.name)}
            onToggle={onToggle}
            isDark={isDark}
          />
        ))
      )}
    </div>
  );
}

export function SuperChatApp({ selectedModel, appId, appName: _appName, appAgents, onModelChange }: SuperChatAppProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';
  // Phase 40-03: Route param 名が slugOrThreadId / threadId に変更。
  // 単独 segment が UUID なら default app の threadId、それ以外なら 3 段目の threadId を採用する。
  const { slugOrThreadId, threadId: routeThreadId } = useParams<{ slugOrThreadId?: string; threadId?: string }>();
  const urlThreadId = isUuidLike(slugOrThreadId) ? slugOrThreadId : routeThreadId;
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
  } = useThreads(appId || 'superchat');

  // Phase 25: URL を single source of truth として switchThread と同期
  // Phase 40: 初回 mount で urlThreadId === undefined && activeThreadId === null の場合は
  // 次の useEffect (auto-create) が起動し、自動的に新規 thread を作成する。
  useEffect(() => {
    if (urlThreadId && urlThreadId !== activeThreadId) {
      switchThread(urlThreadId);
    }
  }, [urlThreadId, activeThreadId, switchThread]);

  // Phase 40 UI-INIT-THREAD (#10): Chat 側と同形。buildSuperChatPath で default app 短縮形
  // (/superchat/{uuid}) を維持する。AND 3 条件 + inFlight gate で初回 mount 直後の
  // 中ぶらりん状態だけが通過する。useThreads.createNewThread が activeThreadId を更新するため、
  // 自動作成後の再 render では activeThreadId !== null となり再発火しない。
  const initThreadInFlightRef = useRef<boolean>(false);
  useEffect(() => {
    if (initThreadInFlightRef.current) return;
    if (urlThreadId !== undefined) return; // URL に既に thread がある
    if (activeThreadId !== null) return; // 既存 thread がアクティブ
    if (messages.length !== 0) return; // 既存メッセージが残っている
    initThreadInFlightRef.current = true;
    (async () => {
      try {
        const tid = await createNewThread();
        navigate(buildSuperChatPath(appId || DEFAULT_SUPERCHAT_SLUG, tid), { replace: true });
      } finally {
        initThreadInFlightRef.current = false;
      }
    })();
  }, [urlThreadId, activeThreadId, messages.length, createNewThread, navigate, appId]);

  // Phase 40-04: model info を /api/models から取得し、useAttachments の vision_limits pre-validate を有効化
  const { modelById, suggestedVisionModel } = useModels();
  const currentModelInfo = modelById(selectedModel);

  // Phase 40-04: staging attachments — selectedModelInfo を渡すと vision_limits pre-validate が有効化される
  const attachments = useAttachments(activeThreadId, currentModelInfo ?? null);

  // Phase 40-04: vision 警告バナー dismiss state (モデル変更時にリセット)
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

  // Fetch all agents then filter client-side to the app's declared agents (Option A)
  const { agents: allAgents, selectedAgents, toggleAgent, isLoading: agentsLoading } = useAgents();

  // Filter agents to those declared in appAgents (if provided); default select all app agents
  const filteredAgents = appAgents && appAgents.length > 0
    ? allAgents.filter((a) => appAgents.includes(a.name))
    : allAgents;

  // Keep only selectedAgents that are in filteredAgents (avoid stale selection after app change)
  const visibleSelectedAgents = selectedAgents.filter(
    (name) => filteredAgents.some((a) => a.name === name)
  );

  const [selectedGemIds, setSelectedGemIds] = useState<string[]>([]);
  const handleToggleGem = (gemId: string) => {
    setSelectedGemIds((prev) =>
      prev.includes(gemId) ? prev.filter((id) => id !== gemId) : [...prev, gemId]
    );
  };

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const dragStartX = useRef<number | null>(null);
  const dragStartWidth = useRef<number>(SIDEBAR_DEFAULT);

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

  const { isThinking, currentTool, streamPreview, sendMessage, cancelJob, pendingQuestion, handleQuestionSubmit } = useChat({
    activeThreadId,
    selectedModel,
    selectedMode: 'super',
    agents: visibleSelectedAgents,
    appId: appId || undefined,
    gemIds: selectedGemIds,
    onCanvasResponse: (app: CanvasAppInfo) => setCanvasApp(app),
    setMessages,
    refreshThreads,
    // Phase 40-04: attachments pipeline — ChatRequest.attachments への載せ替えと送信成功時のクリア
    getReadyAttachments: attachments.getReadyItems,
    onAttachmentsSent: attachments.clearAll,
  });

  const handleNewChat = async () => {
    const tid = await createNewThread();
    navigate(buildSuperChatPath(appId || DEFAULT_SUPERCHAT_SLUG, tid), { replace: true });
  };

  const handleSelectThread = async (threadId: string) => {
    navigate(buildSuperChatPath(appId || DEFAULT_SUPERCHAT_SLUG, threadId));
  };

  const handleRenameThread = async (threadId: string, label: string) => {
    await renameThread(threadId, label);
    await refreshThreads();
  };

  const handleSend = async (text: string, contextMessages?: ContextMessage[]) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
      navigate(buildSuperChatPath(appId || DEFAULT_SUPERCHAT_SLUG, threadId), { replace: true });
    }
    await sendMessage(text, threadId, contextMessages);
    await refreshThreads();
  };

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

        {/* Chat area: agent selector + gem selector + messages */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, overflow: 'hidden' }}>
          <AgentSelector
            agents={filteredAgents}
            selectedAgents={visibleSelectedAgents}
            onToggle={toggleAgent}
            isLoading={agentsLoading}
            isDark={isDark}
          />
          <GemSelector
            selectedGemIds={selectedGemIds}
            onToggleGem={handleToggleGem}
          />

          {isLoadingMessages ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
              <p>Loading messages...</p>
            </div>
          ) : (
            <MessageArea
              messages={messages}
              isThinking={isThinking}
              currentTool={currentTool}
              streamPreview={streamPreview}
              onSend={handleSend}
              onCancel={cancelJob}
              enableResend
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
        </div>
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
      </MainContainer>
    </div>
  );
}
