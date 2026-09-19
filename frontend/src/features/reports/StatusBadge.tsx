import { STATUS_LABELS } from '@/lib/doctrine';

const STATUS_CLASSES: Record<string, string> = {
  ready: 'bg-emerald-400/15 text-emerald-300',
  needs_review: 'bg-amber-400/15 text-amber-300',
  failed: 'bg-critical/15 text-critical',
};

/** One report's doctrine status, named rather than coloured alone. */
export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded px-1.5 py-0.5 font-mono text-[11px] uppercase ${
        STATUS_CLASSES[status] ?? 'bg-zinc-500/15 text-muted'
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}
