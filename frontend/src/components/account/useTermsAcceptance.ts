/**
 * Whether the signed-in account must accept the current Terms, and the accept action.
 * The answer arrives with the session's user, so no extra request is made on each visit.
 */
import { fetchMe } from '@/lib/api/auth';
import { isApiError } from '@/lib/api/errors';
import { acceptTerms, type TermsStatus } from '@/lib/api/terms';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

/** Apply a result only to the login that asked for it; a later sign-in keeps its own state. */
function applyTo(generation: number, userId: string, terms: TermsStatus): void {
  const current = useAuthStore.getState();
  if (current.sessionGeneration !== generation || current.user?.id !== userId) return;
  useAuthStore.setState({ user: { ...current.user, terms } });
}

export function useTermsAcceptance() {
  const terms = useAuthStore((state) =>
    state.status === 'authenticated' ? state.user?.terms : undefined,
  );
  const action = useAsyncAction(async (version: string) => {
    const { sessionGeneration, user } = useAuthStore.getState();
    if (user === null) return;
    try {
      applyTo(sessionGeneration, user.id, await acceptTerms(version));
    } catch (error) {
      // The terms changed after this page loaded: show the current version instead.
      if (isApiError(error) && error.code === 'conflict') {
        const fresh = await fetchMe();
        if (fresh.terms !== undefined) applyTo(sessionGeneration, user.id, fresh.terms);
      }
      throw error;
    }
  });
  return {
    terms: terms?.acceptance_required === true ? terms : null,
    accept: action.run,
    busy: action.busy,
    error: action.error,
  };
}
