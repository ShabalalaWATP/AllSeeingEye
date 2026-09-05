import type { StreamStatus } from '@/lib/sse';

const LABELS: Record<StreamStatus, string> = {
  connecting: 'Connecting',
  live: 'Live',
  reconnecting: 'Reconnecting',
  offline: 'Offline',
};

const DOTS: Record<StreamStatus, string> = {
  connecting: 'bg-amber-400 animate-pulse',
  live: 'bg-emerald-400',
  reconnecting: 'bg-amber-400 animate-pulse',
  offline: 'bg-zinc-500',
};

/** Stream state as a coloured dot and a word, for the layer panel header. */
export function ConnectionStatus({ status }: { status: StreamStatus }) {
  return (
    <span
      role="status"
      className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-muted"
    >
      <span aria-hidden="true" className={`inline-block h-2 w-2 rounded-full ${DOTS[status]}`} />
      {LABELS[status]}
    </span>
  );
}
