import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchCameras,
  type Camera,
  type CameraCatalogue,
  type CameraProvider,
} from '@/lib/api/cameras';

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
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    let current = true;
    const ids = Object.keys(providers).filter((id) => providers[id]);
    const initial =
      ids.length === 3 && ['tfl', 'hongkong', 'fintraffic'].every((id) => providers[id]);
    const requests = initial ? [undefined] : ids;
    void Promise.allSettled(requests.map((id) => fetchCameras(controller.signal, id))).then(
      (results) => {
        if (!current) return;
        const success = results.flatMap((result) =>
          result.status === 'fulfilled' ? [result.value] : [],
        );
        const refreshed = requests.flatMap((id, index) =>
          results[index]?.status === 'fulfilled' ? (id ? [id] : ids) : [],
        );
        setCatalogue((previous) => {
          const first = success[0];
          if (!first) return previous;
          const cameras = new Map(
            (previous?.cameras ?? [])
              .filter((camera) => !refreshed.includes(camera.provider))
              .map((camera) => [camera.id, camera]),
          );
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
            cameras: [...cameras.values()].slice(-75000),
            providers: [...statuses.values()],
          };
        });
        setError(
          results.some((result) => result.status === 'rejected')
            ? 'Some camera catalogues could not be loaded. Please try again.'
            : null,
        );
        setLoading(false);
      },
    );
    return () => {
      current = false;
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
  const selected = visible.find((camera) => camera.id === selectedId) ?? null;
  const select = useCallback((camera: Camera | null) => setSelectedId(camera?.id ?? null), []);
  const close = useCallback(() => setSelectedId(null), []);
  const toggleProvider = useCallback((provider: CameraProvider) => {
    setProviders((old) => ({ ...old, [provider]: !old[provider] }));
    setSelectedId(null);
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
