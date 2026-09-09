import { useMemo, useState } from 'react';
import type { JamCell } from '@/lib/api/aviation';

export function sameJamCell(left: JamCell | null, right: JamCell): boolean {
  return left?.lon === right.lon && left.lat === right.lat && left.size === right.size;
}

/** These are observation filters, not probabilities that intentional jamming occurred. */
export function useGnssFilters(cells: readonly JamCell[], receivedAt: number | null, now: number) {
  const [level, setLevel] = useState<'all' | 'red'>('all');
  const [minimum, setMinimum] = useState(5);
  // Per-cell observation ages are unavailable. Bound the age of the entire retrieved snapshot.
  const age = receivedAt === null ? 0 : Math.max(0, now - receivedAt);
  const stale = age >= 6 * 60_000;
  const expired = age >= 15 * 60_000;
  const filtered = useMemo(
    () =>
      cells.filter(
        (cell) =>
          !expired &&
          (cell.level === 'amber' || cell.level === 'red') &&
          (level === 'all' || cell.level === level) &&
          cell.good + cell.bad >= minimum,
      ),
    [cells, expired, level, minimum],
  );
  return { filtered, level, setLevel, minimum, setMinimum, stale, expired };
}
