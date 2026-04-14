// frontend/src/components/CanvasChatApp.tsx
// CanvasChatApp: Canvas App 専用チャット画面。
// 左右分割レイアウト: ThreadSidebar + sidebar drag handle + MessageArea + canvas drag handle + CanvasPane
// GemChatApp.tsx を参照実装として、CanvasPane 常時表示（D-01〜D-04, D-14, D-15, D-17）を追加。
// Phase 25: canvasGemId を内部で取得、useParams/useNavigate で URL 同期。

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { CanvasPane } from './CanvasPane';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';
import { useCanvas } from '../hooks/useCanvas';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { renameThread, getCanvasGemId } from '../api/client';

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const SIDEBAR_DEFAULT = 240;
const CANVAS_PANE_MIN = 320;    // UI-SPEC: CanvasPane 最小幅
const CANVAS_PANE_DEFAULT = 400; // 初期幅（ピクセル）

// Phase 25: canvasGemId と initialThreadId props を廃止
// App.tsx 側は selectedModel と onBack のみ渡す
interface CanvasChatAppProps {
  selectedModel: string;
  onBack: () => void;
}

export function CanvasChatApp({ selectedModel, onBack }: CanvasChatAppProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const cardBg = isDark ? '#2a2a3e' : '#ffffff';
  const textColor = isDark ? '#e0e0e0' : '#333333';

  const { threadId: urlThreadId } = useParams<{ threadId?: string }>();
  const navigate = useNavigate();

  // Phase 25: canvasGemId をマウント時に内部取得（App.tsx の state を廃止）
  const [canvasGemId, setCanvasGemId] = useState<string | null>(null);
  const [gemLoadError, setGemLoadError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { gem_id } = await getCanvasGemId();
        if (!cancelled) setCanvasGemId(gem_id);
      } catch {
        if (!cancelled) setGemLoadError(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // D-17: gem_id でスレッドを分離（app_id に依存しない）
  // canvasGemId が取得できるまで useThreads を呼ばない（空文字避け）
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
  } = useThreads(undefined, canvasGemId ?? undefined);

  // Phase 25: URL を single source of truth として switchThread と同期
  useEffect(() => {
    if (urlThreadId && urlThreadId !== activeThreadId) {
      switchThread(urlThreadId);
    }
  }, [urlThreadId, activeThreadId, switchThread]);

  // サイドバー幅
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const dragStartX = useRef<number | null>(null);
  const dragStartWidth = useRef<number>(SIDEBAR_DEFAULT);

  // Canvas ペイン幅
  const [canvasPaneWidth, setCanvasPaneWidth] = useState(CANVAS_PANE_DEFAULT);
  const canvasDragStartX = useRef<number | null>(null);
  const canvasDragStartWidth = useRef<number>(CANVAS_PANE_DEFAULT);
  // ドラッグ中フラグ — iframe がマウスイベントを奪うのを防ぐオーバーレイ制御に使う
  const [isResizing, setIsResizing] = useState(false);

  // Canvas 状態管理
  const { canvasApp, setCanvasApp, isSaving, isDeploying, deployUrl, deployError, saveCanvas, deployCanvas, loadCanvasForThread } = useCanvas();

  // エディタの現在の HTML（AI生成 or ユーザー手動編集）を追跡
  // 送信時にこれをプロンプトに埋め込むことで、AI が常に最新 HTML をベースに修正できる
  const [currentHtml, setCurrentHtml] = useState<string | null>(null);

  // TODO: DB 永続化 — 現状はフロント state のみの即時表示（LangGraph checkpointer には反映されない）
  const handleDeploy = useCallback(async (appId: string): Promise<string> => {
    const url = await deployCanvas(appId);
    const htmlSnippet = currentHtml
      ? currentHtml.slice(0, 200) + (currentHtml.length > 200 ? '...' : '')
      : '';
    const deployMessage = `🚀 **デプロイ完了**\n\nURL: [${url}](${url})\n\n\`\`\`html\n${htmlSnippet}\n\`\`\``;
    setMessages((prev) => [...prev, { role: 'ai' as const, content: deployMessage, senderName: 'System' }]);
    return url;
  }, [deployCanvas, currentHtml, setMessages]);

  // スレッド切り替え時に最新の canvas app を復元（Todo #2）
  useEffect(() => {
    if (!activeThreadId) {
      setCanvasApp(null);
      setCurrentHtml(null);
      return;
    }
    loadCanvasForThread(activeThreadId);
  }, [activeThreadId, loadCanvasForThread, setCanvasApp]);

  // DB からスレッドの canvasApp が復元されたとき currentHtml を初期化する
  // app_id が変わったとき（＝別スレッドに切り替え）のみ実行し、ユーザー編集を上書きしない
  useEffect(() => {
    if (canvasApp?.html) setCurrentHtml(canvasApp.html);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasApp?.app_id]);

  const handleNewChat = async () => {
    const tid = await createNewThread();
    navigate(`/canvaschat/${tid}`, { replace: true });
  };

  const handleSelectThread = async (threadId: string) => {
    navigate(`/canvaschat/${threadId}`);
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
    gemId: canvasGemId ?? undefined,
    setMessages,
    refreshThreads,
    onCanvasResponse: (app) => { setCanvasApp(app); setCurrentHtml(app.html); },
  });

  const handleSend = async (text: string) => {
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
      navigate(`/canvaschat/${threadId}`, { replace: true });
    }
    // エディタに HTML があればプロンプトに埋め込む — AI が常に最新 HTML をベースに修正できる
    const prompt = currentHtml
      ? `${text}\n\n（現在の HTML）\n\`\`\`html\n${currentHtml}\n\`\`\``
      : text;
    await sendMessage(prompt, threadId);
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
    setIsResizing(true); // オーバーレイ表示: iframe のマウスイベント奪取を防ぐ

    const onMouseMove = (ev: MouseEvent) => {
      if (canvasDragStartX.current === null) return;
      const delta = ev.clientX - canvasDragStartX.current;
      // 右から左への drag で CanvasPane が拡大 → delta を反転
      const newWidth = Math.max(CANVAS_PANE_MIN, canvasDragStartWidth.current - delta);
      setCanvasPaneWidth(newWidth);
    };

    const onMouseUp = () => {
      canvasDragStartX.current = null;
      setIsResizing(false); // オーバーレイ非表示
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }, [canvasPaneWidth]);

  // gemId ロード前はローディング表示、エラー時はエラー表示
  if (!canvasGemId) {
    if (gemLoadError) return <div>Canvas gem が取得できませんでした</div>;
    return null;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* ドラッグ中オーバーレイ: iframe がマウスイベントを奪うのを防ぐ */}
      {isResizing && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999, cursor: 'col-resize',
        }} />
      )}
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
              onDeploy={handleDeploy}
              onClose={() => {}}
              onHtmlChange={setCurrentHtml}
              style={{ minWidth: `${CANVAS_PANE_MIN}px`, width: `${canvasPaneWidth}px` }}
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
