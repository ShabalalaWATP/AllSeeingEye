import { fileURLToPath, URL } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv, type Plugin } from 'vite';
import { privacyPublication } from './scripts/privacy-plugin.js';

// The dev server proxies /api to the FastAPI backend so cookies stay same-origin.
// Point it elsewhere with ASE_DEV_API_TARGET in frontend/.env.local (never committed).
const localEnv = loadEnv('development', process.cwd(), 'ASE_');
const apiTarget = localEnv.ASE_DEV_API_TARGET ?? 'http://127.0.0.1:8001';

// MapLibre starts a module worker that imports the same shared module as the main thread.
// Building the worker as an extra entry of this graph lets both import one hashed shared
// chunk, so a cold load fetches and parses it once, and a deploy never pairs old main-thread
// code with a new worker. The map passes the hashed worker URL to setWorkerUrl. In
// development and tests the URL is empty and MapLibre finds its worker beside the library.
const WORKER_URL_MODULE = 'virtual:maplibre-worker-url';
function maplibreWorker(): Plugin {
  const resolved = `\0${WORKER_URL_MODULE}`;
  let building = false;
  let reference: string | null = null;
  return {
    name: 'maplibre-worker',
    configResolved(config) {
      building = config.command === 'build';
    },
    buildStart() {
      if (!building) return;
      reference = this.emitFile({
        type: 'chunk',
        id: fileURLToPath(
          new URL('./node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs', import.meta.url),
        ),
        name: 'maplibre-gl-worker',
      });
    },
    resolveId(id) {
      return id === WORKER_URL_MODULE ? resolved : null;
    },
    load(id) {
      if (id !== resolved) return null;
      return reference === null
        ? 'export default "";'
        : `export default import.meta.ROLLUP_FILE_URL_${reference};`;
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), maplibreWorker(), privacyPublication()],
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
            // These dependency-free constants already share the public route.
            // One small chunk avoids four requests and repeated response headers.
            {
              name: 'public-constants',
              test: /src[\\/](?:lib[\\/](?:mapLayerDirectory|categories|safeStorage)|components[\\/]brand[\\/]tokens)\.ts$/,
              priority: 1,
            },
            // Vite's preload helper is shared by every lazy route. Without its own
            // higher-priority group, recursion captures it into the first vendor group
            // that uses dynamic imports, and the entry then loads all of deck.gl.
            { name: 'preload-helper', test: /vite[\\/]preload-helper/, priority: 10 },
            // The worker entry imports this chunk too, so it holds the shared module alone:
            // no main-thread code may reach the worker.
            {
              name: 'maplibre-shared',
              test: /node_modules[\\/]maplibre-gl[\\/]dist[\\/]maplibre-gl-shared\.mjs$/,
              priority: 5,
            },
            {
              name: 'maplibre',
              test: /node_modules[\\/]maplibre-gl[\\/]dist[\\/]maplibre-gl\.(?:mjs|css)$/,
            },
            { name: 'deck', test: /node_modules[\\/]@(?:deck|luma|loaders|math)\.gl[\\/]/ },
            // three.js is only ever reached through the lazily imported Ukraine timeline scene.
            { name: 'three', test: /node_modules[\\/]three[\\/]/ },
          ],
        },
      },
    },
  },
});
