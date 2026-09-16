/**
 * Development-only page (registered when import.meta.env.DEV) that frames the report
 * reader against a frozen publication fixture, so the document, its review status and
 * the export menu can be inspected at any width without an account. Nothing here
 * reaches the API with a credential.
 */
import { useSyncExternalStore } from 'react';

import { MobileReportContents, ReportContentsRail } from '@/features/reports/ReportContentsNav';
import { ReportExports } from '@/features/reports/ReportExports';
import { ReportMasthead } from '@/features/reports/ReportMasthead';
import {
  publicationContents,
  ReportPublicationView,
} from '@/features/reports/ReportPublication';
import '@/features/reports/reportReader.css';
import type { ReportStatus } from '@/lib/api/reports';
import { reportPublication } from '@/test/fixtures.reportPublication';

const VIEWS = ['needs_review', 'ready', 'failed'] as const;
type View = (typeof VIEWS)[number];

const subscribe = (onChange: () => void) => {
  window.addEventListener('hashchange', onChange);
  return () => window.removeEventListener('hashchange', onChange);
};
const readView = (): View => {
  const hash = window.location.hash.replace('#', '');
  return VIEWS.find((view) => view === hash) ?? 'needs_review';
};

export default function ReportPreviewPage() {
  const view = useSyncExternalStore(subscribe, readView, () => 'needs_review' as View);
  const status: ReportStatus = view;
  const contents = publicationContents(reportPublication);
  return (
    <section
      aria-label="Report reader"
      className="report-reader-shell h-full min-w-0 overflow-y-auto"
    >
      <div className="report-reader-frame px-3 py-4 sm:px-6 sm:py-6">
        <nav aria-label="Preview status" className="mb-4 flex flex-wrap gap-2 text-xs">
          {VIEWS.map((entry) => (
            <a
              key={entry}
              href={`#${entry}`}
              aria-current={entry === view ? 'page' : undefined}
              className={`rounded border px-3 py-1.5 ${
                entry === view
                  ? 'border-ember/60 bg-ember/10 text-text'
                  : 'border-line text-muted hover:text-text'
              }`}
            >
              {entry}
            </a>
          ))}
        </nav>
        <ReportMasthead
          reportId="preview"
          workspaceLabel="Personal workspace"
          version={2}
          latestVersion={3}
          period="2026-09-03 01:00 UTC to 2026-09-05 01:00 UTC"
          createdLabel="5 September 2026, 01:00 UTC"
          actions={
            <>
              <button
                type="button"
                className="rounded-md border border-cyan/50 bg-cyan/10 px-3 py-2 text-sm font-medium text-text"
              >
                Ask Eye about this version
              </button>
              <button
                type="button"
                className="rounded-md border border-line px-3 py-2 text-sm font-medium text-text"
              >
                Sources &amp; methods
              </button>
              <ReportExports
                id="preview"
                version={2}
                title={reportPublication.title}
                status={status}
                language="ar"
              />
            </>
          }
        />
        <MobileReportContents contents={contents} />
        <div className={contents.length ? 'lg:grid lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-8' : ''}>
          <ReportContentsRail contents={contents} />
          <article className="report-reader-paper report-reader-enter min-w-0 overflow-hidden rounded-card">
            <div className="report-reader-content">
              <ReportPublicationView publication={reportPublication} status={status} />
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
