import { expect, it, vi } from 'vitest';
import { plainUser, tokenFor } from '@/test/fixtures';
import { useAuthStore } from '@/stores/auth';
import { invalidateWorkspaceAccess } from './workspaceAccess';
import { clearAreaWatchDraft, prepareAreaWatch, readAreaWatchDraft } from './areaWatchDraft';
import type { WatchAreaInput } from './map/areaWatchGeometry';

const area: WatchAreaInput = {
  source: 'viewport',
  bounds: { west: 170, east: -170, south: -10, north: 10 },
};
const login = () => useAuthStore.getState().setSession(tokenFor(plainUser));
it('keeps immutable, validated coordinates in memory only for the active actor', () => {
  expect(() => prepareAreaWatch(area)).toThrow('Sign in');
  login();
  const storage = vi.spyOn(Storage.prototype, 'setItem');
  prepareAreaWatch(area);
  expect(readAreaWatchDraft()).toMatchObject(area);
  expect(Object.isFrozen(readAreaWatchDraft()?.bounds)).toBe(true);
  expect(storage).not.toHaveBeenCalled();
  const id = readAreaWatchDraft()!.id;
  clearAreaWatchDraft(id + 1);
  expect(readAreaWatchDraft()).not.toBeNull();
  clearAreaWatchDraft(id);
  expect(readAreaWatchDraft()).toBeNull();
  expect(() => prepareAreaWatch({ ...area, bounds: { ...area.bounds, north: Infinity } })).toThrow(
    'finite',
  );
  expect(readAreaWatchDraft()).toBeNull();
  storage.mockRestore();
});
it('clears across logout/login, account changes, role changes and access invalidation', () => {
  login();
  prepareAreaWatch(area);
  useAuthStore.getState().clearSession();
  login();
  expect(readAreaWatchDraft()).toBeNull();
  prepareAreaWatch(area);
  useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: 'another-user' }));
  login();
  expect(readAreaWatchDraft()).toBeNull();
  prepareAreaWatch(area);
  invalidateWorkspaceAccess();
  expect(readAreaWatchDraft()).toBeNull();
  prepareAreaWatch(area);
  useAuthStore.getState().setSession(tokenFor({ ...plainUser, role: 'manager' }));
  expect(readAreaWatchDraft()).toBeNull();
  prepareAreaWatch(area);
  useAuthStore.getState().setSession(tokenFor({ ...plainUser, is_active: false }));
  expect(readAreaWatchDraft()).toBeNull();
});
