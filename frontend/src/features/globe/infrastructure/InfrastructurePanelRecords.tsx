import { MapControlIcon } from '../MapControlIcon';
import type { InfrastructureSelection } from './useInfrastructure';
import {
  infrastructureRecordDescription,
  type InfrastructureChoice,
} from './infrastructurePanelModel';

export function InfrastructureLayerSwitch({ choice }: { choice: InfrastructureChoice }) {
  return (
    <button
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
          {choice.count !== undefined ? ` / ${choice.count.toLocaleString('en-GB')} loaded` : ''}
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
  );
}

export function InfrastructureRecordList({
  records,
  selected,
  onSelect,
}: {
  records: readonly Exclude<InfrastructureSelection, { kind: 'military_country' }>[];
  selected: InfrastructureSelection | null;
  onSelect: (value: InfrastructureSelection) => void;
}) {
  return (
    <>
      <ul className="max-h-56 overflow-y-auto">
        {records.slice(0, 50).map((value) => (
          <li key={`${value.kind}:${value.item.id}`}>
            <button
              type="button"
              onClick={() => onSelect(value)}
              aria-pressed={selected?.kind === value.kind && selected.item.id === value.item.id}
              className="min-h-14 w-full border-b border-line px-2 py-3 text-left text-xs hover:bg-white/5 aria-pressed:bg-cyan/10 focus-visible:outline-2 focus-visible:outline-cyan"
            >
              <span className="block">{value.item.name}</span>
              <span className="text-[10px] text-muted">
                {infrastructureRecordDescription(value)}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {records.length > 50 && (
        <p className="mt-2 text-xs text-muted">
          Showing the first 50 of {records.length}. Refine the search to narrow the list.
        </p>
      )}
      {records.length === 0 && (
        <p className="py-2 text-xs text-muted">No matching infrastructure in the enabled layers.</p>
      )}
    </>
  );
}
