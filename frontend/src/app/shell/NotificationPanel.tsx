import type { RefObject } from 'react';
import { Link } from 'react-router';

import { LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { ReportJob } from '@/lib/api/reportJobs';
import { formatUtc } from '@/lib/format';

import { BellAlertList, headingClass } from './BellAlertList';
import { BellSettings } from './BellSettings';
import type { BellAlertActions } from './useBellAlertActions';
import type { NotificationBellState } from './useNotificationBell';

const JOB_OUTCOME: Partial<Record<ReportJob['status'], string>> = {
  completed: 'Report ready',
  needs_review: 'Report needs review',
  failed: 'Stopped with an error',
};

const itemClass =
  'block rounded-md px-2 py-2 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember';
const footerLinkClass = 'text-sm text-ember underline-offset-2 hover:underline';

export function jobHref(job: ReportJob): string {
  return job.report_id !== null && job.status !== 'failed'
    ? `/reports/${job.report_id}`
    : `/research/jobs/${job.id}`;
}

function FinishedResearch({ state }: { state: NotificationBellState }) {
  const { jobs, close } = state;
  return (
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
  );
}

/** The bell's contents: alerts to act on and research that has finished, or the settings. */
export function NotificationPanel({
  state,
  actions,
  settings,
  headingRef,
  returnFocus,
}: {
  state: NotificationBellState;
  actions: BellAlertActions;
  settings: boolean;
  headingRef: RefObject<HTMLHeadingElement | null>;
  returnFocus: RefObject<HTMLElement | null>;
}) {
  const { alerts, jobs, close } = state;
  if (settings) return <BellSettings state={state} />;
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
  const showAlerts = !alerts.muted && (alerts.total > 0 || alerts.error !== null);
  const showJobs = !jobs.muted && (jobs.total > 0 || jobs.error !== null);
  const listNotice = actions.notice?.alertId === null && !showAlerts;
  const empty = !showAlerts && !showJobs;
  return (
    <div className="space-y-4">
      {empty && (
        <p className="px-2 text-sm text-muted">
          You are up to date.{' '}
          {alerts.muted || jobs.muted
            ? 'Some notification kinds are hidden by your settings.'
            : 'New alerts and finished research will appear here.'}
        </p>
      )}
      {(showAlerts || listNotice) && (
        <BellAlertList
          state={state}
          actions={actions}
          headingRef={headingRef}
          returnFocus={returnFocus}
        />
      )}
      {showJobs && <FinishedResearch state={state} />}
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
