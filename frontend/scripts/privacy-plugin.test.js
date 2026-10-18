import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

import { privacyPublication } from './privacy-plugin.js';
import { footerDetails, readPublicationState } from './privacy-publication.js';

test('exports only the verified approval and ignores other virtual modules', () => {
  const plugin = privacyPublication();
  assert.equal(plugin.resolveId('unrelated'), null);
  assert.equal(plugin.load('unrelated'), null);
  assert.equal(
    plugin.load(plugin.resolveId('virtual:policy-approval')),
    `export default ${readPublicationState().approved};`,
  );
});

test('exports the footer operator strings from the same reviewed content', () => {
  const plugin = privacyPublication();
  const source = plugin.load(plugin.resolveId('virtual:policy-footer'));
  assert.equal(source, `export default ${JSON.stringify(footerDetails())};`);
  assert.deepEqual(Object.keys(footerDetails()).sort(), ['address', 'contact', 'operator']);
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
  // Both virtual modules are invalidated for each of the three content events.
  assert.equal(invalidated, 6);
  assert.equal(reloads, 3);
  close();
  assert.equal(detached, true);
});
