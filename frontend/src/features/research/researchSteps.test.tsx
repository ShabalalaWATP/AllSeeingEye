import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { conflictCard } from '@/test/fixtures';
import { jobId, readReportJobRequest, reportJob } from '@/test/reportJobFixture';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function captureJob() {
  let body: Record<string, unknown> | undefined;
  server.use(
    http.post('/api/report-jobs', async ({ request }) => {
      body = await readReportJobRequest(request);
      return HttpResponse.json(reportJob(), { status: 202 });
    }),
  );
  return () => body;
}

it('reads top to bottom and sends regions, themes and a pinned conflict with the question', async () => {
  const read = captureJob();
  const { user, router } = renderApp('/research', 'user');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  const headings = form.getAllByRole('heading', { level: 3 }).map((h) => h.textContent);
  expect(headings).toEqual([
    'What to ask',
    'How deep to go',
    'Where to look',
    'Which themes',
    'Conflict or disaster',
    'What to read',
    'Which period',
    'Scope and sources',
  ]);
  await user.type(form.getByLabelText('Your question'), 'What is changing across the region?');
  await user.click(form.getByRole('checkbox', { name: 'Europe' }));
  await user.click(form.getByRole('checkbox', { name: 'Middle East' }));
  const themes = within(form.getByRole('group', { name: 'Themes' }));
  await user.click(themes.getByRole('checkbox', { name: 'Cyber' }));
  await user.click(themes.getByRole('checkbox', { name: 'Economy' }));
  await user.selectOptions(await form.findByLabelText('Conflict'), conflictCard.conflict.id);
  expect(form.getByRole('checkbox', { name: /Fresh web search/ })).not.toBeChecked();
  await waitFor(() => expect(form.getByRole('button', { name: 'Start research' })).toBeEnabled());
  await user.click(form.getByRole('button', { name: 'Start research' }));
  await waitFor(() => expect(router.state.location.pathname).toBe(`/research/jobs/${jobId}`));
  expect(read()).toMatchObject({
    question: 'What is changing across the region?',
    countries: [],
    regions: ['europe', 'middle_east'],
    categories: ['cyber', 'economic'],
    conflict: conflictCard.conflict.id,
    research_web_search: false,
  });
  expect(read()).not.toHaveProperty('hazard');
});

it('drops the place, theme and conflict steps for a company question and clears their values', async () => {
  const read = captureJob();
  const { user, router } = renderApp('/research', 'user');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  await user.type(form.getByLabelText('Your question'), 'What is Example Company doing?');
  await user.click(form.getByRole('checkbox', { name: 'Africa' }));
  await user.selectOptions(await form.findByLabelText('Natural disaster'), 'earthquake');
  await user.selectOptions(form.getByLabelText('Research focus'), 'company');
  expect(form.queryByRole('group', { name: 'Regions' })).not.toBeInTheDocument();
  expect(form.queryByLabelText('Natural disaster')).not.toBeInTheDocument();
  expect(form.getByRole('group', { name: 'Themes' })).toBeInTheDocument();
  await user.type(form.getByLabelText('Company name'), 'Example Company');
  await waitFor(() => expect(form.getByRole('button', { name: 'Start research' })).toBeEnabled());
  await user.click(form.getByRole('button', { name: 'Start research' }));
  await waitFor(() => expect(router.state.location.pathname).toBe(`/research/jobs/${jobId}`));
  expect(read()).toMatchObject({ research_focus: 'company', research_subject: 'Example Company' });
  expect(read()).not.toHaveProperty('regions');
  expect(read()).not.toHaveProperty('hazard');
  expect(read()).not.toHaveProperty('categories');
});
