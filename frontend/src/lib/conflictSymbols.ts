import type { ConflictKind } from './conflicts';

/** Fixed 24px stroke symbols. Colour supports the shape, never carries meaning alone. */
export const CONFLICT_SYMBOLS: Record<
  ConflictKind,
  {
    path: string;
    colour: readonly [number, number, number];
    css: string;
  }
> = {
  armed_clashes: {
    path: 'M3 3l5 1 10 10-4 4L4 8Zm18 0-5 1L6 14l4 4L20 8ZM12 19l7-7M5 12l7 7M16 16l5 5M8 16l-5 5M19 22l3-3M2 19l3 3',
    colour: [248, 113, 113],
    css: '#f87171',
  },
  organised_violence: {
    path: 'm12 2 9 5v5c0 5-5 8-9 10-4-2-9-5-9-10V7Zm0 5v7m0 3h.01',
    colour: [251, 113, 133],
    css: '#fb7185',
  },
  strikes: {
    path: 'm12 2 2 6 6-3-3 6 5 2-6 2 3 6-6-3-3 4-1-6-6 1 4-5-4-4 7 1Z',
    colour: [251, 146, 60],
    css: '#fb923c',
  },
  civilian_harm: {
    path: 'M12 2 3 6v6c0 5 5 8 9 10 4-2 9-5 9-10V6ZM9 9a3 3 0 1 0 6 0 3 3 0 0 0-6 0m-2 9v-1a5 5 0 0 1 10 0v1',
    colour: [244, 114, 182],
    css: '#f472b6',
  },
  protests: {
    path: 'M3 3h18v12H3Zm9 12v7M7 7h10M7 11h7',
    colour: [56, 189, 248],
    css: '#38bdf8',
  },
  riots: {
    path: 'm12 2 10 19H2Zm1 5-5 7h4l-1 5 6-8h-4Z',
    colour: [251, 191, 36],
    css: '#fbbf24',
  },
  unrest: {
    path: 'M5 5h14v14H5ZM9 9a3 3 0 0 1 6 0c0 2-3 2-3 4m0 3h.01',
    colour: [167, 139, 250],
    css: '#a78bfa',
  },
  military_activity: {
    path: 'M5 22V3m0 0h14l-3 5 3 5H5',
    colour: [163, 230, 53],
    css: '#a3e635',
  },
  other: {
    path: 'm12 2 10 10-10 10L2 12Zm0 5v7m0 3h.01',
    colour: [148, 163, 184],
    css: '#94a3b8',
  },
};

export const CONFLICT_ICON_SHAPES = Object.fromEntries(
  Object.entries(CONFLICT_SYMBOLS).map(([kind, symbol]) => [
    kind,
    `<g transform="scale(2.666667)"><path d="${symbol.path}" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>`,
  ]),
) as Record<ConflictKind, string>;
