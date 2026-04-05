// frontend/src/App.tsx
// Root component: AuthProvider + auth gate.
// AuthPanel shown when unauthenticated/expired.
// 4-screen navigation: menu | superchat | gems | gemchat

import { useState } from 'react';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import { AuthPanel } from './components/AuthPanel';
import { Header } from './components/Header';
import { SuperChatApp } from './components/SuperChatApp';
import { MenuScreen } from './components/MenuScreen';
import { GemsScreen } from './components/GemsScreen';
import { GemChatApp } from './components/GemChatApp';
import { useTheme } from './hooks/useTheme';
import { ThemeContext } from './contexts/ThemeContext';
import type { AppDefinition, GemInfo } from './types';

type Screen = 'menu' | 'superchat' | 'gems' | 'gemchat';

export function App() {
  const authValue = useAuthProvider();
  // Default model per D-07
  const [selectedModel, setSelectedModel] = useState('gpt-4.1');
  const { theme, toggleTheme } = useTheme();
  const [currentScreen, setCurrentScreen] = useState<Screen>('menu');
  const [activeApp, setActiveApp] = useState<AppDefinition | null>(null);
  const [activeGem, setActiveGem] = useState<GemInfo | null>(null);

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
                <MenuScreen onNavigate={handleNavigate} onOpenGems={handleOpenGems} />
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
          </div>
        ) : (
          <AuthPanel />
        )}
      </ThemeContext.Provider>
    </AuthContext.Provider>
  );
}
