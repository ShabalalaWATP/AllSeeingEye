import type { EvidenceItem, Finding } from '@/lib/api/reports';
import type { ReportAssessment } from '@/lib/api/reportAssessment';

import { EvidenceItemDetails } from './EvidenceItemDetails';
import './evidenceSignals.css';

/**
 * The frozen sources behind one report version. The index is scannable; the recorded
 * detail stays one disclosure away so the annex reads rather than dumps.
 */
export function EvidenceAnnex({
  evidence,
  findings,
  status,
  assessment,
}: {
  evidence: readonly EvidenceItem[];
  findings: readonly Finding[];
  status: string;
  assessment?: ReportAssessment | null | undefined;
}) {
  const warnings = findings.filter((finding) => finding.severity === 'warning');
  return (
    <div className="flex min-w-0 flex-col gap-4 text-sm">
      {status === 'ready' && warnings.length > 0 && (
        <details className="rounded border border-line bg-surface-2/40 px-3 py-2 text-xs text-muted">
          <summary className="cursor-pointer font-medium">
            {warnings.length} validator note{warnings.length === 1 ? '' : 's'}
          </summary>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {warnings.map((finding, index) => (
              <li key={index}>
                {finding.location}: {finding.message}
              </li>
            ))}
          </ul>
        </details>
      )}
      <section aria-label="Evidence annex" className="min-w-0">
        <header className="border-b border-line pb-3">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h2 className="text-base font-semibold">Evidence annex</h2>
            <p className="font-mono text-xs text-muted">
              {evidence.length} retained source{evidence.length === 1 ? '' : 's'}
            </p>
          </div>
          <p className="mt-2 max-w-prose text-xs leading-5 text-muted">
            Open a source to inspect its frozen metadata and snippet. Source content and
            translations are not independently verified.
          </p>
          <p className="mt-2 max-w-prose text-xs leading-5 text-muted">
            Each saved grade separates source reliability (A to F) from information credibility (1
            to 6). F6 means there was not enough basis to judge, not that the report was false. Open
            the Assessment tab for confidence limits and the UK probability yardstick.
          </p>
        </header>
        {evidence.length === 0 ? (
          <p className="mt-4 text-sm text-muted">No frozen evidence was saved for this version.</p>
        ) : (
          <div className="mt-1">
            {evidence.map((item) => (
              <EvidenceItemDetails
                key={item.label}
                item={item}
                assessment={assessment?.evidence.find((row) => row.label === item.label)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
