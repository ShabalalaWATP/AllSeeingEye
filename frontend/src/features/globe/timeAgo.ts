const MINUTE_MS = 60_000;
const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;

/** Coarse relative age for the ticker ("5m ago"); returns the input when unparseable. */
export function formatAgo(iso: string, now: number): string {
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return iso;
  const delta = Math.max(0, now - time);
  if (delta < MINUTE_MS) return 'just now';
  if (delta < HOUR_MS) return `${Math.floor(delta / MINUTE_MS)}m ago`;
  if (delta < DAY_MS) return `${Math.floor(delta / HOUR_MS)}h ago`;
  return `${Math.floor(delta / DAY_MS)}d ago`;
}
