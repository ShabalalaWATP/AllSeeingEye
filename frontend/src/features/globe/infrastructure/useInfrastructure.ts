import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import {
  fetchInfrastructure,
  type Infrastructure,
  type Cable,
  type NuclearFacility,
  type GroundStation,
} from '@/lib/api/infrastructure';

import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';

export type InfrastructureSelection =
  | { kind: 'cable'; item: Cable }
  | { kind: 'station'; item: GroundStation }
  | { kind: 'nuclear'; item: NuclearFacility };

export function useInfrastructure() {
  const authority = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const accessRevision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const scope = `${authority}:${accessRevision}`;
  const anonymous = authority.startsWith('anonymous:');
  const request = useScopedRequest();
  const [dataScope, setDataScope] = useState<string | null>(null);

  const [cablesEnabled, setCablesEnabled] = useState(false);
  const [stationsEnabled, setStationsEnabled] = useState(false);
  const [nuclearEnabled, setNuclearEnabled] = useState(false);
  const [data, setData] = useState<Infrastructure | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [selection, setSelection] = useState<{
    scope: string;
    value: InfrastructureSelection;
  } | null>(null);
  const enabled = cablesEnabled || stationsEnabled || nuclearEnabled;
  useEffect(() => {
    if (!enabled || anonymous) return;
    const signal = request();
    let current = true;
    void fetchInfrastructure(signal)
      .then((value) => {
        if (current && !signal.aborted) {
          setData(value);
          setDataScope(scope);
          setError(null);
          setLoading(false);
        }
      })
      .catch(() => {
        if (current && !signal.aborted) {
          setData(null);
          setDataScope(scope);
          setError('Infrastructure could not be loaded. Retry to reconnect.');
          setLoading(false);
        }
      });
    return () => {
      current = false;
      request();
    };
  }, [enabled, revision, scope, anonymous, request]);
  const close = useCallback(() => setSelection(null), []);
  const selected =
    selection?.scope === scope &&
    ((selection.value.kind === 'cable' && cablesEnabled) ||
      (selection.value.kind === 'station' && stationsEnabled) ||
      (selection.value.kind === 'nuclear' && nuclearEnabled))
      ? selection.value
      : null;
  return {
    data: dataScope === scope ? data : null,
    loading: !anonymous && enabled && (loading || dataScope !== scope),
    error: dataScope === scope ? error : null,
    cablesEnabled,
    stationsEnabled,
    nuclearEnabled,
    selected,
    close,
    select: useCallback(
      (value: InfrastructureSelection) => setSelection({ scope, value }),
      [scope],
    ),
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
    toggleNuclear: () => {
      setSelection(null);
      if (!enabled) setLoading(true);
      setNuclearEnabled(!nuclearEnabled);
    },
    retry: () => {
      setLoading(enabled);
      setError(null);
      setRevision((value) => value + 1);
    },
  };
}
export type InfrastructureState = ReturnType<typeof useInfrastructure>;
