import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { reportPublicationSchema, type ReportPublication } from '@/lib/api/reports';

import { publicationContents, ReportPublicationView } from './ReportPublication';

const citation = { text: '[1]', direction: 'ltr' as const, citation_numbers: [1] };
const publication: ReportPublication = {
  schema_version: 1,
  title: 'Regional assessment',
  reference: 'Report example | version 2',
  language: 'en',
  blocks: [
    {
      kind: 'title',
      text: 'Regional assessment',
      inlines: [],
      items: [],
      ordered: false,
      table: null,
      figure: null,
    },
    {
      kind: 'heading',
      text: 'Executive summary',
      inlines: [],
      items: [],
      ordered: false,
      table: null,
      figure: null,
    },
    {
      kind: 'text',
      text: 'Activity increased [1]',
      inlines: [{ text: 'Activity increased ', direction: 'auto', citation_numbers: [] }, citation],
      items: [],
      ordered: false,
      table: null,
      figure: null,
    },
    {
      kind: 'table',
      text: 'Date\tObservation\n2026-09-11\tActivity [1]',
      inlines: [],
      items: [],
      ordered: false,
      table: {
        title: 'Event chronology',
        columns: ['Date', 'Observation'],
        rows: [
          [
            { text: '2026-09-11', inlines: [] },
            {
              text: 'Activity [1]',
              inlines: [{ text: 'Activity ', direction: 'auto', citation_numbers: [] }, citation],
            },
          ],
        ],
        caption: 'Source-reported dates.',
      },
      figure: null,
    },
    {
      kind: 'diagram',
      text: 'Movement recorded on 11 September, then activity on 12 September.',
      inlines: [],
      items: [],
      ordered: false,
      table: null,
      figure: null,
      diagram: {
        title: 'Sequence of reported activity',
        caption: 'Drawn by the application from the cited reporting.',
        alt_text: 'Movement recorded on 11 September, then activity on 12 September.',
        content_base64: btoa("<svg xmlns='http://www.w3.org/2000/svg'></svg>"),
        media_type: 'image/svg+xml',
        citation_numbers: [1],
      },
    },
    {
      kind: 'heading',
      text: 'References',
      inlines: [],
      items: [],
      ordered: false,
      table: null,
      figure: null,
    },
    {
      kind: 'reference',
      text: '[1] Example source',
      inlines: [],
      items: [],
      ordered: false,
      table: null,
      figure: null,
    },
  ],
  references: [
    {
      number: 1,
      evidence_label: 'E1',
      title: 'Activity report',
      original_title: null,
      publisher: 'Example source',
      language: 'en',
      published_at: '2026-09-11',
      accessed_at: '2026-09-12T00:00:00Z',
      url: 'https://example.org/report',
      archive_url: null,
    },
  ],
};

describe('professional report publication', () => {
  it('renders the canonical blocks, linked numeric citations and one reference list', () => {
    render(<ReportPublicationView publication={publication} />);
    expect(screen.getByRole('heading', { name: 'Regional assessment' })).toBeInTheDocument();
    // The paragraph, the table cell and the diagram caption each cite reference one.
    expect(screen.getAllByRole('link', { name: 'View reference 1' })).toHaveLength(3);
    const table = screen.getByRole('table');
    expect(within(table).getByText('2026-09-11')).toBeInTheDocument();
    const references = screen.getByRole('region', { name: 'References' });
    expect(within(references).getByText(/Activity report/)).toBeInTheDocument();
    expect(within(references).getByRole('link', { name: 'Original source' })).toHaveAttribute(
      'href',
      'https://example.org/report',
    );
    expect(screen.getAllByRole('heading', { name: 'References' })).toHaveLength(1);
  });

  it('draws a diagram as an image and keeps its words on the page', () => {
    render(<ReportPublicationView publication={reportPublicationSchema.parse(publication)} />);
    const figure = screen.getByRole('figure', { name: 'Sequence of reported activity' });
    const image = within(figure).getByRole('img', {
      name: 'Movement recorded on 11 September, then activity on 12 September.',
    });
    // An image source, never markup inserted into the page.
    expect(image).toHaveAttribute('src', expect.stringContaining('data:image/svg+xml;base64,'));
    expect(figure).toHaveTextContent('Drawn by the application from the cited reporting.');
    expect(within(figure).getByText('Text alternative')).toBeVisible();
    expect(within(figure).getByRole('link', { name: 'View reference 1' })).toBeVisible();
  });

  it('links every source in a multi-reference citation independently', () => {
    const multi: ReportPublication = {
      ...publication,
      blocks: publication.blocks.map((block, index) =>
        index === 2
          ? {
              ...block,
              text: 'Activity increased [1, 2]',
              inlines: [
                { text: 'Activity increased ', direction: 'auto', citation_numbers: [] },
                { text: '[1, 2]', direction: 'ltr', citation_numbers: [1, 2] },
              ],
            }
          : block,
      ),
      references: [
        ...publication.references,
        {
          ...publication.references[0]!,
          number: 2,
          evidence_label: 'E2',
          title: 'Independent report',
          url: 'https://example.net/report',
        },
      ],
    };
    render(<ReportPublicationView publication={multi} />);
    expect(screen.getByRole('link', { name: 'View reference 2' })).toHaveAttribute(
      'href',
      '#report-reference-2',
    );
    expect(screen.getAllByRole('link', { name: 'View reference 1' })[0]).toHaveAttribute(
      'href',
      '#report-reference-1',
    );
  });

  it('builds contents from reader headings and rejects active figure media', () => {
    expect(publicationContents(publication)).toEqual([
      { id: 'report-section-2-executive-summary', label: 'Executive summary' },
    ]);
    expect(() =>
      reportPublicationSchema.parse({
        ...publication,
        blocks: [
          {
            ...publication.blocks[0],
            kind: 'figure',
            figure: {
              title: 'Unsafe',
              caption: '',
              alt_text: 'Unsafe vector image',
              content_base64: 'PHN2Zz4=',
              media_type: 'image/svg+xml',
              width_px: 10,
              height_px: 10,
              citation_numbers: [],
            },
          },
        ],
      }),
    ).toThrow();
  });
});
