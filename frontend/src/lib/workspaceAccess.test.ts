import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';

import {
  invalidateWorkspaceAccess,
  scopedMutation,
  scopedRead,
  subscribeWorkspaceAccess,
  workspaceRevision,
} from './workspaceAccess';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

describe('scoped requests across an access change', () => {
  it('reports a committed write as done and refreshes scoped views once', async () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const listener = vi.fn();
    const off = subscribeWorkspaceAccess(listener);
    const first = deferred<string>();
    const second = deferred<string>();
    const saving = scopedMutation(() => first.promise);
    const archiving = scopedMutation(() => second.promise);
    invalidateWorkspaceAccess();
    const changed = workspaceRevision();
    first.resolve('saved');
    await expect(saving).resolves.toBe('saved');
    // Views reloaded by the access change may have read before the write landed.
    expect(workspaceRevision()).toBe(changed + 1);
    second.resolve('archived');
    await expect(archiving).resolves.toBe('archived');
    // A second stale completion does not start another refresh, so requests never loop.
    expect(workspaceRevision()).toBe(changed + 1);
    expect(listener).toHaveBeenCalledTimes(2);
    off();
  });

  it('refreshes again only after a later, genuine access change', async () => {
    const early = deferred<number>();
    const late = deferred<number>();
    const one = scopedMutation(() => early.promise);
    invalidateWorkspaceAccess();
    early.resolve(1);
    await one;
    const two = scopedMutation(() => late.promise);
    invalidateWorkspaceAccess();
    const before = workspaceRevision();
    late.resolve(2);
    await expect(two).resolves.toBe(2);
    expect(workspaceRevision()).toBe(before + 1);
  });

  it('leaves the revision alone when nothing changed in flight', async () => {
    const before = workspaceRevision();
    await expect(scopedMutation(() => Promise.resolve('done'))).resolves.toBe('done');
    await expect(scopedRead(() => Promise.resolve('read'))).resolves.toBe('read');
    expect(workspaceRevision()).toBe(before);
  });

  it('rejects a read that completed across the change, as it may hold revoked records', async () => {
    const pending = deferred<string[]>();
    const reading = scopedRead(() => pending.promise);
    invalidateWorkspaceAccess();
    const changed = workspaceRevision();
    pending.resolve(['team record']);
    await expect(reading).rejects.toMatchObject({ status: 409, code: 'access_changed' });
    expect(workspaceRevision()).toBe(changed);
  });

  it('still rejects a write whose result belongs to the previous account', async () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const pending = deferred<string>();
    const saving = scopedMutation(() => pending.promise);
    useAuthStore.getState().clearSession();
    pending.resolve('private result');
    await expect(saving).rejects.toMatchObject({ code: 'access_changed' });
  });

  it('invalidates on a denied read and passes other failures through untouched', async () => {
    const before = workspaceRevision();
    await expect(
      scopedRead(() => Promise.reject(new ApiError(403, 'forbidden', 'No longer shared.'))),
    ).rejects.toMatchObject({ status: 403 });
    expect(workspaceRevision()).toBe(before + 1);
    await expect(
      scopedMutation(() => Promise.reject(new ApiError(422, 'invalid', 'Bad input.'))),
    ).rejects.toMatchObject({ status: 422 });
    expect(workspaceRevision()).toBe(before + 1);
  });
});
