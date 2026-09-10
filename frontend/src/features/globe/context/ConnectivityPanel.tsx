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

const SOURCES = ['ioda_outages'] as const;

export function ConnectivityPanel({ country, onSelect }: ContextPanelProps) {
  const snapshot = useContextEvents(SOURCES, country);
  const [query, setQuery] = useState('');
  const [signal, setSignal] = useState('all');
  const signals = [...new Set(snapshot.events.map((event) => attribute(event, 'datasource')))];
  const events = newest(snapshot.events).filter(
    (event) =>
      matchesQuery(event, query) && (signal === 'all' || attribute(event, 'datasource') === signal),
  );
  return (
    <ContextShell
      title="Connectivity signals"
      snapshot={snapshot}
      scope={`IODA reported connectivity signals. ${country ? `Nation: ${country}, using source country attribution.` : 'Worldwide, including records without a country attribution.'} No location is inferred from a network name.`}
    >
      <p className="rounded-lg border border-amber-300/20 bg-amber-300/5 p-3 text-[11px] leading-relaxed text-muted">
        Reported signal drops, not a list of current outages. Recovery messages are not retained by
        this feed, so these records do not establish whether a disruption is ongoing, its cause or
        the number of affected users.
      </p>
      <label className="block space-y-1 text-muted">
        Search country, network or signal
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className={controlClass}
          placeholder="Country name, ASN, BGP…"
        />
      </label>
      <label className="block space-y-1 text-muted">
        Measurement source
        <select
          value={signal}
          onChange={(event) => setSignal(event.target.value)}
          className={controlClass}
        >
          <option value="all">All reported signals</option>
          {signals.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
      <p className="text-[10px] text-muted">
        {Math.min(25, events.length)} of {events.length} matching collected signals
      </p>
      {!snapshot.loading && events.length === 0 && (
        <p className="text-muted">No matching connectivity signals in this snapshot.</p>
      )}
      <ul className="space-y-2">
        {events.slice(0, 25).map((event) => (
          <li key={event.id} className="rounded-lg border border-line p-3">
            <h4 className="font-medium leading-relaxed text-text">{event.title}</h4>
            <p className="mt-1 text-[10px] text-muted">Reported: {utcDate(event.published_at)}</p>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[11px]">
              <dt className="text-muted">Entity</dt>
              <dd className="break-words text-text">
                {attribute(event, 'entity_type')} · {attribute(event, 'entity_code')}
              </dd>
              <dt className="text-muted">Signal / level</dt>
              <dd className="text-text">
                {attribute(event, 'datasource')} · {attribute(event, 'level')}
              </dd>
              <dt className="text-muted">Value / baseline</dt>
              <dd className="text-text">
                {attribute(event, 'value')} / {attribute(event, 'history_value')}
              </dd>
            </dl>
            <EventActions event={event} onSelect={onSelect} />
          </li>
        ))}
      </ul>
    </ContextShell>
  );
}
