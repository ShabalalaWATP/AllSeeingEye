import { useCallback, useEffect } from 'react';

import { fetchUkraineDigest, type UkraineDigestView } from '@/lib/api/ukraineDigest';
import { useResource } from '@/lib/hooks/useResource';

/** While a digest is being written the panel checks again; otherwise nothing polls. */
export const DIGEST_POLL_MS = 15 * 1000;

export function useUkraineDigest(load: () => Promise<UkraineDigestView> = fetchUkraineDigest) {
  const loader = useCallback(() => load(), [load]);
  const resource = useResource<UkraineDigestView>(loader);
  const { data, reload } = resource;
  const generating = data?.generating ?? false;
  useEffect(() => {
    if (!generating) return undefined;
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void reload();
    }, DIGEST_POLL_MS);
    return () => window.clearInterval(timer);
  }, [generating, reload]);
  return resource;
}
