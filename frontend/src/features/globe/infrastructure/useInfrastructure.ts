import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import type { Country } from '@/lib/api/geoSchemas';
import {
  militaryCountryReferences,
  type MilitaryCountryReference,
} from './militarySourceReferences';
import {
  fetchInfrastructure,
  type Infrastructure,
  type Cable,
  type DataCentre,
  type NuclearFacility,
  type GroundStation,
  type Site,
} from '@/lib/api/infrastructure';

import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { mapSourceAllowed, sourceUnavailable, useMapSourcePolicy } from '@/lib/map/sourcePolicy';
import { INFRASTRUCTURE_SOURCES } from './infrastructurePolicy';

export type InfrastructureSelection =
  | { kind: 'cable'; item: Cable }
  | { kind: 'station'; item: GroundStation }
  | { kind: 'nuclear'; item: NuclearFacility }
  | { kind: 'data_centre'; item: DataCentre }
  | { kind: 'energy_site'; item: Site }
  | { kind: 'semiconductor_site'; item: Site }
  | { kind: 'military_country'; item: MilitaryCountryReference };

const EMPTY_COUNTRIES: Record<string, Country> = {};

export function useInfrastructure(countries: Record<string, Country> = EMPTY_COUNTRIES) {
  const policy = useMapSourcePolicy();
  const militaryReason = sourceUnavailable(policy, INFRASTRUCTURE_SOURCES.military_country);
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
  const [dataCentresEnabled, setDataCentresEnabled] = useState(false);
  const [energyEnabled, setEnergyEnabled] = useState(false);
  const [semiconductorEnabled, setSemiconductorEnabled] = useState(false);
  const [militaryEnabled, setMilitaryEnabled] = useState(false);
  const militaryCountries = useMemo(() => militaryReason ? [] : militaryCountryReferences(countries), [countries, militaryReason]);
  const [data, setData] = useState<Infrastructure | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [selection, setSelection] = useState<{
    scope: string;
    value: InfrastructureSelection;
  } | null>(null);
  const enabled =
    (cablesEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.cable)) ||
    (stationsEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.station)) ||
    (nuclearEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.nuclear)) ||
    (dataCentresEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.data_centre)) ||
    (energyEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.energy_site)) ||
    (semiconductorEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.semiconductor_site));
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
  const enableTechnology = useCallback(() => {
    setCablesEnabled(mapSourceAllowed(INFRASTRUCTURE_SOURCES.cable));
    setStationsEnabled(mapSourceAllowed(INFRASTRUCTURE_SOURCES.station));
    setDataCentresEnabled(mapSourceAllowed(INFRASTRUCTURE_SOURCES.data_centre));
    setSemiconductorEnabled(mapSourceAllowed(INFRASTRUCTURE_SOURCES.semiconductor_site));
    setLoading(true);
  }, []);
  const selected =
    selection?.scope === scope &&
    mapSourceAllowed(INFRASTRUCTURE_SOURCES[selection.value.kind]) &&
    ((selection.value.kind === 'cable' && cablesEnabled) ||
      (selection.value.kind === 'station' && stationsEnabled) ||
      (selection.value.kind === 'nuclear' && nuclearEnabled) ||
      (selection.value.kind === 'data_centre' && dataCentresEnabled) ||
      (selection.value.kind === 'energy_site' && energyEnabled) ||
      (selection.value.kind === 'semiconductor_site' && semiconductorEnabled) ||
      (selection.value.kind === 'military_country' && militaryEnabled))
      ? selection.value
      : null;
  return {
    data: dataScope === scope ? data : null,
    loading: !anonymous && enabled && (loading || dataScope !== scope),
    error: dataScope === scope ? error : null,
    cablesEnabled: cablesEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.cable),
    stationsEnabled: stationsEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.station),
    nuclearEnabled: nuclearEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.nuclear),
    dataCentresEnabled: dataCentresEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.data_centre),
    energyEnabled: energyEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.energy_site),
    semiconductorEnabled: semiconductorEnabled && mapSourceAllowed(INFRASTRUCTURE_SOURCES.semiconductor_site),
    militaryEnabled: militaryEnabled && !militaryReason,
    militaryCountries,
    selected,
    close,
    enableTechnology,
    select: useCallback(
      (value: InfrastructureSelection) => setSelection({ scope, value }),
      [scope],
    ),
    toggleCables: () => {
      if (!mapSourceAllowed(INFRASTRUCTURE_SOURCES.cable)) return;
      setSelection(null);
      if (!enabled) setLoading(true);
      setCablesEnabled(!cablesEnabled);
    },
    toggleStations: () => {
      if (!mapSourceAllowed(INFRASTRUCTURE_SOURCES.station)) return;
      setSelection(null);
      if (!enabled) setLoading(true);
      setStationsEnabled(!stationsEnabled);
    },
    toggleNuclear: () => {
      if (!mapSourceAllowed(INFRASTRUCTURE_SOURCES.nuclear)) return;
      setSelection(null);
      if (!enabled) setLoading(true);
      setNuclearEnabled(!nuclearEnabled);
    },
    toggleDataCentres: () => {
      if (!mapSourceAllowed(INFRASTRUCTURE_SOURCES.data_centre)) return;
      setSelection(null);
      if (!enabled) setLoading(true);
      setDataCentresEnabled(!dataCentresEnabled);
    },
    toggleEnergy: () => {
      if (!mapSourceAllowed(INFRASTRUCTURE_SOURCES.energy_site)) return;
      setSelection(null);
      if (!enabled) setLoading(true);
      setEnergyEnabled(!energyEnabled);
    },
    toggleSemiconductor: () => {
      if (!mapSourceAllowed(INFRASTRUCTURE_SOURCES.semiconductor_site)) return;
      setSelection(null);
      if (!enabled) setLoading(true);
      setSemiconductorEnabled(!semiconductorEnabled);
    },
    toggleMilitary: () => {
      if (militaryReason) return;
      setSelection(null);
      setMilitaryEnabled(!militaryEnabled);
    },
    retry: () => {
      setLoading(enabled);
      setError(null);
      setRevision((value) => value + 1);
    },
  };
}
export type InfrastructureState = ReturnType<typeof useInfrastructure>;
