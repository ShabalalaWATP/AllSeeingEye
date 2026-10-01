import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { resetYardstick } from '@/lib/hooks/useYardstick';
import { useAuthStore } from '@/stores/auth';
import { plainUser, report, reportSummary, tokenFor } from '@/test/fixtures';
import { reportMethodology } from '@/test/fixtures.reportAssessment';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { EvidenceAnnex } from './EvidenceAnnex';
import { DirectionView, ReportBodyView } from './ReportSections';

/** The backend's configured bands (domain/doctrine.py YARDSTICK), as the API describes them. */
const BANDS = [
  ['remote_chance', 'remote chance', 0, 5, 'above 0 to about 5 percent'],
  ['highly_unlikely', 'highly unlikely', 10, 20, 'about 10 to about 20 percent'],
  ['unlikely', 'unlikely', 25, 35, 'about 25 to about 35 percent'],
  ['realistic_possibility', 'realistic possibility', 40, 50, 'about 40 to under 50 percent'],
  ['likely', 'likely', 55, 75, 'about 55 to about 75 percent'],
  ['highly_likely', 'highly likely', 80, 90, 'about 80 to about 90 percent'],
  ['almost_certain', 'almost certain', 95, 100, 'about 95 to under 100 percent'],
] as const;

function configuredYardstick() {
  server.use(
    http.get('/api/report-methodology', () =>
      HttpResponse.json({
        ...reportMethodology,
        probability_yardstick: BANDS.map(([probability, term, low, high, range]) => ({
          probability,
          term,
          low_percent: low,
          high_percent: high,
          range_description: range,
        })),
      }),
    ),
  );
}

const judgement = report.version.body.key_judgements[0]!;
const bodyWith = (probabilities: string[]) => ({
  ...report.version.body,
  key_judgements: probabilities.map((probability, index) => ({
    ...judgement,
    id: `KJ${String(index + 1)}`,
    probability,
  })),
});

beforeEach(() => {
  resetYardstick();
  useAuthStore.getState().setSession(tokenFor(plainUser));
});

describe('research terminology', () => {
  it('shows every configured likelihood band as text and labels unknown terms honestly', async () => {
    configuredYardstick();
    render(<ReportBodyView body={bodyWith([...BANDS.map(([value]) => value), 'maybe'])} />);
    const summary = screen.getByRole('region', { name: 'Executive summary' });
    for (const [, , , , range] of BANDS)
      expect(await within(summary).findByText(range)).toBeVisible();
    expect(within(summary).getByText('No configured band for this term')).toBeVisible();
  });

  it('says when the bands cannot be loaded instead of guessing', async () => {
    server.use(
      http.get('/api/report-methodology', () =>
        HttpResponse.json({ error: { code: 'server_error', message: 'Down' } }, { status: 500 }),
      ),
    );
    render(<ReportBodyView body={bodyWith(['likely'])} />);
    expect(await screen.findByText('Band unavailable')).toBeVisible();
    expect(screen.queryByText(/percent/)).not.toBeInTheDocument();
  });

  it('opens and closes the likelihood explanation from the keyboard and restores focus', async () => {
    configuredYardstick();
    const user = userEvent.setup();
    render(<ReportBodyView body={bodyWith(['likely'])} />);
    const trigger = screen.getByRole('button', { name: 'How to read likelihood and confidence' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    trigger.focus();
    await user.keyboard('{Enter}');
    const panel = screen.getByRole('region', { name: 'How to read likelihood and confidence' });
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(panel).toHaveTextContent('not a measured probability');
    expect(await within(panel).findByText(/likely: about 55 to about 75 percent/)).toBeVisible();
    await user.keyboard('{Escape}');
    expect(
      screen.queryByRole('region', { name: 'How to read likelihood and confidence' }),
    ).toBeNull();
    expect(trigger).toHaveFocus();
  });

  it('expands PIR, SIR and EEI once beside the codes and keeps the codes concise', () => {
    render(
      <DirectionView
        direction={{
          pir: 'What will happen?',
          sirs: ['Where?', 'When?'],
          eeis: ['Who?'],
          search_terms: [],
          categories: [],
        }}
      />,
    );
    const direction = screen.getByRole('region', { name: 'Direction' });
    expect(within(direction).getAllByText(/priority intelligence requirement/)).toHaveLength(1);
    expect(within(direction).getAllByText(/specific intelligence requirement/)).toHaveLength(1);
    expect(within(direction).getAllByText(/essential element of information/)).toHaveLength(1);
    expect(within(direction).getByText('SIR-2')).toBeVisible();
    expect(within(direction).getByRole('link', { name: 'Glossary of terms' })).toHaveAttribute(
      'href',
      '/help#glossary',
    );
  });

  it('links evidence grades to an explanation that does not present them as proof', () => {
    render(<EvidenceAnnex evidence={[]} findings={[]} status="ready" />);
    expect(screen.getByRole('link', { name: 'What source grades mean' })).toHaveAttribute(
      'href',
      '/help#glossary-source-grades',
    );
    expect(screen.getByText(/A grade is not proof that a claim is true/)).toBeVisible();
  });

  it('keeps a glossary in Help, linked from the report reader', async () => {
    configuredYardstick();
    const view = renderApp(`/reports/${reportSummary.id}`, 'user');
    const link = await screen.findByRole('link', { name: 'Glossary of report terms' });
    expect(link).toHaveAttribute('href', '/help#glossary');
    view.unmount();
    renderApp('/help', 'user');
    const glossary = await screen.findByRole('region', { name: 'Glossary' });
    for (const term of [
      'PIR (priority intelligence requirement)',
      'SIR (specific intelligence requirement)',
      'EEI (essential element of information)',
      'Likelihood',
      'Source reliability and information credibility',
      'Alert rule',
    ])
      expect(within(glossary).getByText(term)).toBeVisible();
    expect(
      await within(glossary).findByText(/almost certain: about 95 to under 100 percent/),
    ).toBeVisible();
    expect(within(glossary).getByText(/it is not proof that a claim is true/)).toBeVisible();
  });
});
