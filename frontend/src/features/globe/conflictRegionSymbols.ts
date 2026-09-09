import { CONFLICT_SYMBOLS } from '@/lib/conflictSymbols';

const paths = {
  war: CONFLICT_SYMBOLS.armed_clashes.path,
  tension: 'M12 3 21 7v5c0 5-5 8-9 10-4-2-9-5-9-10V7l9-4Zm0 5v5m0 4v.1',
};

/** Cached SVG masks, sharing the war glyph with the category rail and incident legend. */
export const CONFLICT_REGION_MARKERS = Object.fromEntries(
  Object.entries(paths).map(([status, path]) => [
    status,
    'data:image/svg+xml,' +
      encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24"><path d="${path}" stroke="white" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" fill="none"/></svg>`,
      ),
  ]),
) as Record<keyof typeof paths, string>;
