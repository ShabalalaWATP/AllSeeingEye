import { useAuthStore, type AuthState } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
const identity = (state: AuthState) =>
  `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`;
/** Radio drafts and private studies must clear even when authority changes without an SSE notice. */
export function subscribeRfWorkspaceReset(clear: () => void): () => void {
  const offAccess = subscribeWorkspaceAccess(clear);
  const offAuth = useAuthStore.subscribe((next, previous) => {
    if (identity(next) !== identity(previous)) clear();
  });
  return () => {
    offAccess();
    offAuth();
  };
}
