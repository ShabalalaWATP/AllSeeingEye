import type { ReportJob } from '@/lib/api/reportJobs';
import { formatAgo, formatUtc } from '@/lib/format';
import { useNow } from '@/lib/hooks/useNow';
import { jobRunning, jobStage } from './jobLabels';

function StartedNote({ job }: { job: ReportJob }) {
  const now = useNow();
  return <span>Started {formatAgo(job.created_at, now)}, including any time queued</span>;
}

/**
 * A known section total is shown as completed sections of that total: it says nothing about
 * remaining time or provider work. An unknown total stays indeterminate while work runs.
 */
export function ReportJobProgress({ job }: { job: ReportJob }) {
  const running = jobRunning(job);
  const known = job.total_sections > 0;
  const plural = job.completed_sections === 1 ? 'section' : 'sections';
  return (
    <>
      <div className="job-progress-label">
        <p role="status">{jobStage(job.stage)}</p>
        <span>
          {known
            ? `${job.completed_sections} of ${job.total_sections} ${job.total_sections === 1 ? 'section' : 'sections'} saved`
            : running
              ? 'Section count not known yet'
              : `${job.completed_sections} ${plural} saved`}
        </span>
      </div>
      {known ? (
        <progress
          aria-label="Sections completed"
          value={job.completed_sections}
          max={job.total_sections}
        />
      ) : (
        running && <progress aria-label="Research progress" />
      )}
      <p className="mt-3 text-xs text-muted">
        {running ? (
          <StartedNote job={job} />
        ) : (
          <span>
            Started {formatUtc(job.created_at)} · Last updated {formatUtc(job.updated_at)}
          </span>
        )}
      </p>
    </>
  );
}
