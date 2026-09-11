import { Link } from 'react-router';
import { ResearchNavigation } from '@/components/research/ResearchNavigation';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchReportJobs } from '@/lib/api/reportJobs';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import { jobStage, jobStatus, jobsRunning } from './jobLabels';
import { useJobPolling } from './useJobPolling';
import './reportJobs.css';

export default function ReportJobsPage() {
  const resource = useJobPolling(fetchReportJobs, jobsRunning);
  return (
    <section className="report-jobs-page">
      <div className="report-jobs-workspace">
        <header className="job-list-heading">
          <div>
            <h1>Research jobs</h1>
            <p>Follow ongoing research, review partial sections and return to completed reports.</p>
          </div>
          <Link to="/research" className="job-report-link">
            New research →
          </Link>
        </header>
        <ResearchNavigation />
        {resource.loading && <LoadingNote label="Loading research jobs" />}
        {resource.error && (
          <Alert tone="error">
            {describeError(resource.error)}{' '}
            <Button variant="secondary" onClick={resource.reload}>
              Retry research jobs
            </Button>
          </Alert>
        )}
        {resource.data && (
          <>
            <div className="job-list-caption">
              <p>Your latest {resource.data.length} jobs</p>
              <Button variant="ghost" onClick={resource.reload}>
                Refresh
              </Button>
            </div>
            {resource.data.length === 0 ? (
              <div className="job-empty">
                <h2>No research jobs yet</h2>
                <p>Start a question from New research. Its progress will stay available here.</p>
              </div>
            ) : (
              <ul className="job-list" aria-label="Research jobs">
                {resource.data.map((job) => (
                  <li key={job.id}>
                    <Link to={`/research/jobs/${job.id}`}>
                      <div className="job-row-main">
                        <strong>{job.title}</strong>
                        <span>
                          {jobStage(job.stage)} · {job.completed_sections}{' '}
                          {job.completed_sections === 1 ? 'section' : 'sections'} saved
                        </span>
                      </div>
                      <div className="job-row-context">
                        <span>{jobStatus[job.status]}</span>
                        <time dateTime={job.updated_at}>{formatUtc(job.updated_at)}</time>
                      </div>
                      <span className="job-row-arrow" aria-hidden="true">
                        ↗
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </section>
  );
}
