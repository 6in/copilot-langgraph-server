// frontend/src/components/DebateChatApp.tsx
// Phase 17: 討論チャットアプリ
// 設定パネル (DebateConfigPanel) → チャット画面 (MessageArea + ExtensionBanner) の 2 フェーズ構造。
// SuperChatApp.tsx のレイアウトパターンを流用。

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useAgents } from '../hooks/useAgents';
import { useGems } from '../hooks/useGems';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { renameThread } from '../api/client';
import type { AgentInfo, GemInfo } from '../types';

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;

// 討論パターン
type DebatePattern = 'debate' | 'panel' | 'chain';

interface DebateConfig {
  pattern: DebatePattern;
  participants: string[];
  gemIds: string[];
  gemNames: string[];
  maxTurns: number;
}

interface DebateChatAppProps {
  selectedModel: string;
}

// ---- SelectableChip (汎用チェックボックス風チップ) ----

interface SelectableChipProps {
  id: string;
  label: string;
  description?: string;
  selected: boolean;
  onToggle: (id: string) => void;
  isDark: boolean;
}

function SelectableChip({ id, label, description, selected, onToggle, isDark }: SelectableChipProps) {
  const accentColor = isDark ? '#7c6ff7' : '#0366d6';

  return (
    <button
      role="checkbox"
      aria-checked={selected}
      onClick={() => onToggle(id)}
      title={description}
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
      {label}
    </button>
  );
}

// ---- ParticipantChecklist ----

interface ParticipantChecklistProps {
  agents: AgentInfo[];
  gems: GemInfo[];
  selectedIds: string[];  // agent名 or "gem:<gem_id>"
  onToggle: (id: string) => void;
  isLoading: boolean;
  isDark: boolean;
}

function ParticipantChecklist({
  agents,
  gems,
  selectedIds,
  onToggle,
  isLoading,
  isDark,
}: ParticipantChecklistProps) {
  const selectedSet = new Set(selectedIds);
  const textColor = isDark ? '#e8e8f0' : '#333';
  const mutedColor = isDark ? '#9090a8' : '#aaa';
  const warningColor = '#f0a500';
  const sectionLabelStyle = { fontSize: '0.75rem', color: mutedColor, marginBottom: '6px', marginTop: '8px' };

  return (
    <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
      <legend
        id="participants-legend"
        style={{ fontSize: '20px', fontWeight: 600, color: textColor, marginBottom: '12px', padding: 0 }}
      >
        参加者
      </legend>
      {isLoading ? (
        <span style={{ fontSize: '0.78rem', color: mutedColor }}>Loading...</span>
      ) : agents.length === 0 && gems.length === 0 ? (
        <span style={{ fontSize: '0.78rem', color: warningColor }}>エージェント・Gem が見つかりません</span>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {agents.length > 0 && (
            <>
              <div style={sectionLabelStyle}>エージェント</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                {agents.map((agent) => (
                  <SelectableChip
                    key={agent.name}
                    id={agent.name}
                    label={agent.name}
                    description={agent.description}
                    selected={selectedSet.has(agent.name)}
                    onToggle={onToggle}
                    isDark={isDark}
                  />
                ))}
              </div>
            </>
          )}
          {gems.length > 0 && (
            <>
              <div style={sectionLabelStyle}>Gem</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {gems.map((gem) => (
                  <SelectableChip
                    key={gem.gem_id}
                    id={`gem:${gem.gem_id}`}
                    label={gem.name}
                    description={gem.description}
                    selected={selectedSet.has(`gem:${gem.gem_id}`)}
                    onToggle={onToggle}
                    isDark={isDark}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </fieldset>
  );
}

// ---- PatternRadioGroup ----

interface PatternRadioGroupProps {
  value: DebatePattern;
  onChange: (p: DebatePattern) => void;
  isDark: boolean;
}

const PATTERNS: { value: DebatePattern; label: string; description: string }[] = [
  { value: 'debate', label: '討論 (Debate)', description: 'A と B が交互に反論する' },
  { value: 'panel', label: 'パネル (Panel)', description: '複数エージェントが順に意見を述べる' },
  { value: 'chain', label: 'チェーン (Chain)', description: 'A → B → C の順に引き継ぐ' },
];

function PatternRadioGroup({ value, onChange, isDark }: PatternRadioGroupProps) {
  const labelId = 'pattern-group-label';
  const textColor = isDark ? '#e8e8f0' : '#333';
  const mutedColor = isDark ? '#9090a8' : '#777';
  const accentColor = isDark ? '#7c6ff7' : '#0366d6';

  return (
    <div role="radiogroup" aria-labelledby={labelId}>
      <div
        id={labelId}
        style={{
          fontSize: '20px',
          fontWeight: 600,
          color: textColor,
          marginBottom: '12px',
        }}
      >
        会話パターン
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {PATTERNS.map((p) => (
          <label
            key={p.value}
            style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer' }}
          >
            <input
              type="radio"
              name="debate-pattern"
              value={p.value}
              checked={value === p.value}
              onChange={() => onChange(p.value)}
              style={{ marginTop: '3px', accentColor }}
            />
            <span>
              <span style={{ fontSize: '16px', color: textColor }}>
                {p.label}
              </span>
              <span
                style={{
                  display: 'block',
                  fontSize: '12.5px',
                  color: mutedColor,
                  marginTop: '2px',
                }}
              >
                {p.description}
              </span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

// ---- ExtensionBanner ----

interface ExtensionBannerProps {
  currentTurn: number;
  extensionTurns: number;
  onExtensionTurnsChange: (v: number) => void;
  onExtend: () => void;
  onEnd: () => void;
  isDark: boolean;
}

function ExtensionBanner({
  currentTurn,
  extensionTurns,
  onExtensionTurnsChange,
  onExtend,
  onEnd,
  isDark,
}: ExtensionBannerProps) {
  const accentColor = isDark ? '#7c6ff7' : '#0366d6';
  const bannerBg = isDark ? 'rgba(124, 111, 247, 0.15)' : 'rgba(3, 102, 214, 0.08)';
  const bannerBorder = isDark ? '1px solid #7c6ff7' : '1px solid #0366d6';
  const textColor = isDark ? '#e8e8f0' : '#333';

  return (
    <div
      role="alert"
      style={{
        background: bannerBg,
        border: bannerBorder,
        borderRadius: '8px',
        padding: '12px 16px',
        margin: '0 0 8px',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          fontSize: '15px',
          fontWeight: 600,
          color: textColor,
          marginBottom: '10px',
        }}
      >
        討論が {currentTurn} ターン終了しました
      </div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '12px',
          flexWrap: 'wrap',
        }}
      >
        <span style={{ fontSize: '14px', color: textColor }}>あと</span>
        <input
          type="number"
          min={1}
          max={20}
          value={extensionTurns}
          onChange={(e) => onExtensionTurnsChange(Math.min(20, Math.max(1, Number(e.target.value))))}
          aria-label="延長ターン数"
          style={{
            width: '64px',
            padding: '4px 8px',
            border: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,
            borderRadius: '4px',
            background: isDark ? '#1e1e2e' : '#fff',
            color: textColor,
            fontSize: '14px',
          }}
        />
        <span style={{ fontSize: '14px', color: textColor }}>ターン</span>
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        <button
          onClick={onExtend}
          style={{
            background: accentColor,
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            padding: '7px 16px',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          延長する
        </button>
        <button
          onClick={onEnd}
          style={{
            background: 'transparent',
            color: textColor,
            border: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,
            borderRadius: '6px',
            padding: '7px 16px',
            fontSize: '14px',
            cursor: 'pointer',
          }}
        >
          終了する
        </button>
      </div>
    </div>
  );
}

// ---- DebateConfigPanel ----

interface DebateConfigPanelProps {
  onStart: (config: DebateConfig) => void;
  isDark: boolean;
}

function DebateConfigPanel({ onStart, isDark }: DebateConfigPanelProps) {
  const { agents, isLoading: agentsLoading } = useAgents();
  const { gems, isLoading: gemsLoading } = useGems();
  const [pattern, setPattern] = useState<DebatePattern>('debate');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [maxTurns, setMaxTurns] = useState(3);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const textColor = isDark ? '#e8e8f0' : '#333';
  const panelBg = isDark ? '#2a2a3e' : '#fff';
  const panelBorder = isDark ? '1px solid #3a3a52' : '1px solid #d1dbe3';
  const accentColor = isDark ? '#7c6ff7' : '#0366d6';
  const screenBg = isDark ? '#1e1e2e' : '#f5f5f5';

  const handleToggleParticipant = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((n) => n !== id) : [...prev, id]
    );
    setValidationError(null);
  };

  const handleStart = () => {
    if (selectedIds.length < 2) {
      setValidationError('参加者を2名以上選択してください');
      return;
    }
    setIsSubmitting(true);
    const participants = selectedIds.filter((id) => !id.startsWith('gem:'));
    const gemIds = selectedIds.filter((id) => id.startsWith('gem:')).map((id) => id.slice(4));
    const gemNames = gems
      .filter((g) => gemIds.includes(g.gem_id))
      .map((g) => g.name);
    onStart({ pattern, participants, gemIds, gemNames, maxTurns });
  };

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        padding: '48px 16px 32px',
        background: screenBg,
        overflowY: 'auto',
      }}
    >
      <div
        style={{
          maxWidth: '480px',
          width: '100%',
          background: panelBg,
          border: panelBorder,
          borderRadius: '12px',
          padding: '32px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
        }}
      >
        <h2
          style={{
            margin: 0,
            fontSize: '20px',
            fontWeight: 600,
            color: textColor,
          }}
        >
          討論チャットを設定
        </h2>

        {/* セクション1: パターン選択 */}
        <PatternRadioGroup value={pattern} onChange={setPattern} isDark={isDark} />

        {/* セクション2: 参加者選択 */}
        <ParticipantChecklist
          agents={agents}
          gems={gems}
          selectedIds={selectedIds}
          onToggle={handleToggleParticipant}
          isLoading={agentsLoading || gemsLoading}
          isDark={isDark}
        />

        {/* バリデーションエラー */}
        {validationError && (
          <div
            role="alert"
            style={{ fontSize: '16px', color: '#e05252' }}
          >
            {validationError}
          </div>
        )}

        {/* セクション3: ターン数入力 */}
        <div>
          <label
            htmlFor="max-turns"
            style={{
              display: 'block',
              fontSize: '20px',
              fontWeight: 600,
              color: textColor,
              marginBottom: '12px',
            }}
          >
            各エージェントのターン数
          </label>
          <input
            id="max-turns"
            type="number"
            min={1}
            max={20}
            value={maxTurns}
            onChange={(e) => setMaxTurns(Math.min(20, Math.max(1, Number(e.target.value))))}
            style={{
              width: '64px',
              padding: '6px 10px',
              border: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,
              borderRadius: '6px',
              background: isDark ? '#1e1e2e' : '#fff',
              color: textColor,
              fontSize: '16px',
            }}
          />
        </div>

        {/* 討論を開始ボタン */}
        <button
          onClick={handleStart}
          disabled={isSubmitting}
          aria-disabled={isSubmitting}
          style={{
            width: '100%',
            background: isSubmitting ? 'rgba(3, 102, 214, 0.5)' : accentColor,
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '16px',
            fontWeight: 600,
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            opacity: isSubmitting ? 0.6 : 1,
            transition: 'opacity 0.15s',
          }}
        >
          {isSubmitting ? '開始中...' : '討論を開始'}
        </button>
      </div>
    </div>
  );
}

// ---- DebateChatPanel (チャットフェーズ) ----

interface DebateChatPanelProps {
  config: DebateConfig;
  selectedModel: string;
}

function DebateChatPanel({ config, selectedModel }: DebateChatPanelProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';
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
    setMessages,
    refreshThreads,
  } = useThreads('debate');

  // Phase 25: URL を single source of truth として switchThread と同期
  useEffect(() => {
    if (urlThreadId && urlThreadId !== activeThreadId) {
      switchThread(urlThreadId);
    }
  }, [urlThreadId, activeThreadId, switchThread]);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const dragStartX = useRef<number | null>(null);
  const dragStartWidth = useRef<number>(SIDEBAR_DEFAULT);

  const [currentTurn, setCurrentTurn] = useState(0);
  const [awaitingExtension, setAwaitingExtension] = useState(false);
  const [debateEnded, setDebateEnded] = useState(false);
  const [extensionTurns, setExtensionTurns] = useState(3);
  const [dynamicMaxTurns, setDynamicMaxTurns] = useState(config.maxTurns);
  const [dynamicCurrentTurn, setDynamicCurrentTurn] = useState<number | undefined>(undefined);

  const handleDebateResult = useCallback(
    (result: { debate_text: string; final_turn: number; max_turns: number; is_complete: boolean }) => {
      setCurrentTurn(result.final_turn);
      if (result.is_complete) {
        setAwaitingExtension(true);
      }
    },
    []
  );

  const { isThinking, sendMessage } = useChat({
    activeThreadId,
    selectedModel,
    selectedTaskType: 'debate',
    appId: 'debate',
    participants: config.participants,
    pattern: config.pattern,
    maxTurns: dynamicMaxTurns,
    currentTurn: dynamicCurrentTurn,
    gemIds: config.gemIds,
    setMessages,
    refreshThreads,
    onDebateResult: handleDebateResult,
  });

  const handleNewChat = async () => {
    const tid = await createNewThread();
    navigate(`/debate/${tid}`, { replace: true });
  };

  const handleSelectThread = async (threadId: string) => {
    navigate(`/debate/${threadId}`);
  };

  const handleRenameThread = async (threadId: string, label: string) => {
    await renameThread(threadId, label);
    await refreshThreads();
  };

  const handleSend = async (text: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
      navigate(`/debate/${threadId}`, { replace: true });
    }
    await sendMessage(text, threadId);
    await refreshThreads();
  };

  const handleExtend = () => {
    if (!activeThreadId) return; // 延長は既存スレッドが必須
    const newMaxTurns = currentTurn + extensionTurns;
    setDynamicMaxTurns(newMaxTurns);
    setDynamicCurrentTurn(currentTurn);
    setAwaitingExtension(false);
    // 再エンキュー: 延長メッセージを送信
    handleSend('延長');
  };

  const handleEnd = () => {
    setAwaitingExtension(false);
    setDebateEnded(true);
  };

  const handleDividerMouseDown = useCallback(
    (e: React.MouseEvent) => {
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
    },
    [sidebarWidth]
  );

  // MessageArea の disabled 状態と placeholder
  const inputDisabled = isThinking || debateEnded || awaitingExtension;
  const inputPlaceholder = isThinking
    ? '討論進行中...'
    : debateEnded
    ? '討論が終了しました'
    : awaitingExtension
    ? '延長または終了を選択してください'
    : 'お題を入力して討論を開始してください';

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
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = '#b0c4d8';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
          />
        )}

        {/* チャットエリア */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minWidth: 0,
            overflow: 'hidden',
          }}
        >
          {/* 参加者チップ行 */}
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
              参加者:
            </span>
            {[...config.participants, ...config.gemNames].map((name) => (
              <span
                key={name}
                style={{
                  padding: '4px 12px',
                  borderRadius: '16px',
                  border: `1px solid ${isDark ? '#7c6ff7' : '#0366d6'}`,
                  background: isDark ? '#7c6ff7' : '#0366d6',
                  color: '#fff',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                }}
              >
                {name}
              </span>
            ))}
          </div>

          {isLoadingMessages ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flex: 1,
              }}
            >
              <p>Loading messages...</p>
            </div>
          ) : (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                flex: 1,
                minHeight: 0,
              }}
            >
              {/* ExtensionBanner: MessageArea と MessageInput の間 */}
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
                <MessageArea
                  messages={messages}
                  isThinking={isThinking}
                  onSend={inputDisabled ? () => {} : handleSend}
                  disabled={inputDisabled}
                  placeholder={inputPlaceholder}
                />
                {awaitingExtension && (
                  <div style={{ padding: '0 8px 0' }}>
                    <ExtensionBanner
                      currentTurn={currentTurn}
                      extensionTurns={extensionTurns}
                      onExtensionTurnsChange={setExtensionTurns}
                      onExtend={handleExtend}
                      onEnd={handleEnd}
                      isDark={isDark}
                    />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </MainContainer>
    </div>
  );
}

// ---- DebateChatApp (メインコンテナ) ----

export function DebateChatApp({ selectedModel }: DebateChatAppProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';
  const [config, setConfig] = useState<DebateConfig | null>(null);

  const handleStart = (c: DebateConfig) => {
    setConfig(c);
  };

  if (config === null) {
    return <DebateConfigPanel onStart={handleStart} isDark={isDark} />;
  }

  return <DebateChatPanel config={config} selectedModel={selectedModel} />;
}
