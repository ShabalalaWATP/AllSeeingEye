import { useState } from 'react';
import { MapControlIcon } from '../MapControlIcon';
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
    ...(state.nuclearEnabled
      ? (state.data?.nuclear_facilities ?? []).map((item) => ({ kind: 'nuclear' as const, item }))
      : []),
  ];
  const matches = records.filter(({ item }) =>
    `${item.name} ${'operator' in item ? `${item.operator ?? ''} ${item.country}` : item.category}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );
  return (
    <section aria-label="Map infrastructure" className="space-y-3 p-1">
      <h3 className="text-sm font-medium">Infrastructure layers</h3>
      <p className="mb-3 text-xs leading-relaxed text-muted">
        Public infrastructure, with approximate routes and locations. Select a line or site icon on
        the map for its source.
      </p>
      {[
        {
          label: 'Undersea cables',
          icon: 'route' as const,
          description: 'Approximate public route segments',
          count: state.data?.cables.length,
          enabled: state.cablesEnabled,
          toggle: state.toggleCables,
        },
        {
          label: 'Satellite ground stations',
          icon: 'space' as const,
          description: 'Public station locations',
          count: state.data?.ground_stations.length,
          enabled: state.stationsEnabled,
          toggle: state.toggleStations,
        },
        {
          label: 'Nuclear power facilities',
          icon: 'infrastructure' as const,
          description: 'Historical power-plant inventory',
          count: state.data?.nuclear_facilities.length,
          enabled: state.nuclearEnabled,
          toggle: state.toggleNuclear,
        },
      ].map((choice) => (
        <button
          key={choice.label}
          type="button"
          role="switch"
          aria-label={choice.label}
          aria-checked={choice.enabled}
          onClick={choice.toggle}
          className="flex min-h-16 w-full items-center gap-3 rounded-lg border border-line px-3 py-3 text-left text-sm transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-cyan"
        >
          <span className="text-cyan">
            <MapControlIcon name={choice.icon} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block font-medium">{choice.label}</span>
            <span className="mt-1 block text-[11px] leading-relaxed text-muted">
              {choice.description}
              {choice.count !== undefined
                ? ` / ${choice.count.toLocaleString('en-GB')} loaded`
                : ''}
            </span>
          </span>
          <span
            aria-hidden="true"
            className={`flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 ${choice.enabled ? 'bg-cyan/70' : 'bg-white/15'}`}
          >
            <span
              className={`h-4 w-4 rounded-full bg-white transition-transform ${choice.enabled ? 'translate-x-4' : ''}`}
            />
          </span>
        </button>
      ))}
      {state.nuclearEnabled && (
        <p className="text-[11px] text-muted">
          Historical public power-plant inventory. Not a current operational status or radiation
          alert.
        </p>
      )}
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
            {state.data.ground_stations.length} ground stations ·{' '}
            {state.data.nuclear_facilities.length} historical nuclear facilities. Coverage is
            incomplete; segments are not individual cable systems.
          </p>
          <label className="block text-xs">
            Find infrastructure
            <input
              type="search"
              maxLength={200}
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
                  aria-pressed={
                    state.selected?.kind === value.kind && state.selected.item.id === value.item.id
                  }
                  className="min-h-14 w-full border-b border-line px-2 py-3 text-left text-xs hover:bg-white/5 aria-pressed:bg-cyan/10 focus-visible:outline-2 focus-visible:outline-cyan"
                >
                  <span className="block">{value.item.name}</span>
                  <span className="text-[10px] text-muted">
                    {value.kind === 'nuclear'
                      ? `Nuclear power · ${value.item.country}`
                      : value.kind === 'station'
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
          {state.nuclearEnabled && (
            <p className="mt-3 text-[10px] text-muted">
              {state.data.nuclear_attribution} · Dataset {state.data.nuclear_dataset_version},
              downloaded {state.data.nuclear_snapshot_date}.{' '}
              <a
                href={state.data.nuclear_licence_url}
                target="_blank"
                rel="noreferrer"
                className="underline"
              >
                Nuclear inventory licence
              </a>
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
