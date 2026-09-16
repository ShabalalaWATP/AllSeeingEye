/**
 * Shared block-level presentation for the semantic report document: inline runs,
 * citation markers, tables and figures. Nothing here interprets markup; every run
 * is rendered as text exactly as the backend projected it.
 */
import { SourceLink } from '@/components/ui/SourceLink';
import type { ReportPublication } from '@/lib/api/reports';
import { isHttpUrl } from '@/lib/urls';

type Block = ReportPublication['blocks'][number];
export type Inline = Block['inlines'][number];

export function CitationNumbers({ numbers }: { numbers: readonly number[] }) {
  if (!numbers.length) return null;
  return (
    <span className="report-reader-citation" aria-label={`References ${numbers.join(', ')}`}>
      [
      {numbers.map((number, index) => (
        <span key={number}>
          {index > 0 ? ', ' : ''}
          <a href={`#report-reference-${String(number)}`} aria-label={`View reference ${number}`}>
            {number}
          </a>
        </span>
      ))}
      ]
    </span>
  );
}

export function Inlines({ runs, fallback }: { runs: readonly Inline[]; fallback: string }) {
  if (!runs.length) return fallback;
  return runs.map((run, index) => {
    const key = `${index}:${run.text}`;
    if (!run.citation_numbers.length)
      return (
        <span key={key} dir={run.direction}>
          {run.text}
        </span>
      );
    return <CitationNumbers key={key} numbers={run.citation_numbers} />;
  });
}

/**
 * Tables keep the full page width and scroll horizontally on narrow screens. The
 * wrapper is focusable so the scroll region is reachable from the keyboard.
 */
export function TableBlock({ block }: { block: Block }) {
  if (!block.table) return null;
  const table = block.table;
  return (
    <figure className="report-reader-wide mt-8" aria-label={table.title}>
      <h3 className="report-reader-subheading">{table.title}</h3>
      {/* A focusable region keeps the horizontal scroll reachable from the keyboard. */}
      <div
        className="report-reader-table-wrap"
        tabIndex={0}
        role="region"
        aria-label={`${table.title} (scrollable table)`}
      >
        <table className="report-reader-table">
          <thead>
            <tr>
              {table.columns.map((column) => (
                <th key={column} scope="col">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex}>
                    <Inlines runs={cell.inlines} fallback={cell.text} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.caption && <figcaption className="report-reader-caption">{table.caption}</figcaption>}
    </figure>
  );
}

/**
 * A figure or diagram: a titled card, its caption, and the text alternative on the
 * page rather than only in the accessibility tree, since a described diagram is often
 * the only way a reader can check what it claims.
 */
export function FigureBlock({ block }: { block: Block }) {
  if (!block.figure) return null;
  const figure = block.figure;
  return (
    <figure className="report-reader-figure report-reader-wide" aria-label={figure.title}>
      <p className="report-reader-figure-label">Figure</p>
      <p className="mt-0.5 font-semibold leading-6">{figure.title}</p>
      <img
        src={`data:${figure.media_type};base64,${figure.content_base64}`}
        alt={figure.alt_text}
        width={figure.width_px}
        height={figure.height_px}
      />
      <figcaption className="report-reader-caption">
        {figure.caption}
        <CitationNumbers numbers={figure.citation_numbers} />
      </figcaption>
      {figure.alt_text && (
        <details>
          <summary>Text alternative</summary>
          <p className="mt-1">{figure.alt_text}</p>
        </details>
      )}
    </figure>
  );
}

export function References({
  publication,
  index,
}: {
  publication: ReportPublication;
  index: number;
}) {
  if (!publication.references.length) return null;
  return (
    <section id="report-references" aria-label="References" className="report-reader-section">
      <h2>
        <span className="report-reader-section-number" aria-hidden="true">
          {String(index).padStart(2, '0')}
        </span>
        <span>References</span>
      </h2>
      <p className="report-reader-note">
        {publication.references.length} cited source
        {publication.references.length === 1 ? '' : 's'}, numbered in order of first citation.
      </p>
      <ol className="mt-3">
        {publication.references.map((reference) => (
          <ReferenceRow key={reference.number} reference={reference} />
        ))}
      </ol>
    </section>
  );
}

function ReferenceRow({ reference }: { reference: ReportPublication['references'][number] }) {
  return (
    <li id={`report-reference-${String(reference.number)}`} className="report-reader-reference">
      <span className="font-mono text-xs text-[color:var(--paper-accent)]">
        [{reference.number}]
      </span>
      <div className="min-w-0">
        <p>
          <strong>{reference.publisher}.</strong> {reference.title}.{' '}
          {reference.published_at ?? 'Publication date not reported'}.
        </p>
        {reference.original_title && reference.original_title !== reference.title && (
          <p dir="auto" className="report-reader-note">
            Original title{reference.language ? ` (${reference.language})` : ''}:{' '}
            {reference.original_title}
          </p>
        )}
        <ReferenceLinks reference={reference} />
      </div>
    </li>
  );
}

function ReferenceLinks({ reference }: { reference: ReportPublication['references'][number] }) {
  return (
    <p className="report-reader-note flex flex-wrap items-center gap-x-4 gap-y-1">
      <ReferenceLink url={reference.url} label="Original source" />
      <ReferenceLink url={reference.archive_url} label="Archived copy" />
      <span>Accessed {reference.accessed_at.slice(0, 10)}</span>
    </p>
  );
}

/** Keeps the absence of a usable link visible instead of silently dropping it. */
function ReferenceLink({ url, label }: { url: string | null; label: string }) {
  if (!isHttpUrl(url)) return <span>No {label.toLowerCase()} recorded</span>;
  return <SourceLink url={url}>{label}</SourceLink>;
}
