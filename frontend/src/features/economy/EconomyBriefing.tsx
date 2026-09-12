import { Link } from 'react-router';
import { EconomySummary } from './EconomySummary';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { EconomyDays } from '@/lib/api/economyBriefing';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import type { EconomyBriefingState } from './useEconomyBriefing';

export function EconomyBriefing({
  days,
  state,
}: {
  days: EconomyDays;
  state: EconomyBriefingState;
}) {
  const { briefing, report, loading, error, retry } = state;
  const job = briefing?.job;
  const pending = job?.status === 'queued' || job?.status === 'running';
  return (
    <section aria-label="Daily economic analysis" className="space-y-5 border-y border-line py-7">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">{days}-day economic summary</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            A cited briefing on global trends and the UK, USA, Russia, China and Iran over the
            selected {days} days. Each period refreshes every 24 hours while this page is visible.
          </p>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-wider text-ember">
          AI assisted · source backed
        </span>
      </header>
      {briefing && (
        <p className="border-l-2 border-ember pl-4 text-sm leading-6">
          Reporting period:{' '}
          <strong className="font-medium">
            {formatUtc(briefing.period_from)} to {formatUtc(briefing.period_to)}
          </strong>
        </p>
      )}
      {loading && <LoadingNote label="Loading your economic briefing" />}
      {error && (
        <Alert tone="error">
          {describeError(error)}{' '}
          <Button variant="ghost" onClick={retry}>
            Retry economic briefing
          </Button>
        </Alert>
      )}
      {briefing && (
        <p className="flex flex-wrap gap-x-6 gap-y-2 font-mono text-[10px] text-muted">
          <span>
            {report ? 'Updated' : 'Started'}{' '}
            {formatUtc(report?.version.created_at ?? job?.created_at ?? '')}
          </span>
          <span>Next refresh {formatUtc(briefing.next_refresh_at)}</span>
        </p>
      )}
      {pending && (
        <div role="status" className="space-y-3 border-l-2 border-ember pl-4">
          <p className="text-sm">
            Collecting evidence and preparing your {days}-day economic summary…
          </p>
          <p className="text-xs text-muted">
            Research continues on the server while you explore. Returning here reuses the same
            briefing.
          </p>
          {job.total_sections > 0 && (
            <progress
              className="h-1 w-full max-w-lg accent-ember"
              aria-label="Economic briefing sections completed"
              value={job.completed_sections}
              max={job.total_sections}
            />
          )}
        </div>
      )}
      {job && !pending && !report && !error && (
        <Alert tone="warning">
          {job.status === 'paused'
            ? 'The economic briefing is paused.'
            : 'The economic briefing could not be completed.'}{' '}
          <Link className="text-ember underline" to={`/research/jobs/${job.id}`}>
            Review research progress
          </Link>
        </Alert>
      )}
      {report && <EconomySummary report={report} />}
      <p className="max-w-4xl text-xs leading-5 text-muted">
        {briefing?.coverage_note ??
          'Analysis uses collected economic reporting and published indicators. It does not see the external market chart. Source gaps and the observation dates of annual statistics remain part of the assessment.'}
      </p>
    </section>
  );
}
