import { STATUS_LABELS } from '@/lib/doctrine';

const STATUS_CLASSES: Record<string, string> = {
  ready: 'bg-good/15 text-good',
  needs_review: 'bg-amber/15 text-amber',
  failed: 'bg-critical/15 text-critical',
};

/** One report's doctrine status, named rather than coloured alone. */
export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded px-1.5 py-0.5 font-mono text-2xs uppercase ${
        STATUS_CLASSES[status] ?? 'bg-muted/15 text-muted'
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}
