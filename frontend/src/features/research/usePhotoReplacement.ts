import { useEffect, useRef, useState } from 'react';

import { describeError } from '@/lib/api/errors';
import { discardResearchInput } from '@/lib/api/researchGeolocation';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

import type { useResearchInput } from './useResearchInput';
import {
  forgetPhotoReceipt,
  outstandingPhotoReceipts,
  rememberPhotoReceipt,
} from './photoReceiptRegistry';

/** Free the original and its derived receipts before replacing a private photo. */
export function usePhotoReplacement(input: ReturnType<typeof useResearchInput>) {
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const [snapshot, setSnapshot] = useState({
    key: input.key,
    busy: false,
    error: null as string | null,
  });
  const state = snapshot.key === input.key ? snapshot : { busy: false, error: null };
  useEffect(() => {
    return () => {
      sequence.current += 1;
      controller.current?.abort();
      controller.current = null;
    };
  }, [input.key]);
  useEffect(() => {
    if (input.receipt) rememberPhotoReceipt(input.key, input.receipt);
  }, [input.key, input.receipt]);

  const replace = async (file?: File) => {
    if (controller.current) return false;
    if (input.receipt) rememberPhotoReceipt(input.key, input.receipt);
    const actor = useAuthStore.getState().user;
    const revision = workspaceRevision();
    const abort = new AbortController();
    controller.current = abort;
    const attempt = ++sequence.current;
    const current = () => {
      const user = useAuthStore.getState().user;
      return (
        attempt === sequence.current &&
        !abort.signal.aborted &&
        user?.id === actor?.id &&
        user?.role === actor?.role &&
        user?.is_active &&
        workspaceRevision() === revision
      );
    };
    setSnapshot({ key: input.key, busy: true, error: null });
    try {
      const ids = outstandingPhotoReceipts(input.key);
      input.clear();
      for (const id of ids) {
        await discardResearchInput(id, abort.signal);
        if (!current()) return false;
        forgetPhotoReceipt(input.key, id);
      }
      if (!current()) return false;
      if (file) void input.upload(file);
      return true;
    } catch (error) {
      if (current()) setSnapshot({ key: input.key, busy: false, error: describeError(error) });
      return false;
    } finally {
      if (attempt === sequence.current) {
        controller.current = null;
        setSnapshot((previous) => ({ ...previous, busy: false }));
      }
    }
  };
  return { ...state, replace };
}
