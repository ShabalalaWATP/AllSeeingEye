import { useEffect, useState } from 'react';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useNow } from '@/lib/hooks/useNow';
import { ApiError } from '@/lib/api/errors';
import { testSource } from '@/lib/api/sourceControls';
import {
  FIRMS_ID,
  fetchFirmsConnection,
  saveFirmsDraft,
  testFirmsDraft,
  confirmFirmsConnection,
  removeFirmsConnection,
  type FirmsConnection,
} from '@/lib/api/firmsConnection';

type Operation = 'load' | 'draft' | 'confirm' | 'remove' | 'current';
function freshProof(value: FirmsConnection, now: number): boolean {
  return (
    value.draft_present &&
    value.test_ok &&
    value.test_generation > 0 &&
    value.draft_expires_at !== null &&
    Date.parse(value.draft_expires_at) > now &&
    value.tested_at !== null &&
    Date.parse(value.tested_at) + 15 * 60_000 > now
  );
}
function connectionError(value: unknown): string {
  if (value instanceof ApiError) {
    if (value.status === 409)
      return 'The connection changed or its test expired. Refresh the status and test the draft again.';
    if (value.status === 401 || value.status === 403)
      return 'Your administrator access is no longer available. Sign in again.';
    if (value.status === 429) return 'Too many connection attempts. Wait before testing again.';
    if (value.status === 422)
      return 'The draft could not be validated. Check the MAP_KEY and test again.';
  }
  return 'The connection request could not be completed. Refresh the status before trying again.';
}
export function useFirmsConnection() {
  const request = useScopedRequest();
  const now = useNow();
  const [status, setStatus] = useState<FirmsConnection | null>(null);
  const [expiredStatus, setExpiredStatus] = useState<FirmsConnection | null>(null);
  useEffect(() => {
    if (!status?.draft_expires_at || !status.tested_at || !status.test_ok) return;
    const deadline = Math.min(
      Date.parse(status.draft_expires_at),
      Date.parse(status.tested_at) + 900_000,
    );
    const timer = setTimeout(() => setExpiredStatus(status), Math.max(0, deadline - Date.now()));
    return () => clearTimeout(timer);
  }, [status]);
  const [apiKey, setApiKey] = useState('');
  const [busy, setBusy] = useState<Operation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [removeReview, setRemoveReview] = useState(false);
  const changeKey = (value: string) => {
    request();
    setBusy(null);
    setApiKey(value);
    setReviewed(false);
    setRemoveReview(false);
    setNotice(null);
    setError(null);
  };
  const run = async (operation: Operation) => {
    if (busy) return;
    if (operation !== 'load' && !status) return;
    if (operation === 'draft' && apiKey && !/^[A-Za-z0-9_-]{16,128}$/.test(apiKey)) {
      setError('Enter a MAP_KEY containing 16 to 128 letters, numbers, underscores or hyphens.');
      return;
    }
    if (operation === 'confirm' && (!status || !reviewed || !freshProof(status, Date.now()))) {
      setReviewed(false);
      setError('This test has expired. Test the draft again before confirming.');
      return;
    }
    const signal = request();
    const key = apiKey;
    setApiKey('');
    setBusy(operation);
    setError(null);
    setNotice(null);
    setReviewed(false);
    try {
      if (operation === 'load') {
        const loaded = await fetchFirmsConnection(signal);
        signal.throwIfAborted();
        setStatus(loaded);
      } else if (operation === 'draft' && status) {
        const draft = key
          ? await saveFirmsDraft({ api_key: key, expected_revision: status.revision }, signal)
          : status;
        signal.throwIfAborted();
        setStatus(draft);
        const result = await testFirmsDraft(draft.revision, signal);
        signal.throwIfAborted();
        if (result.status.revision !== draft.revision)
          throw new ApiError(409, 'stale_revision', '');
        setStatus(result.status);
        if (result.ok && freshProof(result.status, Date.now())) {
          setReviewed(true);
          setNotice(
            `Draft test passed: ${result.fetched} observations received. Review the global change before confirming.`,
          );
        } else
          setError(
            'The draft did not pass the bounded NASA connection test. Check the key and try again.',
          );
      } else if (operation === 'confirm' && status) {
        const active = await confirmFirmsConnection(
          { expected_revision: status.revision, test_generation: status.test_generation },
          signal,
        );
        signal.throwIfAborted();
        setStatus(active);
        setRemoveReview(false);
        setNotice(
          'FIRMS connection confirmed for all users and teams. The next scheduled poll uses this connection; source enablement is unchanged.',
        );
      } else if (operation === 'remove' && status) {
        const cleared = await removeFirmsConnection(status.revision, signal);
        signal.throwIfAborted();
        setStatus(cleared);
        setRemoveReview(false);
        setNotice(
          'Stored connection and draft removed. Future polls have no stored MAP_KEY. Existing observations and reports remain available.',
        );
      } else if (operation === 'current') {
        const result = await testSource(FIRMS_ID, signal);
        signal.throwIfAborted();
        if (result.ok)
          setNotice(
            `Current connection test passed: ${result.fetched}${result.capped ? '+' : ''} observations received. Nothing was published or saved.`,
          );
        else
          setError(
            'The current connection test failed. Check its configuration and source status.',
          );
      }
    } catch (failure) {
      if (!signal.aborted) setError(connectionError(failure));
    } finally {
      if (!signal.aborted) setBusy(null);
    }
  };
  useEffect(() => {
    // The scoped request aborts on unmount or authority change.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run('load');
    // A parent authority key remounts this journey when access changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return {
    status,
    apiKey,
    changeKey,
    busy,
    error,
    notice,
    run,
    removeReview,
    setRemoveReview,
    canConfirm:
      !!status && status !== expiredStatus && reviewed && !apiKey && freshProof(status, now),
    proofExpired: !!status?.test_ok && (status === expiredStatus || !freshProof(status, now)),
    cancel: () => {
      request();
      setApiKey('');
      setBusy(null);
      setReviewed(false);
      setRemoveReview(false);
      setNotice('Request cancelled. Refresh the status before continuing.');
    },
  };
}
