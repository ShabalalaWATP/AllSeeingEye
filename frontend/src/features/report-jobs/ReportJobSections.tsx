import type { ReportJob } from '@/lib/api/reportJobs';
import { jobRunning } from './jobLabels';
import './reportJobSections.css';

const labels = {
  running: 'Writing',
  completed: 'Section accepted',
  split: 'Split into smaller sections',
  incomplete: 'Incomplete',
};
export function ReportJobSections({ job }: { job: ReportJob }) {
  return (
    <section className="job-sections" aria-label="Research sections">
      <header>
        <h2>Sections</h2>
        <p>
          Saved sections are a working draft. Final checks determine whether the report is ready or
          needs review.
        </p>
      </header>
      {job.sections.length === 0 && (
        <p className="job-empty">Sections will appear as research progresses.</p>
      )}
      {job.sections.map((section, index) => (
        <details key={section.id} className="job-section">
          <summary>
            <span className="job-section-number">{String(index + 1).padStart(2, '0')}</span>
            <span className="job-section-title">
              {section.title}
              <small>
                {section.kind === 'synthesis'
                  ? 'Overall synthesis'
                  : section.status === 'running' && !jobRunning(job)
                    ? 'Unfinished'
                    : labels[section.status]}
                {section.status === 'incomplete' && section.error && <> · {section.error}</>}
              </small>
            </span>
            <span
              className="job-section-indicator"
              data-complete={section.status === 'completed'}
              aria-hidden="true"
            >
              {section.status === 'completed' ? '✓' : '+'}
            </span>
          </summary>
          <div className="job-section-body">
            {(section.reporting?.length ?? 0) > 0 && (
              <div>
                <h3>Reporting</h3>
                {section.reporting?.map((text, item) => (
                  <p key={item}>{text}</p>
                ))}
              </div>
            )}
            {section.assessment && (
              <div>
                <h3>Assessment</h3>
                <p>{section.assessment}</p>
              </div>
            )}
            {(section.gaps?.length ?? 0) > 0 && (
              <div>
                <h3>Evidence gaps</h3>
                {section.gaps?.map((text, item) => (
                  <p key={item}>{text}</p>
                ))}
              </div>
            )}
            {(section.citations?.length ?? 0) > 0 && (
              <p className="job-citations">Evidence labels: {section.citations?.join(' · ')}</p>
            )}
            {section.error && <p className="job-section-note">{section.error}</p>}
            {!section.reporting?.length &&
              !section.assessment &&
              !section.gaps?.length &&
              !section.error && <p>This section is still being prepared.</p>}
          </div>
        </details>
      ))}
    </section>
  );
}
