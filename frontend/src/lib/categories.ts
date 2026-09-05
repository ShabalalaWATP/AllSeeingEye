/** Category labels and colours shared by map layers, legends and event lists. */
import type { Category } from './api/eventSchemas';

export interface CategoryStyle {
  label: string;
  colour: [number, number, number];
  css: string;
  order: number;
}

export const CATEGORY_STYLES: Record<Category, CategoryStyle> = {
  disaster: { label: 'Disasters', colour: [255, 111, 55], css: '#ff6f37', order: 0 },
  conflict: { label: 'Conflict', colour: [255, 90, 90], css: '#ff5a5a', order: 1 },
  news: { label: 'News', colour: [233, 228, 220], css: '#e9e4dc', order: 2 },
  aviation: { label: 'Aviation', colour: [245, 181, 63], css: '#f5b53f', order: 3 },
  maritime: { label: 'Maritime', colour: [92, 211, 155], css: '#5cd39b', order: 4 },
  space: { label: 'Space', colour: [167, 139, 250], css: '#a78bfa', order: 5 },
  cyber: { label: 'Cyber', colour: [34, 211, 238], css: '#22d3ee', order: 6 },
  social: { label: 'Social', colour: [244, 114, 182], css: '#f472b6', order: 7 },
  political: { label: 'Political', colour: [148, 163, 184], css: '#94a3b8', order: 8 },
  humanitarian: { label: 'Humanitarian', colour: [251, 191, 36], css: '#fbbf24', order: 9 },
  economic: { label: 'Economic', colour: [110, 231, 183], css: '#6ee7b7', order: 10 },
};

export const ORDERED_CATEGORIES = (Object.keys(CATEGORY_STYLES) as Category[]).sort(
  (a, b) => CATEGORY_STYLES[a].order - CATEGORY_STYLES[b].order,
);
