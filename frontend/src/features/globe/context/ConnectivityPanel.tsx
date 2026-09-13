import { useState } from 'react';
import { useContextEvents } from './useContextEvents';
import { NETWORK_SOURCES } from '../networkSources';
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

export function ConnectivityPanel({ country, onSelect }: ContextPanelProps) {
  const snapshot = useContextEvents(NETWORK_SOURCES, country);
  return (
    <ConnectivityPanelView
      country={country ?? null}
      {...(onSelect ? { onSelect } : {})}
      snapshot={snapshot}
    />
  );
}

/** The map and panel can share one bounded snapshot when Network is open. */
export function ConnectivityPanelView({
  country,
  onSelect,
  snapshot,
  mappedCount,
}: ContextPanelProps & {
  snapshot: ReturnType<typeof useContextEvents>;
  mappedCount?: number;
}) {
  const [query, setQuery] = useState('');
  const [provider, setProvider] = useState('all');
  const [signal, setSignal] = useState('all');
  const signals = [...new Set(snapshot.events.map((event) => attribute(event, 'datasource')))];
  const events = newest(snapshot.events).filter(
    (event) =>
      matchesQuery(event, query) &&
      (provider === 'all' || event.source_id === provider) &&
      (signal === 'all' || attribute(event, 'datasource') === signal),
  );
  return (
    <ContextShell
      title="Connectivity signals"
      snapshot={snapshot}
      scope={`IODA measurements and Cloudflare Radar annotations. ${country ? `Nation: ${country}, using provider country attribution.` : 'Worldwide, including records without a country attribution.'} No location is inferred from a network name.`}
    >
      <p className="rounded-lg border border-amber-300/20 bg-amber-300/5 p-3 text-[11px] leading-relaxed text-muted">
        IODA alerts and event windows are measured anomalies. Cloudflare Radar annotations are a
        separate provider assessment. Neither feed establishes that a disruption is ongoing or
        caused by an attack. Country markers indicate reported scope, not an outage location.
      </p>
      {mappedCount !== undefined && !snapshot.loading && (
        <p className="text-[11px] text-muted">
          {mappedCount} source-attributed {mappedCount === 1 ? 'country' : 'countries'} shown on the
          map. Other records have no safe map position. Markers show country references, not outage
          locations.
        </p>
      )}
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
        Provider and record type
        <select
          value={provider}
          onChange={(event) => setProvider(event.target.value)}
          className={controlClass}
        >
          <option value="all">All network records</option>
          <option value="ioda_outages">IODA alerts</option>
          <option value="ioda_outage_events">IODA event windows</option>
          <option value="cloudflare_radar_outages">Cloudflare Radar outages</option>
        </select>
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
              {event.source_id === 'cloudflare_radar_outages' ? (
                <>
                  <dt className="text-muted">Outage type</dt>
                  <dd className="text-text">{attribute(event, 'outage_type')}</dd>
                  <dt className="text-muted">Reported scope</dt>
                  <dd className="text-text">{attribute(event, 'scope')}</dd>
                </>
              ) : (
                <>
                  <dt className="text-muted">Signal / level</dt>
                  <dd className="text-text">
                    {attribute(event, 'datasource')}
                    {event.source_id === 'ioda_outages' && ` · ${attribute(event, 'level')}`}
                  </dd>
                </>
              )}
              {event.source_id === 'ioda_outages' ? (
                <>
                  <dt className="text-muted">Value / baseline</dt>
                  <dd className="text-text">
                    {attribute(event, 'value')} / {attribute(event, 'history_value')}
                  </dd>
                </>
              ) : (
                <>
                  <dt className="text-muted">Start</dt>
                  <dd className="text-text">{utcDate(attribute(event, 'start'))}</dd>
                  <dt className="text-muted">End</dt>
                  <dd className="text-text">{utcDate(attribute(event, 'end'))}</dd>
                </>
              )}
            </dl>
            <EventActions event={event} onSelect={onSelect} />
          </li>
        ))}
      </ul>
    </ContextShell>
  );
}
