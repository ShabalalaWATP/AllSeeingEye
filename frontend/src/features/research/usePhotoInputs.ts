/** Bounded private photo batches. Only expiring references survive navigation. */
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';

import { ApiError, describeError } from '@/lib/api/errors';
import { discardResearchInput } from '@/lib/api/researchGeolocation';
import { uploadResearchInput, type ResearchInputReceipt } from '@/lib/api/researchInputs';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

import {
  forgetPhotoReceipt,
  outstandingPhotoReceipts,
  rememberPhotoReceipt,
} from './photoReceiptRegistry';

export const PHOTO_EXTENSIONS = '.png,.jpg,.jpeg,.webp';
export const MAX_PHOTOS = 6;
const MAX_BYTES = 8 * 1024 * 1024;
type Status = 'idle' | 'loading' | 'ready' | 'error' | 'cancelled' | 'expired';
interface State {
  key: string;
  receipts: readonly ResearchInputReceipt[];
  status: Status;
  filename: string;
  error: string | null;
}
const empty = (key: string, status: Status = 'idle'): State => ({
  key,
  receipts: [],
  status,
  filename: '',
  error: null,
});
function actorKey() {
  const user = useAuthStore.getState().user;
  return `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
}

export function usePhotoInputs() {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const actor = `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
  const key = `${actor}:${revision}`;
  const [snapshot, setSnapshot] = useState(() => empty(key));
  const state = snapshot.key === key ? snapshot : empty(key);
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    sequence.current += 1;
    controller.current?.abort();
    controller.current = null;
    return () => {
      sequence.current += 1;
      controller.current?.abort();
      controller.current = null;
    };
  }, [key]);
  useEffect(() => {
    if (!state.receipts.length) return;
    const expiry = Math.min(...state.receipts.map((item) => Date.parse(item.expires_at)));
    const timer = window.setTimeout(
      () => {
        sequence.current += 1;
        controller.current?.abort();
        controller.current = null;
        setSnapshot(empty(key, 'expired'));
      },
      Math.max(0, Math.min(expiry - Date.now(), 900_000)),
    );
    return () => window.clearTimeout(timer);
  }, [key, state.receipts]);

  const clear = (status: Status = 'idle') => {
    sequence.current += 1;
    controller.current?.abort();
    controller.current = null;
    setSnapshot(empty(key, status));
  };

  const change = async (files: readonly File[] = [], removeId?: string) => {
    if (controller.current) return false;
    const abort = new AbortController();
    controller.current = abort;
    const attempt = ++sequence.current;
    const current = () =>
      attempt === sequence.current &&
      !abort.signal.aborted &&
      actorKey() === actor &&
      workspaceRevision() === revision;
    const retained = removeId ? state.receipts.filter((item) => item.id !== removeId) : [];
    setSnapshot({ ...empty(key, 'loading'), receipts: retained });
    try {
      // Outstanding references include cancelled uploads and prior page visits.
      const pending = outstandingPhotoReceipts(key);
      const discarded = removeId ? pending.filter((id) => id === removeId) : pending;
      for (const id of discarded) {
        await discardResearchInput(id, abort.signal);
        if (!current()) return false;
        forgetPhotoReceipt(key, id);
      }
      if (files.length > MAX_PHOTOS)
        throw new ApiError(422, 'invalid_photos', 'Choose up to six photographs per analysis.');
      for (const file of files) {
        const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
        if (!PHOTO_EXTENSIONS.split(',').includes(extension))
          throw new ApiError(422, 'invalid_photo', 'Choose a PNG, JPEG or WebP photograph.');
        if (!file.size || file.size > MAX_BYTES)
          throw new ApiError(
            422,
            'invalid_photo',
            'Each photograph must be non-empty and no larger than 8 MiB.',
          );
      }
      // Upload sequentially to bound decoding pressure and keep partial failures visible.
      const receipts = [...retained];
      for (const file of files) {
        if (!current()) return false;
        setSnapshot({
          key,
          receipts: [...receipts],
          status: 'loading',
          filename: file.name,
          error: null,
        });
        const receipt = await uploadResearchInput(file, abort.signal);
        if (actorKey() === actor && workspaceRevision() === revision)
          rememberPhotoReceipt(key, receipt);
        if (!current()) return false;
        if (Date.parse(receipt.expires_at) <= Date.now()) {
          setSnapshot(empty(key, 'expired'));
          return false;
        }
        receipts.push(receipt);
        setSnapshot({ key, receipts: [...receipts], status: 'loading', filename: '', error: null });
      }
      if (!current()) return false;
      setSnapshot({
        key,
        receipts,
        status: receipts.length ? 'ready' : 'idle',
        filename: '',
        error: null,
      });
      return true;
    } catch (error) {
      if (current())
        setSnapshot((previous) => ({
          ...previous,
          status: 'error',
          error:
            describeError(error) +
            (error instanceof ApiError && error.status === 429
              ? ' Remove unused photos or wait for temporary uploads to expire, then retry.'
              : ''),
        }));
      return false;
    } finally {
      if (attempt === sequence.current) controller.current = null;
    }
  };
  return {
    ...state,
    key,
    busy: state.status === 'loading',
    clear,
    replace: change,
    remove: (id: string) => change([], id),
  };
}
