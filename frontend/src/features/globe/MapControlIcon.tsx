export type ControlIcon =
  | 'aircraft'
  | 'vessels'
  | 'firms'
  | 'camera'
  | 'space'
  | 'disaster'
  | 'conflict'
  | 'news'
  | 'night'
  | 'signal'
  | 'layers'
  | 'measure'
  | 'filter'
  | 'nation'
  | 'settings'
  | 'precision'
  | 'grid'
  | 'close';
const paths: Record<ControlIcon, string> = {
  aircraft:
    'M12 2c1 0 1.5 1 1.5 2v4l7.5 5v2l-7.5-2v5l2.5 2v1l-4-1-4 1v-1l2.5-2v-5L3 15v-2l7.5-5V4c0-1 .5-2 1.5-2Z',
  vessels: 'M3 13h18l-3 6H6l-3-6Zm4 0V7h10v6M10 7V3h4v4M2 22q2-3 5 0 2-3 5 0 2-3 5 0 2-3 5 0',
  firms: 'M12 2c2 5-3 6-1 10 2-1 3-3 4-5 8 8 4 15-3 15S1 15 7 9c0 4 2 5 2 5-1-5 3-6 3-12Z',
  camera: 'm3 4 17 5-3 8-14-4V4Zm14 13 4 1 2-5-4-1M8 15v5H3m0-3v6',
  space: 'm9 9 6 6 4-4-6-6-4 4Zm-6 3 5 5-3 3-5-5 3-3Zm13-12 5 5-3 3-5-5 3-3ZM8 16l-4 4M16 16l4 4',
  disaster: 'm12 3 10 18H2L12 3Zm0 6v5m0 3v1',
  conflict: 'm5 3 16 16-2 2L3 5V3h2Zm14 0h2v2l-7 7M3 21l7-7M3 16l5 5m8-18 5 5',
  news: 'M4 3h16v18H4V3Zm4 4h8M8 11h8m-8 4h3m2 0h3',
  night: 'M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11Z',
  signal: 'M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14M8 8a6 6 0 0 0 0 8m8-8a6 6 0 0 1 0 8M12 11v2',
  layers: 'm12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5',
  measure: 'm3 16 13-13 5 5L8 21l-5-5Zm5-5 3 3m1-7 3 3m1-7 3 3',
  filter: 'M3 4h18l-7 9v7l-4-2v-5L3 4Z',
  nation: 'M3 21V3m0 1c6-5 12 5 18 0v11c-6 5-12-5-18 0',
  settings: 'M4 5h16M4 12h16M4 19h16M8 2v6m8 1v6m-6 1v6',
  precision: 'M12 2v4m0 12v4M2 12h4m12 0h4M19 12a7 7 0 1 1-14 0 7 7 0 0 1 14 0Zm-7-1v2',
  grid: 'M3 3h18v18H3V3Zm6 0v18m6-18v18M3 9h18M3 15h18',
  close: 'm6 6 12 12M6 18 18 6',
};
export function MapControlIcon({ name }: { name: ControlIcon }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-5 shrink-0"
    >
      <path d={paths[name]} />
    </svg>
  );
}
