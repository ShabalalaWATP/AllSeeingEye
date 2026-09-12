import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';

import { DailyBriefingSummary } from './DailyBriefingSummary';
import { useDailyBriefing } from './useDailyBriefing';

export function DailyBriefing() {
  const { briefing, report, loading, error, retry } = useDailyBriefing();
  const job = briefing?.job;
  const pending = job?.status === 'queued' || job?.status === 'running';
  return (
    <section aria-label="Daily briefing" className="space-y-5 border-y border-line py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Daily briefing</h2>
          <p className="mt-1 text-sm text-muted">
            A daily situation summary of conflicts, global disasters and humanitarian developments.
          </p>
        </div>
        <span className="font-mono text-[11px] uppercase tracking-wider text-ember">
          24-hour update
        </span>
      </div>
      {loading && <LoadingNote label="Loading your daily briefing" />}
      {error && (
        <div className="space-y-3">
          <Alert tone="error">{describeError(error)}</Alert>
          <Button variant="secondary" onClick={retry}>
            Retry briefing
          </Button>
        </div>
      )}
      {briefing && (
        <p className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-[11px] text-muted">
          <span>
            {report ? 'Updated' : 'Started'}{' '}
            {formatUtc(report?.version.created_at ?? job?.created_at ?? '')}
          </span>
          <span>Next refresh {formatUtc(briefing.next_refresh_at)}</span>
        </p>
      )}
      {pending && (
        <div role="status" className="space-y-2">
          <p className="text-sm">Preparing the latest situation summary…</p>
          {job.total_sections > 0 && (
            <progress
              aria-label="Briefing sections completed"
              value={job.completed_sections}
              max={job.total_sections}
              className="h-1 w-full max-w-sm accent-ember"
            />
          )}
          <p className="text-xs text-muted">
            You can leave this page while it runs. The same briefing is reused for 24 hours.
          </p>
        </div>
      )}
      {job && !pending && !report && !error && (
        <div className="space-y-3">
          <Alert tone="warning">
            {job.status === 'paused'
              ? 'The daily briefing is paused.'
              : 'The daily briefing could not be completed.'}
          </Alert>
          <Link to={`/research/jobs/${job.id}`} className="text-sm text-ember hover:underline">
            Review briefing progress
          </Link>
        </div>
      )}
      {report && <DailyBriefingSummary report={report} />}
      <p className="text-xs leading-5 text-muted">
        {briefing?.coverage_note ??
          'The briefing covers available connected sources. Missing reporting is not evidence that a region is quiet.'}
      </p>
    </section>
  );
}
