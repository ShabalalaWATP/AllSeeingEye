/**
 * Dated daily imagery from NASA Global Imagery Browse Services (GIBS). Only a fixed
 * allowlist of corrected-reflectance layers is offered, and the only caller-supplied
 * part of a tile URL is a validated ISO date inside that product's published range.
 * Tiles load directly from the GIBS origin, which the production CSP admits.
 */
import type { Map as MapLibreMap, RasterSourceSpecification } from 'maplibre-gl';

export const GIBS_ORIGIN = 'https://gibs.earthdata.nasa.gov';
export const DAILY_IMAGERY_SOURCE_ID = 'ase-daily-imagery';
export const DAILY_IMAGERY_LAYER_ID = 'ase-daily-imagery';
/** The 250 m products publish GoogleMapsCompatible_Level9; MapLibre overzooms beyond it. */
export const DAILY_IMAGERY_MAX_ZOOM = 9;
export const DAILY_IMAGERY_ATTRIBUTION =
  'Imagery from <a href="https://www.earthdata.nasa.gov/gibs">NASA GIBS</a>, ' +
  'part of NASA ESDIS (EOSDIS)';

export interface DailyImageryProduct {
  readonly id: DailyImageryProductId;
  readonly label: string;
  readonly layer: string;
  /** First date GIBS publishes for this layer, inclusive. */
  readonly start: string;
}

export type DailyImageryProductId = 'modis_terra' | 'modis_aqua' | 'viirs_snpp';

export const DAILY_IMAGERY_PRODUCTS: readonly DailyImageryProduct[] = [
  {
    id: 'modis_terra',
    label: 'MODIS Terra true colour (morning pass)',
    layer: 'MODIS_Terra_CorrectedReflectance_TrueColor',
    start: '2000-02-24',
  },
  {
    id: 'modis_aqua',
    label: 'MODIS Aqua true colour (afternoon pass)',
    layer: 'MODIS_Aqua_CorrectedReflectance_TrueColor',
    start: '2002-07-04',
  },
  {
    id: 'viirs_snpp',
    label: 'VIIRS Suomi NPP true colour (afternoon pass)',
    layer: 'VIIRS_SNPP_CorrectedReflectance_TrueColor',
    start: '2015-11-24',
  },
];

export interface DailyImagery {
  product: DailyImageryProductId;
  /** Calendar date in UTC, YYYY-MM-DD. */
  date: string;
}

const DAY_MS = 86_400_000;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function utcDate(time: number): string {
  return new Date(time).toISOString().slice(0, 10);
}

export function dailyImageryProduct(id: DailyImageryProductId): DailyImageryProduct | null {
  return DAILY_IMAGERY_PRODUCTS.find((product) => product.id === id) ?? null;
}

/** Yesterday in UTC: today's swaths are still arriving, so yesterday is complete. */
export function defaultDailyImageryDate(now: number): string {
  return utcDate(now - DAY_MS);
}

export function dailyImageryDateRange(
  id: DailyImageryProductId,
  now: number,
): { min: string; max: string } {
  return { min: dailyImageryProduct(id)?.start ?? utcDate(now), max: utcDate(now) };
}

/** The imagery to draw, or null unless the product is allowlisted and the date is real and in range. */
export function validDailyImagery(
  id: DailyImageryProductId,
  date: string,
  now: number,
): DailyImagery | null {
  const product = dailyImageryProduct(id);
  if (product === null || !ISO_DATE.test(date)) return null;
  const parsed = Date.parse(`${date}T00:00:00Z`);
  // Rejects impossible days such as 30 February, which Date would roll forward.
  if (!Number.isFinite(parsed) || utcDate(parsed) !== date) return null;
  const { min, max } = dailyImageryDateRange(id, now);
  if (date < min || date > max) return null;
  return { product: product.id, date };
}

export function dailyImageryTiles(imagery: DailyImagery, now: number): string | null {
  const valid = validDailyImagery(imagery.product, imagery.date, now);
  const product = valid && dailyImageryProduct(valid.product);
  if (!valid || !product) return null;
  return (
    `${GIBS_ORIGIN}/wmts/epsg3857/best/${product.layer}/default/${valid.date}` +
    '/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg'
  );
}

export function dailyImagerySource(
  imagery: DailyImagery,
  now: number,
): RasterSourceSpecification | null {
  const tiles = dailyImageryTiles(imagery, now);
  if (tiles === null) return null;
  return {
    type: 'raster',
    tiles: [tiles],
    tileSize: 256,
    maxzoom: DAILY_IMAGERY_MAX_ZOOM,
    attribution: DAILY_IMAGERY_ATTRIBUTION,
  };
}

/**
 * Replaces the imagery layer above the base raster and beneath borders and labels.
 * Call after the base raster is applied so the order holds on every style change.
 */
export function applyDailyImagery(
  map: MapLibreMap,
  imagery: DailyImagery | null,
  now: number = Date.now(),
): void {
  if (map.getLayer(DAILY_IMAGERY_LAYER_ID) !== undefined) map.removeLayer(DAILY_IMAGERY_LAYER_ID);
  if (map.getSource(DAILY_IMAGERY_SOURCE_ID) !== undefined) {
    map.removeSource(DAILY_IMAGERY_SOURCE_ID);
  }
  const source = imagery === null ? null : dailyImagerySource(imagery, now);
  if (source === null) return;
  map.addSource(DAILY_IMAGERY_SOURCE_ID, source);
  const above = map
    .getStyle()
    .layers.find((layer) => layer.type === 'line' || layer.type === 'symbol');
  map.addLayer(
    { id: DAILY_IMAGERY_LAYER_ID, type: 'raster', source: DAILY_IMAGERY_SOURCE_ID },
    above?.id,
  );
}

/** MapLibre tile errors carry the failing source id; only this layer's failures count. */
export function isDailyImageryError(payload: unknown): boolean {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    (payload as { sourceId?: unknown }).sourceId === DAILY_IMAGERY_SOURCE_ID
  );
}
