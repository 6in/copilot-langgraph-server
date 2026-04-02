// frontend/src/main.tsx
// IMPORTANT: chatscope CSS must be imported here, before any React rendering.
// Per 07-RESEARCH.md Pattern section: import at app root, not in components.
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
