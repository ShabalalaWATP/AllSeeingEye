import { useEffect, useRef } from 'react';
import type { Infrastructure } from '@/lib/api/infrastructure';
import type { InfrastructureSelection } from './useInfrastructure';
import { InfrastructureFacts, selectionLabel } from './InfrastructureFacts';

export function InfrastructureInspector({
  selected,
  onClose,
  data,
}: {
  selected: InfrastructureSelection;
  onClose: () => void;
  data?: Infrastructure | null;
}) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    close.current?.focus();
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', dismiss);
    return () => {
      window.removeEventListener('keydown', dismiss);
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [onClose]);
  if (selected.kind === 'military_country')
    return (
      <aside
        aria-label="Infrastructure details"
        className="map-details-inspector absolute bottom-16 right-16 z-20 w-96 max-w-[calc(100%-5rem)] rounded-lg border border-line bg-ground p-4 shadow-xl"
      >
        <header className="flex items-start justify-between gap-3">
          <div>
            <p className="text-2xs uppercase tracking-wider text-cyan">Country source index</p>
            <h2 className="mt-1 text-sm font-medium">{selected.item.name}</h2>
          </div>
          <button
            ref={close}
            type="button"
            onClick={onClose}
            aria-label="Close infrastructure details"
            className="px-2 py-1 text-muted hover:text-cyan"
          >
            ×
          </button>
        </header>
        <p className="mt-3 text-xs leading-relaxed text-muted">
          This country-centre badge indexes official public sources. It is not a military base
          location or a current unit roster. Coverage differs between countries and is incomplete.
        </p>
        <ul className="mt-3 max-h-64 space-y-3 overflow-y-auto text-xs">
          {selected.item.sources.map((source) => (
            <li key={source.id} className="border-t border-line pt-3">
              <a href={source.url} target="_blank" rel="noreferrer" className="text-cyan underline">
                {source.title}
              </a>
              <p className="mt-1 text-muted">
                {source.publisher} · {source.assertion_scope}
              </p>
              <p className="mt-1 text-muted">{source.limitation}</p>
            </li>
          ))}
        </ul>
      </aside>
    );
  return (
    <aside
      aria-label="Infrastructure details"
      className="map-details-inspector absolute bottom-16 right-16 z-20 w-80 max-w-[calc(100%-5rem)] rounded-lg border border-line bg-ground p-4 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-2xs uppercase tracking-wider text-cyan">{selectionLabel(selected)}</p>
          <h2 className="mt-1 text-sm font-medium">{selected.item.name}</h2>
        </div>
        <button
          ref={close}
          type="button"
          onClick={onClose}
          aria-label="Close infrastructure details"
          className="px-2 py-1 text-muted hover:text-cyan"
        >
          ×
        </button>
      </header>
      <InfrastructureFacts selected={selected} />
      {selected.kind === 'nuclear' && (
        <div className="mt-3 space-y-2 text-xs text-muted">
          <p>
            {selected.item.country} ({selected.item.country_code}) ·{' '}
            {selected.item.operator ?? 'Operator not recorded'}
          </p>
          <p>
            Recorded capacity:{' '}
            {selected.item.capacity_mw === null
              ? 'Unknown'
              : `${selected.item.capacity_mw.toLocaleString()} MW`}
            {selected.item.capacity_year ? ` (${selected.item.capacity_year})` : ' (year unknown)'}.
            This is historical capacity, not current output.
          </p>
          <p>
            Inventory source: {selected.item.source_name}. Geolocation:{' '}
            {selected.item.geolocation_source}.
          </p>
          {data && (
            <p>
              {data.nuclear_attribution} · Version {data.nuclear_dataset_version}, downloaded{' '}
              {data.nuclear_snapshot_date}.{' '}
              <a
                href={data.nuclear_licence_url}
                target="_blank"
                rel="noreferrer"
                className="underline"
              >
                Inventory licence
              </a>
            </p>
          )}
        </div>
      )}
      <p className="mt-3 text-xs font-medium text-cyan">
        Approximate {selected.kind !== 'cable' ? 'location' : 'route'}
      </p>
      <p className="mt-2 text-xs leading-relaxed text-muted">{selected.item.note}</p>
      <p className="mt-2 text-xs leading-relaxed text-muted">
        {selected.kind === 'nuclear'
          ? 'This historical power-plant record does not establish current operating status, reactor activity or a radiation hazard.'
          : selected.kind === 'station'
            ? 'A public site or locality marker does not indicate current communications or activity.'
            : selected.kind === 'data_centre'
              ? 'A mapped data centre is a building record, not a statement of tenants, capacity or current operation.'
              : selected.kind === 'energy_site' || selected.kind === 'semiconductor_site'
                ? 'A researched site record; output, ownership and current operation are not verified here.'
                : 'This segment is an incomplete map record, not proof of its condition, exact seabed route or operational status.'}
      </p>
      <a
        className="mt-3 inline-block text-xs text-cyan underline"
        href={selected.item.source_url}
        target="_blank"
        rel="noreferrer"
      >
        View public source
      </a>
    </aside>
  );
}
