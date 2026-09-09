import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  fetchCameras,
  type Camera,
  type CameraCatalogue,
  type CameraProvider,
} from '@/lib/api/cameras';

interface CachedCatalogue {
  revision: number;
  value: CameraCatalogue;
}
const CAMERA_LIMIT = 75000;

/** Evict disabled regions before older enabled ones; a toggle reloads an evicted region. */
function boundCache(cache: Map<string, CachedCatalogue>, providers: Record<string, boolean>) {
  let count = [...cache.values()].reduce((total, entry) => total + entry.value.cameras.length, 0);
  let activeEvicted = false;
  const oldestFirst = [...cache.keys()].sort(
    (a, b) => Number(Boolean(providers[a])) - Number(Boolean(providers[b])),
  );
  for (const id of oldestFirst) {
    if (count <= CAMERA_LIMIT) break;
    const entry = cache.get(id);
    if (!entry) continue;
    count -= entry.value.cameras.length;
    activeEvicted ||= Boolean(providers[id]);
    cache.delete(id);
  }
  return activeEvicted;
}

export function useCameras() {
  const [enabled, setEnabled] = useState(false);
  const [catalogue, setCatalogue] = useState<CameraCatalogue | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [query, setQuery] = useState('');
  const [providers, setProviders] = useState<Record<CameraProvider, boolean>>({
    tfl: true,
    hongkong: true,
    fintraffic: true,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const cache = useRef(new Map<string, CachedCatalogue>());
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    let current = true;
    const ids = Object.keys(providers).filter((id) => providers[id]);
    const missing = ids.filter((id) => cache.current.get(id)?.revision !== revision);
    const requests = missing;
    let next = 0;
    let failed = false;
    let limited = false;
    const publish = () => {
      if (!current) return;
      // The bounded cache is the sole owner of camera payloads. Old revisions
      // remain usable after a failed refresh, but evicted regions must not live
      // indefinitely in a second copy of the rendered catalogue.
      const success = [...cache.current.values()].map((entry) => entry.value);
      setCatalogue((previous) => {
        const first = success[0];
        if (!first) return previous ? { ...previous, cameras: [] } : null;
        const cameras = new Map<string, Camera>();
        const statuses = new Map(
          previous?.providers.map((provider) => [provider.id, provider]) ?? [],
        );
        for (const result of success) {
          for (const camera of result.cameras) cameras.set(camera.id, camera);
          for (const provider of result.providers) {
            if (provider.status !== 'not_loaded' || !statuses.has(provider.id))
              statuses.set(provider.id, provider);
          }
        }
        return {
          ...first,
          cameras: [...cameras.values()].slice(-CAMERA_LIMIT),
          providers: [...statuses.values()],
        };
      });
    };
    let publishTimer: ReturnType<typeof setTimeout> | undefined;
    const schedulePublish = () => {
      publishTimer ??= setTimeout(() => {
        publishTimer = undefined;
        publish();
      }, 100);
    };
    // Only four provider requests may be outstanding. Completed responses survive
    // a checkbox change, so adding one region never re-downloads its neighbours.
    const worker = async () => {
      while (current && next < requests.length) {
        const provider = requests[next++];
        try {
          const value = await fetchCameras(controller.signal, provider);
          if (controller.signal.aborted) return;
          for (const id of provider ? [provider] : ids)
            cache.current.set(id, {
              revision,
              value: {
                ...value,
                cameras: value.cameras.filter((camera) => camera.provider === id),
              },
            });
          limited = boundCache(cache.current, providers) || limited;
          schedulePublish();
        } catch {
          if (!controller.signal.aborted) failed = true;
        }
      }
    };
    void Promise.all(Array.from({ length: Math.min(4, requests.length) }, worker)).then(() => {
      if (!current) return;
      clearTimeout(publishTimer);
      publish();
      setError(
        failed
          ? 'Some camera catalogues could not be loaded. Please try again.'
          : limited
            ? 'Camera catalogue limit reached (75,000). Disable some regions before loading more.'
            : null,
      );
      setLoading(false);
    });
    return () => {
      current = false;
      clearTimeout(publishTimer);
      controller.abort();
    };
  }, [enabled, revision, providers]);
  const toggleEnabled = useCallback((value: boolean) => {
    setEnabled(value);
    setLoading(value);
    setError(null);
    if (!value) setSelectedId(null);
  }, []);
  const visible = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    return enabled
      ? (catalogue?.cameras ?? []).filter(
          (camera) =>
            providers[camera.provider] &&
            `${camera.title} ${camera.provider}`.toLocaleLowerCase().includes(term),
        )
      : [];
  }, [catalogue, enabled, providers, query]);
  const selected = useMemo(
    () =>
      selectedId === null ? null : (visible.find((camera) => camera.id === selectedId) ?? null),
    [visible, selectedId],
  );
  const select = useCallback((camera: Camera | null) => setSelectedId(camera?.id ?? null), []);
  const close = useCallback(() => setSelectedId(null), []);
  const toggleProvider = useCallback(
    (provider: CameraProvider) => {
      if (
        providers[provider] &&
        catalogue?.cameras.some(
          (camera) => camera.id === selectedId && camera.provider === provider,
        )
      )
        setSelectedId(null);
      setProviders((old) => ({ ...old, [provider]: !old[provider] }));
      setLoading(true);
    },
    [catalogue, providers, selectedId],
  );
  const setProviderGroup = useCallback((ids: readonly string[], value: boolean) => {
    setProviders((old) => ({ ...old, ...Object.fromEntries(ids.map((id) => [id, value])) }));
    if (!value) setSelectedId(null);
    setLoading(true);
  }, []);
  const search = useCallback((value: string) => {
    setQuery(value);
    setSelectedId(null);
  }, []);
  const refresh = useCallback(() => {
    setLoading(true);
    setRevision((old) => old + 1);
  }, []);
  return {
    enabled,
    setEnabled: toggleEnabled,
    catalogue,
    loading,
    error,
    providers,
    toggleProvider,
    setProviderGroup,
    query,
    setQuery: search,
    visible,
    selected,
    select,
    close,
    refresh,
  };
}
export type CameraState = ReturnType<typeof useCameras>;
