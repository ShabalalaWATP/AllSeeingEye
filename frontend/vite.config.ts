import { readFileSync } from 'node:fs';
import { fileURLToPath, URL } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv, type Plugin } from 'vite';

// The dev server proxies /api to the FastAPI backend so cookies stay same-origin.
// Point it elsewhere with ASE_DEV_API_TARGET in frontend/.env.local (never committed).
const localEnv = loadEnv('development', process.cwd(), 'ASE_');
const apiTarget = localEnv.ASE_DEV_API_TARGET ?? 'http://127.0.0.1:8001';

// MapLibre resolves its module worker beside the bundled library at runtime.
// Its worker also imports the shared module, so preserve both package assets.
function maplibreWorkerAssets(): Plugin {
  return {
    name: 'maplibre-worker-assets',
    apply: 'build',
    generateBundle() {
      for (const name of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) {
        this.emitFile({
          type: 'asset',
          fileName: `assets/${name}`,
          source: readFileSync(new URL(`./node_modules/maplibre-gl/dist/${name}`, import.meta.url)),
        });
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), maplibreWorkerAssets()],
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
    // Keep fonts as same-origin files, matching Caddy's font-src 'self' policy.
    assetsInlineLimit: 0,
    sourcemap: false,
    rolldownOptions: {
      output: {
        codeSplitting: {
          // Keep dependency recursion enabled to avoid circular runtime initialisation.
          groups: [
            { name: 'maplibre', test: /node_modules[\\/]maplibre-gl[\\/]/ },
            { name: 'deck', test: /node_modules[\\/]@(?:deck|luma|loaders|math)\.gl[\\/]/ },
          ],
        },
      },
    },
  },
});
