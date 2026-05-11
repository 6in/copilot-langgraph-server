// frontend/src/App.tsx
// Phase 25: React Router v6(v7 declarative) による URL ルーティング
// URL 構造: /{APP_PREFIX}/{appType}/{threadId?}
//   - /orochi/             → MenuScreen
//   - /orochi/chat[/:tid]  → ChatApp
//   - /orochi/superchat/:appSlug[/:tid] → SuperChatWrapper
//   - /orochi/gems         → GemsScreen
//   - /orochi/gemchat/:gemId[/:tid] → GemChatWrapper
//   - /orochi/canvas       → CanvasScreen
//   - /orochi/canvaschat[/:tid] → CanvasChatApp
//   - /orochi/debate[/:tid] → DebateChatApp
// basename("/orochi") は main.tsx の BrowserRouter で設定済み

import { useEffect, useState } from 'react';
import { Routes, Route, useNavigate, useParams, Navigate } from 'react-router';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import { AuthPanel } from './components/AuthPanel';
import { Header } from './components/Header';
import { ChatApp } from './components/ChatApp';
import { SuperChatApp } from './components/SuperChatApp';
import { MenuScreen } from './components/MenuScreen';
import { GemsScreen } from './components/GemsScreen';
import { GemChatApp } from './components/GemChatApp';
import { DebateChatApp } from './components/DebateChatApp';
import { CanvasScreen } from './components/CanvasScreen';
import { CanvasChatApp } from './components/CanvasChatApp';
import { useTheme } from './hooks/useTheme';
import { ThemeContext } from './contexts/ThemeContext';
import { getApps, listGems } from './api/client';
import type { AppDefinition, GemInfo } from './types';

// ---- SuperChat ラッパー: appSlug → AppDefinition 解決 ----
// 25-RESEARCH.md Pitfall 4 対応。useParams で appSlug を取得し、
// /api/apps からアプリ定義を解決してから SuperChatApp に渡す。
function SuperChatWrapper({
  selectedModel,
  theme,
  onToggleTheme,
  onModelChange,
}: {
  selectedModel: string;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onModelChange: (m: string) => void;
}) {
  const { appSlug } = useParams<{ appSlug: string }>();
  const [app, setApp] = useState<AppDefinition | null>(null);
  const [notFound, setNotFound] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const apps = await getApps();
        const found = apps.find((a) => a.slug === appSlug) ?? null;
        if (!cancelled) {
          if (!found) {
            setNotFound(true);
          } else {
            setApp(found);
          }
        }
      } catch {
        if (!cancelled) setNotFound(true);
      }
    })();
    return () => { cancelled = true; };
  }, [appSlug]);

  if (notFound) return <Navigate to="/" replace />;
  if (!app) return null; // ロード中

  return (
    <>
      <Header
        selectedModel={selectedModel}
        onModelChange={onModelChange}
        theme={theme}
        onToggleTheme={onToggleTheme}
        onBackToMenu={() => navigate('/')}
        appName={app.name}
      />
      <SuperChatApp
        selectedModel={selectedModel}
        appId={app.slug}
        appName={app.name}
        appAgents={app.agents}
      />
    </>
  );
}

// ---- GemChat ラッパー: gemId → GemInfo 解決 ----
function GemChatWrapper({
  selectedModel,
  theme,
  onToggleTheme,
  onModelChange,
}: {
  selectedModel: string;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onModelChange: (m: string) => void;
}) {
  const { gemId } = useParams<{ gemId: string }>();
  const [gem, setGem] = useState<GemInfo | null>(null);
  const [notFound, setNotFound] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const gems = await listGems();
        const found = gems.find((g) => g.gem_id === gemId) ?? null;
        if (!cancelled) {
          if (!found) setNotFound(true);
          else setGem(found);
        }
      } catch {
        if (!cancelled) setNotFound(true);
      }
    })();
    return () => { cancelled = true; };
  }, [gemId]);

  if (notFound) return <Navigate to="/gems" replace />;
  if (!gem) return null;

  return (
    <>
      <Header
        selectedModel={selectedModel}
        onModelChange={onModelChange}
        theme={theme}
        onToggleTheme={onToggleTheme}
      />
      <GemChatApp
        gem={gem}
        selectedModel={selectedModel}
        onBack={() => navigate('/gems')}
      />
    </>
  );
}

// ---- Menu / Gems / Canvas スクリーンラッパー(URL ナビゲーション注入) ----
function MenuScreenRoute({
  selectedModel, theme, onToggleTheme, onModelChange,
}: { selectedModel: string; theme: 'light' | 'dark'; onToggleTheme: () => void; onModelChange: (m: string) => void; }) {
  const navigate = useNavigate();
  return (
    <>
      <Header selectedModel={selectedModel} onModelChange={onModelChange} theme={theme} onToggleTheme={onToggleTheme} />
      <MenuScreen
        onNavigate={(app) => {
          if (app.type === 'chat') navigate('/chat');
          else navigate(`/superchat/${app.slug}`);
        }}
        onOpenGems={() => navigate('/gems')}
        onOpenDebate={() => navigate('/debate')}
        onOpenCanvas={() => navigate('/canvas')}
      />
    </>
  );
}

function GemsScreenRoute({
  selectedModel, theme, onToggleTheme, onModelChange,
}: { selectedModel: string; theme: 'light' | 'dark'; onToggleTheme: () => void; onModelChange: (m: string) => void; }) {
  const navigate = useNavigate();
  return (
    <>
      <Header selectedModel={selectedModel} onModelChange={onModelChange} theme={theme} onToggleTheme={onToggleTheme} />
      <GemsScreen
        onSelectGem={(gem) => navigate(`/gemchat/${gem.gem_id}`)}
        onBack={() => navigate('/')}
      />
    </>
  );
}

function CanvasScreenRoute({
  selectedModel, theme, onToggleTheme, onModelChange,
}: { selectedModel: string; theme: 'light' | 'dark'; onToggleTheme: () => void; onModelChange: (m: string) => void; }) {
  const navigate = useNavigate();
  return (
    <>
      <Header selectedModel={selectedModel} onModelChange={onModelChange} theme={theme} onToggleTheme={onToggleTheme} />
      <CanvasScreen
        onBack={() => navigate('/')}
        onStartChat={(tid) => navigate(tid ? `/canvaschat/${tid}` : '/canvaschat')}
      />
    </>
  );
}

// ---- ChatApp / CanvasChatApp / DebateChatApp 用 Header 付きルート ----
function ChatRoute({
  selectedModel, theme, onToggleTheme, onModelChange,
}: { selectedModel: string; theme: 'light' | 'dark'; onToggleTheme: () => void; onModelChange: (m: string) => void; }) {
  const navigate = useNavigate();
  return (
    <>
      <Header selectedModel={selectedModel} onModelChange={onModelChange} theme={theme} onToggleTheme={onToggleTheme} onBackToMenu={() => navigate('/')} />
      {/* Phase 36 D-17: ChatApp 内 VisionWarningBanner CTA からモデル切替を発火するため onModelChange も渡す */}
      <ChatApp selectedModel={selectedModel} onModelChange={onModelChange} />
    </>
  );
}

function CanvasChatRoute({
  selectedModel, theme, onToggleTheme, onModelChange,
}: { selectedModel: string; theme: 'light' | 'dark'; onToggleTheme: () => void; onModelChange: (m: string) => void; }) {
  const navigate = useNavigate();
  return (
    <>
      <Header selectedModel={selectedModel} onModelChange={onModelChange} theme={theme} onToggleTheme={onToggleTheme} />
      <CanvasChatApp selectedModel={selectedModel} onBack={() => navigate('/canvas')} />
    </>
  );
}

function DebateRoute({
  selectedModel, theme, onToggleTheme, onModelChange,
}: { selectedModel: string; theme: 'light' | 'dark'; onToggleTheme: () => void; onModelChange: (m: string) => void; }) {
  const navigate = useNavigate();
  return (
    <>
      <Header selectedModel={selectedModel} onModelChange={onModelChange} theme={theme} onToggleTheme={onToggleTheme} onBackToMenu={() => navigate('/')} appName="討論チャット" />
      <DebateChatApp selectedModel={selectedModel} />
    </>
  );
}

// ---- ルート App コンポーネント ----
export function App() {
  const authValue = useAuthProvider();
  const [selectedModel, setSelectedModel] = useState('gpt-4.1');
  const { theme, toggleTheme } = useTheme();
  const isAuthenticated = authValue.authState === 'authenticated';

  const common = {
    selectedModel,
    theme,
    onToggleTheme: toggleTheme,
    onModelChange: setSelectedModel,
  };

  return (
    <AuthContext.Provider value={authValue}>
      <ThemeContext.Provider value={theme}>
        {isAuthenticated ? (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Routes>
              <Route index element={<MenuScreenRoute {...common} />} />

              <Route path="chat" element={<ChatRoute {...common} />} />
              <Route path="chat/:threadId" element={<ChatRoute {...common} />} />

              <Route path="superchat/:appSlug" element={<SuperChatWrapper {...common} />} />
              <Route path="superchat/:appSlug/:threadId" element={<SuperChatWrapper {...common} />} />

              <Route path="gems" element={<GemsScreenRoute {...common} />} />
              <Route path="gemchat/:gemId" element={<GemChatWrapper {...common} />} />
              <Route path="gemchat/:gemId/:threadId" element={<GemChatWrapper {...common} />} />

              <Route path="canvas" element={<CanvasScreenRoute {...common} />} />
              <Route path="canvaschat" element={<CanvasChatRoute {...common} />} />
              <Route path="canvaschat/:threadId" element={<CanvasChatRoute {...common} />} />

              <Route path="debate" element={<DebateRoute {...common} />} />
              <Route path="debate/:threadId" element={<DebateRoute {...common} />} />

              {/* 未知のパスはメニューへ */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        ) : (
          <AuthPanel />
        )}
      </ThemeContext.Provider>
    </AuthContext.Provider>
  );
}
