// frontend/src/main.tsx
// IMPORTANT: chatscope CSS must be imported here, before any React rendering.
// Per 07-RESEARCH.md Pattern section: import at app root, not in components.
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import './theme.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { App } from './App';

// Phase 25: APP_PREFIX 対応
// Vite は VITE_APP_BASE を元に import.meta.env.BASE_URL を末尾スラッシュ付きで公開する
// (例: VITE_APP_BASE=/orochi → BASE_URL="/orochi/")。
// BrowserRouter の basename は末尾スラッシュなしを期待するため replace で除去する。
// 25-RESEARCH.md Pitfall 1 参照。
const basename = (import.meta.env.BASE_URL ?? '/').replace(/\/$/, '');

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </StrictMode>
);
