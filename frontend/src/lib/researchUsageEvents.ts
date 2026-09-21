/** Refresh visible allowances after research admission, including uncertain failures. */
import { scopedMutation } from './workspaceAccess';

const listeners = new Set<() => void>();

export function subscribeResearchUsage(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function invalidateResearchUsage() {
  for (const listener of listeners) listener();
}

export async function researchUsageMutation<T>(action: () => Promise<T>): Promise<T> {
  try {
    return await scopedMutation(action);
  } finally {
    // A lost response or failed admitted job may still have consumed one run.
    invalidateResearchUsage();
  }
}
