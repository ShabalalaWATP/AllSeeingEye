import { fileURLToPath, URL } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// The dev server proxies /api to the FastAPI backend so cookies stay same-origin.
// Point it elsewhere with ASE_DEV_API_TARGET in frontend/.env.local (never committed).
const localEnv = loadEnv('development', process.cwd(), 'ASE_');
const apiTarget = localEnv.ASE_DEV_API_TARGET ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  optimizeDeps: {
    // MapLibre 6 starts a module worker with `new URL(..., import.meta.url)`. Pre-bundling
    // moves the module into .vite/deps, where that relative worker file does not exist,
    // so vector tiles silently never parse in development. Serving the package as-is fixes it.
    exclude: ['maplibre-gl'],
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        // 127.0.0.1 rather than localhost: Node may resolve localhost to ::1 first.
        target: apiTarget,
        changeOrigin: false,
      },
    },
  },
  build: {
    target: 'es2022',
    sourcemap: false,
  },
});
