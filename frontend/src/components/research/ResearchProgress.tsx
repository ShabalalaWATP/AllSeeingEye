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
  onRetry?: (() => void) | undefined;
}

export function ResearchProgress({ snapshot, active, onCancel, onRetry }: ResearchProgressProps) {
  if (snapshot === null) return null;
  if (snapshot.submission)
    return (
      <section aria-label="Research progress" className="space-y-3 border-t border-line pt-4">
        <p role="status" className="text-sm font-medium">
          {active ? 'Starting your research job' : 'Submission not confirmed'}
        </p>
        <p className="text-sm text-muted">
          {active
            ? 'Once accepted, research continues on the server when you leave this page.'
            : 'The job may already be running. Check Research jobs before submitting again.'}
        </p>
        <div className="flex flex-wrap gap-3">
          {active ? (
            <Button variant="secondary" onClick={onCancel}>
              Stop waiting
            </Button>
          ) : (
            onRetry && (
              <Button variant="secondary" onClick={onRetry}>
                Retry this submission
              </Button>
            )
          )}
          <Link to="/research/jobs" className="py-2 text-sm text-ember underline">
            Research jobs
          </Link>
        </div>
        {!active && onRetry && (
          <p className="text-xs text-muted">
            Retry uses the original question and scope without creating a duplicate job.
          </p>
        )}
      </section>
    );
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
