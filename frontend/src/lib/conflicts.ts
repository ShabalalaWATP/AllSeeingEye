import type { LiveEvent } from './api/eventSchemas';

export type ConflictKind =
  | 'armed_clashes'
  | 'organised_violence'
  | 'strikes'
  | 'civilian_harm'
  | 'protests'
  | 'military_activity'
  | 'other';
export type ConflictGroup = 'all' | ConflictKind;

export const CONFLICT_GROUPS: readonly { value: ConflictGroup; label: string }[] = [
  { value: 'all', label: 'All loaded reports' },
  { value: 'armed_clashes', label: 'Armed clashes' },
  { value: 'organised_violence', label: 'Organised violence (unspecified type)' },
  { value: 'strikes', label: 'Strikes and explosions' },
  { value: 'civilian_harm', label: 'Civilian harm' },
  { value: 'protests', label: 'Protests and riots' },
  { value: 'military_activity', label: 'Military activity' },
  { value: 'other', label: 'Other reported incidents' },
];

const kinds: Readonly<Record<string, ConflictKind>> = {
  fight: 'armed_clashes',
  armed_clash: 'armed_clashes',
  battle: 'armed_clashes',
  organised_violence: 'organised_violence',
  strike: 'strikes',
  explosion: 'strikes',
  civilian_harm: 'civilian_harm',
  violence_against_civilians: 'civilian_harm',
  mass_violence: 'civilian_harm',
  protest: 'protests',
  riot: 'protests',
  force_posture: 'military_activity',
  coercion: 'other',
  assault: 'other',
};

/** Provider event types describe reports, not independent confirmation of an armed conflict. */
export function conflictKind(event: Pick<LiveEvent, 'category' | 'subtype'>): ConflictKind | null {
  if (event.category !== 'conflict') return null;
  const subtype = event.subtype.toLowerCase().trim().replace(/[ -]+/g, '_');
  return Object.hasOwn(kinds, subtype) ? (kinds[subtype] ?? 'other') : 'other';
}

export function conflictReportLabel(event: Pick<LiveEvent, 'category' | 'subtype'>): string {
  const kind = conflictKind(event);
  return CONFLICT_GROUPS.find((group) => group.value === kind)?.label ?? 'Other report';
}

/** Keep unrelated overlays intact and retain all reports until the operator narrows the view. */
export function isHistoricalConflict(event: LiveEvent): boolean {
  return (
    event.category === 'conflict' &&
    (event.attributes.dataset_status === 'provisional_monthly' ||
      event.tags.includes('provisional_monthly'))
  );
}

export function filterConflictReports(
  events: LiveEvent[],
  group: ConflictGroup,
  includeHistorical = false,
): LiveEvent[] {
  if (group === 'all' && (includeHistorical || !events.some(isHistoricalConflict))) return events;
  return events.filter((event) => {
    if (!includeHistorical && isHistoricalConflict(event)) return false;
    const kind = conflictKind(event);
    return group === 'all' || kind === null || kind === group;
  });
}

export function countConflictReports(events: readonly LiveEvent[]): Record<ConflictGroup, number> {
  const counts: Record<ConflictGroup, number> = {
    all: 0,
    armed_clashes: 0,
    organised_violence: 0,
    strikes: 0,
    civilian_harm: 0,
    protests: 0,
    military_activity: 0,
    other: 0,
  };
  for (const event of events) {
    const kind = conflictKind(event);
    if (kind !== null) {
      counts.all++;
      counts[kind]++;
    }
  }
  return counts;
}
