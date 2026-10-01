/** Short series are read out in full; longer ones by their first, latest and extreme values. */
export const FULL_SERIES_LIMIT = 10;

const formatValue = (value: number) => value.toLocaleString('en-GB');

/** Text alternative for a trend line, so its accessible name carries the values it draws. */
export function sparklineSummary(
  values: readonly number[],
  format: (value: number) => string = formatValue,
): string {
  if (values.length === 0) return 'no values';
  const lowest = format(Math.min(...values));
  const highest = format(Math.max(...values));
  if (values.length <= FULL_SERIES_LIMIT) {
    return `${values.map(format).join(', ')} (lowest ${lowest}, highest ${highest})`;
  }
  const first = format(values[0] ?? 0);
  const latest = format(values.at(-1) ?? 0);
  return `${values.length} values, first ${first}, latest ${latest}, lowest ${lowest}, highest ${highest}`;
}
