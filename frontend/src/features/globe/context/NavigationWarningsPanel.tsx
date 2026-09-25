import { useState } from 'react';
import { useContextEvents } from './useContextEvents';
import {
  ContextShell,
  EventActions,
  attribute,
  controlClass,
  matchesQuery,
  newest,
  utcDate,
  type ContextPanelProps,
} from './contextPresentation';

const SOURCES = ['nga_navarea'] as const;
const KINDS: Record<string, string> = {
  security: 'Security',
  gnss: 'GNSS / interference',
  military_exercise: 'Exercises / firing',
  hazard: 'Navigation hazards',
  navigation: 'General navigation',
};

export function NavigationWarningsPanel({ country, onSelect }: ContextPanelProps) {
  const snapshot = useContextEvents(SOURCES);
  const [query, setQuery] = useState('');
  const [area, setArea] = useState('all');
  const [kind, setKind] = useState('all');
  const areas = [...new Set(snapshot.events.map((event) => attribute(event, 'nav_area')))];
  const events = newest(snapshot.events).filter(
    (event) =>
      matchesQuery(event, query) &&
      (area === 'all' || attribute(event, 'nav_area') === area) &&
      (kind === 'all' || attribute(event, 'kind') === kind),
  );
  return (
    <ContextShell
      title="Navigation warnings"
      snapshot={snapshot}
      scope={`Worldwide NAVAREA / HYDROARC broadcasts relayed by NGA.${country ? ` The ${country} nation filter does not apply to maritime warning areas.` : ''}`}
    >
      <p className="rounded-lg border border-line bg-white/[0.03] p-3 text-[11px] leading-relaxed text-muted">
        The feed requests active broadcasts, but this is a dated snapshot. Read the source for
        validity and cancellations. A map marker is the first reported position, not an
        exclusion-zone boundary or the centre of a warning area.
      </p>
      <label className="block space-y-1 text-muted">
        Search warning text or authority
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className={controlClass}
          placeholder="Warning number, authority, place…"
        />
      </label>
      <div className="grid grid-cols-2 gap-2">
        <label className="block space-y-1 text-muted">
          NAVAREA
          <select
            value={area}
            onChange={(event) => setArea(event.target.value)}
            className={controlClass}
          >
            <option value="all">All areas</option>
            {areas.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-1 text-muted">
          Topic match
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value)}
            className={controlClass}
          >
            <option value="all">All topics</option>
            {Object.entries(KINDS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="text-2xs leading-relaxed text-muted">
        Topics are keyword matches, not official classifications. A GNSS match is a warning report,
        not a measured jamming footprint.
      </p>
      <p className="text-2xs text-muted">
        {Math.min(25, events.length)} of {events.length} matching collected warnings
      </p>
      {!snapshot.loading && events.length === 0 && (
        <p className="text-muted">No matching navigation warnings in this snapshot.</p>
      )}
      <ul className="space-y-2">
        {events.slice(0, 25).map((event) => (
          <li key={event.id} className="rounded-lg border border-line p-3">
            <h4 className="font-medium leading-relaxed text-text">{event.title}</h4>
            <p className="mt-1 text-2xs text-muted">Issued: {utcDate(event.published_at)}</p>
            <p className="mt-2 text-[11px] text-muted">
              Authority: {attribute(event, 'authority')} · Source status:{' '}
              {attribute(event, 'status')}
            </p>
            <p className="mt-1 text-[11px] text-muted">
              Reported positions: {attribute(event, 'positions')}
              {event.point ? '. Only the first position is mapped.' : '. No parsed map position.'}
            </p>
            <EventActions event={event} onSelect={onSelect} locate />
          </li>
        ))}
      </ul>
    </ContextShell>
  );
}
