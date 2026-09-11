import type { ReportJob } from '@/lib/api/reportJobs';
import { formatUtc } from '@/lib/format';

export function ReportJobBudget({ job }: { job: ReportJob }) {
  const number = (value: number) => value.toLocaleString('en-GB');
  return (
    <details className="job-budget">
      <summary>Model, usage and run details</summary>
      <dl>
        <div>
          <dt>Model</dt>
          <dd>{job.model}</dd>
        </div>
        <div>
          <dt>Thinking level</dt>
          <dd>{job.reasoning_effort ?? 'Provider default'}</dd>
        </div>
        <div>
          <dt>Model calls used</dt>
          <dd>
            {number(job.usage.calls)} of {number(job.usage.max_calls)}
          </dd>
        </div>
        <div>
          <dt>Output/reasoning tokens used or reserved</dt>
          <dd>
            {number(job.usage.output_tokens)} of {number(job.usage.output_allowance)}
          </dd>
        </div>
        <div>
          <dt>Unconfirmed calls</dt>
          <dd>{number(job.usage.uncertain_calls)}</dd>
        </div>
        <div>
          <dt>Started</dt>
          <dd>
            <time dateTime={job.created_at}>{formatUtc(job.created_at)}</time>
          </dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>
            <time dateTime={job.updated_at}>{formatUtc(job.updated_at)}</time>
          </dd>
        </div>
        <div>
          <dt>Destination</dt>
          <dd>{job.team_id ? 'Shared team workspace' : 'Personal workspace'}</dd>
        </div>
      </dl>
      <p>
        Unconfirmed calls retain their reserved allowance and may still incur provider charges.
        Input tokens are additional. This allowance is not a currency spending cap.
      </p>
    </details>
  );
}
