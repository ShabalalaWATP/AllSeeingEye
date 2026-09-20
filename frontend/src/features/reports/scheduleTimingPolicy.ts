export type LookbackUnit = 'days' | 'hours' | 'default';
export type Cadence =
  'daily' | 'weekdays' | 'weekly' | 'monthly' | 'quarterly' | 'semiannual' | 'annual';
export const CADENCE_DAYS: Record<Cadence, number> = {
  daily: 1,
  weekdays: 3,
  weekly: 7,
  monthly: 31,
  quarterly: 92,
  semiannual: 184,
  annual: 366,
};

export function scheduleWindowHours(lookback: string, unit: LookbackUnit): number | null {
  return unit === 'default' ? null : Number(lookback) * (unit === 'days' ? 24 : 1);
}

export function lookbackForCadence(
  lookback: string,
  unit: LookbackUnit,
  previous: Cadence,
  next: Cadence,
  editing: boolean,
): string {
  return !editing && unit === 'days' && Number(lookback) === CADENCE_DAYS[previous]
    ? String(CADENCE_DAYS[next])
    : lookback;
}

export function convertLookback(
  lookback: string,
  previous: LookbackUnit,
  next: LookbackUnit,
): string {
  if (next === 'default') return lookback;
  const hours = scheduleWindowHours(lookback, previous) ?? 168;
  return String(next === 'days' ? Math.max(1, Math.ceil(hours / 24)) : hours);
}
