import { Link, useParams } from 'react-router';
import { ResearchNavigation } from '@/components/research/ResearchNavigation';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { jobRunning, jobStage, jobStatus } from './jobLabels';
import { ReportJobSections } from './ReportJobSections';
import { ReportJobBudget } from './ReportJobBudget';
import { DiscardReportJob } from './DiscardReportJob';
import { useReportJob } from './useReportJob';
import './reportJobs.css';

export default function ReportJobPage() {
  const { id = '' } = useParams();
  const resource = useReportJob(id);
  const job = resource.data;
  return (
    <section className="report-jobs-page">
      <div className="report-jobs-workspace">
        <ResearchNavigation />
        <Link to="/research/jobs" className="job-back">
          ← Research jobs
        </Link>
        {resource.loading && <LoadingNote label="Loading research job" />}
        {resource.error && (
          <Alert tone="error">
            {describeError(resource.error)}{' '}
            <Button variant="secondary" onClick={resource.reload}>
              Retry job status
            </Button>
          </Alert>
        )}
        {job && (
          <>
            <header className="job-heading">
              <p className="job-eyebrow">
                Research job <span>{jobStatus[job.status]}</span>
              </p>
              <h1>{job.title}</h1>
              <p className="job-connection">
                {job.model} · Thinking: {job.reasoning_effort ?? 'provider default'}
              </p>
              <p className="job-continuity">
                {jobRunning(job)
                  ? 'You can leave this page or close the browser. Accepted research continues on the server.'
                  : job.status === 'paused'
                    ? 'This job is paused. Accepted sections are saved; resume when you are ready.'
                    : job.report_id
                      ? 'Research has finished. Open the report to review its findings and cited evidence.'
                      : 'Accepted sections remain saved. Review the job status before continuing.'}
              </p>
            </header>
            <div className="job-progress" data-running={jobRunning(job)}>
              <div className="job-progress-label">
                <p role="status">{jobStage(job.stage)}</p>
                <span>
                  {job.completed_sections} {job.completed_sections === 1 ? 'section' : 'sections'}{' '}
                  saved
                </span>
              </div>
              <progress
                aria-label={jobRunning(job) ? 'Research progress' : 'Saved research sections'}
                value={jobRunning(job) ? undefined : job.completed_sections}
                max={Math.max(1, job.total_sections)}
              />
              <div className="job-actions">
                {jobRunning(job) && (
                  <Button
                    variant="secondary"
                    busy={resource.busy}
                    onClick={() => void resource.control('pause')}
                  >
                    {resource.action === 'pause' ? 'Stopping…' : 'Stop'}
                  </Button>
                )}
                {job.can_resume && (
                  <Button busy={resource.busy} onClick={() => void resource.control('resume')}>
                    {resource.action === 'resume' ? 'Resuming…' : 'Resume research'}
                  </Button>
                )}
                {job.report_id && (
                  <Link className="job-report-link" to={`/reports/${job.report_id}`}>
                    Open completed report →
                  </Link>
                )}
                {jobRunning(job) && (
                  <span>Stop pauses this job and preserves accepted sections.</span>
                )}
              </div>
            </div>
            {resource.operationError && (
              <Alert tone="error">
                {describeError(resource.operationError)} Read the latest status before retrying.{' '}
                <Button variant="secondary" onClick={resource.reload}>
                  Refresh job
                </Button>
              </Alert>
            )}
            {job.error && <Alert tone="warning">{job.error}</Alert>}
            {job.usage.uncertain_calls > 0 && (
              <Alert tone="warning">
                A previous provider call has an unconfirmed outcome and may already have incurred
                usage. Resuming preserves accepted sections, but unfinished work may need another
                call.
              </Alert>
            )}
            {!jobRunning(job) && !job.can_resume && !job.report_id && (
              <p className="job-section-note">
                This job cannot currently resume. Review its error and remaining allowance before
                starting new research.
              </p>
            )}
            <ReportJobSections job={job} />
            <ReportJobBudget job={job} />
            {['paused', 'failed'].includes(job.status) && (
              <DiscardReportJob
                key={`${resource.key}:${job.id}:${job.status}`}
                busy={resource.busy}
                onDiscard={() => void resource.control('discard')}
              />
            )}
          </>
        )}
      </div>
    </section>
  );
}
