import { Link } from 'react-router';
import { ResearchNavigation } from '@/components/research/ResearchNavigation';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { OwnershipScopeControl } from '@/components/workspace/OwnershipScopeControl';
import type { ReportJob, ReportJobStatusGroup } from '@/lib/api/reportJobs';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { ownerLabel } from '@/lib/ownershipScope';
import { jobStage, jobStatus } from './jobLabels';
import { ReportJobFilters, ReportJobPager } from './ReportJobListControls';
import { useReportJobList } from './useReportJobList';
import './reportJobs.css';

const EMPTY: Record<ReportJobStatusGroup, string> = {
  all: 'No research runs yet',
  attention: 'No research needs attention',
  running: 'No running research',
  finished: 'No finished research yet',
};

function attention(job: ReportJob) {
  if (job.status !== 'paused' && job.status !== 'failed') return null;
  return job.can_resume ? 'Can resume' : 'Cannot resume';
}

function JobRow({ job, owner }: { job: ReportJob; owner: string }) {
  const hint = attention(job);
  return (
    <li>
      <Link to={`/research/jobs/${job.id}`}>
        <div className="job-row-main">
          <strong>{job.title}</strong>
          <span>
            {owner} · {jobStage(job.stage)} · {job.completed_sections}{' '}
            {job.completed_sections === 1 ? 'section' : 'sections'} saved
            {job.origin === 'briefing' && ' · Automatic briefing'}
          </span>
        </div>
        <div className="job-row-context">
          <span>{jobStatus[job.status]}</span>
          {hint && <span className="mt-1 block text-2xs text-muted">{hint}</span>}
          <time dateTime={job.updated_at}>{formatUtc(job.updated_at)}</time>
        </div>
        <span className="job-row-arrow" aria-hidden="true">
          ↗
        </span>
      </Link>
    </li>
  );
}

export default function ReportJobsPage() {
  const list = useReportJobList();
  const workspaces = useWorkspaces();
  const items = list.data?.items ?? null;
  const owner = (job: ReportJob) =>
    ownerLabel(
      { team_id: job.team_id, ownerId: job.owner_id, ownerName: job.owner_name },
      workspaces.label,
      list.ownership.viewerId,
    );
  return (
    <section className="report-jobs-page">
      <div className="report-jobs-workspace">
        <header className="job-list-heading">
          <div>
            <h1>Research progress</h1>
            <p>Follow ongoing research, review partial sections and return to completed reports.</p>
          </div>
          <Link to="/research" className="job-report-link">
            New research →
          </Link>
        </header>
        <ResearchNavigation />
        <OwnershipScopeControl state={list.ownership} noun="research runs" />
        <ReportJobFilters list={list} />
        {list.loading && <LoadingNote label="Loading research progress" />}
        {list.error && (
          <Alert tone="error">
            {describeError(list.error)}{' '}
            <Button variant="secondary" onClick={list.reload}>
              Retry research progress
            </Button>
            {list.page > 1 && (
              <Button variant="ghost" onClick={list.newest}>
                Back to the newest runs
              </Button>
            )}
          </Alert>
        )}
        {items && (
          <>
            <div className="job-list-caption">
              <p role="status">
                Page {list.page} · {items.length} research {items.length === 1 ? 'run' : 'runs'}
              </p>
              <Button variant="ghost" onClick={list.reload}>
                Refresh
              </Button>
            </div>
            {items.length === 0 ? (
              <div className="job-empty">
                <h2>{EMPTY[list.status]}</h2>
                <p>
                  {list.page > 1
                    ? 'No further matching runs remain on this page.'
                    : 'Start a question from New research. Its progress will stay available here.'}
                </p>
              </div>
            ) : (
              <ul className="job-list" aria-label="Research runs">
                {items.map((job) => (
                  <JobRow key={job.id} job={job} owner={owner(job)} />
                ))}
              </ul>
            )}
          </>
        )}
        <ReportJobPager list={list} />
      </div>
    </section>
  );
}
