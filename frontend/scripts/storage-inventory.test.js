import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

import { browserStorageKeys, cookieKeys, storageProblems } from './storage-inventory.js';

test('every current local-storage key and cookie is declared', () => {
  const declarations = JSON.parse(
    readFileSync(new URL('../src/features/public-policy/storage.json', import.meta.url)),
  );
  assert.deepEqual(
    storageProblems(fileURLToPath(new URL('../../', import.meta.url)), declarations),
    [],
  );
});

test('discovers new literal, constant, persisted and per-account keys without an ase prefix assumption', () => {
  assert.deepEqual(
    browserStorageKeys(`
    import { persist } from 'zustand/middleware';
    const KEY = 'new-key'; localStorage.setItem(KEY, 'value');
    readStored('another'); persist(() => ({}), {name:'persisted'});
    const PREFIX = 'seen:'; function key(id) { return \`\${PREFIX}\${id}\`; }
    writeStored(key('user'), 'value');
  `).keys,
    ['another', 'new-key', 'persisted', 'seen:*'],
  );
  assert.equal(browserStorageKeys('writeStored(unknown(), "value")').failures.length, 1);
  assert.ok(browserStorageKeys('sessionStorage.setItem("session", "value")').failures.length);
  assert.ok(browserStorageKeys('document.cookie = "new-cookie=value"').failures.length);
  assert.deepEqual(
    browserStorageKeys(
      "import { writeStored as save } from './safeStorage'; save('aliased-new', 'value');",
    ).keys,
    ['aliased-new'],
  );
  assert.ok(
    browserStorageKeys(
      "function a(){const key='new';writeStored(key,'x')} function b(){const key='old';writeStored(key,'x')}",
    ).failures.length,
  );
  assert.ok(
    browserStorageKeys("const store=localStorage; store.setItem('new','value')").failures.length,
  );
  assert.deepEqual(
    browserStorageKeys(
      'localStorage.setItem("adapter-new", "value"); localStorage.getItem(key)',
      'adapter.ts',
      true,
    ).keys,
    ['adapter-new'],
  );
});

test('new backend cookie names and unresolved cookie indirection cannot pass silently', () => {
  assert.deepEqual(
    cookieKeys(
      'COOKIE = "new-cookie"\nresponse.set_cookie(COOKIE, value)\nresponse.delete_cookie("other")',
    ),
    ['new-cookie', 'other'],
  );
  assert.throws(() => cookieKeys('response.set_cookie(dynamic_name(), value)'));
});
