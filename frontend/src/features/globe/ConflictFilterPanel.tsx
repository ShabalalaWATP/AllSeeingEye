import { useId } from 'react';
import { CONFLICT_GROUPS, type ConflictGroup } from '@/lib/conflicts';

export function ConflictFilterPanel({
  group,
  setGroup,
  counts,
  includeHistorical,
  setIncludeHistorical,
  historicalCount,
}: {
  group: ConflictGroup;
  setGroup: (value: ConflictGroup) => void;
  counts: Record<ConflictGroup, number>;
  includeHistorical: boolean;
  setIncludeHistorical: (value: boolean) => void;
  historicalCount: number;
}) {
  const id = useId();
  return (
    <section aria-label="Conflict report filters" className="space-y-3 p-3">
      <label className="flex min-h-10 items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs">
        <input
          type="checkbox"
          checked={includeHistorical}
          onChange={(event) => setIncludeHistorical(event.target.checked)}
          className="accent-cyan"
        />
        <span>Historical baseline ({historicalCount.toLocaleString()} loaded)</span>
      </label>
      <p className="text-[11px] leading-relaxed text-muted">
        Monthly UCDP releases describe earlier periods and are hidden by default. Enabling the
        historical baseline does not make these reports live incidents; release and occurrence dates
        appear in details.
      </p>
      <fieldset className="space-y-1">
        <legend className="mb-2 text-xs text-muted">
          Choose which reported incidents appear on the map.
        </legend>
        {CONFLICT_GROUPS.map((choice) => (
          <label
            key={choice.value}
            className={`flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs ${group === choice.value ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-200' : 'border-white/10 text-muted hover:bg-white/5'}`}
          >
            <input
              type="radio"
              aria-label={`${choice.label} ${counts[choice.value]} loaded reports`}
              name={id}
              value={choice.value}
              checked={group === choice.value}
              onChange={() => setGroup(choice.value)}
              className="accent-cyan"
            />
            <span className="flex-1">{choice.label}</span>
            <span className="font-mono tabular-nums">
              {counts[choice.value].toLocaleString()}
              <span className="sr-only"> loaded reports</span>
            </span>
          </label>
        ))}
      </fieldset>
      <p className="text-[11px] leading-relaxed text-muted">
        Counts are loaded reports in the selected nation and time window, not verified conflicts or
        unique incidents. Several sources may report the same event.
      </p>
      <p className="text-[11px] leading-relaxed text-muted">
        Types come from the source. Protests, force movements and other incidents do not establish
        armed conflict. The main conflict layer switch still controls visibility.
      </p>
    </section>
  );
}
