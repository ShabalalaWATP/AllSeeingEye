import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import type { Layer } from '@deck.gl/core';
import type { Country } from '@/lib/api/geoSchemas';
import { zoomForBounds } from '@/lib/api/geo';
import { fetchRadarAttackTrends, type RadarAttackSnapshot } from '@/lib/api/cyber';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import type { ViewMode } from '@/stores/globe';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { radarAttackCountries, type RadarAttackCountry } from './radarAttackCountries';
import { radarAttackCountryLayers } from './layers/radarAttackCountries';

/** Bounded Radar snapshot, requested only while Cyber and its default-on sublayer are active. */
export function useRadarAttackMap(
  cyberEnabled: boolean,
  pageVisible: boolean,
  countries: Record<string, Country>,
) {
  const user = useAuthStore((state) => state.user);
  const authenticated = useAuthStore(
    (state) => state.status === 'authenticated' && state.user?.is_active === true,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}:${revision}`;
  const signalFor = useScopedRequest();
  const [enabled, setEnabled] = useState(true);
  const [selectedIso, setSelectedIso] = useState<string | null>(null);
  const [result, setResult] = useState<{
    scope: string;
    data: RadarAttackSnapshot | null;
    error: boolean;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const active = enabled && cyberEnabled && authenticated;
  useEffect(() => {
    if (!active || !pageVisible) return;
    const signal = signalFor();
    let current = true;
    void fetchRadarAttackTrends(signal)
      .then((data) => {
        if (current && !signal.aborted) setResult({ scope, data, error: false });
      })
      .catch(() => {
        if (current && !signal.aborted) setResult({ scope, data: null, error: true });
      })
      .finally(() => {
        if (current && !signal.aborted) setLoading(false);
      });
    return () => {
      current = false;
      signalFor();
    };
  }, [active, pageVisible, scope, reloadKey, signalFor]);
  const data = result?.scope === scope ? result.data : null;
  const rows = useMemo(() => radarAttackCountries(data, countries), [data, countries]);
  const selected =
    active && selectedIso ? (rows.find((row) => row.country.iso2 === selectedIso) ?? null) : null;
  const close = useCallback(() => setSelectedIso(null), []);
  const toggle = useCallback(() => {
    close();
    setEnabled((value) => !value);
  }, [close]);
  return {
    active,
    enabled,
    toggle,
    data: active ? data : null,
    rows: active ? rows : [],
    selected,
    select: setSelectedIso,
    close,
    loading: active && (loading || result?.scope !== scope),
    error: active && result?.scope === scope && result.error,
    reload: () => {
      setLoading(true);
      setReloadKey((value) => value + 1);
    },
  };
}

export function useRadarAttackLayers({
  radar,
  engine,
  closeOthers,
  picking,
  mode,
}: {
  radar: ReturnType<typeof useRadarAttackMap>;
  engine: GlobeEngineHandle;
  closeOthers: () => void;
  picking: boolean;
  mode: ViewMode;
}): Layer[] {
  const { active, rows, selected, select } = radar;
  const selectedIso = selected?.country.iso2 ?? null;
  const focus = useCallback(
    (row: RadarAttackCountry) => {
      if (!active || picking) return;
      closeOthers();
      select(row.country.iso2);
      engine.flyTo({ center: row.country.centroid, zoom: zoomForBounds(row.country.bounds) });
    },
    [active, picking, closeOthers, select, engine],
  );
  return useMemo(
    () =>
      active ? radarAttackCountryLayers(rows, selectedIso, focus, mode === 'map', !picking) : [],
    [active, rows, selectedIso, focus, mode, picking],
  );
}
