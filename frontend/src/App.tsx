// frontend/src/App.tsx
// Root component: AuthProvider + auth gate.
// AuthPanel shown when unauthenticated/expired.
// 7-screen navigation: menu | superchat | gems | gemchat | debate | canvas | canvaschat

import { useState } from 'react';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import { AuthPanel } from './components/AuthPanel';
import { Header } from './components/Header';
import { SuperChatApp } from './components/SuperChatApp';
import { MenuScreen } from './components/MenuScreen';
import { GemsScreen } from './components/GemsScreen';
import { GemChatApp } from './components/GemChatApp';
import { DebateChatApp } from './components/DebateChatApp';
import { CanvasScreen } from './components/CanvasScreen';
import { CanvasChatApp } from './components/CanvasChatApp';
import { useTheme } from './hooks/useTheme';
import { ThemeContext } from './contexts/ThemeContext';
import { getCanvasGemId } from './api/client';
import type { AppDefinition, GemInfo } from './types';

type Screen = 'menu' | 'superchat' | 'gems' | 'gemchat' | 'debate' | 'canvas' | 'canvaschat';

export function App() {
  const authValue = useAuthProvider();
  // Default model per D-07
  const [selectedModel, setSelectedModel] = useState('gpt-4.1');
  const { theme, toggleTheme } = useTheme();
  const [currentScreen, setCurrentScreen] = useState<Screen>('menu');
  const [activeApp, setActiveApp] = useState<AppDefinition | null>(null);
  const [activeGem, setActiveGem] = useState<GemInfo | null>(null);
  const [activeCanvasAppId, setActiveCanvasAppId] = useState<string | null>(null);
  const [canvasGemId, setCanvasGemId] = useState<string | null>(null);

  const isAuthenticated = authValue.authState === 'authenticated';

  const handleNavigate = (app: AppDefinition) => {
    setActiveApp(app);
    setCurrentScreen('superchat');
  };

  const handleBackToMenu = () => {
    setCurrentScreen('menu');
    setActiveApp(null);
  };

  const handleOpenGems = () => { setCurrentScreen('gems'); };

  const handleOpenDebate = () => { setCurrentScreen('debate'); };
  const handleBackFromDebate = () => { setCurrentScreen('menu'); };

  const handleSelectGem = (gem: GemInfo) => {
    setActiveGem(gem);
    setCurrentScreen('gemchat');
  };

  // Pitfall 4 対策: GemChatApp → GemsScreen に戻る（MenuScreen まで戻さない）
  const handleBackFromGemChat = () => {
    setActiveGem(null);
    setCurrentScreen('gems');
  };

  const handleBackFromGems = () => { setCurrentScreen('menu'); };

  // Phase 16: Canvas ナビゲーション（D-07）
  const handleOpenCanvas = () => { setCurrentScreen('canvas'); };
  const handleBackFromCanvas = () => { setCurrentScreen('menu'); };

  const handleOpenCanvasChat = async (initialThreadId?: string) => {
    // canvasGemId が未取得の場合は取得してから遷移
    let gemId = canvasGemId;
    if (!gemId) {
      try {
        const result = await getCanvasGemId();
        gemId = result.gem_id;
        setCanvasGemId(gemId);
      } catch {
        // 取得失敗でも遷移は許可（CanvasChatApp 側でエラーハンドリング）
      }
    }
    setActiveCanvasAppId(initialThreadId ?? null);
    setCurrentScreen('canvaschat');
  };

  const handleBackFromCanvasChat = () => {
    setCurrentScreen('canvas');
  };

  return (
    <AuthContext.Provider value={authValue}>
      <ThemeContext.Provider value={theme}>
        {isAuthenticated ? (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {currentScreen === 'menu' && (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                />
                <MenuScreen onNavigate={handleNavigate} onOpenGems={handleOpenGems} onOpenDebate={handleOpenDebate} onOpenCanvas={handleOpenCanvas} />
              </>
            )}
            {currentScreen === 'superchat' && (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  onBackToMenu={handleBackToMenu}
                  appName={activeApp?.name}
                />
                <SuperChatApp
                  selectedModel={selectedModel}
                  appId={activeApp?.slug ?? ''}
                  appName={activeApp?.name ?? ''}
                  appAgents={activeApp?.agents}
                />
              </>
            )}
            {currentScreen === 'gems' && (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                />
                <GemsScreen onSelectGem={handleSelectGem} onBack={handleBackFromGems} />
              </>
            )}
            {/* Threat model: activeGem null check prevents null ref error */}
            {currentScreen === 'gemchat' && activeGem && (
              <>
                {/* Pitfall 4: onBackToMenu を渡さない。GemChatApp 内の Back ボタンで GemsScreen に戻る */}
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                />
                <GemChatApp
                  gem={activeGem}
                  selectedModel={selectedModel}
                  onBack={handleBackFromGemChat}
                />
              </>
            )}
            {/* Phase 16: Canvas 画面 */}
            {currentScreen === 'canvas' && (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                />
                <CanvasScreen
                  onBack={handleBackFromCanvas}
                  onStartChat={handleOpenCanvasChat}
                />
              </>
            )}
            {/* Phase 16: CanvasChatApp 画面 — canvasGemId が null の場合は表示しない（T-16-09） */}
            {currentScreen === 'canvaschat' && canvasGemId && (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                />
                <CanvasChatApp
                  canvasGemId={canvasGemId}
                  selectedModel={selectedModel}
                  onBack={handleBackFromCanvasChat}
                  initialThreadId={activeCanvasAppId}
                />
              </>
            )}
            {/* Phase 17: 討論チャット画面 */}
            {currentScreen === 'debate' && (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  onBackToMenu={handleBackFromDebate}
                  appName="討論チャット"
                />
                <DebateChatApp selectedModel={selectedModel} />
              </>
            )}
          </div>
        ) : (
          <AuthPanel />
        )}
      </ThemeContext.Provider>
    </AuthContext.Provider>
  );
}
