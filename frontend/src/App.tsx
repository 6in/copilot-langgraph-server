// frontend/src/App.tsx
// Root component: AuthProvider + auth gate.
// AuthPanel shown when unauthenticated/expired.
// MenuScreen shown when authenticated (landing page).
// ChatApp shown when user navigates from menu to chat.

import { useState } from 'react';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import { AuthPanel } from './components/AuthPanel';
import { Header } from './components/Header';
import { ChatApp } from './components/ChatApp';
import { SuperChatApp } from './components/SuperChatApp';
import { MenuScreen } from './components/MenuScreen';
import { useTheme } from './hooks/useTheme';
import { ThemeContext } from './contexts/ThemeContext';

export function App() {
  const authValue = useAuthProvider();
  // Default model per D-07
  const [selectedModel, setSelectedModel] = useState('gpt-4.1');
  const { theme, toggleTheme } = useTheme();
  const [currentScreen, setCurrentScreen] = useState<'menu' | 'chat' | 'superchat'>('menu');

  const isAuthenticated = authValue.authState === 'authenticated';

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
                <MenuScreen
                  onNavigate={(s) => setCurrentScreen(s as 'menu' | 'chat' | 'superchat')}
                />
              </>
            ) : currentScreen === 'superchat' ? (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  onBackToMenu={() => setCurrentScreen('menu')}
                />
                <SuperChatApp selectedModel={selectedModel} />
              </>
            ) : (
              <>
                <Header
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  onBackToMenu={() => setCurrentScreen('menu')}
                />
                <ChatApp selectedModel={selectedModel} />
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
