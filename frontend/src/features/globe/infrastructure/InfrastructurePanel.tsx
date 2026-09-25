import { useState, type ReactNode } from 'react';
import {
  filterInfrastructureRecords,
  infrastructureChoices,
  showsInfrastructureKind,
  type InfrastructureGroup,
} from './infrastructurePanelModel';
import { InfrastructureRecordList, InfrastructureLayerSwitch } from './InfrastructurePanelRecords';
import { MapControlIcon } from '../MapControlIcon';
import type { InfrastructureSelection, InfrastructureState } from './useInfrastructure';

export type { InfrastructureGroup } from './infrastructurePanelModel';
const COPY: Record<InfrastructureGroup | 'all', { title: string; intro: string; aria: string }> = {
  all: {
    title: 'Infrastructure layers',
    intro:
      'Public infrastructure, with approximate routes and locations. Select a line or site icon on the map for its source.',
    aria: 'Map infrastructure',
  },
  technology: {
    title: 'Technology and communications',
    intro:
      'Undersea cables, satellite ground stations, data centres, semiconductor sites and connectivity signals. All five layers start on when this control is first selected.',
    aria: 'Technology and communications',
  },
  infrastructure: {
    title: 'Energy and industry',
    intro:
      'Nuclear power, oil and gas facilities and the military source index, with approximate locations. Select a site icon on the map for its source.',
    aria: 'Map infrastructure',
  },
};

/** One panel body; `group` narrows the switches and records to a rail control's remit. */
export function InfrastructurePanel({
  state,
  onSelect,
  group,
  connectivity,
  connectivityEnabled = false,
  connectivityCount = 0,
  onToggleConnectivity,
}: {
  state: InfrastructureState;
  onSelect: (value: InfrastructureSelection) => void;
  group?: InfrastructureGroup;
  connectivity?: ReactNode;
  connectivityEnabled?: boolean;
  connectivityCount?: number;
  onToggleConnectivity?: () => void;
}) {
  const [query, setQuery] = useState('');
  const copy = COPY[group ?? 'all'];
  const matches = filterInfrastructureRecords(state, query, group);
  const layers = (
    <section aria-label={copy.aria} className="space-y-3 p-1">
      <h3 className="text-sm font-medium">{copy.title}</h3>
      <p className="mb-3 text-xs leading-relaxed text-muted">{copy.intro}</p>
      {infrastructureChoices(state, group).map((choice) => (
        <InfrastructureLayerSwitch key={choice.kind} choice={choice} />
      ))}
      {group === 'technology' && onToggleConnectivity && (
        <button
          type="button"
          role="switch"
          aria-label="Connectivity signals"
          aria-checked={connectivityEnabled}
          onClick={onToggleConnectivity}
          className="flex min-h-16 w-full items-center gap-3 rounded-lg border border-line px-3 py-3 text-left text-sm transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-cyan"
        >
          <span className="text-cyan">
            <MapControlIcon name="connectivity" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block font-medium">Connectivity signals</span>
            <span className="mt-1 block text-[11px] leading-relaxed text-muted">
              IODA and Cloudflare Radar country-level network signals /{' '}
              {connectivityCount.toLocaleString('en-GB')} countries mapped
            </span>
          </span>
          <span
            aria-hidden="true"
            className={`flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 ${connectivityEnabled ? 'bg-cyan/70' : 'bg-white/15'}`}
          >
            <span
              className={`h-4 w-4 rounded-full bg-white transition-transform ${connectivityEnabled ? 'translate-x-4' : ''}`}
            />
          </span>
        </button>
      )}
      {group === 'technology' && connectivityEnabled && connectivity && (
        <details className="rounded-lg border border-line bg-white/[0.03] p-3">
          <summary className="cursor-pointer text-xs font-medium text-cyan">
            Browse connectivity signals
          </summary>
          <div className="mt-3">{connectivity}</div>
        </details>
      )}
      {showsInfrastructureKind('military_country', group) && state.militaryEnabled && (
        <div className="rounded-lg border border-line bg-white/[0.03] p-3">
          <p className="text-xs leading-relaxed text-muted">
            Map badges show country source coverage at country centres. They do not identify
            installations, current units or operational activity.
          </p>
          {state.militaryCountries.length === 0 ? (
            <p role="status" className="mt-2 text-xs text-muted">
              Loading country reference data…
            </p>
          ) : (
            <ul className="mt-2 max-h-52 overflow-y-auto">
              {state.militaryCountries.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect({ kind: 'military_country', item })}
                    aria-pressed={
                      state.selected?.kind === 'military_country' &&
                      state.selected.item.id === item.id
                    }
                    className="min-h-12 w-full border-b border-line px-2 py-2 text-left text-xs hover:bg-white/5 aria-pressed:bg-cyan/10 focus-visible:outline-2 focus-visible:outline-cyan"
                  >
                    <span className="font-medium">{item.name}</span>
                    <span className="ml-2 text-muted">
                      {item.sources.length} official source{item.sources.length === 1 ? '' : 's'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
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
            {state.data.nuclear_facilities.length} historical nuclear facilities ·{' '}
            {state.data.data_centres.length} data centres. Coverage is incomplete; segments are not
            individual cable systems.
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
          <InfrastructureRecordList
            records={matches}
            selected={state.selected}
            onSelect={onSelect}
          />
          {state.nuclearEnabled && (
            <p className="mt-3 text-2xs text-muted">
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
          {(state.energyEnabled || state.semiconductorEnabled) && (
            <p className="mt-3 text-2xs text-muted">
              {state.data.site_attribution} Snapshot {state.data.site_snapshot_date}.{' '}
              <a
                href={state.data.site_licence_url}
                target="_blank"
                rel="noreferrer"
                className="underline"
              >
                Site data licence
              </a>
            </p>
          )}
          {state.dataCentresEnabled && (
            <p className="mt-3 text-2xs text-muted">
              {state.data.data_centre_attribution} Snapshot {state.data.data_centre_snapshot_date}.{' '}
              <a
                href={state.data.data_centre_licence_url}
                target="_blank"
                rel="noreferrer"
                className="underline"
              >
                Data centre licence
              </a>
            </p>
          )}
          <p className="mt-3 text-2xs text-muted">
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
  return layers;
}
