import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { readPublicationState } from './privacy-publication.js';

const moduleId = 'virtual:policy-approval';
const resolved = `\0${moduleId}`;
const contentDir = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../src/features/public-policy',
);

/** Browser receives a verified boolean only. Node validation never enters its bundle. */
export function privacyPublication() {
  return {
    name: 'privacy-publication',
    resolveId(id) {
      return id === moduleId ? resolved : null;
    },
    load(id) {
      return id === resolved ? `export default ${readPublicationState().approved};` : null;
    },
    configureServer(server) {
      server.watcher.add(contentDir);
      const changed = (event, file) => {
        if (!['add', 'change', 'unlink'].includes(event)) return;
        if (dirname(resolve(file)) !== contentDir) return;
        const module = server.moduleGraph.getModuleById(resolved);
        if (module) server.moduleGraph.invalidateModule(module);
        server.ws.send({ type: 'full-reload' });
      };
      server.watcher.on('all', changed);
      server.httpServer?.once('close', () => {
        server.watcher.off('all', changed);
      });
    },
  };
}
