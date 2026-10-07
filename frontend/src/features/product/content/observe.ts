/**
 * What the Observe chapter says about each map layer. Labels and descriptions come
 * from the app's own layer directory (lib/mapLayerDirectory); this module adds the
 * filters each layer offers and the colour its dots use, mirrored from the globe's
 * filter panels. productContent.test.ts fails if a directory layer has no entry here.
 */
import { CATEGORY_STYLES } from '@/lib/categories';
import { MAP_LAYER_GROUPS, type MapLayerEntry } from '@/lib/mapLayerDirectory';

export interface LayerStory {
  colour: string;
  filters: readonly string[];
}

export const LAYER_STORIES: Readonly<Record<string, LayerStory>> = {
  conflict: {
    colour: CATEGORY_STYLES.conflict.css,
    filters: [
      'Armed clashes',
      'Strikes and explosions',
      'Violence against civilians',
      'Protests and riots',
      'Military activity',
      'Historical baseline',
      'Location precision',
    ],
  },
  disaster: {
    colour: CATEGORY_STYLES.disaster.css,
    filters: [
      'Earthquakes by magnitude',
      'Cyclones and severe weather',
      'Floods',
      'Volcanoes',
      'Tsunamis',
      'GDACS alert level',
    ],
  },
  fires: { colour: '#ffb15a', filters: ['Satellite thermal detections', 'Reported wildfires'] },
  news: {
    colour: CATEGORY_STYLES.news.css,
    filters: ['General news', 'Politics and policy', 'Humanitarian', 'Economy', 'Publisher'],
  },
  cyber: {
    colour: CATEGORY_STYLES.cyber.css,
    filters: [
      'Ransomware claims',
      'Connectivity signals',
      'Known exploited vulnerabilities',
      'Security advisories',
      'Threat reports',
    ],
  },
  space: {
    colour: CATEGORY_STYLES.space.css,
    filters: ['Stations and crewed vehicles', 'Public military catalogue', 'Space weather'],
  },
  aircraft: {
    colour: CATEGORY_STYLES.aviation.css,
    filters: ['All or military', 'Airborne or on ground', 'Source'],
  },
  vessels: {
    colour: CATEGORY_STYLES.maritime.css,
    filters: ['All or military vessels', 'Navigation warnings', 'Search'],
  },
  cameras: { colour: '#62debe', filters: ['Streams', 'Clips', 'Snapshots', 'Provider links'] },
  technology: {
    colour: '#7ddaec',
    filters: ['Undersea cables', 'Ground stations', 'Data centres', 'Semiconductor sites'],
  },
  infrastructure: {
    colour: '#fbbf24',
    filters: ['Nuclear power', 'Oil and gas', 'Military source index'],
  },
  figures: { colour: '#f5c462', filters: ['Heads of state', 'Heads of government'] },
  regions: { colour: '#ff6a6a', filters: ['Wars', 'Tensions'] },
  interference: {
    colour: '#f5b53f',
    filters: ['Jamming and spoofing cells', 'Red only', 'Minimum observations'],
  },
  grid: { colour: '#9aa3b2', filters: ['Ordnance Survey grid references'] },
};

function group(title: string): readonly MapLayerEntry[] {
  return MAP_LAYER_GROUPS.find((entry) => entry.title === title)?.items ?? [];
}

/** Live layers first, then reference layers: the order the globe reveals them. */
export const STORY_LAYERS: readonly MapLayerEntry[] = [
  ...group('Live events'),
  ...group('Reference layers'),
];

export const LIVE_LAYER_COUNT = group('Live events').length;

export const MAP_TOOLS: readonly MapLayerEntry[] = [
  ...group('Map setup'),
  ...group('Planning tools'),
];

export const GLOBAL_FILTERS: readonly { label: string; values: readonly string[] }[] = [
  {
    label: 'Event time',
    values: ['1 h', '6 h', '24 h', '72 h', '7 d', 'All', 'Hour by hour replay'],
  },
  {
    label: 'Location quality',
    values: ['Source-reported exact', 'Approximate', 'Propagated satellite', 'Not plotted'],
  },
  { label: 'Focus', values: ['Find nation', 'Collection plan requirements', 'Research area'] },
  { label: 'View', values: ['3D globe', '2D map', 'Daily NASA imagery', 'Day and night'] },
];
