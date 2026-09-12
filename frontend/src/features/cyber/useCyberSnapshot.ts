import { useCallback } from 'react';

import { fetchCyberSnapshot, type CyberDays } from '@/lib/api/cyber';
import { isApiError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

const MAX_RETRIES = 4;
const MAX_RETRY_DELAY_SECONDS = 10;

function waitForRetry(milliseconds: number, signal: AbortSignal): Promise<void> {
  signal.throwIfAborted();
  return new Promise((resolve, reject) => {
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException('The snapshot request was aborted.', 'AbortError'));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', abort);
      resolve();
    }, milliseconds);
    signal.addEventListener('abort', abort, { once: true });
  });
}

async function readSnapshot(days: CyberDays, signal: AbortSignal) {
  for (let retries = 0; ; retries += 1) {
    signal.throwIfAborted();
    try {
      return await fetchCyberSnapshot(days, signal);
    } catch (error) {
      signal.throwIfAborted();
      if (!isApiError(error) || error.status !== 429 || retries >= MAX_RETRIES) throw error;
      const seconds = error.retryAfterSeconds ?? 1;
      // Never retry before a longer server cooldown. Leave the normal error and
      // manual reload available once this short read-only retry budget is spent.
      if (!Number.isFinite(seconds) || seconds < 0 || seconds > MAX_RETRY_DELAY_SECONDS)
        throw error;
      await waitForRetry(Math.max(250, seconds * 1000), signal);
    }
  }
}

/** Superseded periods cancel both GET work and retry timers, including access changes. */
export function useCyberSnapshot(days: CyberDays) {
  const beginRequest = useScopedRequest();
  const load = useCallback(() => readSnapshot(days, beginRequest()), [days, beginRequest]);
  return useScopedResource(load);
}
