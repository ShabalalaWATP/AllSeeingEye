import { Link } from 'react-router';

import { Button } from '@/components/ui/Button';
import type { ResearchStage } from '@/lib/api/researchProgress';

import type { ResearchProgressSnapshot } from '@/lib/hooks/useResearchProgress';

const stages: Record<ResearchStage, string> = {
  planning: 'Planning the research',
  collecting: 'Collecting relevant evidence',
  drafting: 'Drafting the report',
  challenging: 'Challenging the findings',
  validating: 'Checking the report',
  saving: 'Saving the report',
  completed: 'Report saved',
  cancelled: 'Research cancelled',
  failed: 'Research failed',
  timed_out: 'Research reached its time limit',
};

export interface ResearchProgressProps {
  snapshot: ResearchProgressSnapshot | null;
  active: boolean;
  onCancel: () => void;
}

export function ResearchProgress({ snapshot, active, onCancel }: ResearchProgressProps) {
  if (snapshot === null) return null;
  const cancelled = snapshot.outcome === 'cancelled';
  const title = cancelled
    ? 'Cancellation requested'
    : snapshot.outcome === 'completed'
      ? 'Report saved'
      : snapshot.outcome === 'failed'
        ? 'Research request ended'
        : snapshot.stage === null
          ? 'Starting research'
          : stages[snapshot.stage];
  return (
    <section aria-label="Research progress" className="space-y-3 border-t border-line pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p role="status" className="text-sm font-medium">
          {title}
        </p>
        {active && (
          <Button variant="secondary" onClick={onCancel}>
            Cancel research
          </Button>
        )}
      </div>
      {snapshot.unavailable && active && (
        <p className="text-xs text-muted">
          Live progress is unavailable. The research request is still pending.
        </p>
      )}
      {(cancelled || snapshot.outcome === 'failed') && (
        <p className="text-sm text-muted">
          A report being saved may still complete.{' '}
          <Link to="/reports" className="text-ember underline">
            Check Reports
          </Link>{' '}
          before starting again.
        </p>
      )}
    </section>
  );
}
