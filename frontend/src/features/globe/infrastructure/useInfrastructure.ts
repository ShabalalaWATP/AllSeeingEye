import { useCallback, useEffect, useState } from 'react';
import {
  fetchInfrastructure,
  type Infrastructure,
  type Cable,
  type GroundStation,
} from '@/lib/api/infrastructure';

export type InfrastructureSelection =
  { kind: 'cable'; item: Cable } | { kind: 'station'; item: GroundStation };

export function useInfrastructure() {
  const [cablesEnabled, setCablesEnabled] = useState(false);
  const [stationsEnabled, setStationsEnabled] = useState(false);
  const [data, setData] = useState<Infrastructure | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [selection, setSelection] = useState<InfrastructureSelection | null>(null);
  const enabled = cablesEnabled || stationsEnabled;
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    let current = true;
    void fetchInfrastructure(controller.signal)
      .then((value) => {
        if (current) {
          setData(value);
          setError(null);
          setLoading(false);
        }
      })
      .catch(() => {
        if (current) {
          setError('Infrastructure could not be loaded. Retry to reconnect.');
          setLoading(false);
        }
      });
    return () => {
      current = false;
      controller.abort();
    };
  }, [enabled, revision]);
  const close = useCallback(() => setSelection(null), []);
  const selected =
    selection &&
    ((selection.kind === 'cable' && cablesEnabled) ||
      (selection.kind === 'station' && stationsEnabled))
      ? selection
      : null;
  return {
    data,
    loading: loading && enabled,
    error,
    cablesEnabled,
    stationsEnabled,
    selected,
    close,
    select: useCallback((value: InfrastructureSelection) => setSelection(value), []),
    toggleCables: () => {
      setSelection(null);
      if (!enabled) setLoading(true);
      setCablesEnabled(!cablesEnabled);
    },
    toggleStations: () => {
      setSelection(null);
      if (!enabled) setLoading(true);
      setStationsEnabled(!stationsEnabled);
    },
    retry: () => {
      setLoading(enabled);
      setError(null);
      setRevision((value) => value + 1);
    },
  };
}
export type InfrastructureState = ReturnType<typeof useInfrastructure>;
