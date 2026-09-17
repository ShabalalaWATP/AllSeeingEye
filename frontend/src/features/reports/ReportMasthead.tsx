import type { ReactNode } from 'react';
import { Link } from 'react-router';

/**
 * Workspace chrome above the document: where the reader is, which frozen version is
 * open, and the actions for it. The document's own title block lives on the paper.
 */
export function ReportMasthead({
  reportId,
  workspaceLabel,
  version,
  latestVersion,
  period,
  createdLabel,
  actions,
}: {
  reportId: string;
  workspaceLabel: string;
  version: number;
  latestVersion: number;
  period: string;
  createdLabel: string;
  actions: ReactNode;
}) {
  const versions = Array.from({ length: latestVersion }, (_, index) => index + 1);
  return (
    <header className="report-reader-print-hide mb-5 flex flex-col gap-3 border-b border-line pb-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Link
            to="/reports"
            className="rounded px-2 py-2 text-sm text-muted transition-colors hover:bg-surface hover:text-text motion-reduce:transition-none"
          >
            ← Reports
          </Link>
          <span className="hidden h-4 w-px bg-line sm:block" aria-hidden="true" />
          <p className="truncate text-xs text-muted">{workspaceLabel}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      </div>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <dl className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
          <MastheadFact label="Reporting period" value={period} mono />
          <MastheadFact label="Version created" value={createdLabel} mono />
        </dl>
        <nav aria-label="Versions" className="flex flex-wrap items-center gap-1 text-xs">
          <span className="mr-1 text-muted">Versions</span>
          {versions.map((number) => (
            <Link
              key={number}
              to={`/reports/${reportId}?version=${String(number)}`}
              aria-current={number === version ? 'page' : undefined}
              className={`rounded px-2 py-1 font-mono transition-colors motion-reduce:transition-none ${
                number === version
                  ? 'bg-surface-2 text-text ring-1 ring-ember/40'
                  : 'text-muted hover:bg-surface hover:text-text'
              }`}
            >
              {number}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}

function MastheadFact({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">{label}</dt>
      <dd className={`mt-0.5 text-text ${mono ? 'font-mono text-[11px] leading-5' : ''}`}>
        {value}
      </dd>
    </div>
  );
}
