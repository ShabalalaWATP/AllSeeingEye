import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { ReportPublication } from '@/lib/api/reports';
import { report, reportSummary } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const block = (kind: 'title' | 'heading', text: string) => ({
  kind,
  text,
  inlines: [],
  items: [],
  ordered: false,
  table: null,
  figure: null,
  diagram: null,
});

it('offers collapsible report contents on narrow screens and closes after section selection', async () => {
  const publication: ReportPublication = {
    schema_version: 1,
    title: reportSummary.title,
    reference: 'Report example | version 1',
    language: 'en',
    blocks: [block('title', reportSummary.title), block('heading', 'Executive summary')],
    references: [],
  };
  server.use(
    http.get('/api/reports/:id', () =>
      HttpResponse.json({ ...report, version: { ...report.version, publication } }),
    ),
  );
  const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
  const summary = await screen.findByText('Jump to section');
  const details = summary.closest('details');
  expect(details).not.toBeNull();
  expect(details).not.toHaveAttribute('open');
  await user.click(summary);
  expect(details).toHaveAttribute('open');
  const link = within(details!).getByRole('link', { name: 'Executive summary' });
  expect(link).toHaveAttribute('href', '#report-section-2-executive-summary');
  await user.click(link);
  expect(details).not.toHaveAttribute('open');
});
