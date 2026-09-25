import { useState } from 'react';
import { useContextEvents } from './useContextEvents';
import {
  ContextShell,
  EventActions,
  actionClass,
  controlClass,
  matchesQuery,
  newest,
  utcDate,
  type ContextPanelProps,
} from './contextPresentation';

const SOURCES = ['noaa_swpc_scales', 'swpc_kp', 'noaa_swpc_alerts'] as const;
const SCALES = [
  { key: 'r', label: 'Radio blackouts' },
  { key: 's', label: 'Solar radiation storms' },
  { key: 'g', label: 'Geomagnetic storms' },
] as const;

export function SpaceWeatherPanel({ country, onSelect }: ContextPanelProps) {
  const snapshot = useContextEvents(SOURCES);
  const [query, setQuery] = useState('');
  const events = newest(snapshot.events);
  const scales = events.find((event) => event.source_id === 'noaa_swpc_scales');
  const kp = events.find((event) => event.source_id === 'swpc_kp');
  const kpValue = kp?.attributes.kp;
  const bulletins = events.filter(
    (event) => event.source_id === 'noaa_swpc_alerts' && matchesQuery(event, query),
  );
  return (
    <ContextShell
      title="Space weather"
      snapshot={snapshot}
      scope={`Worldwide NOAA observations and bulletins. These are global indices${country ? `; the ${country} nation filter does not apply` : ', not location-specific measurements'}.`}
    >
      <div className="grid grid-cols-3 gap-2">
        {SCALES.map(({ key, label }) => {
          const value = scales?.attributes[key];
          const known =
            (typeof value === 'string' || typeof value === 'number') &&
            /^[0-5]$/.test(String(value));
          return (
            <div key={key} className="rounded-lg border border-cyan-300/15 bg-cyan-300/[0.04] p-2">
              <p className="text-2xs leading-snug text-muted">{label}</p>
              <p className="mt-2 font-mono text-xl text-cyan">
                {known ? `${key.toUpperCase()}${value}` : 'Unknown'}
              </p>
            </div>
          );
        })}
      </div>
      <p className="text-2xs text-muted">
        Scales issued: {utcDate(scales?.attributes.stamp)}. Reported levels, not inferred from Kp.
      </p>
      <div className="rounded-lg border border-line p-3">
        <p className="font-medium text-text">
          Planetary Kp{' '}
          <span className="ml-2 font-mono text-lg text-cyan">
            {typeof kpValue === 'number' && Number.isFinite(kpValue) && kpValue >= 0 && kpValue <= 9
              ? kpValue.toFixed(2)
              : 'Unknown'}
          </span>
        </p>
        <p className="mt-1 text-2xs text-muted">
          Three-hour index. Observation: {utcDate(kp?.attributes.time_tag)}.
        </p>
      </div>
      <p className="text-[11px] leading-relaxed text-muted">
        These measurements do not establish local GPS jamming, HF coverage or a forecast. Check the
        dated bulletin for its stated validity and cancellations.
      </p>
      <a
        href="https://www.spaceweather.gov/noaa-scales-explanation"
        target="_blank"
        rel="noopener noreferrer"
        className={actionClass}
      >
        Understand the NOAA R / S / G scales
      </a>
      <label className="block space-y-1 text-muted">
        Search NOAA bulletins
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className={controlClass}
          placeholder="Watch, warning, cancellation…"
        />
      </label>
      <p className="text-2xs text-muted">
        {Math.min(25, bulletins.length)} of {bulletins.length} matching collected bulletins
      </p>
      {!snapshot.loading && bulletins.length === 0 && (
        <p className="text-muted">No matching bulletins in this snapshot.</p>
      )}
      <ul className="space-y-2">
        {bulletins.slice(0, 25).map((event) => (
          <li key={event.id} className="rounded-lg border border-line p-3">
            <h4 className="font-medium leading-relaxed text-text">{event.title}</h4>
            <p className="mt-1 text-2xs text-muted">Issued: {utcDate(event.published_at)}</p>
            <EventActions event={event} onSelect={onSelect} />
          </li>
        ))}
      </ul>
    </ContextShell>
  );
}
