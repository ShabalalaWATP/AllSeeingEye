/** Accept only the server's bounded idle-session duration. */
export function parseIdleMinutes(value: unknown): number | undefined {
  const minutes = typeof value === 'string' || typeof value === 'number' ? Number(value) : NaN;
  return Number.isInteger(minutes) && minutes >= 5 && minutes <= 1440 ? minutes : undefined;
}
