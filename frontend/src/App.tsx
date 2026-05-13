// frontend/src/App.tsx
// Phase 25: React Router v6(v7 declarative) による URL ルーティング
// URL 構造: /{APP_PREFIX}/{appType}/{threadId?}
//   - /orochi/             → MenuScreen
//   - /orochi/chat[/:tid]  → ChatApp
//   - /orochi/superchat                    → SuperChatWrapper (default app)             (Phase 40-03)
//   - /orochi/superchat/<uuid>             → SuperChatWrapper (default app, thread=uuid) (Phase 40-03)
//   - /orochi/superchat/<slug>[/<uuid>]    → SuperChatWrapper (別 app)
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

// ---- SuperChat URL helpers (Phase 40-03) ----
// Default app の slug。`applications` テーブル上の default SuperChat 行と一致。
export const DEFAULT_SUPERCHAT_SLUG = 'superchat';

// UUID 形式判定 (RFC 4122 v1-v5 互換、case insensitive)。
// `applications.slug` は UUID 形式禁止前提のため、UUID なら threadId と確定できる。
// eslint-disable-next-line react-refresh/only-export-components
export function isUuidLike(s: string | undefined): s is string {
  if (s === undefined) return false;
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);
}

// SuperChat 用の URL 生成 helper。default app は `/superchat[/<tid>]` に短縮、
// それ以外の app は `/superchat/<slug>[/<tid>]` の従来形式を返す。
// `/superchat/superchat[/<uuid>]` の二段 URL は新規生成しない (Phase 40-03 — todo Out of Scope)。
// eslint-disable-next-line react-refresh/only-export-components
export function buildSuperChatPath(appSlug: string, threadId?: string | null): string {
  if (appSlug === DEFAULT_SUPERCHAT_SLUG) {
    return threadId ? `/superchat/${threadId}` : '/superchat';
  }
  return threadId ? `/superchat/${appSlug}/${threadId}` : `/superchat/${appSlug}`;
}

// ---- SuperChat ラッパー: slugOrThreadId / threadId → AppDefinition 解決 ----
// 25-RESEARCH.md Pitfall 4 対応 + Phase 40-03: 単独 segment は UUID 形式かで分岐する。
//   /superchat                          → default app, no thread
//   /superchat/<uuid>                   → default app, threadId=<uuid>
//   /superchat/<non-uuid-slug>          → 別 app, no thread
//   /superchat/<non-uuid-slug>/<uuid>   → 別 app, threadId=<uuid>
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
  const { slugOrThreadId, threadId } = useParams<{ slugOrThreadId?: string; threadId?: string }>();
  // 単独 segment が UUID なら default app の threadId、それ以外なら非 default app の slug。
  const isUuidFirst = isUuidLike(slugOrThreadId);
  const appSlug = isUuidFirst ? DEFAULT_SUPERCHAT_SLUG : (slugOrThreadId ?? DEFAULT_SUPERCHAT_SLUG);
  // SuperChatApp 側で URL→state 同期する際は別途 useParams を持つため、ここでは AppDefinition 解決のみ責務。
  void threadId; // 参照のみ — appSlug 決定には不要だが React Router へキー宣言として残す。

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
        onModelChange={onModelChange}
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
        onModelChange={onModelChange}
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
          else navigate(buildSuperChatPath(app.slug));
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
      <Header selectedModel={selectedModel} onModelChange={onModelChange} theme={theme} onToggleTheme={onToggleTheme} onBackToMenu={() => navigate('/')} appName="Gems" />
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
      <Header selectedModel={selectedModel} onModelChange={onModelChange} theme={theme} onToggleTheme={onToggleTheme} onBackToMenu={() => navigate('/')} appName="Canvas" />
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
      <CanvasChatApp selectedModel={selectedModel} onBack={() => navigate('/canvas')} onModelChange={onModelChange} />
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

              {/* Phase 40-03: default app slug 短縮対応。UUID 判定は SuperChatWrapper 内で処理。 */}
              <Route path="superchat" element={<SuperChatWrapper {...common} />} />
              <Route path="superchat/:slugOrThreadId" element={<SuperChatWrapper {...common} />} />
              <Route path="superchat/:slugOrThreadId/:threadId" element={<SuperChatWrapper {...common} />} />

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
