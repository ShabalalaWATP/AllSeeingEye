import { Link } from 'react-router';

import { LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { ReportJob } from '@/lib/api/reportJobs';
import { formatUtc } from '@/lib/format';

import type { NotificationBellState } from './useNotificationBell';

const JOB_OUTCOME: Partial<Record<ReportJob['status'], string>> = {
  completed: 'Report ready',
  needs_review: 'Report needs review',
  failed: 'Stopped with an error',
};

const itemClass =
  'block rounded-md px-2 py-2 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember';
const headingClass = 'px-2 font-mono text-xs tracking-widest text-muted uppercase';
const footerLinkClass = 'text-sm text-ember underline-offset-2 hover:underline';

export function jobHref(job: ReportJob): string {
  return job.report_id !== null && job.status !== 'failed'
    ? `/reports/${job.report_id}`
    : `/research/jobs/${job.id}`;
}

/** The bell's contents: alerts to acknowledge and research that has finished. */
export function NotificationPanel({ state }: { state: NotificationBellState }) {
  const { alerts, jobs, close } = state;
  if (state.loading && alerts.items.length === 0 && jobs.items.length === 0)
    return <LoadingNote label="Checking for notifications…" />;
  if (alerts.error && jobs.error)
    return (
      <div role="alert" className="space-y-2 px-2 text-sm">
        <p>Notifications could not be loaded.</p>
        <Button variant="secondary" onClick={state.retry}>
          Try again
        </Button>
      </div>
    );
  const empty = alerts.total === 0 && jobs.total === 0 && !alerts.error && !jobs.error;
  return (
    <div className="space-y-4">
      {empty && (
        <p className="px-2 text-sm text-muted">
          You are up to date. New alerts and finished research will appear here.
        </p>
      )}
      {(alerts.total > 0 || alerts.error) && (
        <section aria-label="Unacknowledged alerts">
          <h3 className={headingClass}>Alerts to review</h3>
          {alerts.error ? (
            <p className="px-2 pt-1 text-sm text-muted">Alerts could not be loaded.</p>
          ) : (
            <ul className="mt-1">
              {alerts.items.map((alert) => (
                <li key={alert.id}>
                  <Link to="/warning" onClick={close} className={itemClass}>
                    <span className="block text-sm text-text">{alert.title}</span>
                    <span className="mt-0.5 block text-xs text-muted">
                      Fired {formatUtc(alert.fired_at)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {alerts.total > alerts.items.length && (
            <p className="px-2 pt-1 text-xs text-muted">
              {alerts.total - alerts.items.length} more on the alerts page
            </p>
          )}
        </section>
      )}
      {(jobs.total > 0 || jobs.error) && (
        <section aria-label="Finished research">
          <h3 className={headingClass}>Finished research</h3>
          {jobs.error ? (
            <p className="px-2 pt-1 text-sm text-muted">Research progress could not be loaded.</p>
          ) : (
            <ul className="mt-1">
              {jobs.items.map(({ job, isNew }) => (
                <li key={job.id}>
                  <Link to={jobHref(job)} onClick={close} className={itemClass}>
                    <span className="flex items-baseline justify-between gap-2">
                      <span className="text-sm text-text">{job.title}</span>
                      {isNew && (
                        <span className="shrink-0 rounded border border-ember/60 px-1 font-mono text-xs text-ember uppercase">
                          New
                        </span>
                      )}
                    </span>
                    <span className="mt-0.5 block text-xs text-muted">
                      {JOB_OUTCOME[job.status]} · {formatUtc(job.updated_at)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {(alerts.error ?? jobs.error) && (
        <Button variant="ghost" className="min-h-11" onClick={state.retry}>
          Try again
        </Button>
      )}
      <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-line px-2 pt-3">
        <Link to="/warning" onClick={close} className={footerLinkClass}>
          All alerts
        </Link>
        <Link to="/research/jobs" onClick={close} className={footerLinkClass}>
          Research progress
        </Link>
      </div>
    </div>
  );
}
