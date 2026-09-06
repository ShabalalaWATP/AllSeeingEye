/** Invalidate scoped data after access changes; never stores a selected workspace. */
import { ApiError, isApiError } from './api/errors';
import { useAuthStore } from '@/stores/auth';

let revision = 0;
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

/** A rejected mutation invalidates cached authority and linked choices. */
export async function scopedMutation<T>(action: () => Promise<T>): Promise<T> {
  const actor = useAuthStore.getState().user?.id;
  const access = revision;
  try {
    const result = await action();
    if (actor !== useAuthStore.getState().user?.id || access !== revision) {
      throw new ApiError(
        409,
        'access_changed',
        'Account or team access changed. Refresh before continuing.',
      );
    }
    return result;
  } catch (error) {
    if (isApiError(error) && (error.status === 403 || error.status === 404)) {
      invalidateWorkspaceAccess();
    }
    throw error;
  }
}
