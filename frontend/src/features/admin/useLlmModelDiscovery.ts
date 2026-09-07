import { useEffect, useMemo, useState } from 'react';
import { discoverLlmModels } from '@/lib/api/llm';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
export function useLlmModelDiscovery(
  baseUrl: string,
  apiKey: string,
  profileId: string | undefined,
  enabled: boolean,
) {
  const request = useScopedRequest();
  const [result, setResult] = useState<{
    key: object;
    models: string[];
    error: string | null;
    busy: boolean;
    loaded: boolean;
  } | null>(null);
  // Credential identity stays in component memory only; never local/session storage or query strings.
  const key = useMemo(
    () => ({ baseUrl, profileId, keyLength: apiKey.length }),
    [baseUrl, apiKey, profileId],
  );
  useEffect(() => {
    request();
  }, [key, request]);
  const load = async () => {
    if (!enabled || !baseUrl.trim()) return;
    const signal = request();
    setResult({ key, models: [], error: null, busy: true, loaded: false });
    try {
      const value = await discoverLlmModels(
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
      setResult({ key, models: value.models, error: null, busy: false, loaded: true });
    } catch (error) {
      if (!signal.aborted)
        setResult({ key, models: [], error: describeError(error), busy: false, loaded: false });
    }
  };
  return {
    models: result?.key === key ? result.models : [],
    busy: result?.key === key && result.busy,
    error: result?.key === key ? result.error : null,
    loaded: result?.key === key && result.loaded,
    load,
  };
}
