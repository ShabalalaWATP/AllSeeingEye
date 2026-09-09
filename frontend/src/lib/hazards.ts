import type { LiveEvent } from '@/lib/api/eventSchemas';

export const HAZARD_GROUPS = [
  { value: 'all', label: 'All natural hazards' },
  { value: 'earthquake', label: 'Earthquakes' },
  { value: 'weather', label: 'Severe weather / cyclones' },
  { value: 'flood', label: 'Floods' },
  { value: 'volcano', label: 'Volcanoes' },
  { value: 'fires', label: 'Fires' },
  { value: 'wildfire', label: 'Wildfire alerts' },
  { value: 'thermal', label: 'Satellite thermal detections' },
  { value: 'tsunami', label: 'Tsunamis' },
  { value: 'drought', label: 'Drought' },
  { value: 'landslide', label: 'Landslides' },
  { value: 'ice', label: 'Sea and lake ice' },
  { value: 'other', label: 'Other / unclassified' },
] as const;
export type HazardGroup = (typeof HAZARD_GROUPS)[number]['value'];
export type HazardKind = Exclude<HazardGroup, 'all' | 'fires'>;
export type HazardWindow = 'all' | '24' | '72' | '168';
export type HazardAlert = 'all' | 'orange_red' | 'red';
export interface HazardOptions {
  group: HazardGroup;
  hours: HazardWindow;
  minimumMagnitude: number;
  alert: HazardAlert;
  includeUnknown: boolean;
}
export const DEFAULT_HAZARD_OPTIONS: HazardOptions = {
  group: 'all',
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

/** Composite display groups do not change a source's event classification. */
export function matchesHazardGroup(event: LiveEvent, group: HazardGroup): boolean {
  const kind = hazardKind(event);
  if (kind === null || group === 'all') return true;
  return group === 'fires' ? kind === 'wildfire' || kind === 'thermal' : group === kind;
}

export function matchesHazard(event: LiveEvent, options: HazardOptions, now: number): boolean {
  const kind = hazardKind(event);
  if (kind === null) return true;
  if (!matchesHazardGroup(event, options.group)) return false;
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

export function countHazards(events: LiveEvent[]): Record<HazardGroup, number> {
  const counts = Object.fromEntries(HAZARD_GROUPS.map(({ value }) => [value, 0])) as Record<
    HazardGroup,
    number
  >;
  for (const event of events) {
    const kind = hazardKind(event);
    if (kind !== null) {
      counts.all++;
      counts[kind]++;
      if (kind === 'wildfire' || kind === 'thermal') counts.fires++;
    }
  }
  return counts;
}
