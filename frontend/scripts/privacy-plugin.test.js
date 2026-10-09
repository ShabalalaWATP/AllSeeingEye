import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

import { privacyPublication } from './privacy-plugin.js';
import { readPublicationState } from './privacy-publication.js';

test('exports only the verified approval and ignores other virtual modules', () => {
  const plugin = privacyPublication();
  assert.equal(plugin.resolveId('unrelated'), null);
  assert.equal(plugin.load('unrelated'), null);
  assert.equal(
    plugin.load(plugin.resolveId('virtual:policy-approval')),
    `export default ${readPublicationState().approved};`,
  );
});

test('adding, editing and deleting policy inputs invalidates a running preview', () => {
  let changed;
  let close;
  let invalidated = 0;
  let reloads = 0;
  let detached = false;
  privacyPublication().configureServer({
    watcher: {
      add() {},
      on(event, handler) {
        assert.equal(event, 'all');
        changed = handler;
      },
      off() {
        detached = true;
      },
    },
    moduleGraph: {
      getModuleById() {
        return {};
      },
      invalidateModule() {
        invalidated += 1;
      },
    },
    ws: {
      send(message) {
        assert.deepEqual(message, { type: 'full-reload' });
        reloads += 1;
      },
    },
    httpServer: {
      once(event, handler) {
        assert.equal(event, 'close');
        close = handler;
      },
    },
  });
  const file = fileURLToPath(
    new URL('../src/features/public-policy/privacy.json', import.meta.url),
  );
  for (const event of ['add', 'change', 'unlink']) changed(event, file);
  changed('change', '/unrelated');
  changed('ready', file);
  assert.equal(invalidated, 3);
  assert.equal(reloads, 3);
  close();
  assert.equal(detached, true);
});
