/**
 * Six fixed categorical slots. Colour follows the entity, never its rank, and a series
 * beyond the sixth folds into the muted "other" treatment rather than a new hue.
 */
export type ChartSlot = 1 | 2 | 3 | 4 | 5 | 6 | 'muted';

export const SLOT_FILL: Record<ChartSlot, string> = {
  1: 'fill-chart-1',
  2: 'fill-chart-2',
  3: 'fill-chart-3',
  4: 'fill-chart-4',
  5: 'fill-chart-5',
  6: 'fill-chart-6',
  muted: 'fill-muted/60',
};

export const SLOT_STROKE: Record<ChartSlot, string> = {
  1: 'stroke-chart-1',
  2: 'stroke-chart-2',
  3: 'stroke-chart-3',
  4: 'stroke-chart-4',
  5: 'stroke-chart-5',
  6: 'stroke-chart-6',
  muted: 'stroke-muted/60',
};

export const SLOT_BG: Record<ChartSlot, string> = {
  1: 'bg-chart-1',
  2: 'bg-chart-2',
  3: 'bg-chart-3',
  4: 'bg-chart-4',
  5: 'bg-chart-5',
  6: 'bg-chart-6',
  muted: 'bg-muted/60',
};

// Use consistent K/M/B/T chart suffixes; en-GB CLDR versions vary (k/bn/tn).
export const compactNumber = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

export function formatCount(value: number): string {
  return value >= 10_000 ? compactNumber.format(value) : value.toLocaleString('en-GB');
}
