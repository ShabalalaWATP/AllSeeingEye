import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { footerDetails, readPublicationState } from './privacy-publication.js';

const moduleId = 'virtual:policy-approval';
const resolved = `\0${moduleId}`;
const footerId = 'virtual:policy-footer';
const footerResolved = `\0${footerId}`;
const contentDir = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../src/features/public-policy',
);

/**
 * Browser receives a verified boolean and the footer's operator strings only. Node
 * validation never enters its bundle.
 */
export function privacyPublication() {
  return {
    name: 'privacy-publication',
    resolveId(id) {
      if (id === moduleId) return resolved;
      return id === footerId ? footerResolved : null;
    },
    load(id) {
      if (id === resolved) return `export default ${readPublicationState().approved};`;
      return id === footerResolved ? `export default ${JSON.stringify(footerDetails())};` : null;
    },
    configureServer(server) {
      server.watcher.add(contentDir);
      const changed = (event, file) => {
        if (!['add', 'change', 'unlink'].includes(event)) return;
        if (dirname(resolve(file)) !== contentDir) return;
        for (const id of [resolved, footerResolved]) {
          const module = server.moduleGraph.getModuleById(id);
          if (module) server.moduleGraph.invalidateModule(module);
        }
        server.ws.send({ type: 'full-reload' });
      };
      server.watcher.on('all', changed);
      server.httpServer?.once('close', () => {
        server.watcher.off('all', changed);
      });
    },
  };
}
