const utcFormatter = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'UTC',
});

/** Formats an ISO 8601 timestamp as a UK-style UTC string; returns the input when unparseable. */
export function formatUtc(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${utcFormatter.format(date)} UTC`;
}

const MINUTE_MS = 60_000;
const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;

/** Coarse relative age ("5m ago"); returns the input when unparseable. */
export function formatAgo(iso: string, now: number): string {
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return iso;
  const delta = Math.max(0, now - time);
  if (delta < MINUTE_MS) return 'just now';
  if (delta < HOUR_MS) return `${Math.floor(delta / MINUTE_MS)}m ago`;
  if (delta < DAY_MS) return `${Math.floor(delta / HOUR_MS)}h ago`;
  return `${Math.floor(delta / DAY_MS)}d ago`;
}

/** A poll interval as people say it: "5 min", "1 h", "90 s". */
export function formatInterval(seconds: number): string {
  if (seconds % 3600 === 0) return `${seconds / 3600} h`;
  if (seconds % 60 === 0) return `${seconds / 60} min`;
  return `${seconds} s`;
}
