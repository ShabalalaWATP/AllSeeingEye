import { useCallback, useEffect } from 'react';

import { fetchUkraineDigest, type UkraineDigestView } from '@/lib/api/ukraineDigest';
import { useResource } from '@/lib/hooks/useResource';
import { useVisiblePolling, type PollOutcome } from '@/lib/hooks/useVisiblePolling';

/** While a digest is being written the panel checks again; otherwise nothing polls. */
export const DIGEST_POLL_MS = 15 * 1000;

export function useUkraineDigest(load: () => Promise<UkraineDigestView> = fetchUkraineDigest) {
  const loader = useCallback(() => load(), [load]);
  const resource = useResource<UkraineDigestView>(loader);
  const { data, reload } = resource;
  const generating = data?.generating ?? false;
  const poll = useCallback(async (): Promise<PollOutcome> => {
    await reload();
    return 'ok';
  }, [reload]);
  const { markLoaded } = useVisiblePolling({
    enabled: generating,
    intervalMs: DIGEST_POLL_MS,
    poll,
  });
  // Any fresh view, including one returned by a generate request, restarts the wait.
  useEffect(() => {
    if (data !== null) markLoaded();
  }, [data, markLoaded]);
  return resource;
}
