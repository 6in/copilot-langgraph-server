// frontend/src/App.tsx
// Root component: AuthProvider + auth gate.
// AuthPanel shown when unauthenticated/expired.
// ChatApp shown when authenticated.

import { useState } from 'react';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import { AuthPanel } from './components/AuthPanel';
import { Header } from './components/Header';
import { ChatApp } from './components/ChatApp';

export function App() {
  const authValue = useAuthProvider();
  // Default model per D-07
  const [selectedModel, setSelectedModel] = useState('gpt-4.1');

  const isAuthenticated = authValue.authState === 'authenticated';

  return (
    <AuthContext.Provider value={authValue}>
      {isAuthenticated ? (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
          <Header selectedModel={selectedModel} onModelChange={setSelectedModel} />
          <ChatApp selectedModel={selectedModel} />
        </div>
      ) : (
        <AuthPanel />
      )}
    </AuthContext.Provider>
  );
}
