/** A transient attachment belongs to the current account, never a shared or stored cache. */
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';

import { describeError } from '@/lib/api/errors';
import { uploadResearchInput } from '@/lib/api/researchInputs';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

export const IMPORT_EXTENSIONS = '.txt,.csv,.json,.pdf,.docx,.png,.jpg,.jpeg,.webp,.mp4,.mov,.webm';
export const MAX_IMPORT_BYTES = 8 * 1024 * 1024;
type Status = 'idle' | 'loading' | 'ready' | 'error' | 'cancelled' | 'expired';
interface State {
  key: string;
  status: Status;
  receipt: ResearchInputReceipt | null;
  filename: string;
  error: string | null;
}

function actorKey() {
  const user = useAuthStore.getState().user;
  return `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
}

function empty(key: string, status: Status = 'idle'): State {
  return { key, status, receipt: null, filename: '', error: null };
}

export function useResearchInput(onChange: (inputId: string | null) => void) {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const actor = `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}`;
  const key = `${actor}:${revision}`;
  const [snapshot, setSnapshot] = useState<State>(() => empty(key));
  const state = snapshot.key === key ? snapshot : empty(key);
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const changed = useRef(onChange);
  useEffect(() => {
    changed.current = onChange;
  }, [onChange]);
  useEffect(() => {
    controller.current?.abort();
    sequence.current += 1;
    changed.current(null);
    return () => {
      sequence.current += 1;
      controller.current?.abort();
    };
  }, [key]);

  const clear = useCallback(
    (status: Status = 'idle') => {
      sequence.current += 1;
      controller.current?.abort();
      controller.current = null;
      setSnapshot(empty(key, status));
      changed.current(null);
    },
    [key],
  );

  useEffect(() => {
    if (state.receipt === null) return;
    const attempt = sequence.current;
    const expire = () => {
      if (attempt !== sequence.current) return;
      setSnapshot(empty(key, 'expired'));
      changed.current(null);
    };
    const remaining = Date.parse(state.receipt.expires_at) - Date.now();
    const timer = window.setTimeout(expire, Math.max(0, Math.min(remaining, 15 * 60_000)));
    return () => window.clearTimeout(timer);
  }, [key, state.receipt]);

  const upload = useCallback(
    async (file: File) => {
      clear();
      const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
      let invalid: string | null = null;
      if (file.size === 0 || file.size > MAX_IMPORT_BYTES)
        invalid = 'Choose a non-empty file up to 8 MiB.';
      else if (!IMPORT_EXTENSIONS.split(',').includes(extension))
        invalid = 'Choose a supported document, dataset, image or video.';
      if (invalid !== null) {
        setSnapshot({ ...empty(key, 'error'), error: invalid });
        return;
      }
      const attempt = ++sequence.current;
      const abort = new AbortController();
      controller.current = abort;
      const current = () =>
        attempt === sequence.current && actorKey() === actor && workspaceRevision() === revision;
      setSnapshot({ ...empty(key, 'loading'), filename: file.name });
      try {
        const receipt = await uploadResearchInput(file, abort.signal);
        if (!current()) return;
        if (Date.parse(receipt.expires_at) <= Date.now()) {
          setSnapshot(empty(key, 'expired'));
          return;
        }
        setSnapshot({ key, status: 'ready', receipt, filename: file.name, error: null });
        changed.current(receipt.id);
      } catch (error) {
        if (!current()) return;
        setSnapshot({ ...empty(key, 'error'), error: describeError(error) });
      } finally {
        if (current()) controller.current = null;
      }
    },
    [actor, clear, key, revision],
  );

  const replaceReceipt = (receipt: ResearchInputReceipt) => {
    if (
      actorKey() !== actor ||
      workspaceRevision() !== revision ||
      Date.parse(receipt.expires_at) <= Date.now()
    )
      return;
    sequence.current += 1;
    setSnapshot({ key, status: 'ready', receipt, filename: receipt.filename, error: null });
    changed.current(receipt.id);
  };
  return { ...state, key, upload, clear, replaceReceipt, busy: state.status === 'loading' };
}
