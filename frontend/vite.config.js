import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the Vite server proxies API calls to the FastAPI backend,
// mirroring what Nginx (Docker/Kubernetes) and the Ingress do in deployed environments.
const backend = process.env.VITE_BACKEND_URL || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
      '/health': backend,
    },
  },
  preview: {
    proxy: {
      '/api': backend,
      '/health': backend,
    },
  },
});
