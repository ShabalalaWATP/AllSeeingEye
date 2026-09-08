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
    void fetchCameras(controller.signal)
      .then((result) => {
        if (current) {
          setCatalogue(result);
          setError(null);
        }
      })
      .catch(() => {
        if (current) setError('The camera catalogue could not be loaded. Please try again.');
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
      controller.abort();
    };
  }, [enabled, revision]);
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
