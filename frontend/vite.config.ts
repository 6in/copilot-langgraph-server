import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        // NO rewrite — FastAPI routes are already at /api/...
        // Adding rewrite here would strip the prefix and break all routes.
      },
    },
  },
});
