import { useCallback, useEffect, useMemo } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import { zoomForBounds } from '@/lib/api/geo';
import { hasCyberCountryContext, matchesCyberFilters } from '@/lib/cyber';
import { cyberAuthority, useCyberFiltersStore } from '@/stores/cyberFilters';
import { filterByWindow } from '@/stores/events';
import type { ViewMode } from '@/stores/globe';
import type { useContextSelection } from './context/useContextSelection';
import type { useCyberCountryContext } from './useCyberCountryContext';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { isMappedEvent, locationQuality, type LocationQualityFilter } from './geographicPrecision';
import { cyberCountryLayers } from './layers/cyberCountries';
import type { CyberCountryContext } from './cyberCountryContext';

export function useCyberMapSelection({
  cyber,
  enabled,
  picking,
  closeOthers,
  engine,
  mode,
  context,
  countries,
  quality,
  windowHours,
  now,
}: {
  cyber: ReturnType<typeof useCyberCountryContext>;
  enabled: boolean;
  picking: boolean;
  closeOthers: () => void;
  engine: GlobeEngineHandle;
  mode: ViewMode;
  context: ReturnType<typeof useContextSelection>;
  countries: Record<string, Country>;
  quality: LocationQualityFilter;
  windowHours: number | null;
  now: number;
}) {
  const pending = useCyberFiltersStore((state) => state.pending);
  const kind = useCyberFiltersStore((state) => state.kind);
  const query = useCyberFiltersStore((state) => state.query);
  const consume = useCyberFiltersStore((state) => state.consumeFocus);
  const chooseContext = context.choose;
  const closeContext = context.close;
  const selectCountry = cyber.select;
  const selectGroup = useCallback(
    (group: CyberCountryContext) => {
      if (!enabled || picking) return;
      closeOthers();
      selectCountry(group.country.iso2);
      engine.flyTo({ center: group.country.centroid, zoom: zoomForBounds(group.country.bounds) });
    },
    [enabled, picking, closeOthers, selectCountry, engine],
  );
  const selectRecord = useCallback(
    (event: LiveEvent) => {
      if (!enabled || picking || !matchesCyberFilters(event, kind, query)) return;
      closeOthers();
      chooseContext(event);
      const country = event.country_iso ? countries[event.country_iso] : undefined;
      if (isMappedEvent(event) && event.point) {
        engine.flyTo({ center: [event.point.lon, event.point.lat], zoom: 5 });
      } else if (hasCyberCountryContext(event) && country) {
        engine.flyTo({ center: country.centroid, zoom: zoomForBounds(country.bounds) });
      }
    },
    [enabled, picking, kind, query, closeOthers, chooseContext, countries, engine],
  );
  useEffect(() => {
    if (!pending || picking) return;
    if (pending.authority !== cyberAuthority()) {
      consume();
      return;
    }
    const iso = pending.country ?? pending.event?.country_iso;
    const country = iso ? countries[iso] : undefined;
    if (iso && !Object.keys(countries).length) return;
    consume();
    if (pending.event?.category === 'cyber') selectRecord(pending.event);
    else if (country) {
      engine.flyTo({ center: country.centroid, zoom: zoomForBounds(country.bounds) });
    }
  }, [pending, picking, countries, consume, selectRecord, engine]);
  useEffect(() => {
    const event = context.event;
    if (
      event?.category === 'cyber' &&
      (!enabled ||
        !matchesCyberFilters(event, kind, query) ||
        (quality !== 'all' && locationQuality(event) !== quality) ||
        !filterByWindow([event], windowHours, now).length)
    )
      closeContext();
  }, [context.event, enabled, kind, query, quality, windowHours, now, closeContext]);
  const layers = useMemo(() => {
    if (!enabled) return [];
    const event = context.event;
    // Link inspected records to an existing country reference without opening another inspector.
    const selected =
      cyber.selected ??
      (event && hasCyberCountryContext(event)
        ? (cyber.groups.find(
            (group) =>
              group.country.iso2 === event.country_iso &&
              group.events.some((member) => member.id === event.id),
          ) ?? null)
        : null);
    return cyberCountryLayers(cyber.groups, selected, selectGroup, mode === 'map', !picking);
  }, [enabled, cyber.groups, cyber.selected, context.event, selectGroup, mode, picking]);
  return { selectGroup, selectRecord, layers };
}
