/** Line icons for the primary rail. Purely decorative; the link text carries the name. */
export type RailIconName =
  | 'map'
  | 'research'
  | 'subscriptions'
  | 'geolocation'
  | 'economy'
  | 'cyber'
  | 'ukraine'
  | 'admin';

const PATHS: Record<RailIconName, string> = {
  map: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 0c-2.5 2.6-3.8 5.6-3.8 9s1.3 6.4 3.8 9m0-18c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9M3.5 9h17M3.5 15h17',
  research: 'M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Zm5 11.5L20 20M8 10.5h5M10.5 8v5',
  subscriptions: 'M6 17V11a6 6 0 1 1 12 0v6l1.5 2h-15L6 17Zm4 3.5a2 2 0 0 0 4 0M12 3.5V5',
  geolocation:
    'M12 21s-6.5-6-6.5-11a6.5 6.5 0 1 1 13 0c0 5-6.5 11-6.5 11Zm0-8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z',
  economy: 'M4 19h16M5 15l4-4 3 3 4-5 3 2M17 8h3v3',
  cyber: 'M12 3 20 6.2v5.6c0 4.6-3.3 8-8 9.7-4.7-1.7-8-5.1-8-9.7V6.2L12 3Zm-3.5 9 2.4 2.4 4.6-4.9',
  admin: 'M4 7h9m4 0h3M4 12h3m4 0h9M4 17h11m4 0h1M13 5v4M7 10v4M15 15v4',
  ukraine:
    'M3 16c2.5-1.5 4-4 6.5-4s3.5 3 6 3 3.5-2.5 5.5-3M12 13.5V4m0 0 5 2.5L12 9m-4 12h8',
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
