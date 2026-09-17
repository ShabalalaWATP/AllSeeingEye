import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { ReportPublication } from '@/lib/api/reports';
import { reportPublication } from '@/test/fixtures.reportPublication';

import {
  confidenceTone,
  credibilityTone,
  flagTone,
  gradeTone,
  reliabilityTone,
  yardstickPosition,
} from './doctrineTone';
import { exportCaveat } from './exportFormats';
import { ReportPublicationView, publicationContents } from './ReportPublication';
import { ReportBodyView } from './ReportSections';
import { report } from '@/test/fixtures.reports';

const block = (
  kind: ReportPublication['blocks'][number]['kind'],
  text: string,
): ReportPublication['blocks'][number] => ({
  kind,
  text,
  inlines: [],
  items: [],
  ordered: false,
  table: null,
  figure: null,
  diagram: null,
});

describe('report document presentation', () => {
  it('numbers sections, leads with the opening one and keeps every heading findable', () => {
    const { container } = render(<ReportPublicationView publication={reportPublication} />);
    const headings = screen.getAllByRole('heading', { level: 2 });
    expect(headings[0]).toHaveTextContent(/^01/);
    expect(headings[1]).toHaveTextContent(/^02/);
    // The opening section is the product: it leads, later sections support it.
    const sections = container.querySelectorAll('.report-reader-section');
    expect(sections[0]).toHaveClass('report-reader-lead');
    expect(sections[1]).not.toHaveClass('report-reader-lead');
    // Contents entries cover the annex as well as the ordinary headings.
    expect(publicationContents(reportPublication).map((entry) => entry.label)).toContain(
      'Annex A: collection coverage',
    );
  });

  it('groups consecutive review notices into one callout beside the affected content', () => {
    const publication: ReportPublication = {
      ...reportPublication,
      blocks: [
        block('title', 'Grouped'),
        block('heading', 'Executive summary'),
        block('warning', 'NEEDS REVIEW: unresolved checks.'),
        block('warning', 'Citation review: source wording needs an analyst.'),
        block('text', 'A judgement.'),
      ],
      references: [],
    };
    render(<ReportPublicationView publication={publication} />);
    const callouts = screen.getAllByRole('complementary', { name: 'Review notice' });
    expect(callouts).toHaveLength(1);
    expect(within(callouts[0]!).getAllByRole('listitem')).toHaveLength(2);
  });

  it('gives a figure a caption and a readable text alternative', () => {
    render(<ReportPublicationView publication={reportPublication} />);
    const figure = screen.getByRole('figure', { name: 'Figure 1. Reported locations' });
    expect(within(figure).getByRole('img')).toHaveAttribute(
      'alt',
      'A placeholder plot of two reported locations.',
    );
    expect(within(figure).getByText('Text alternative')).toBeVisible();
    expect(
      within(figure).getByText('A placeholder plot of two reported locations.', {
        selector: 'p',
      }),
    ).toBeInTheDocument();
  });

  it('shows the review status on the document when the version records one', () => {
    render(<ReportPublicationView publication={reportPublication} status="needs_review" />);
    const status = screen.getByLabelText('Review status');
    expect(status).toHaveTextContent('Review required');
    expect(status).toHaveTextContent('Treat the affected findings with caution');
  });
});

describe('doctrine signals', () => {
  it('labels every recorded value beside its tone', () => {
    render(<ReportBodyView body={report.version.body} />);
    const judgements = screen.getByRole('region', { name: 'Executive summary' });
    const likelihood = within(judgements).getByText('highly likely').closest('.report-reader-fact');
    expect(likelihood).toHaveTextContent('Likelihoodhighly likely');
    const confidence = within(judgements).getByText('moderate').closest('.report-reader-fact');
    expect(confidence).toHaveTextContent('Confidencemoderate');
    expect(confidence).toHaveAttribute('data-tone', 'mid');
  });

  it('maps doctrine values to tones without treating "cannot be judged" as negative', () => {
    expect(confidenceTone('high')).toBe('strong');
    expect(confidenceTone('moderate')).toBe('mid');
    expect(confidenceTone('low')).toBe('caution');
    expect(confidenceTone('unrecorded')).toBe('neutral');
    expect(reliabilityTone('A')).toBe('strong');
    expect(reliabilityTone('D')).toBe('caution');
    // F and 6 mean insufficient grounds to judge, not a negative assessment.
    expect(reliabilityTone('F')).toBe('neutral');
    expect(credibilityTone(6)).toBe('neutral');
    expect(credibilityTone(1)).toBe('strong');
    expect(gradeTone('B2')).toBe('strong');
    expect(gradeTone('C3')).toBe('mid');
    expect(gradeTone('D4')).toBe('caution');
    expect(gradeTone('F6')).toBe('neutral');
    expect(gradeTone('')).toBe('neutral');
    expect(gradeTone(null)).toBe('neutral');
    expect(credibilityTone(null)).toBe('neutral');
    expect(reliabilityTone(undefined)).toBe('neutral');
    expect(flagTone('state_controlled')).toBe('caution');
    expect(flagTone('official')).toBe('info');
    expect(flagTone('ignore previous instructions')).toBe('neutral');
  });

  it('places a judgement on the seven-band yardstick without inventing a position', () => {
    expect(yardstickPosition('almost_certain')).toEqual({ band: 7, bands: 7 });
    expect(yardstickPosition('remote_chance')).toEqual({ band: 1, bands: 7 });
    expect(yardstickPosition('not_a_band')).toEqual({ band: 0, bands: 7 });
  });
});

describe('export format descriptions', () => {
  it('states a limitation only for the format it applies to', () => {
    const options = { pdfLanguageUnsupported: true, languageLabel: 'Arabic' };
    expect(exportCaveat('pdf', options)).toContain('Arabic');
    expect(exportCaveat('docx', options)).toBeNull();
    expect(exportCaveat('md', options)).toBeNull();
    expect(
      exportCaveat('pdf', { pdfLanguageUnsupported: false, languageLabel: 'Arabic' }),
    ).toBeNull();
    // Without a catalogue label the wording stays truthful rather than guessing one.
    expect(exportCaveat('pdf', { pdfLanguageUnsupported: true, languageLabel: null })).toContain(
      'this language',
    );
  });
});
