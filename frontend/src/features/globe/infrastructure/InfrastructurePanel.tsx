import { useState } from 'react';
import type { InfrastructureSelection, InfrastructureState } from './useInfrastructure';

export function InfrastructurePanel({
  state,
  onSelect,
}: {
  state: InfrastructureState;
  onSelect: (value: InfrastructureSelection) => void;
}) {
  const [query, setQuery] = useState('');
  const records: InfrastructureSelection[] = [
    ...(state.cablesEnabled
      ? (state.data?.cables ?? []).map((item) => ({ kind: 'cable' as const, item }))
      : []),
    ...(state.stationsEnabled
      ? (state.data?.ground_stations ?? []).map((item) => ({ kind: 'station' as const, item }))
      : []),
  ];
  const matches = records.filter(({ item }) =>
    `${item.name} ${'operator' in item ? `${item.operator} ${item.country}` : item.category}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );
  return (
    <section aria-label="Map infrastructure">
      <p className="mb-3 text-xs leading-relaxed text-muted">
        Public infrastructure, with approximate routes and locations. Select a line or dish on the
        map for its source.
      </p>
      <button
        type="button"
        role="switch"
        aria-label="Undersea cables"
        aria-checked={state.cablesEnabled}
        onClick={state.toggleCables}
        className="flex min-h-11 w-full items-center justify-between text-sm"
      >
        <span>Undersea cables</span>
        <span className="text-cyan">{state.cablesEnabled ? 'ON' : 'OFF'}</span>
      </button>
      <button
        type="button"
        role="switch"
        aria-label="Satellite ground stations"
        aria-checked={state.stationsEnabled}
        onClick={state.toggleStations}
        className="flex min-h-11 w-full items-center justify-between text-sm"
      >
        <span>Satellite ground stations</span>
        <span className="text-cyan">{state.stationsEnabled ? 'ON' : 'OFF'}</span>
      </button>
      {state.loading && (
        <p role="status" className="py-2 text-xs text-muted">
          Loading public infrastructure…
        </p>
      )}
      {state.error && (
        <div role="alert" className="py-2 text-xs">
          <p>{state.error}</p>
          <button type="button" className="mt-2 text-cyan underline" onClick={state.retry}>
            Retry infrastructure
          </button>
        </div>
      )}
      {state.data && (
        <>
          <p className="my-3 text-[11px] text-muted">
            Snapshot: {state.data.snapshot_date}. {state.data.cables.length} route segments ·{' '}
            {state.data.ground_stations.length} ground stations. Coverage is incomplete; segments
            are not individual cable systems.
          </p>
          <label className="block text-xs">
            Find infrastructure
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name, operator or country code"
              className="my-2 w-full rounded border border-line bg-ground px-2 py-2 text-sm"
            />
          </label>
          <ul className="max-h-56 overflow-y-auto">
            {matches.slice(0, 50).map((value) => (
              <li key={`${value.kind}:${value.item.id}`}>
                <button
                  type="button"
                  onClick={() => onSelect(value)}
                  className="w-full border-t border-line py-2 text-left text-xs hover:text-cyan"
                >
                  <span className="block">{value.item.name}</span>
                  <span className="text-[10px] text-muted">
                    {value.kind === 'station'
                      ? `${value.item.operator} · ${value.item.country}`
                      : `Cable segment · ${value.item.category}`}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {matches.length > 50 && (
            <p className="mt-2 text-xs text-muted">
              Showing the first 50 of {matches.length}. Refine the search to narrow the list.
            </p>
          )}
          {matches.length === 0 && (
            <p className="py-2 text-xs text-muted">
              No matching infrastructure in the enabled layers.
            </p>
          )}
          <p className="mt-3 text-[10px] text-muted">
            {state.data.cable_attribution} ·{' '}
            <a
              href={state.data.cable_licence_url}
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              Cable data licence
            </a>
          </p>
        </>
      )}
    </section>
  );
}
