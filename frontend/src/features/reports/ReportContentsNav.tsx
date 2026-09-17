import { useRef } from 'react';

export interface ContentsEntry { id: string; label: string }

/** A collapsible jump list for narrow screens, closed again after a jump. */
export function MobileReportContents({ contents }: { contents: readonly ContentsEntry[] }) {
  const details = useRef<HTMLDetailsElement>(null);
  if (contents.length === 0) return null;
  return (
    <details
      ref={details}
      className="report-reader-print-hide mb-4 rounded-lg border border-line bg-surface px-4 py-3 lg:hidden"
    >
      <summary className="cursor-pointer text-sm font-medium text-text">Jump to section</summary>
      <nav aria-label="Mobile report contents" className="pt-3">
        <ol className="space-y-1 border-t border-line pt-3 text-sm text-muted">
          {contents.map((entry, index) => (
            <li key={entry.id}>
              <a
                className="flex gap-3 rounded px-1 py-1.5 hover:bg-surface-2 hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ember"
                href={`#${entry.id}`}
                onClick={() => details.current?.removeAttribute('open')}
              >
                <span aria-hidden="true" className="font-mono text-xs text-ember">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="min-w-0">{entry.label}</span>
              </a>
            </li>
          ))}
        </ol>
      </nav>
    </details>
  );
}

/** The sticky desktop contents rail beside the document. */
export function ReportContentsRail({ contents }: { contents: readonly ContentsEntry[] }) {
  if (contents.length === 0) return null;
  return (
    <aside className="report-reader-print-hide hidden lg:block" aria-label="Report contents">
      <nav className="sticky top-6 border-l border-line pl-4">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Contents</p>
        <ol className="mt-3 space-y-2 text-xs leading-5 text-muted">
          {contents.map((entry, index) => (
            <li key={entry.id}>
              <a
                className="flex gap-2 rounded py-0.5 transition-colors hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ember motion-reduce:transition-none"
                href={`#${entry.id}`}
              >
                <span aria-hidden="true" className="font-mono text-[10px] text-ember">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="min-w-0">{entry.label}</span>
              </a>
            </li>
          ))}
        </ol>
      </nav>
    </aside>
  );
}
