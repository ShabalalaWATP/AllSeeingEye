/**
 * Line icons for the administration workspace, drawn in the same 24px stroke style
 * as the research rail. Always decorative: adjacent text carries the meaning.
 */
import type { AdminIconName } from '@/lib/adminNavigation';

export type AdminGlyph =
  | AdminIconName
  | 'back'
  | 'menu'
  | 'refresh'
  | 'arrow'
  | 'check'
  | 'alert'
  | 'cross'
  | 'pause'
  | 'clock'
  | 'shield'
  | 'key'
  | 'collapse'
  | 'expand'
  | 'gauge';

const PATHS: Record<AdminGlyph, string> = {
  overview: 'M4 4h7v7H4V4Zm9 0h7v4h-7V4Zm0 6h7v10h-7V10ZM4 13h7v7H4v-7Z',
  requests:
    'M4 6.5 12 12l8-5.5M4.5 5h15a.5.5 0 0 1 .5.5v13a.5.5 0 0 1-.5.5h-15a.5.5 0 0 1-.5-.5v-13a.5.5 0 0 1 .5-.5Z',
  users:
    'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm-6 9v-1a6 6 0 0 1 12 0v1m1-15.8a3.5 3.5 0 0 1 0 6.6M21 20v-1a6 6 0 0 0-3.5-5.4',
  teams:
    'M12 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-6.5 2.5a2.5 2.5 0 1 0 0-5M18.5 12.5a2.5 2.5 0 1 0 0-5M7 20v-1.5a5 5 0 0 1 10 0V20M2 19v-1a4 4 0 0 1 3.5-4M22 19v-1a4 4 0 0 0-3.5-4',
  ai: 'M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3M7 6h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1Zm3 4h4v4h-4v-4Z',
  sources:
    'M5 12.5a7 7 0 0 1 14 0M8 12.5a4 4 0 0 1 8 0M12 13.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm0 0V21M2 12.5a10 10 0 0 1 20 0',
  audit:
    'M8 4h8m-8 0a2 2 0 0 0-2 2v13a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6a2 2 0 0 0-2-2m-8 0a1.5 1.5 0 0 0 1.5 1.5h5A1.5 1.5 0 0 0 16 4M9 11h6M9 15h4',
  security:
    'M12 3 20 6.2v5.6c0 4.6-3.3 8-8 9.7-4.7-1.7-8-5.1-8-9.7V6.2L12 3Zm-2.5 8.5V10a2.5 2.5 0 0 1 5 0v1.5M9 11.5h6v4H9v-4Z',
  back: 'M19 12H5m6-6-6 6 6 6',
  menu: 'M4 6h16M4 12h16M4 18h16',
  refresh: 'M20 11a8 8 0 0 0-14.6-4.5M4 4v3.5h3.5M4 13a8 8 0 0 0 14.6 4.5M20 20v-3.5h-3.5',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  check: 'm5 12.5 4.5 4.5L19 7.5',
  alert: 'M12 4 21 19.5H3L12 4Zm0 6v4.5m0 2.5v.01',
  cross: 'M6 6l12 12M18 6 6 18',
  pause: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm-2 6v6m4-6v6',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4.5V12l3 2',
  shield: 'M12 3 20 6.2v5.6c0 4.6-3.3 8-8 9.7-4.7-1.7-8-5.1-8-9.7V6.2L12 3Zm-3.5 9 2.4 2.4 4.6-4.9',
  key: 'M14.5 4a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM10.6 13.4 3 21m3.5-3.5L9 20m-1-5 2 2m6.5-9h.01',
  collapse: 'm14 6-6 6 6 6',
  expand: 'm10 6 6 6-6 6',
  gauge: 'M4.5 17.5a8.5 8.5 0 1 1 15 0M12 13.5l3.5-3.5M12 14.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z',
};

export function AdminIcon({
  name,
  size = 20,
  className = '',
}: {
  name: AdminGlyph;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={`shrink-0 ${className}`}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
