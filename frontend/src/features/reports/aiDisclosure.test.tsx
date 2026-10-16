import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { report, reportSummary } from '@/test/fixtures';
import { reportPublication } from '@/test/fixtures.reportPublication';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it.each([false, true])(
  'discloses AI assistance on the report page, including frozen publication=%s',
  async (published) => {
    const saved = structuredClone(report);
    saved.version.publication = published ? structuredClone(reportPublication) : null;
    server.use(http.get('/api/reports/:id', () => HttpResponse.json(saved)));
    renderApp('/reports/' + reportSummary.id, 'user');

    const label = await screen.findByText('AI-assisted assessment');
    expect(label).toBeVisible();
    expect(label.closest('.report-reader-paper')).not.toBeNull();
    expect(screen.getByText('Automated checks passed')).toBeVisible();
    expect(screen.getByText(/Check original sources and important details/)).toBeVisible();
  },
);

it('identifies a no-evidence gap notice without attributing it to AI', async () => {
  const saved = structuredClone(report);
  saved.version.findings = [
    {
      rule: 'no_evidence',
      severity: 'error',
      location: 'evidence',
      message: 'No eligible evidence.',
    },
  ];
  saved.version.attempts = 0;
  saved.version.publication = null;
  saved.version.body.key_judgements = [];
  saved.version.body.assessment = [];
  saved.version.body.reporting = [];
  server.use(http.get('/api/reports/:id', () => HttpResponse.json(saved)));
  renderApp('/reports/' + reportSummary.id, 'user');
  expect(await screen.findByText(/No AI assessment was generated/)).toBeVisible();
  expect(screen.queryByText('AI-assisted assessment')).not.toBeInTheDocument();
});
