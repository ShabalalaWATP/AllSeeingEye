import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { eventResearchPeriod, eventResearchHref } from '@/lib/researchNavigation';
import { liveEvent, report } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { readReportJobRequest, reportJob } from '@/test/reportJobFixture';
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

const headings = () =>
  within(screen.getByRole('form', { name: 'Research a question' }))
    .getAllByRole('heading', { level: 3 })
    .map((heading) => heading.textContent);

it('opens in quick mode with the question and scope, and sends the saved defaults', async () => {
  const read = captureJob();
  const { user } = renderApp('/research?country=UA', 'user');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  expect(headings()).toEqual(['What to ask', 'Where and when']);
  const toggle = form.getByRole('button', { name: 'Advanced options' });
  expect(toggle).toHaveAttribute('aria-expanded', 'false');
  expect(form.getByText(/Research depth: Basic\. Search languages: 1\./)).toBeVisible();
  expect(form.queryByLabelText('Research focus')).not.toBeInTheDocument();
  expect(form.queryByRole('group', { name: 'Themes' })).not.toBeInTheDocument();
  expect(await form.findByRole('button', { name: 'Remove Ukraine' })).toBeVisible();
  expect(form.getByLabelText('Reporting window')).toHaveValue('72');
  await user.type(form.getByLabelText('Your question'), 'What changed this week?');
  await waitFor(() => expect(form.getByRole('button', { name: 'Start research' })).toBeEnabled());
  await user.click(form.getByRole('button', { name: 'Start research' }));
  await waitFor(() => expect(read()).toBeDefined());
  expect(read()).toMatchObject({
    template: 'ask',
    question: 'What changed this week?',
    countries: ['UA'],
    regions: [],
    window_hours: 72,
    research_mode: 'quick',
    research_languages: ['en'],
    research_focus: 'general',
    research_web_search: false,
  });
  expect(read()).not.toHaveProperty('categories');
});

it('edits place and period in quick mode', async () => {
  const read = captureJob();
  const { user } = renderApp('/research?country=UA&question=What%20changed%3F', 'user');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  await user.click(await form.findByRole('button', { name: 'Remove Ukraine' }));
  await user.selectOptions(form.getByLabelText('Reporting window'), 'custom');
  expect(form.getByLabelText('Start date (UTC)')).toBeVisible();
  await user.selectOptions(form.getByLabelText('Reporting window'), '168');
  expect(form.queryByLabelText('Start date (UTC)')).not.toBeInTheDocument();
  await waitFor(() => expect(form.getByRole('button', { name: 'Start research' })).toBeEnabled());
  await user.click(form.getByRole('button', { name: 'Start research' }));
  await waitFor(() => expect(read()).toMatchObject({ countries: [], window_hours: 168 }));
});

it('reveals every existing step unchanged and keeps advanced choices after hiding them', async () => {
  const read = captureJob();
  const { user } = renderApp('/research', 'user');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  await user.type(form.getByLabelText('Your question'), 'Which cyber reporting matters?');
  const toggle = form.getByRole('button', { name: 'Advanced options' });
  await user.click(toggle);
  expect(toggle).toHaveFocus();
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  const controlled = document.getElementById(toggle.getAttribute('aria-controls') ?? '');
  expect(controlled).toContainElement(form.getByLabelText('Research focus'));
  expect(headings()).toEqual([
    'What to ask',
    'How deep to go',
    'Where to look',
    'Which themes',
    'Conflict or disaster',
    'What to read',
    'Which period',
    'Scope and sources',
  ]);
  expect(form.getByLabelText('Your question')).toHaveValue('Which cyber reporting matters?');
  await user.click(
    within(form.getByRole('group', { name: 'Themes' })).getByRole('checkbox', { name: 'Cyber' }),
  );
  await user.click(toggle);
  expect(headings()).toEqual(['What to ask', 'Where and when']);
  await waitFor(() => expect(form.getByRole('button', { name: 'Start research' })).toBeEnabled());
  await user.click(form.getByRole('button', { name: 'Start research' }));
  await waitFor(() => expect(read()).toMatchObject({ categories: ['cyber'] }));
});

it('keeps the full form while a record focus needs its fields', async () => {
  const { user } = renderApp('/research', 'user');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  await user.click(form.getByRole('button', { name: 'Advanced options' }));
  await user.selectOptions(form.getByLabelText('Research focus'), 'company');
  expect(form.queryByRole('button', { name: 'Advanced options' })).not.toBeInTheDocument();
  expect(form.getByLabelText('Company name')).toBeVisible();
  await user.selectOptions(form.getByLabelText('Research focus'), 'general');
  expect(form.getByRole('button', { name: 'Advanced options' })).toHaveAttribute(
    'aria-expanded',
    'true',
  );
});

it('shows a follow-up in full, without a quick mode', async () => {
  renderApp(`/research?parent=${report.report.id}`, 'user');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  expect(form.getByRole('heading', { name: 'How deep to go' })).toBeVisible();
  expect(form.queryByRole('button', { name: 'Advanced options' })).not.toBeInTheDocument();
});

it('opens an event draft with its question, country and period in quick mode', async () => {
  const read = captureJob();
  const now = Date.now();
  const event = liveEvent({
    title: 'Reported strike near a power station',
    country_iso: 'UA',
    published_at: new Date(now - 5 * 24 * 3_600_000).toISOString(),
    point: { lat: 47.51, lon: 34.58 },
    geo_confidence: 'city',
  });
  const period = eventResearchPeriod(event, now);
  const { user } = renderApp(eventResearchHref(event, now), 'user');
  const form = within(await screen.findByRole('form', { name: 'Research a question' }));
  expect(form.getByLabelText<HTMLTextAreaElement>('Your question').value).toContain(
    'mapped near latitude 47.51, longitude 34.58',
  );
  expect(await form.findByRole('button', { name: 'Remove Ukraine' })).toBeVisible();
  expect(form.getByLabelText('Reporting window')).toHaveValue('custom');
  expect(form.getByLabelText('Start date (UTC)')).toHaveValue(period?.since.slice(0, 16));
  await waitFor(() => expect(form.getByRole('button', { name: 'Start research' })).toBeEnabled());
  await user.click(form.getByRole('button', { name: 'Start research' }));
  await waitFor(() =>
    expect(read()).toMatchObject({
      countries: ['UA'],
      research_since: period?.since,
      research_until: period?.until,
    }),
  );
  expect(read()).not.toHaveProperty('window_hours');
});
