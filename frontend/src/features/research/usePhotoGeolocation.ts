import { useCallback, useEffect, useRef, useState } from 'react';

import { describeError } from '@/lib/api/errors';
import {
  discardResearchInput,
  geolocateResearchInput,
  type ResearchGeolocation,
} from '@/lib/api/researchGeolocation';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

type Status = 'idle' | 'loading' | 'ready' | 'error' | 'cancelled';
interface Snapshot {
  key: string;
  status: Status;
  result: ResearchGeolocation | null;
  error: string | null;
  question: string;
}
const empty = (key: string, status: Status = 'idle'): Snapshot => ({
  key,
  status,
  result: null,
  error: null,
  question: '',
});

/** Responses never survive an attachment, destination, account or authority change. */
export function usePhotoGeolocation(
  receipt: ResearchInputReceipt | null,
  authorityKey: string,
  teamId: string,
) {
  const key = `${authorityKey}:${receipt?.id ?? ''}:${teamId}`;
  const [snapshot, setSnapshot] = useState(() => empty(key));
  const state = snapshot.key === key ? snapshot : empty(key);
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const derivedReceipt = useRef<string | null>(null);
  useEffect(() => {
    sequence.current += 1;
    controller.current?.abort();
    controller.current = null;
    derivedReceipt.current = null;
    return () => {
      sequence.current += 1;
      controller.current?.abort();
      controller.current = null;
    };
  }, [key]);

  const clear = useCallback(
    (status: Status = 'idle') => {
      sequence.current += 1;
      controller.current?.abort();
      controller.current = null;
      setSnapshot(empty(key, status));
    },
    [key],
  );

  const analyse = async (question: string, hints: string, consent: boolean) => {
    if (controller.current || !receipt || !consent) return;
    if (Date.parse(receipt.expires_at) <= Date.now()) {
      setSnapshot({ ...empty(key, 'error'), error: 'This photo has expired. Upload it again.' });
      return;
    }
    const abort = new AbortController();
    controller.current = abort;
    const attempt = ++sequence.current;
    const actor = useAuthStore.getState().user;
    const revision = workspaceRevision();
    const current = () => {
      const account = useAuthStore.getState().user;
      return (
        attempt === sequence.current &&
        !abort.signal.aborted &&
        actor?.id === account?.id &&
        actor?.role === account?.role &&
        account?.is_active &&
        workspaceRevision() === revision
      );
    };
    setSnapshot({ ...empty(key, 'loading'), question });
    try {
      if (derivedReceipt.current) {
        await discardResearchInput(derivedReceipt.current, abort.signal);
        if (!current()) return;
        derivedReceipt.current = null;
      }
      const result = await geolocateResearchInput(
        receipt.id,
        {
          question: question.trim() || 'Where might this photograph have been taken?',
          hints: hints.trim(),
          team_id: teamId || null,
          consent_to_send_image: true,
        },
        abort.signal,
      );
      if (!current()) return;
      derivedReceipt.current = result.input.id;
      if (Date.parse(result.input.expires_at) <= Date.now()) {
        setSnapshot({
          ...empty(key, 'error'),
          error: 'The analysis expired. Upload the photo again.',
        });
        return;
      }
      setSnapshot({ key, status: 'ready', result, error: null, question });
    } catch (error) {
      if (current()) setSnapshot({ ...empty(key, 'error'), error: describeError(error) });
    } finally {
      if (attempt === sequence.current) controller.current = null;
    }
  };
  return { ...state, analyse, clear, busy: state.status === 'loading' };
}
