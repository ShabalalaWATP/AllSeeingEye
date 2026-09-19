/**
 * Renders the frozen semantic report document as structured React text.
 *
 * Presentation only: every heading, judgement, warning and reference comes from the
 * publication the backend froze for this version. Nothing here adds a claim, and no
 * value is parsed out of prose to decorate the page.
 */
import type { ReactNode } from 'react';

import type { ReportPublication, ReportStatus } from '@/lib/api/reports';

import {
  DiagramBlock,
  FigureBlock,
  Inlines,
  References,
  TableBlock,
  type Inline,
} from './publicationBlocks';
import { ReportReviewStatus } from './ReportReviewStatus';

type Block = ReportPublication['blocks'][number];

function sectionId(index: number, text: string): string {
  const slug = text
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 48);
  return `report-section-${String(index + 1)}-${slug || 'section'}`;
}

export function publicationContents(publication: ReportPublication) {
  return publication.blocks.flatMap((block, index) =>
    (block.kind === 'heading' || block.kind === 'annex') && block.text !== 'References'
      ? [{ id: sectionId(index, block.text), label: block.text }]
      : [],
  );
}

/** Consecutive warning blocks are one concern, so they read as one callout. */
function WarningCallout({ blocks }: { blocks: readonly Block[] }) {
  const first = blocks[0];
  if (!first) return null;
  return (
    <aside className="report-reader-callout" aria-label="Review notice">
      <p className="report-reader-callout-title">Review notice</p>
      {blocks.length === 1 ? (
        <p className="mt-1">
          <Inlines runs={first.inlines} fallback={first.text} />
        </p>
      ) : (
        <ul>
          {blocks.map((block, index) => (
            <li key={index}>
              <Inlines runs={block.inlines} fallback={block.text} />
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

function Masthead({
  title,
  colophon,
  status,
}: {
  title: string;
  colophon: readonly { text: string; inlines: readonly Inline[] }[];
  status: ReportStatus | undefined;
}) {
  return (
    <header className="report-reader-masthead">
      <p className="report-reader-eyebrow">Research report</p>
      <h1 className="report-reader-title">{title}</h1>
      {colophon.length > 0 && (
        <div className="report-reader-colophon">
          {colophon.map((block, index) => (
            <p key={index}>
              <Inlines runs={block.inlines} fallback={block.text} />
            </p>
          ))}
        </div>
      )}
      {status && (
        <div className="mt-4">
          <ReportReviewStatus status={status} variant="paper" />
        </div>
      )}
    </header>
  );
}

interface Section {
  key: string;
  id: string;
  title: string;
  index: number;
  children: ReactNode[];
}

interface Rendered {
  nodes: ReactNode[];
  section: Section | null;
}

function blockNode(block: Block, key: string): ReactNode {
  if (block.kind === 'subheading')
    return (
      <h3 key={key} className="report-reader-subheading">
        {block.text}
      </h3>
    );
  if (block.kind === 'metadata')
    return (
      <p key={key} className="report-reader-note font-mono">
        <Inlines runs={block.inlines} fallback={block.text} />
      </p>
    );
  if (block.kind === 'list') {
    const List = block.ordered ? 'ol' : 'ul';
    return (
      <List
        key={key}
        className={`${block.ordered ? 'list-decimal' : 'list-disc'} mt-3 space-y-2 pl-5 marker:text-[color:var(--paper-accent-soft)]`}
      >
        {block.items.map((item, itemIndex) => (
          <li key={itemIndex}>
            <Inlines runs={item.inlines} fallback={item.text} />
          </li>
        ))}
      </List>
    );
  }
  if (block.kind === 'table') return <TableBlock key={key} block={block} />;
  if (block.kind === 'figure') return <FigureBlock key={key} block={block} />;
  if (block.kind === 'diagram') return <DiagramBlock key={key} block={block} />;
  return (
    <p key={key} className="report-reader-paragraph">
      <Inlines runs={block.inlines} fallback={block.text} />
    </p>
  );
}

export function ReportPublicationView({
  publication,
  status,
}: {
  publication: ReportPublication;
  status?: ReportStatus | undefined;
}) {
  const blocks = publication.blocks;
  const state: Rendered = { nodes: [], section: null };
  let sectionCount = 0;
  const flush = () => {
    const current = state.section;
    if (!current) return;
    state.nodes.push(
      <section
        key={current.key}
        id={current.id}
        aria-label={current.title}
        // The opening section of an intelligence product carries its judgements, so
        // it leads the page. Later sections read as the supporting material.
        className={`report-reader-section${current.index === 1 ? ' report-reader-lead' : ''}`}
      >
        <h2>
          <span className="report-reader-section-number" aria-hidden="true">
            {String(current.index).padStart(2, '0')}
          </span>
          <span>{current.title}</span>
        </h2>
        {current.children}
      </section>,
    );
    state.section = null;
  };
  const add = (node: ReactNode) => {
    if (state.section) state.section.children.push(node);
    else state.nodes.push(node);
  };

  // Only the leading title and metadata blocks form the masthead; anything later in
  // the document keeps its own place so no frozen block is silently dropped.
  const leading: Block[] = [];
  for (const block of blocks) {
    if (block.kind === 'title' || block.kind === 'metadata') leading.push(block);
    else break;
  }
  const title = leading.find((block) => block.kind === 'title')?.text ?? publication.title;
  state.nodes.push(
    <Masthead
      key="masthead"
      title={title}
      colophon={leading.filter((block) => block.kind === 'metadata')}
      status={status}
    />,
  );

  let index = leading.length;
  while (index < blocks.length) {
    const block = blocks[index];
    if (!block) break;
    const key = `${index}:${block.kind}`;
    if (block.kind === 'reference') {
      index += 1;
      continue;
    }
    if (block.kind === 'title') {
      add(
        <h2 key={key} className="report-reader-subheading text-lg">
          {block.text}
        </h2>,
      );
      index += 1;
      continue;
    }
    if (block.kind === 'heading' || block.kind === 'annex') {
      flush();
      if (block.text !== 'References') {
        sectionCount += 1;
        state.section = {
          key,
          id: sectionId(index, block.text),
          title: block.text,
          index: sectionCount,
          children: [],
        };
      }
      index += 1;
      continue;
    }
    if (block.kind === 'warning') {
      const group: Block[] = [];
      while (blocks[index]?.kind === 'warning') {
        const warning = blocks[index];
        if (warning) group.push(warning);
        index += 1;
      }
      add(<WarningCallout key={key} blocks={group} />);
      continue;
    }
    add(blockNode(block, key));
    index += 1;
  }
  flush();
  return (
    <div dir="auto" lang={publication.language}>
      {state.nodes}
      <References publication={publication} index={sectionCount + 1} />
    </div>
  );
}
