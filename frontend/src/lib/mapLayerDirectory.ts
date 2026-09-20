/**
 * What the map can show, in one list. The guide panel, the source catalogue and the
 * command palette all read this, so a layer is described in exactly one place.
 * `panel` is the label of the existing map tool that owns the layer.
 */
export type MapLayerToggle =
  | 'conflict'
  | 'disaster'
  | 'fires'
  | 'news'
  | 'cyber'
  | 'space'
  | 'aircraft'
  | 'vessels'
  | 'cameras'
  | 'figures'
  | 'regions'
  | 'interference'
  | 'grid';

export interface MapLayerEntry {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  /** Map tool that holds this layer's filters, opened from the guide. */
  readonly panel?: string;
  /** Layer switch the guide can operate directly. */
  readonly toggle?: MapLayerToggle;
}

export interface MapLayerGroup {
  readonly title: string;
  readonly items: readonly MapLayerEntry[];
}

export const MAP_LAYER_GROUPS: readonly MapLayerGroup[] = [
  {
    title: 'Live events',
    items: [
      {
        id: 'conflict',
        label: 'Conflict & unrest',
        description: 'Reported armed clashes, strikes and unrest, placed where they were reported.',
        panel: 'Conflict reports',
        toggle: 'conflict',
      },
      {
        id: 'disaster',
        label: 'Natural hazards',
        description: 'Earthquakes, storms, floods and volcanic activity with their alert level.',
        panel: 'Natural hazards',
        toggle: 'disaster',
      },
      {
        id: 'fires',
        label: 'Fires and thermal detections',
        description: 'Satellite thermal detections and reported wildfires.',
        panel: 'Fires',
        toggle: 'fires',
      },
      {
        id: 'news',
        label: 'News and context',
        description:
          'Collected reporting, including political, humanitarian, economic and social items.',
        panel: 'News briefing',
        toggle: 'news',
      },
      {
        id: 'cyber',
        label: 'Cyber incidents',
        description: 'Outage signals, ransomware claims and exploited vulnerabilities.',
        panel: 'Cyber threat intelligence',
        toggle: 'cyber',
      },
      {
        id: 'space',
        label: 'Space',
        description: 'Stations and satellites overhead, launches and the geomagnetic picture.',
        panel: 'Space',
        toggle: 'space',
      },
      {
        id: 'aircraft',
        label: 'Flights',
        description: 'Volunteer ADS-B positions, with military and emergency filters.',
        panel: 'Flight filters',
        toggle: 'aircraft',
      },
      {
        id: 'vessels',
        label: 'Boats',
        description: 'Reported ship positions and broadcast navigation warnings.',
        panel: 'Boat list',
        toggle: 'vessels',
      },
    ],
  },
  {
    title: 'Reference layers',
    items: [
      {
        id: 'cameras',
        label: 'Public cameras',
        description: 'Public traffic and civic camera indexes, by provider.',
        panel: 'CCTV',
        toggle: 'cameras',
      },
      {
        id: 'technology',
        label: 'Technology & communications',
        description:
          'Undersea cables, satellite ground stations, data centres, semiconductor sites and connectivity signals.',
        panel: 'Technology & communications',
      },
      {
        id: 'infrastructure',
        label: 'Infrastructure',
        description: 'Nuclear facilities, oil and gas sites and the military source index.',
        panel: 'Infrastructure',
      },
      {
        id: 'figures',
        label: 'Public figures',
        description: 'Heads of state and government, placed by public reporting or at their seat.',
        panel: 'Public figures',
        toggle: 'figures',
      },
      {
        id: 'regions',
        label: 'Conflict regions',
        description: 'Regional overview markers for tracked wars and areas of tension.',
        panel: 'Conflict reports',
        toggle: 'regions',
      },
      {
        id: 'interference',
        label: 'GPS and GNSS interference',
        description: 'Reported jamming and spoofing cells, with a severity floor.',
        panel: 'Cyber threat intelligence',
        toggle: 'interference',
      },
      {
        id: 'grid',
        label: 'British National Grid',
        description: 'OSGB grid lines and references over Great Britain.',
        panel: 'British National Grid',
        toggle: 'grid',
      },
    ],
  },
  {
    title: 'Map setup',
    items: [
      {
        id: 'style',
        label: 'Map style',
        description: 'Base map, satellite imagery, Ordnance Survey styles, day and night shading.',
        panel: 'Map style',
      },
      {
        id: 'time',
        label: 'Event time',
        description: 'How far back the map reaches, from one hour to everything collected.',
        panel: 'Event time',
      },
      {
        id: 'nation',
        label: 'Find nation',
        description: 'Move to a country and scope the map to it.',
        panel: 'Find nation',
      },
      {
        id: 'quality',
        label: 'Location quality',
        description: 'Hide items that are only placed to a country or region centre.',
        panel: 'Location quality',
      },
    ],
  },
  {
    title: 'Planning tools',
    items: [
      {
        id: 'area',
        label: 'Research area',
        description: 'Save a geographic area and reuse it in research and subscriptions.',
        panel: 'Research area',
      },
      {
        id: 'draw',
        label: 'Draw on map',
        description: 'Sketch points, lines and shapes over the current view.',
        panel: 'Draw on map',
      },
      {
        id: 'route',
        label: 'Route planner',
        description: 'Plan a route and read its legs and bearings.',
        panel: 'Route planner',
      },
      {
        id: 'rf',
        label: 'RF link calculator',
        description: 'Estimate a radio link between two placed points.',
        panel: 'RF link calculator',
      },
      {
        id: 'measure',
        label: 'Measure distance and area',
        description: 'Measure along the ground and close a shape for its area.',
        panel: 'Measure distance and area',
      },
      {
        id: 'workspace',
        label: 'On this map',
        description: 'Manage saved drawings, radio studies and the objects on this map.',
        panel: 'On this map',
      },
      {
        id: 'terrain',
        label: 'Terrain profile and visibility',
        description: 'Inspect ground elevation and geometric visibility along a measured path.',
        panel: 'Terrain profile and visibility',
      },
      {
        id: 'coordinates',
        label: 'Coordinates',
        description: 'Read, convert and navigate to geographic or projected coordinates.',
        panel: 'Coordinates',
      },
      {
        id: 'nuclear-education',
        label: 'Nuclear effects (education)',
        description: 'Explore attributed educational references about humanitarian consequences.',
        panel: 'Nuclear effects (education)',
      },
    ],
  },
];

/** The guide itself, so a link can open it. */
export const MAP_GUIDE_PANEL = 'Map guide';

const PANELS: readonly string[] = [
  MAP_GUIDE_PANEL,
  ...MAP_LAYER_GROUPS.flatMap((group) =>
    group.items.flatMap((item) => (item.panel === undefined ? [] : [item.panel])),
  ),
];

/** Only labels the map actually defines may be opened from a link. */
export function isMapPanel(label: string | null): label is string {
  return label !== null && PANELS.includes(label);
}

/** Stable route identifiers remain independent of the visible tool title. */
export function mapPanelId(label: string): string | null {
  if (label === MAP_GUIDE_PANEL) return 'guide';
  return mapLayerEntries().find((entry) => entry.panel === label)?.id ?? null;
}

/** Accept old bookmarked labels as well as the canonical route identifiers. */
export function resolveMapPanel(value: string | null): string | null {
  if (value === null) return null;
  if (value === 'guide') return MAP_GUIDE_PANEL;
  if (value === 'RF coverage') return 'RF link calculator';
  if (value === 'Measure') return 'Measure distance and area';
  if (isMapPanel(value)) return value;
  return mapLayerEntries().find((entry) => entry.id === value)?.panel ?? null;
}

export function readMapPanel(params: URLSearchParams): string | null {
  return resolveMapPanel(params.get('panel'));
}

export function mapPanelHref(label: string): string {
  const panel = resolveMapPanel(label);
  return panel ? `/?panel=${encodeURIComponent(mapPanelId(panel) ?? panel)}` : '/';
}

export function mapLayerEntries(): readonly MapLayerEntry[] {
  return MAP_LAYER_GROUPS.flatMap((group) => group.items);
}
