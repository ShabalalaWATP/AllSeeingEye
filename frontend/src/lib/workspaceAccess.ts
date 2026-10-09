/** Invalidate scoped data after access changes; never stores a selected workspace. */
import { ApiError, isApiError } from './api/errors';
import { useAuthStore } from '@/stores/auth';

let revision = 0;
// The revision a post-commit refresh produced, so one refresh never triggers another.
let refreshedRevision = -1;
const listeners = new Set<() => void>();

export const workspaceRevision = () => revision;
export function subscribeWorkspaceAccess(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export function invalidateWorkspaceAccess() {
  revision += 1;
  for (const listener of listeners) listener();
}

const accessChanged = () =>
  new ApiError(409, 'access_changed', 'Account or team access changed. Refresh before continuing.');

/**
 * Reload scoped views once after a write committed across an access change, because views
 * reloaded by that change may have read before the write landed. Work already in flight
 * when this refresh fires cannot start another, so concurrent requests never loop.
 */
function refreshAfterCommit() {
  if (revision === refreshedRevision) return;
  invalidateWorkspaceAccess();
  refreshedRevision = revision;
}

async function scoped<T>(action: () => Promise<T>, committed: boolean): Promise<T> {
  const actor = useAuthStore.getState().user?.id;
  const access = revision;
  try {
    const result = await action();
    // Another account's result never reaches the account now signed in.
    if (actor !== useAuthStore.getState().user?.id) throw accessChanged();
    if (access !== revision) {
      if (!committed) throw accessChanged();
      refreshAfterCommit();
    }
    return result;
  } catch (error) {
    if (isApiError(error) && (error.status === 403 || error.status === 404)) {
      invalidateWorkspaceAccess();
    }
    throw error;
  }
}

/**
 * A write the server has committed is reported as done, even if team access changed while
 * it was in flight: failing it would invite a duplicate resubmission. Scoped views refresh
 * instead. A rejected write invalidates cached authority and linked choices.
 */
export function scopedMutation<T>(action: () => Promise<T>): Promise<T> {
  return scoped(action, true);
}

/**
 * A read that completed across an access change may hold records the caller can no
 * longer see, so it fails and the caller reloads under the current access.
 */
export function scopedRead<T>(action: () => Promise<T>): Promise<T> {
  return scoped(action, false);
}
