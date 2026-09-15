import type { Schedule } from '@/lib/api/schedules';
import { formatUtc } from '@/lib/format';

export function scheduleNeedsAttention(item: Schedule): boolean {
  return (
    item.last_error !== null ||
    item.last_outcome === 'failed' ||
    item.last_outcome === 'needs_review' ||
    item.last_coverage === 'partial'
  );
}

/** Keep subscription list filtering and headline figures independent of rendering. */
export function scheduleListSummary(
  items: readonly Schedule[],
  status: string,
  cadence: string,
  search: string,
) {
  const searchTerm = search.trim().toLocaleLowerCase();
  const visible = items.filter((item) => {
    const matchesStatus =
      status === 'all' ||
      (status === 'active' && item.enabled) ||
      (status === 'paused' && !item.enabled) ||
      (status === 'attention' && scheduleNeedsAttention(item));
    const matchesCadence = cadence === 'all' || item.cadence === cadence;
    const matchesSearch =
      !searchTerm ||
      [item.name, item.question, item.research_subject, item.conflict_id, item.hazard]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLocaleLowerCase().includes(searchTerm));
    return matchesStatus && matchesCadence && matchesSearch;
  });
  const active = items.filter((item) => item.enabled);
  const paused = items.filter((item) => !item.enabled);
  const attention = items.filter(scheduleNeedsAttention);
  const nextRun = active.map((item) => item.next_run_at).sort()[0];
  const figures = [
    { label: 'Active', value: String(active.length), tone: 'text-good' },
    { label: 'Paused', value: String(paused.length), tone: 'text-muted' },
    {
      label: 'Needs attention',
      value: String(attention.length),
      tone: attention.length ? 'text-amber' : 'text-muted',
    },
    { label: 'Next run', value: nextRun ? formatUtc(nextRun) : 'None scheduled', tone: '' },
  ];
  return { visible, active, paused, figures };
}
