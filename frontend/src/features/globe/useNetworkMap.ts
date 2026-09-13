import { useCallback, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { zoomForBounds } from '@/lib/api/geo';
import type { ViewMode } from '@/stores/globe';
import { useContextEvents } from './context/useContextEvents';
import { networkCountryGroups, type NetworkCountryGroup } from './networkContext';
import { networkCountryLayers } from './layers/networkCountries';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { NETWORK_SOURCES, isNetworkSource } from './networkSources';

/** The toolbar panel and map share one bounded snapshot per source. */
export function useNetworkMap(country: string | null, countries: Record<string, Country>) {
  const [open, setOpen] = useState(false);
  const [selectedIso, setSelectedIso] = useState<string | null>(null);
  const snapshot = useContextEvents(NETWORK_SOURCES, country, open);
  const groups = useMemo(
    () => networkCountryGroups(snapshot.events, countries),
    [snapshot.events, countries],
  );
  const close = useCallback(() => setSelectedIso(null), []);
  const setEnabled = useCallback((enabled: boolean) => {
    setOpen(enabled);
    if (!enabled) setSelectedIso(null);
  }, []);
  const selected =
    open && selectedIso
      ? (groups.find((group) => group.country.iso2 === selectedIso) ?? null)
      : null;
  return { open, snapshot, groups, selected, selectedIso, setSelectedIso, close, setEnabled };
}

/** Selection owns navigation and highlight without turning on the Cyber layer. */
export function useNetworkMapSelection({
  network,
  contextEvent,
  selectContext,
  picking,
  closeOthers,
  engine,
  mode,
  countries,
}: {
  network: ReturnType<typeof useNetworkMap>;
  contextEvent: LiveEvent | null;
  selectContext: (event: LiveEvent) => void;
  picking: boolean;
  closeOthers: () => void;
  engine: GlobeEngineHandle;
  mode: ViewMode;
  countries: Record<string, Country>;
}) {
  const { open, groups, selectedIso, setSelectedIso } = network;
  const selectGroup = useCallback(
    (group: NetworkCountryGroup) => {
      if (!open || picking) return;
      closeOthers();
      setSelectedIso(group.country.iso2);
      engine.flyTo({ center: group.country.centroid, zoom: zoomForBounds(group.country.bounds) });
    },
    [open, picking, closeOthers, setSelectedIso, engine],
  );
  const selectRecord = useCallback(
    (event: LiveEvent) => {
      if (picking) return;
      selectContext(event);
      const country = event.country_iso ? countries[event.country_iso] : null;
      if (country) engine.flyTo({ center: country.centroid, zoom: zoomForBounds(country.bounds) });
    },
    [picking, selectContext, countries, engine],
  );
  const selectedMarker = useMemo(
    () =>
      groups.find(
        (group) =>
          group.country.iso2 === selectedIso ||
          (contextEvent &&
            isNetworkSource(contextEvent.source_id) &&
            group.events.some((event) => event.id === contextEvent.id)),
      ) ?? null,
    [groups, selectedIso, contextEvent],
  );
  const layers = useMemo(
    () =>
      open
        ? networkCountryLayers(groups, selectedMarker, selectGroup, mode === 'map', !picking)
        : [],
    [open, groups, selectedMarker, selectGroup, mode, picking],
  );
  return { layers, selectRecord };
}
