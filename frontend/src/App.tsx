// frontend/src/App.tsx
// Root component: AuthProvider + auth gate.
// AuthPanel shown when unauthenticated/expired.
// MenuScreen shown when authenticated (landing page).
// SuperChatApp shown when user selects an app from menu.

import { useState } from 'react';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import { AuthPanel } from './components/AuthPanel';
import { Header } from './components/Header';
import { SuperChatApp } from './components/SuperChatApp';
import { MenuScreen } from './components/MenuScreen';
import { useTheme } from './hooks/useTheme';
import { ThemeContext } from './contexts/ThemeContext';
import type { AppDefinition } from './types';

export function App() {
  const authValue = useAuthProvider();
  // Default model per D-07
  const [selectedModel, setSelectedModel] = useState('gpt-4.1');
  const { theme, toggleTheme } = useTheme();
  const [currentScreen, setCurrentScreen] = useState<'menu' | 'superchat'>('menu');
  const [activeApp, setActiveApp] = useState<AppDefinition | null>(null);

  const isAuthenticated = authValue.authState === 'authenticated';

  const handleNavigate = (app: AppDefinition) => {
    setActiveApp(app);
    setCurrentScreen('superchat');
  };

  const handleBackToMenu = () => {
    setCurrentScreen('menu');
    setActiveApp(null);
  };

  return (
    <AuthContext.Provider value={authValue}>
      <ThemeContext.Provider value={theme}>
        {isAuthenticated ? (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {currentScreen === 'menu' ? (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                />
                <MenuScreen onNavigate={handleNavigate} />
              </>
            ) : (
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
          </div>
        ) : (
          <AuthPanel />
        )}
      </ThemeContext.Provider>
    </AuthContext.Provider>
  );
}
