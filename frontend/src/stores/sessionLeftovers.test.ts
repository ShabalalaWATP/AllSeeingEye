import { afterEach, describe, expect, it, vi } from 'vitest';

import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { liveEvent } from '@/test/fixtures.events';

import { useAuthStore } from './auth';
import { initialEventsState, useEventsStore } from './events';
import { useGlobeStore } from './globe';
import { useShellStore } from './shell';

afterEach(() => {
  // Restore blocked storage before the shared clean-up writes to persisted stores.
  vi.restoreAllMocks();
});

describe('browser storage limits', () => {
  it('keeps globe and shell preferences working in memory when storage is full', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Quota exceeded', 'QuotaExceededError');
    });
    expect(() => useGlobeStore.getState().setBaseLayer('dark')).not.toThrow();
    expect(useGlobeStore.getState().baseLayer).toBe('dark');
    expect(() => useShellStore.getState().toggleRail()).not.toThrow();
    expect(useShellStore.getState().railCollapsed).toBe(true);
    useShellStore.getState().setRailCollapsed(false);
  });
});

describe('leftovers from a previous session', () => {
  function seedSessionView() {
    const event = liveEvent({ id: 'e1' });
    useEventsStore.getState().applyUpsert([event]);
    useEventsStore.getState().select('e1', 'view');
    useEventsStore.getState().setCountry('UA');
    useEventsStore.getState().setWindow(24);
    useEventsStore.getState().toggleCategory('aviation');
    useGlobeStore.getState().setOpsRoom(true);
  }

  function expectCleared() {
    const events = useEventsStore.getState();
    expect(events.selectedId).toBeNull();
    expect(events.selectionOwner).toBe('mirror');
    expect(events.country).toBeNull();
    expect(events.windowHours).toBeNull();
    expect(events.hidden).toEqual(initialEventsState.hidden);
    // Public events stay mirrored; only the account's view of them is cleared.
    expect(events.byId.e1).toBeDefined();
    expect(useGlobeStore.getState().opsRoom).toBe(false);
  }

  it('clears the ops room, event selection and filters on sign-out', () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    seedSessionView();
    useAuthStore.getState().clearSession();
    expectCleared();
  });

  it('clears them when another account signs in', () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    seedSessionView();
    useAuthStore.getState().setSession(tokenFor(adminUser));
    expectCleared();
  });

  it('keeps choices made before the first sign-in, such as a deep link', () => {
    seedSessionView();
    useAuthStore.getState().setSession(tokenFor(plainUser));
    expect(useEventsStore.getState().country).toBe('UA');
    expect(useGlobeStore.getState().opsRoom).toBe(true);
  });

  it('keeps them across a token refresh for the same account', () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    seedSessionView();
    useAuthStore.getState().setSession(tokenFor(plainUser));
    expect(useEventsStore.getState().selectedId).toBe('e1');
    expect(useEventsStore.getState().country).toBe('UA');
    expect(useGlobeStore.getState().opsRoom).toBe(true);
  });
});
