/** Line icons for the primary rail. Purely decorative; the link text carries the name. */
import type { WorkspaceIconName } from '@/lib/workspaceNavigation';

export type RailIconName = WorkspaceIconName;

const PATHS: Record<RailIconName, string> = {
  map: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 0c-2.5 2.6-3.8 5.6-3.8 9s1.3 6.4 3.8 9m0-18c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9M3.5 9h17M3.5 15h17',
  research: 'M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Zm5 11.5L20 20M8 10.5h5M10.5 8v5',
  progress: 'M12 3.5a8.5 8.5 0 1 0 8.5 8.5M12 7.5V12l3 2M16.5 3.5h4v4',
  watches:
    'M3.5 15.5a3.5 3.5 0 1 0 7 0 3.5 3.5 0 0 0-7 0Zm10 0a3.5 3.5 0 1 0 7 0 3.5 3.5 0 0 0-7 0ZM10.5 15h3M5 12.5 7 5h2.5l.5 7M19 12.5 17 5h-2.5l-.5 7',
  reports: 'M6.5 3.5H14l4 4v13H6.5ZM14 3.5V8h4M9.5 12.5h6M9.5 16h4',
  subscriptions: 'M6 17V11a6 6 0 1 1 12 0v6l1.5 2h-15L6 17Zm4 3.5a2 2 0 0 0 4 0M12 3.5V5',
  geolocation:
    'M12 21s-6.5-6-6.5-11a6.5 6.5 0 1 1 13 0c0 5-6.5 11-6.5 11Zm0-8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z',
  plans: 'M4 7.5 9.5 5l5 2.5L20 5v11.5L14.5 19l-5-2.5L4 19ZM9.5 5v11.5M14.5 7.5V19',
  monitor: 'M3 12h4l2.5-6 3 12 2.5-6h6',
  alerts: 'M12 4.5 20.5 19.5h-17ZM12 10v4M12 16.8h.01',
  annotations: 'M4.5 5.5h15v10h-8l-4 3.5v-3.5h-3ZM8.5 10.5h7',
  economy: 'M4 19h16M5 15l4-4 3 3 4-5 3 2M17 8h3v3',
  cyber: 'M12 3 20 6.2v5.6c0 4.6-3.3 8-8 9.7-4.7-1.7-8-5.1-8-9.7V6.2L12 3Zm-3.5 9 2.4 2.4 4.6-4.9',
  sources:
    'M12 4c3.9 0 7 1.1 7 2.5S15.9 9 12 9 5 7.9 5 6.5 8.1 4 12 4ZM5 6.5v11C5 18.9 8.1 20 12 20s7-1.1 7-2.5v-11M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5',
  teams:
    'M9 11.5a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4ZM2.5 20v-1.4A5.6 5.6 0 0 1 8.1 13h1.8a5.6 5.6 0 0 1 5.6 5.6V20M16 5.8a3.2 3.2 0 0 1 0 5.8M17.6 13.3A4.6 4.6 0 0 1 21.5 18v2',
  layers: 'm12 3 8.5 4.5L12 12 3.5 7.5ZM3.5 12 12 16.5 20.5 12M3.5 16.5 12 21l8.5-4.5',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14Zm5.2 12.2L20.5 20.5',
  admin: 'M4 7h9m4 0h3M4 12h3m4 0h9M4 17h11m4 0h1M13 5v4M7 10v4M15 15v4',
  ukraine: 'M3 16c2.5-1.5 4-4 6.5-4s3.5 3 6 3 3.5-2.5 5.5-3M12 13.5V4m0 0 5 2.5L12 9m-4 12h8',
};

export function RailIcon({ name, className = '' }: { name: RailIconName; className?: string }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

export function ChevronIcon({ direction }: { direction: 'left' | 'right' }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`transition-transform duration-200 ${direction === 'right' ? 'rotate-180' : ''}`}
    >
      <path d="m14 6-6 6 6 6" />
    </svg>
  );
}
