import type { LiveEvent } from '@/lib/api/eventSchemas';

export const HAZARD_GROUPS = [
  { value: 'earthquake', label: 'Earthquakes' },
  { value: 'weather', label: 'Severe weather / cyclones' },
  { value: 'flood', label: 'Floods' },
  { value: 'volcano', label: 'Volcanoes' },
  { value: 'tsunami', label: 'Tsunamis' },
  { value: 'drought', label: 'Drought' },
  { value: 'landslide', label: 'Landslides' },
  { value: 'ice', label: 'Sea and lake ice' },
  { value: 'other', label: 'Other / unclassified' },
] as const;
export type NaturalHazardKind = (typeof HAZARD_GROUPS)[number]['value'];
export type HazardGroup = NaturalHazardKind | 'all';
export type FireKind = 'wildfire' | 'thermal';
export type HazardKind = NaturalHazardKind | FireKind;
export type HazardWindow = 'all' | '24' | '72' | '168';
export type HazardAlert = 'all' | 'orange_red' | 'red';
export interface HazardOptions {
  groups: readonly NaturalHazardKind[];
  hours: HazardWindow;
  minimumMagnitude: number;
  alert: HazardAlert;
  includeUnknown: boolean;
}
export const DEFAULT_HAZARD_OPTIONS: HazardOptions = {
  groups: HAZARD_GROUPS.map(({ value }) => value),
  hours: 'all',
  minimumMagnitude: 0,
  alert: 'all',
  includeUnknown: true,
};

export function hazardKind(event: LiveEvent): HazardKind | null {
  if (event.category !== 'disaster') return null;
  // Exact adapter output aliases: EONET plural category IDs are snake-cased,
  // while GDACS/USGS/GVP/cyclone feeds use singular event subtypes.
  switch (event.subtype) {
    case 'earthquake':
    case 'earthquakes':
      return 'earthquake';
    case 'tropical_cyclone':
    case 'severe_weather':
    case 'severe_storms':
    case 'storm':
      return 'weather';
    case 'flood':
    case 'floods':
      return 'flood';
    case 'volcano':
    case 'volcanoes':
    case 'volcanic_eruption':
      return 'volcano';
    case 'wildfire':
    case 'wildfires':
      return 'wildfire';
    case 'thermal_detection':
      return 'thermal';
    case 'tsunami':
      return 'tsunami';
    case 'drought':
      return 'drought';
    case 'landslides':
      return 'landslide';
    case 'sea_lake_ice':
      return 'ice';
    default:
      return 'other';
  }
}

/** Fire evidence is controlled independently from other natural hazards. */
export function fireKind(event: LiveEvent): FireKind | null {
  const kind = hazardKind(event);
  return kind === 'wildfire' || kind === 'thermal' ? kind : null;
}

export function matchesHazardGroups(
  event: LiveEvent,
  groups: readonly NaturalHazardKind[],
): boolean {
  const kind = hazardKind(event);
  return kind === null || kind === 'wildfire' || kind === 'thermal' || groups.includes(kind);
}

export function matchesHazard(event: LiveEvent, options: HazardOptions, now: number): boolean {
  const kind = hazardKind(event);
  if (kind === null || kind === 'wildfire' || kind === 'thermal') return true;
  if (!matchesHazardGroups(event, options.groups)) return false;
  if (options.hours !== 'all') {
    const timestamp = event.published_at ? Date.parse(event.published_at) : NaN;
    if (!Number.isFinite(timestamp)) {
      if (!options.includeUnknown) return false;
    } else if (timestamp > now || now - timestamp > Number(options.hours) * 3600000) return false;
  }
  if (kind === 'earthquake' && options.minimumMagnitude > 0) {
    // Only the explicit magnitude field is comparable; GDACS severity_value has variable units.
    const magnitude = event.attributes.magnitude;
    if (typeof magnitude !== 'number' || !Number.isFinite(magnitude)) {
      if (!options.includeUnknown) return false;
    } else if (magnitude < options.minimumMagnitude) return false;
  }
  if (event.source_id === 'gdacs' && options.alert !== 'all') {
    const raw = event.attributes.alert_level;
    const level = typeof raw === 'string' ? raw.toLowerCase() : '';
    if (!['green', 'orange', 'red'].includes(level)) return options.includeUnknown;
    if (level !== 'red' && !(options.alert === 'orange_red' && level === 'orange')) return false;
  }
  return true;
}

export function countHazards(events: readonly LiveEvent[]): Record<HazardGroup, number> {
  const counts = Object.fromEntries([
    ['all', 0],
    ...HAZARD_GROUPS.map(({ value }) => [value, 0]),
  ]) as Record<HazardGroup, number>;
  for (const event of events) {
    const kind = hazardKind(event);
    if (kind !== null && kind !== 'wildfire' && kind !== 'thermal') {
      counts.all++;
      counts[kind]++;
    }
  }
  return counts;
}

export interface FiresOptions {
  thermal: boolean;
  wildfire: boolean;
}
export const DEFAULT_FIRES_OPTIONS: FiresOptions = { thermal: true, wildfire: true };

export function matchesFires(event: LiveEvent, options: FiresOptions, enabled: boolean): boolean {
  const kind = fireKind(event);
  return kind === null || (enabled && options[kind]);
}

export function countFires(events: readonly LiveEvent[]): Record<FireKind | 'all', number> {
  const counts = { all: 0, thermal: 0, wildfire: 0 };
  for (const event of events) {
    const kind = fireKind(event);
    if (kind) {
      counts.all++;
      counts[kind]++;
    }
  }
  return counts;
}

/** Compare values so selecting every checkbox again restores the default scope. */
export function hazardFiltersRefined(options: HazardOptions): boolean {
  return (
    options.groups.length !== HAZARD_GROUPS.length ||
    HAZARD_GROUPS.some(({ value }) => !options.groups.includes(value)) ||
    options.hours !== 'all' ||
    options.minimumMagnitude !== 0 ||
    options.alert !== 'all' ||
    !options.includeUnknown
  );
}
