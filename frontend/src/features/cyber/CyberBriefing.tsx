import { Link } from 'react-router';
import { IntelligenceSummary } from '@/components/research/IntelligenceSummary';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import type { CyberDays } from '@/lib/api/cyber';
import { formatUtc } from '@/lib/format';
import type { CyberBriefingState } from './useCyberWorkspace';

export function CyberBriefing({ state, days }: { state: CyberBriefingState; days: CyberDays }) {
  const { briefing, report, error, loading, retry } = state;
  const job = briefing?.job;
  const pending = job?.status === 'queued' || job?.status === 'running';
  return (
    <section aria-label="Cyber intelligence briefing" className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold">{days}-day cyber intelligence briefing</h2>
        <p className="mt-2 max-w-4xl text-sm leading-7 text-muted">
          A source-backed assessment of campaigns, ransomware claims, exploitation and defensive
          implications. This global report covers the selected period; the activity-list filters do
          not change its scope. Reused for 24 hours.
        </p>
      </header>
      {loading && <LoadingNote label="Loading your cyber briefing" />}
      {error && (
        <Alert tone="error">
          {describeError(error)}{' '}
          <Button variant="ghost" onClick={retry}>
            Retry cyber briefing
          </Button>
        </Alert>
      )}
      {briefing && (
        <div className="space-y-2 border-l-2 border-cyan pl-4">
          <p className="text-sm leading-6">
            Reporting period:{' '}
            <strong className="font-medium">
              {formatUtc(briefing.period_from)} to {formatUtc(briefing.period_to)}
            </strong>
          </p>
          <p className="text-xs text-muted">Next refresh {formatUtc(briefing.next_refresh_at)}</p>
        </div>
      )}
      {pending && (
        <div role="status" className="space-y-3">
          <p className="text-sm">Collecting cyber evidence and preparing the assessment…</p>
          <p className="text-xs text-muted">
            Research continues on the server while you explore this page.
          </p>
          {job.total_sections > 0 && (
            <progress
              aria-label="Cyber briefing sections completed"
              value={job.completed_sections}
              max={job.total_sections}
              className="h-1 w-full max-w-lg accent-ember"
            />
          )}
        </div>
      )}
      {job && !pending && !report && !error && (
        <Alert tone="warning">
          {job.status === 'paused'
            ? 'The cyber briefing is paused.'
            : 'The cyber briefing could not be completed.'}{' '}
          <Link className="text-ember underline" to={`/research/jobs/${job.id}`}>
            Review cyber research progress
          </Link>
        </Alert>
      )}
      {report && <IntelligenceSummary report={report} subject="Cyber" />}
      {briefing && (
        <p className="max-w-4xl text-xs leading-6 text-muted">{briefing.coverage_note}</p>
      )}
    </section>
  );
}
