// frontend/src/App.tsx
// Root component: AuthProvider + auth gate.
// AuthPanel shown when unauthenticated/expired.
// ChatApp shown when authenticated (stub in this plan, implemented in 07-03).

import { useState } from 'react';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import { AuthPanel } from './components/AuthPanel';
import { Header } from './components/Header';

// ChatApp stub — replaced in Plan 07-03
function ChatAppStub() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
      <p style={{ color: '#666' }}>Chat UI coming in Plan 07-03...</p>
    </div>
  );
}

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
          <ChatAppStub />
        </div>
      ) : (
        <AuthPanel />
      )}
    </AuthContext.Provider>
  );
}
