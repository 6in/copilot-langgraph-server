// frontend/src/components/SuperChatApp.tsx
// SuperChat page — multi-agent orchestration with selectable agent chips.
// Always operates in 'super' mode (no mode toggle).
// Agent selection: horizontal chip row above input area.
// Layout mirrors ChatApp: sidebar + chat area.
// appId scopes threads; appAgents filters displayed agent chips.

import { useCallback, useRef, useState } from 'react';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { CanvasPane } from './CanvasPane';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useAgents } from '../hooks/useAgents';
import { useCanvas } from '../hooks/useCanvas';
import { renameThread } from '../api/client';
import type { AgentInfo, CanvasAppInfo } from '../types';

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;

interface SuperChatAppProps {
  selectedModel: string;
  appId: string;
  appName: string;
  appAgents?: string[];
}

interface AgentChipProps {
  agent: AgentInfo;
  selected: boolean;
  onToggle: (name: string) => void;
}

function AgentChip({ agent, selected, onToggle }: AgentChipProps) {
  return (
    <button
      onClick={() => onToggle(agent.name)}
      title={agent.description}
      style={{
        padding: '4px 12px',
        borderRadius: '16px',
        border: `1px solid ${selected ? '#0366d6' : '#d1dbe3'}`,
        background: selected ? '#0366d6' : 'transparent',
        color: selected ? '#fff' : '#555',
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
}

function AgentSelector({ agents, selectedAgents, onToggle, isLoading }: AgentSelectorProps) {
  const selectedSet = new Set(selectedAgents);
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 12px',
        borderBottom: '1px solid #d1dbe3',
        background: '#f8f9fa',
        overflowX: 'auto',
        flexShrink: 0,
        minHeight: '38px',
      }}
    >
      <span
        style={{
          fontSize: '0.78rem',
          color: '#777',
          whiteSpace: 'nowrap',
          flexShrink: 0,
          marginRight: '4px',
        }}
      >
        Agents:
      </span>
      {isLoading ? (
        <span style={{ fontSize: '0.78rem', color: '#aaa' }}>Loading...</span>
      ) : agents.length === 0 ? (
        <span style={{ fontSize: '0.78rem', color: '#f0a500' }}>No agents found</span>
      ) : (
        agents.map((agent) => (
          <AgentChip
            key={agent.name}
            agent={agent}
            selected={selectedSet.has(agent.name)}
            onToggle={onToggle}
          />
        ))
      )}
    </div>
  );
}

export function SuperChatApp({ selectedModel, appId, appName: _appName, appAgents }: SuperChatAppProps) {
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
  } = useThreads(appId || 'superchat');

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

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const [selectedGemId, setSelectedGemId] = useState<string | null>(null);
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

  const { isThinking, sendMessage } = useChat({
    activeThreadId,
    selectedModel,
    selectedMode: 'super',
    agents: visibleSelectedAgents,
    appId: appId || undefined,
    gemId: selectedGemId,
    onCanvasResponse: (app: CanvasAppInfo) => setCanvasApp(app),
    setMessages,
    refreshThreads,
  });

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

  const handleSend = async (text: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
    }
    await sendMessage(text, threadId);
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

        {/* Chat area: agent selector + messages */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, overflow: 'hidden' }}>
          <AgentSelector
            agents={filteredAgents}
            selectedAgents={visibleSelectedAgents}
            onToggle={toggleAgent}
            isLoading={agentsLoading}
          />

          {isLoadingMessages ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
              <p>Loading messages...</p>
            </div>
          ) : (
            <MessageArea
              messages={messages}
              isThinking={isThinking}
              onSend={handleSend}
              selectedGemId={selectedGemId}
              onSelectGem={setSelectedGemId}
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
