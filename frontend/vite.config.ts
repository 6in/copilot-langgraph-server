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
    },
  },
});
