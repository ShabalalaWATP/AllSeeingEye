import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  conflictSourceChoices,
  matchesConflictDisplay,
  type ConflictPrecision,
} from '@/lib/conflictDisplayFilters';
import { isUnreviewedConflictSignal, matchesConflictReview } from '@/lib/conflictReview';
import {
  conflictKind,
  countConflictReports,
  isHistoricalConflict,
  type ConflictGroup,
} from '@/lib/conflicts';

export interface ConflictScopeOptions {
  group: ConflictGroup;
  includeHistorical: boolean;
  includeUnreviewed: boolean;
  query: string;
  source: string;
  precision: ConflictPrecision;
}

/** Derive current raw metadata and eligible display rows without repeating the full pipeline. */
export function deriveConflictScope(events: readonly LiveEvent[], options: ConflictScopeOptions) {
  const sourceRecords: LiveEvent[] = [];
  const filtered: LiveEvent[] = [];
  const counts = countConflictReports([]);
  let historicalCount = 0;
  let unreviewedCount = 0;
  for (const event of events) {
    // These controls describe the raw input, even when search or eligibility hides a row.
    if (event.category === 'conflict') sourceRecords.push(event);
    const historical = isHistoricalConflict(event);
    if (historical) historicalCount++;
    if (isUnreviewedConflictSignal(event)) unreviewedCount++;
    if (!matchesConflictDisplay(event, options.query, options.source, options.precision)) continue;
    if (!options.includeHistorical && historical) continue;
    if (!matchesConflictReview(event, options.includeUnreviewed)) continue;

    // Counts precede the selected group, while the final rows retain current input order.
    const kind = conflictKind(event);
    if (kind !== null) {
      counts.all++;
      counts[kind]++;
    }
    if (options.group === 'all' || kind === null || kind === options.group) filtered.push(event);
  }
  return {
    sourceOptions: conflictSourceChoices(sourceRecords),
    historicalCount,
    unreviewedCount,
    counts,
    filtered,
  };
}
