import type { LiveEvent } from './api/eventSchemas';
import { matchesConflictReview } from './conflictReview';

export type ConflictKind =
  | 'armed_clashes'
  | 'organised_violence'
  | 'strikes'
  | 'civilian_harm'
  | 'protests'
  | 'riots'
  | 'unrest'
  | 'military_activity'
  | 'other';
export type ConflictGroup = 'all' | ConflictKind;

export const CONFLICT_GROUPS: readonly { value: ConflictGroup; label: string; note?: string }[] = [
  { value: 'all', label: 'All loaded reports' },
  { value: 'armed_clashes', label: 'Armed clashes' },
  { value: 'organised_violence', label: 'Organised violence (unspecified type)' },
  { value: 'strikes', label: 'Strikes and explosions' },
  {
    value: 'civilian_harm',
    label: 'Violence against civilians',
    note: 'Source-coded civilian harm, within or outside a war.',
  },
  {
    value: 'protests',
    label: 'Protests / demonstrations',
    note: 'Does not assume protester violence. May include intervention against protesters.',
  },
  {
    value: 'riots',
    label: 'Riots / violent demonstrations',
    note: 'Explicitly classified by the source, not inferred from headline words.',
  },
  {
    value: 'unrest',
    label: 'Unrest (type unspecified)',
    note: 'Screening identifies unrest but does not establish protest, riot or violence.',
  },
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
  riot: 'riots',
  violent_demonstration: 'riots',
  mob_violence: 'riots',
  force_posture: 'military_activity',
  coercion: 'other',
  assault: 'other',
};

type ConflictTypeEvent = Pick<LiveEvent, 'category' | 'subtype'> &
  Partial<Pick<LiveEvent, 'attributes' | 'source_id'>>;

// CAMEO 1.1b3, pp 71–72: explicit violent protest codes, not all root-14 protests.
// https://data.gdeltproject.org/documentation/CAMEO.Manual.1.1b3.pdf
const VIOLENT_PROTEST_CODES = new Set(['145', '1451', '1452', '1453', '1454']);

/** Screening controls relevance; provider detail can refine an armed-conflict report's type. */
export function conflictKind(event: ConflictTypeEvent): ConflictKind | null {
  if (event.category !== 'conflict') return null;
  const relevance =
    event.attributes?.conflict_screening === 'llm' ? event.attributes.conflict_relevance : null;
  if (relevance === 'military_activity') return 'military_activity';
  const subtype = event.subtype.toLowerCase().trim().replace(/[ -]+/g, '_');
  const code = event.attributes?.event_code;
  const kind =
    event.source_id === 'gdelt_events' &&
    subtype === 'protest' &&
    typeof code === 'string' &&
    VIOLENT_PROTEST_CODES.has(code)
      ? 'riots'
      : Object.hasOwn(kinds, subtype)
        ? (kinds[subtype] ?? 'other')
        : 'other';
  // Broad LLM relevance is not evidence that a protest was violent. Preserve only
  // explicit provider detail compatible with that relevance assessment.
  if (relevance === 'civil_unrest')
    return kind === 'protests' || kind === 'riots' ? kind : 'unrest';
  if (
    relevance === 'armed_conflict' &&
    (kind === 'other' || kind === 'protests' || kind === 'riots' || kind === 'military_activity')
  )
    return 'organised_violence';
  return kind;
}

export function conflictReportLabel(event: ConflictTypeEvent): string {
  const kind = conflictKind(event);
  return CONFLICT_GROUPS.find((group) => group.value === kind)?.label ?? 'Other report';
}

/** Monthly research records remain an explicit opt-in, independent of media screening. */
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
  includeUnreviewed = false,
): LiveEvent[] {
  if (
    group === 'all' &&
    events.every(
      (event) =>
        (includeHistorical || !isHistoricalConflict(event)) &&
        matchesConflictReview(event, includeUnreviewed),
    )
  )
    return events;
  return events.filter((event) => {
    if (!includeHistorical && isHistoricalConflict(event)) return false;
    if (!matchesConflictReview(event, includeUnreviewed)) return false;
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
    riots: 0,
    unrest: 0,
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
