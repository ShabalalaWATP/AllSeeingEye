import type { ReportJobStatusGroup } from '@/lib/api/reportJobs';
import type { ReportJobList } from './useReportJobList';

const FILTERS: readonly { value: ReportJobStatusGroup; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'attention', label: 'Needs attention' },
  { value: 'running', label: 'Running' },
  { value: 'finished', label: 'Finished' },
];

const pill =
  'min-h-10 rounded-md px-3 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember';

export function ReportJobFilters({ list }: { list: ReportJobList }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          role="group"
          aria-label="Show research runs"
          className="flex flex-wrap gap-1 rounded-lg bg-surface p-1"
        >
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              aria-pressed={list.status === filter.value}
              onClick={() => list.setStatus(filter.value)}
              className={`${pill} ${
                list.status === filter.value
                  ? 'bg-ember font-semibold text-ground'
                  : 'text-muted hover:bg-surface-2 hover:text-text'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
        <label className="flex min-h-10 items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            className="size-4 accent-ember"
            checked={list.includeBriefings}
            onChange={(event) => list.setBriefings(event.target.checked)}
          />
          Show automatic briefings
        </label>
      </div>
      <p className="text-xs leading-5 text-muted">
        Needs attention lists paused runs and runs that stopped with an error; each says whether it
        can resume. Running lists queued and in-progress runs. Finished lists saved reports,
        including those saved for review. Daily, economy and cyber briefings prepared by visiting
        those workspaces are hidden unless you show automatic briefings.
      </p>
    </div>
  );
}

export function ReportJobPager({ list }: { list: ReportJobList }) {
  return (
    <nav aria-label="Research run pages" className="flex flex-wrap items-center gap-3 text-sm">
      <button
        type="button"
        className={`${pill} border border-line text-text disabled:opacity-50`}
        disabled={!list.newer}
        onClick={list.newer ?? undefined}
      >
        Newer runs
      </button>
      <span className="text-muted">Page {list.page}</span>
      <button
        type="button"
        className={`${pill} border border-line text-text disabled:opacity-50`}
        disabled={!list.older}
        onClick={list.older ?? undefined}
      >
        Older runs
      </button>
    </nav>
  );
}
