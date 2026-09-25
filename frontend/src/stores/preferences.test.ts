import { afterEach, describe, expect, it, vi } from 'vitest';

import { readStored, writeStored } from '@/lib/safeStorage';

import { PREFERENCES_KEY, usePreferencesStore } from './preferences';

afterEach(() => {
  // Restore blocked storage before the shared clean-up writes to persisted stores.
  vi.restoreAllMocks();
  usePreferencesStore.setState({ singleKeyShortcuts: true, shortcutHelpOpen: false });
});

describe('accessibility preferences', () => {
  it('keeps single-key shortcuts on by default and stores only the preference', () => {
    expect(usePreferencesStore.getState().singleKeyShortcuts).toBe(true);
    usePreferencesStore.getState().setSingleKeyShortcuts(false);
    usePreferencesStore.getState().openShortcutHelp();
    const stored = JSON.parse(localStorage.getItem(PREFERENCES_KEY) ?? '{}') as {
      state: Record<string, unknown>;
    };
    expect(stored.state).toEqual({ singleKeyShortcuts: false });
    usePreferencesStore.getState().closeShortcutHelp();
    expect(usePreferencesStore.getState().shortcutHelpOpen).toBe(false);
  });

  it('restores a saved choice and ignores a malformed one', async () => {
    localStorage.setItem(
      PREFERENCES_KEY,
      JSON.stringify({ state: { singleKeyShortcuts: false }, version: 0 }),
    );
    await usePreferencesStore.persist.rehydrate();
    expect(usePreferencesStore.getState().singleKeyShortcuts).toBe(false);
    localStorage.setItem(
      PREFERENCES_KEY,
      JSON.stringify({ state: { singleKeyShortcuts: 'no' }, version: 0 }),
    );
    usePreferencesStore.setState({ singleKeyShortcuts: true });
    await usePreferencesStore.persist.rehydrate();
    expect(usePreferencesStore.getState().singleKeyShortcuts).toBe(true);
  });

  it('keeps working in memory when browser storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Blocked', 'SecurityError');
    });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('Blocked', 'SecurityError');
    });
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new DOMException('Blocked', 'SecurityError');
    });
    expect(() => usePreferencesStore.getState().setSingleKeyShortcuts(false)).not.toThrow();
    expect(usePreferencesStore.getState().singleKeyShortcuts).toBe(false);
    expect(readStored('anything')).toBeNull();
    expect(() => writeStored('anything', 'value')).not.toThrow();
    expect(() => usePreferencesStore.persist.clearStorage()).not.toThrow();
  });
});
