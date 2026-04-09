import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_APP_BASE ?? '/',
  server: {
    // VITE_APP_BASE=/orochi in .env to dev with prefix; rewrite strips it before forwarding
    proxy: {
      [`${process.env.VITE_APP_BASE ?? ''}/api`]: {
        target: process.env.API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        // Rewrite strips VITE_APP_BASE prefix before forwarding to FastAPI.
        // FastAPI routes are at /api/..., nginx strips the outer prefix in production.
        rewrite: (path) =>
          path.replace(
            new RegExp('^' + (process.env.VITE_APP_BASE ?? '')),
            '',
          ),
      },
      // Proxy deployed canvas apps (static files served by FastAPI at /apps/).
      // Strips VITE_APP_BASE prefix to match FastAPI's mount at /apps/.
      [`${process.env.VITE_APP_BASE ?? ''}/apps`]: {
        target: process.env.API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) =>
          path.replace(
            new RegExp('^' + (process.env.VITE_APP_BASE ?? '')),
            '',
          ),
      },
      // Proxy iframe-rpc.js (static file served by FastAPI at /iframe-rpc.js).
      // Required so iframes can import the ESM library in dev via Vite dev server.
      [`${process.env.VITE_APP_BASE ?? ''}/iframe-rpc.js`]: {
        target: process.env.API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) =>
          path.replace(
            new RegExp('^' + (process.env.VITE_APP_BASE ?? '')),
            '',
          ),
      },
    },
  },
});
