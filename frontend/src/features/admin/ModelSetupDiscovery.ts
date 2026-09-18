import { useEffect, useState } from 'react';
import { ApiError, describeError } from '@/lib/api/errors';
import { discoverLlmModels } from '@/lib/api/llm';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';

interface Catalogue {
  models: string[];
  busy: boolean;
  error: string | null;
  attempts: number;
}
const EMPTY: Catalogue = { models: [], busy: false, error: null, attempts: 0 };

/** At most three attempts per visit/refresh, cancelled when the model step closes. */
export function useModelSetupDiscovery(
  visible: boolean,
  baseUrl: string,
  apiKey: string,
  profileId?: string,
) {
  const request = useScopedRequest();
  const [catalogue, setCatalogue] = useState<Catalogue>(EMPTY);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!visible) return;
    const signal = request();
    const aborted = () => signal.aborted;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const run = async (attempt: number) => {
      if (aborted()) return;
      setCatalogue({ models: [], busy: true, error: null, attempts: attempt });
      try {
        const result = await discoverLlmModels(
          {
            provider: 'openai_compatible',
            base_url: baseUrl.trim(),
            ...(apiKey.trim()
              ? { api_key: apiKey.trim() }
              : profileId
                ? { profile_id: profileId }
                : {}),
          },
          signal,
        );
        signal.throwIfAborted();
        setCatalogue({ models: result.models, busy: false, error: null, attempts: attempt });
      } catch (failure) {
        if (aborted()) return;
        const transient =
          failure instanceof ApiError &&
          (failure.status === 0 ||
            failure.status === 408 ||
            failure.status === 429 ||
            failure.status >= 500);
        if (transient && attempt < 3) {
          timer = setTimeout(() => void run(attempt + 1), attempt * 750);
        } else
          setCatalogue({
            models: [],
            busy: false,
            error: describeError(failure),
            attempts: attempt,
          });
      }
    };
    void run(1);
    return () => {
      clearTimeout(timer);
      request();
    };
  }, [visible, baseUrl, apiKey, profileId, refresh, request]);
  return { ...catalogue, refresh: () => setRefresh((value) => value + 1) };
}
