import { Button } from '@/components/ui/Button';
import type { ExplainerProvenance, ExplainerStatus } from '@/lib/api/economyExplainer';
import { formatUtc } from '@/lib/format';
import { STATUS_NOTES } from './explainerModel';

const WRITTEN_BY =
  'Written by the model from the figures on this page. The figures are the source of truth.';

/** A small amber badge whenever the words are behind the figures or being rewritten. */
export function ExplainerBadge({ status }: { status: ExplainerStatus }) {
  if (status !== 'stale' && status !== 'generating') return null;
  return (
    <span
      className="rounded-full border border-amber/50 bg-amber/10 px-2 py-0.5 font-mono text-[10px] tracking-wider text-amber uppercase"
      data-testid="explainer-badge"
    >
      {status === 'stale' ? 'Figures moved on' : 'Updating'}
    </span>
  );
}

function written(provenance: ExplainerProvenance | null): string {
  if (!provenance) return '';
  return ` Model ${provenance.model}, written ${formatUtc(provenance.generated_at)} from figures retrieved ${formatUtc(provenance.snapshot_fetched_at)}.`;
}

export function ExplainerProvenanceNote({
  status,
  provenance,
  isAdmin,
  refreshing,
  onRefresh,
  compact = false,
}: {
  status: ExplainerStatus;
  provenance: ExplainerProvenance | null;
  isAdmin?: boolean;
  refreshing?: boolean;
  onRefresh?: (() => void) | undefined;
  compact?: boolean;
}) {
  const sources =
    !compact && provenance && provenance.sources.length > 0
      ? ` Written from: ${provenance.sources.join('; ')}.`
      : '';
  // "Ready" says nothing the source-of-truth line has not already said.
  const state = status === 'ready' ? '' : ` ${STATUS_NOTES[status]}`;
  return (
    <footer className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-t border-line pt-3 text-[11px] leading-5 text-muted">
      <p className="max-w-[100ch] min-w-0 flex-1">
        {WRITTEN_BY}
        {written(provenance)}
        {sources}
        {state}
      </p>
      {isAdmin && onRefresh ? (
        <Button variant="ghost" busy={refreshing ?? false} onClick={onRefresh}>
          Rewrite summary
        </Button>
      ) : null}
    </footer>
  );
}
