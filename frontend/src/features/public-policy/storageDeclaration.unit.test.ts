// @vitest-environment node
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import {
  browserStorageKeys,
  cookieKeys,
  storageProblems,
} from '../../../scripts/storage-inventory.js';
import storage from './storage.json';

describe('published storage declaration', () => {
  it('covers every current application-owned local-storage key and cookie', () => {
    expect(
      storageProblems(fileURLToPath(new URL('../../../../', import.meta.url)), storage),
    ).toEqual([]);
  });

  it('detects added keys and refuses unresolved storage mechanisms', () => {
    const existing = new Set(storage.map((row) => row.name));
    const added = browserStorageKeys(
      `const KEY = 'not-yet-declared'; localStorage.setItem(KEY, 'value');`,
    );
    expect(added.keys.some((key) => !existing.has(key))).toBe(true);
    expect(
      cookieKeys('response.set_cookie("new-cookie", value)').some((key) => !existing.has(key)),
    ).toBe(true);
    expect(browserStorageKeys('writeStored(dynamicKey(), "value")').failures).not.toEqual([]);
  });
});
