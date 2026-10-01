/**
 * A named live view holds view configuration only: layer switches, filter choices, the
 * time window, the nation filter, the projection, the camera and an optional collection
 * plan filter by ID. It never carries events, geometry or model output. The server
 * rejects unknown ids on save; a reader drops ids retired since and names each one.
 */
import { z } from 'zod';

import { CATEGORIES } from '@/lib/api/eventSchemas';
import type { BaseLayer } from '@/lib/map/baseLayers';

export const LIVE_BASE_LAYERS: readonly BaseLayer[] = [
  'dark',
  'streets',
  'light',
  'satellite',
  'hybrid',
  'os_road',
  'os_outdoor',
  'os_light',
];
export const TRAFFIC_LAYERS = ['aircraft', 'vessels', 'firms'] as const;
export const OVERLAY_LAYERS = ['fires', 'interference', 'terminator'] as const;
export const LIVE_LAYER_IDS: readonly string[] = [
  ...CATEGORIES,
  ...TRAFFIC_LAYERS,
  ...OVERLAY_LAYERS,
];

const CHOICES = {
  quality: ['all', 'reported', 'approximate', 'propagated', 'unplotted'],
  flight: ['all', 'military'],
  vessel: ['all', 'military'],
  gnss_level: ['all', 'red'],
  gnss_minimum: [5, 10, 25, 50],
  cyber_kind: [
    'all',
    'ransomware_claim',
    'outage_signal',
    'known_exploited_vulnerability',
    'advisory',
    'threat_report',
    'news_report',
    'other',
  ],
  conflict_group: [
    'all',
    'armed_clashes',
    'organised_violence',
    'strikes',
    'civilian_harm',
    'protests',
    'riots',
    'unrest',
    'military_activity',
    'other',
  ],
  conflict_precision: ['all', 'exact', 'approximate'],
} as const;
const BOOLEANS = ['conflict_historical', 'conflict_unreviewed'] as const;

type Choices = typeof CHOICES;
export type LiveViewFilters = { -readonly [K in keyof Choices]?: Choices[K][number] } & {
  conflict_historical?: boolean;
  conflict_unreviewed?: boolean;
  cyber_query?: string;
};

export interface LiveViewCamera {
  center: [number, number];
  zoom: number;
  bearing: number;
  pitch: number;
}

export interface LiveViewState {
  version: 1;
  projection: 'globe' | 'map';
  camera: LiveViewCamera;
  /** Null when a saved base map has been retired: the current one is kept. */
  base_layer: BaseLayer | null;
  layers: string[];
  window_hours: number | null;
  nation: string | null;
  filters: LiveViewFilters;
  plan_id: string | null;
}

const number = (min: number, max: number) => z.number().min(min).max(max);
const envelope = z.object({
  version: z.literal(1),
  projection: z.enum(['globe', 'map']),
  camera: z.object({
    center: z.tuple([number(-180, 180), number(-90, 90)]),
    zoom: number(0, 22),
    bearing: number(-180, 180),
    pitch: number(0, 85),
  }),
  base_layer: z.string(),
  layers: z.array(z.string()).max(64),
  window_hours: z.number().positive().max(8760).nullable(),
  nation: z
    .string()
    .regex(/^[A-Z]{2,3}$/)
    .nullable(),
  filters: z.record(z.string(), z.unknown()),
  plan_id: z.uuid().nullable(),
});

const isChoice = (key: string): key is keyof Choices => key in CHOICES;
const isBoolean = (key: string): key is (typeof BOOLEANS)[number] =>
  (BOOLEANS as readonly string[]).includes(key);

/** Read a stored view, dropping retired layers and filters rather than failing. */
export function readLiveView(payload: unknown): { view: LiveViewState; dropped: string[] } {
  const parsed = envelope.safeParse(payload);
  if (!parsed.success) throw new Error('This saved view cannot be opened.');
  const value = parsed.data;
  const dropped: string[] = [];
  const layers: string[] = [];
  for (const layer of value.layers) {
    if (!LIVE_LAYER_IDS.includes(layer)) dropped.push(`layer ${layer}`);
    else if (!layers.includes(layer)) layers.push(layer);
  }
  const base = LIVE_BASE_LAYERS.find((layer) => layer === value.base_layer) ?? null;
  if (base === null) dropped.push(`base map ${value.base_layer}`);
  const filters: LiveViewFilters = {};
  for (const [key, item] of Object.entries(value.filters)) {
    const valid = isChoice(key)
      ? (CHOICES[key] as readonly unknown[]).includes(item)
      : isBoolean(key)
        ? typeof item === 'boolean'
        : key === 'cyber_query' && typeof item === 'string' && item.length <= 100;
    if (valid) Object.assign(filters, { [key]: item });
    else dropped.push(`filter ${key}`);
  }
  return {
    view: { ...value, base_layer: base, layers, filters },
    dropped,
  };
}
