import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';
import type { Report } from '@/lib/api/reports';
import { report } from '@/test/fixtures';
import { EconomySummary } from './EconomySummary';

function example(): Report {
  const result = structuredClone(report);
  result.version.body = {
    ...result.version.body,
    key_judgements: [
      {
        ...result.version.body.key_judgements[0]!,
        statement: 'Trade slowed while price pressures remained uneven.',
        supporting_evidence: ['E1'],
        contradicting_evidence: ['E2'],
        indicators: ['Watch the next official trade release.'],
      },
      {
        ...result.version.body.key_judgements[0]!,
        id: 'KJ2',
        statement: 'The currency change affects the cost of imported goods.',
        supporting_evidence: ['E1'],
        indicators: [
          'Watch the next official trade release.',
          'Monitor the next inflation release.',
        ],
      },
    ],
    assessment: [
      {
        heading: 'Trade exposure',
        text: 'The dated trade evidence indicates external exposure.\n\nA weaker exchange rate can raise import costs.',
        evidence: ['E1'],
      },
    ],
    reporting: [
      {
        theme: 'United Kingdom',
        items: [{ text: 'The UK published trade data.', evidence: ['E1'], grade: 'F6' }],
      },
      {
        theme: 'China',
        items: [{ text: 'China published manufacturing data.', evidence: ['E2'], grade: 'F6' }],
      },
    ],
    gaps: [{ text: 'Iranian exchange prices were unavailable.', eei: null }],
  };
  return result;
}

function show(value = example()) {
  return render(
    <MemoryRouter>
      <EconomySummary report={value} />
    </MemoryRouter>,
  );
}

it('provides an authored executive paragraph, separate key points and themed developments', () => {
  show();
  expect(
    within(screen.getByRole('region', { name: 'Executive summary' })).getByText(
      'Trade slowed while price pressures remained uneven.',
    ).tagName,
  ).toBe('P');
  expect(
    within(screen.getByRole('region', { name: 'Key points' })).getByText(
      'The currency change affects the cost of imported goods.',
    ),
  ).toBeInTheDocument();
  const developments = within(screen.getByRole('region', { name: 'Reported developments' }));
  expect(developments.getByRole('heading', { name: 'United Kingdom' })).toBeInTheDocument();
  expect(developments.getByRole('heading', { name: 'China' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Read full briefing and export' })).toHaveAttribute(
    'href',
    `/reports/${report.report.id}`,
  );
  expect(screen.queryByText(report.version.model)).not.toBeInTheDocument();
});

it('preserves authored paragraph boundaries and identifies watch conditions as uncertain', () => {
  show();
  const analysis = within(screen.getByRole('region', { name: 'Detailed assessment' }));
  expect(analysis.getByRole('heading', { name: 'Trade exposure' })).toBeInTheDocument();
  const lead = analysis.getByText('The dated trade evidence indicates external exposure.');
  const detail = analysis.getByText('A weaker exchange rate can raise import costs.');
  expect(lead.tagName).toBe('P');
  expect(detail.tagName).toBe('P');
  expect(lead).not.toBe(detail);
  const watch = within(screen.getByRole('region', { name: 'Developments to watch' }));
  expect(watch.getByText(/not confirmed future events or forecasts/)).toBeInTheDocument();
  expect(watch.getAllByText('Watch the next official trade release.')).toHaveLength(1);
  expect(screen.getByRole('region', { name: 'Coverage and limitations' })).toHaveTextContent(
    'Iranian exchange prices were unavailable.',
  );
});

it('deduplicates repeated claims and preserves contradictory evidence in the reference list', async () => {
  const value = example();
  const body = value.version.body;
  const repeated = body.key_judgements[0]!.statement;
  body.key_judgements = [{ ...body.key_judgements[0]!, contradicting_evidence: [] }];
  body.assessment = [{ heading: 'Same assessment', text: `  ${repeated} `, evidence: ['E2'] }];
  body.reporting = [
    { theme: 'Same reporting', items: [{ text: repeated, evidence: ['E1', 'E2'], grade: 'F6' }] },
  ];
  show(value);
  expect(screen.getAllByText(repeated)).toHaveLength(1);
  expect(screen.queryByRole('heading', { name: 'Same assessment' })).not.toBeInTheDocument();
  expect(screen.queryByRole('region', { name: 'Reported developments' })).not.toBeInTheDocument();
  const source = screen.getByRole('link', { name: 'Daily briefing reference 2' });
  await userEvent.setup().click(source);
  const target = document.getElementById(source.getAttribute('href')!.slice(1));
  expect(target).toBeVisible();
  expect(target).toHaveTextContent('Ministry statement');
  expect(screen.getAllByRole('link', { name: 'Open source' })).toHaveLength(1);
  expect(screen.getByRole('link', { name: 'Open source' })).toHaveAttribute(
    'href',
    'https://example.org/e1',
  );
});

it('reveals known supporting and contradictory sources without exposing invalid URLs', async () => {
  show();
  await userEvent
    .setup()
    .click(screen.getAllByRole('link', { name: 'Daily briefing reference 1' })[0]!);
  expect(screen.getByText(/BBC News World:/)).toBeVisible();
  expect(screen.getByText(/TASS English:/)).toBeVisible();
  expect(
    screen
      .getAllByRole('link')
      .every((link) => !link.getAttribute('href')?.startsWith('javascript:')),
  ).toBe(true);
  await userEvent.setup().click(screen.getByText('Sources cited in this summary (2)'));
  expect(screen.getByText(/TASS English:/)).not.toBeVisible();
});

it('flags unavailable citation labels without inventing a numbered source', () => {
  const value = example();
  value.version.body.key_judgements[0]!.supporting_evidence = ['missing', 'missing'];
  value.version.body.key_judgements[0]!.contradicting_evidence = [];
  show(value);
  expect(screen.getByText(/Some references could not be matched/)).toBeInTheDocument();
  const lead = within(screen.getByRole('region', { name: 'Executive summary' }));
  expect(lead.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.queryByText('[0]')).not.toBeInTheDocument();
  expect(screen.queryByText('missing')).not.toBeInTheDocument();
});

it('retains the review warning and report link when no usable summary is available', () => {
  const value = example();
  value.version.status = 'needs_review';
  value.version.body = {
    ...value.version.body,
    key_judgements: [],
    assessment: [],
    reporting: [],
    gaps: [],
  };
  show(value);
  expect(screen.getByText(/This briefing needs review/)).toBeInTheDocument();
  expect(
    screen.getByText(/not enough evidence for an overall economic assessment/),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Sources cited/)).not.toBeInTheDocument();
  expect(screen.queryByRole('region', { name: 'Developments to watch' })).not.toBeInTheDocument();
  expect(
    screen.queryByRole('region', { name: 'Coverage and limitations' }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Read full briefing and export' })).toBeInTheDocument();
});

it('falls back to the authored assessment once, without treating a reported event as an overall conclusion', () => {
  const value = example();
  value.version.body.key_judgements = [
    { ...value.version.body.key_judgements[0]!, statement: ' \n ', indicators: [''] },
  ];
  value.version.body.assessment = [
    { heading: 'Summary', text: 'An authored assessment.', evidence: ['E1'] },
  ];
  const { unmount } = show(value);
  expect(
    within(screen.getByRole('region', { name: 'Executive summary' })).getByText(
      'An authored assessment.',
    ),
  ).toBeInTheDocument();
  expect(screen.getAllByText('An authored assessment.')).toHaveLength(1);
  unmount();
  value.version.body.assessment = [];
  show(value);
  expect(
    screen.getByText(/not enough evidence for an overall economic assessment/),
  ).toBeInTheDocument();
  expect(screen.getByText('The UK published trade data.')).toBeInTheDocument();
});

it('bounds the preview while preserving a path to the full report', () => {
  const value = example();
  value.version.body.key_judgements = Array.from({ length: 20 }, (_, index) => ({
    ...value.version.body.key_judgements[0]!,
    id: `KJ${index}`,
    statement: `Authored conclusion ${index}.`,
    indicators: [`Watch condition ${index}.`],
  }));
  value.version.body.assessment = Array.from({ length: 30 }, (_, index) => ({
    heading: `Analysis ${index}`,
    text: `Authored analysis ${index}.`,
    evidence: ['E1'],
  }));
  value.version.body.reporting = [];
  show(value);
  expect(screen.getAllByText(/Authored conclusion \d+\./)).toHaveLength(8);
  expect(screen.getAllByText(/Authored analysis \d+\./)).toHaveLength(12);
  expect(
    within(screen.getByRole('region', { name: 'Developments to watch' })).getAllByRole('listitem'),
  ).toHaveLength(8);
  expect(screen.getByRole('link', { name: 'Read full briefing and export' })).toBeInTheDocument();
});

it('renders report text as inert text and keeps citation targets unique across summaries', () => {
  const value = example();
  value.version.body.key_judgements[0]!.statement = '<img src=x onerror=alert(1)>';
  render(
    <MemoryRouter>
      <EconomySummary report={value} />
      <EconomySummary report={value} />
    </MemoryRouter>,
  );
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(screen.getAllByText('<img src=x onerror=alert(1)>')).toHaveLength(2);
  const sections = screen.getAllByRole('article', { name: 'Economic briefing summary' });
  const targets = sections.map((section) =>
    within(section)
      .getAllByRole('link', { name: 'Daily briefing reference 1' })[0]!
      .getAttribute('href'),
  );
  expect(new Set(targets).size).toBe(2);
});
