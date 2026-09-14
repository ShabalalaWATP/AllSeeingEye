import { useMemo, useState } from 'react';

import {
  GROUP_LABELS,
  LENS_LABELS,
  type Lens,
  type UkraineUpdate,
  type UpdateGroup,
} from '@/lib/api/ukraine';

import { UpdateRow } from './UpdateRow';

const GROUPS: readonly UpdateGroup[] = ['assessments', 'ukrainian', 'russian', 'international'];
const LENSES: readonly Lens[] = ['equipment', 'workforce', 'casualties', 'strikes', 'diplomacy'];

/** Reporting grouped by who says it, with lens chips that narrow every group the same way. */
export function UpdatesTabs({ updates }: { updates: readonly UkraineUpdate[] }) {
  const [group, setGroup] = useState<UpdateGroup>('assessments');
  const [lens, setLens] = useState<Lens | null>(null);
  const counts = useMemo(() => {
    const perGroup = new Map<UpdateGroup, number>();
    for (const update of updates) {
      if (lens && !update.lenses.includes(lens)) continue;
      perGroup.set(update.group, (perGroup.get(update.group) ?? 0) + 1);
    }
    return perGroup;
  }, [updates, lens]);
  const visible = updates.filter(
    (update) => update.group === group && (lens === null || update.lenses.includes(lens)),
  );
  return (
    <section id="updates" aria-labelledby="ukraine-updates-heading" className="flex flex-col gap-3">
      <h2 id="ukraine-updates-heading" className="text-base font-semibold">
        Latest updates
      </h2>
      <div role="group" aria-label="Reporting group" className="flex flex-wrap gap-1">
        {GROUPS.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={group === value}
            onClick={() => setGroup(value)}
            className="min-h-10 rounded border border-line px-3 text-xs text-muted aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
          >
            {GROUP_LABELS[value]} ({counts.get(value) ?? 0})
          </button>
        ))}
      </div>
      <div role="group" aria-label="Lens" className="flex flex-wrap gap-1">
        <button
          type="button"
          aria-pressed={lens === null}
          onClick={() => setLens(null)}
          className="min-h-9 rounded-full border border-line px-3 text-xs text-muted aria-pressed:border-ember aria-pressed:text-ember"
        >
          All
        </button>
        {LENSES.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={lens === value}
            onClick={() => setLens(lens === value ? null : value)}
            className="min-h-9 rounded-full border border-line px-3 text-xs text-muted aria-pressed:border-ember aria-pressed:text-ember"
          >
            {LENS_LABELS[value]}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <p className="text-sm text-muted">Nothing retained for this group in the window.</p>
      ) : (
        <ul aria-label={GROUP_LABELS[group]}>
          {visible.map((update) => (
            <UpdateRow key={update.event.id} update={update} />
          ))}
        </ul>
      )}
    </section>
  );
}
