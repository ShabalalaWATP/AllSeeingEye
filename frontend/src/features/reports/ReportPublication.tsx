import type { ReactNode } from 'react';

import { SourceLink } from '@/components/ui/SourceLink';
import type { ReportPublication } from '@/lib/api/reports';

type Inline = ReportPublication['blocks'][number]['inlines'][number];

function sectionId(index: number, text: string): string {
  const slug = text
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 48);
  return `report-section-${String(index + 1)}-${slug || 'section'}`;
}

function Inlines({ runs, fallback }: { runs: readonly Inline[]; fallback: string }) {
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

function CitationNumbers({ numbers }: { numbers: readonly number[] }) {
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

function TableBlock({ block }: { block: ReportPublication['blocks'][number] }) {
  if (!block.table) return null;
  const table = block.table;
  return (
    <figure className="mt-8" aria-label={table.title}>
      <h3 className="report-reader-subheading">{table.title}</h3>
      <div className="report-reader-table-wrap">
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
      {table.caption && (
        <figcaption className="mt-2 text-xs text-[#6d675e]">{table.caption}</figcaption>
      )}
    </figure>
  );
}

function FigureBlock({ block }: { block: ReportPublication['blocks'][number] }) {
  if (!block.figure) return null;
  const figure = block.figure;
  return (
    <figure className="mt-8" aria-label={figure.title}>
      <h3 className="report-reader-subheading">{figure.title}</h3>
      <img
        className="mt-3 h-auto max-h-[42rem] w-full object-contain"
        src={`data:${figure.media_type};base64,${figure.content_base64}`}
        alt={figure.alt_text}
        width={figure.width_px}
        height={figure.height_px}
      />
      <figcaption className="mt-2 text-xs leading-5 text-[#6d675e]">
        {figure.caption}
        <CitationNumbers numbers={figure.citation_numbers} />
      </figcaption>
    </figure>
  );
}

function References({ publication }: { publication: ReportPublication }) {
  if (!publication.references.length) return null;
  return (
    <section id="report-references" aria-label="References" className="report-reader-section">
      <h2>References</h2>
      <ol className="mt-4">
        {publication.references.map((reference) => (
          <li
            key={reference.number}
            id={`report-reference-${String(reference.number)}`}
            className="report-reader-reference"
          >
            <span className="font-mono text-xs text-[#9b3b18]">[{reference.number}]</span>
            <div>
              <p>
                <strong>{reference.publisher}.</strong> {reference.title}.{' '}
                {reference.published_at ?? 'Publication date not reported'}.
              </p>
              {reference.original_title && reference.original_title !== reference.title && (
                <p dir="auto" className="mt-1 text-xs text-[#6d675e]">
                  Original title{reference.language ? ` (${reference.language})` : ''}:{' '}
                  {reference.original_title}
                </p>
              )}
              <p className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#6d675e]">
                <SourceLink url={reference.url}>Original source</SourceLink>
                <SourceLink url={reference.archive_url}>Archived copy</SourceLink>
                <span>Accessed {reference.accessed_at.slice(0, 10)}</span>
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function publicationContents(publication: ReportPublication) {
  return publication.blocks.flatMap((block, index) =>
    block.kind === 'heading' && block.text !== 'References'
      ? [{ id: sectionId(index, block.text), label: block.text }]
      : [],
  );
}

export function ReportPublicationView({ publication }: { publication: ReportPublication }) {
  const rendered: ReactNode[] = [];
  let section: { key: string; id: string; title: string; children: ReactNode[] } | null = null;
  const flushSection = () => {
    if (!section) return;
    const current = section;
    rendered.push(
      <section
        key={current.key}
        id={current.id}
        aria-label={current.title}
        className="report-reader-section"
      >
        <h2>{current.title}</h2>
        {current.children}
      </section>,
    );
    section = null;
  };
  const add = (node: ReactNode) => {
    if (section) section.children.push(node);
    else rendered.push(node);
  };
  publication.blocks.forEach((block, index) => {
    const key = `${index}:${block.kind}`;
    if (block.kind === 'reference') return;
    if (block.kind === 'heading' || block.kind === 'annex') {
      flushSection();
      if (block.text !== 'References')
        section = {
          key,
          id: sectionId(index, block.text),
          title: block.text,
          children: [],
        };
    } else if (block.kind === 'title') {
      add(
        <h1
          key={key}
          className="text-[clamp(2rem,5vw,3.25rem)] font-semibold leading-[1.05] tracking-[-0.045em] text-[#171512]"
        >
          {block.text}
        </h1>,
      );
    } else if (block.kind === 'metadata') {
      add(
        <p key={key} className="mt-2 font-mono text-[11px] leading-5 text-[#777066]">
          <Inlines runs={block.inlines} fallback={block.text} />
        </p>,
      );
    } else if (block.kind === 'subheading') {
      add(
        <h3 key={key} className="report-reader-subheading mt-5">
          {block.text}
        </h3>,
      );
    } else if (block.kind === 'list') {
      const List = block.ordered ? 'ol' : 'ul';
      add(
        <List
          key={key}
          className={`${block.ordered ? 'list-decimal' : 'list-disc'} mt-3 space-y-2 pl-5 marker:text-[#b9633e]`}
        >
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>
              <Inlines runs={item.inlines} fallback={item.text} />
            </li>
          ))}
        </List>,
      );
    } else if (block.kind === 'table') {
      add(<TableBlock key={key} block={block} />);
    } else if (block.kind === 'figure') {
      add(<FigureBlock key={key} block={block} />);
    } else if (block.kind === 'warning') {
      add(
        <p
          key={key}
          className="mt-4 border-l-2 border-[#c16a43] bg-[#f1e8dc] px-4 py-3 text-sm leading-6 text-[#5a3a2d]"
        >
          <Inlines runs={block.inlines} fallback={block.text} />
        </p>,
      );
    } else {
      add(
        <p key={key} className="report-reader-paragraph">
          <Inlines runs={block.inlines} fallback={block.text} />
        </p>,
      );
    }
  });
  flushSection();
  return (
    <div dir="auto" lang={publication.language} className="text-[0.94rem]">
      {rendered}
      <References publication={publication} />
    </div>
  );
}
