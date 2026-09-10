import type { NavigationRequest } from '@/lib/api/navigation';

type TravelMode = NavigationRequest['mode'];
const MODES: { value: TravelMode; label: string }[] = [
  { value: 'driving', label: 'Driving' },
  { value: 'walking', label: 'Walking' },
  { value: 'cycling', label: 'Cycling' },
];

function TravelIcon({ mode }: { mode: TravelMode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {mode === 'driving' ? (
        <>
          <path d="m5 9 2-5h10l2 5M5 17H3V9h18v8h-2M7 17h10M5 17v3h2v-3m10 0v3h2v-3M3 12h18" />
          <path d="M6 14h2m8 0h2" />
        </>
      ) : mode === 'walking' ? (
        <>
          <circle cx="13" cy="4" r="2" />
          <path d="m7 11 4-4 4 2 3 3m-7-5-1 7 5 3 1 5m-6-8-3 8" />
        </>
      ) : (
        <>
          <circle cx="5" cy="17" r="4" />
          <circle cx="19" cy="17" r="4" />
          <path d="m5 17 5-9 5 9H5m5-9h7l2 9M9 5h4m3 0h3l-2 3" />
        </>
      )}
    </svg>
  );
}

export function RouteTravelMode({
  value,
  onChange,
}: {
  value: TravelMode;
  onChange: (value: TravelMode) => void;
}) {
  return (
    <fieldset className="route-mode-section">
      <legend className="map-tool-section-title">Travel mode</legend>
      <div className="map-tool-choice-grid route-travel-modes">
        {MODES.map((mode) => (
          <button
            key={mode.value}
            type="button"
            className="map-tool-choice"
            aria-pressed={value === mode.value}
            onClick={() => onChange(mode.value)}
          >
            <TravelIcon mode={mode.value} />
            <span>{mode.label}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}
