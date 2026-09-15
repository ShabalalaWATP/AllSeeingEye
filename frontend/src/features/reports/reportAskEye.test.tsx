import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { AssistantRequest } from '@/lib/api/assistant';
import { eyeAnswer } from '@/components/assistant/assistantFixture';
import { report, reportSummary } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const cutoff = '2026-08-31T23:59:00Z';
const versionId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const frozenAnswer = {
  ...eyeAnswer,
  scope: { mode: 'report', bbox: null, selected: null },
  report: {
    id: reportSummary.id,
    version_id: versionId,
    version: 1,
    title: reportSummary.title,
    data_cutoff: cutoff,
  },
  sources: [
    {
      ...eyeAnswer.sources[0],
      kind: 'report_claim',
      record_id: `${versionId}:key_judgement:1:KJ1`,
      source_id: `report_version:${versionId}`,
      title: 'Key judgement KJ1',
      url: null,
      point: null,
    },
  ],
  paragraphs: [
    {
      kind: 'finding',
      text: 'The selected edition assesses fighting near Kharkiv.',
      citations: ['E1'],
    },
  ],
  continuation_id: null,
};

it('opens Eye on the selected older edition and keeps fresh research separate', async () => {
  const bodies: AssistantRequest[] = [];
  server.use(
    http.get('/api/reports/:id', () =>
      HttpResponse.json({
        report: { ...report.report, latest_version: 2 },
        version: { ...report.version, number: 1, data_cutoff: cutoff },
      }),
    ),
    http.post('/api/assistant/answer', async ({ request }) => {
      bodies.push((await request.json()) as AssistantRequest);
      return HttpResponse.json(frozenAnswer);
    }),
    http.get('/api/assistant/conversations', () => HttpResponse.json({ items: [] })),
  );
  const { user } = renderApp(`/reports/${reportSummary.id}?version=1`, 'user');
  await user.click(screen.getByRole('button', { name: 'Open Eye assistant' }));
  await user.selectOptions(screen.getByLabelText('Eye time period'), '168');
  await user.click(screen.getByText('Source types'));
  await user.click(screen.getByRole('checkbox', { name: 'CCTV' }));
  await user.type(screen.getByLabelText('Ask the Eye'), 'An unsent map question');
  await user.click(await screen.findByRole('button', { name: 'Ask Eye about this version' }));
  const panel = await screen.findByRole('dialog', { name: 'Eye assistant' });
  const selection = within(panel).getByLabelText('Selected report edition');
  expect(selection).toHaveTextContent(reportSummary.title);
  expect(selection).toHaveTextContent('VERSION 1');
  expect(selection).toHaveTextContent('Data cutoff');
  expect(within(panel).queryByLabelText('Eye time period')).not.toBeInTheDocument();
  expect(within(panel).queryByText('Source types')).not.toBeInTheDocument();
  expect(within(panel).getByLabelText('Ask the Eye')).toHaveValue('');
  await user.type(
    within(panel).getByLabelText('Ask the Eye'),
    'What does this say about Kharkiv?{Enter}',
  );
  expect(
    await within(panel).findByText('The selected edition assesses fighting near Kharkiv.'),
  ).toBeVisible();
  expect(bodies[0]).toEqual({
    question: 'What does this say about Kharkiv?',
    prior_questions: [],
    scope: 'report',
    report: { id: reportSummary.id, version: 1 },
  });
  expect(within(panel).getByLabelText('Search interpretation')).toHaveTextContent(
    `${reportSummary.title} · Version 1`,
  );
  expect(
    within(panel).getByRole('link', { name: 'Open this frozen report version' }),
  ).toHaveAttribute('href', `/reports/${reportSummary.id}?version=1`);
  const newer = within(panel).getByRole('link', {
    name: 'Search for newer evidence in Research →',
  });
  expect(newer.getAttribute('href')).toMatch(/^\/research\?question=/);
  expect(newer.getAttribute('href')).not.toContain('version=1');
  const draft = new URL(newer.getAttribute('href') ?? '', 'http://localhost');
  expect(draft.searchParams.get('since')).toBe(cutoff);
  expect(Number.isNaN(Date.parse(draft.searchParams.get('until') ?? ''))).toBe(false);
  expect(within(panel).getByText(/This report and its answers stay frozen/)).toBeVisible();
  await user.click(within(panel).getByRole('button', { name: 'Saved chats' }));
  expect(
    within(panel).getByText(/Report Q&A is saved with the exact report edition/),
  ).toBeVisible();
  expect(within(panel).getByRole('button', { name: 'Save chat' })).toBeEnabled();

  await user.type(
    within(panel).getByLabelText('Ask the Eye'),
    'Which of those sources support it?{Enter}',
  );
  await waitFor(() => expect(bodies).toHaveLength(2));
  expect(bodies[1]?.prior_questions).toEqual(['What does this say about Kharkiv?']);
  expect(bodies[1]).not.toHaveProperty('continuation_id');
  expect(bodies[1]).not.toHaveProperty('time_range');
  expect(bodies[1]).not.toHaveProperty('source_categories');
});

it('rejects an answer attributed to a different report edition', async () => {
  server.use(
    http.get('/api/reports/:id', () => HttpResponse.json(report)),
    http.post('/api/assistant/answer', () =>
      HttpResponse.json({
        ...frozenAnswer,
        report: { ...frozenAnswer.report, version: 2 },
      }),
    ),
  );
  const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
  await user.click(await screen.findByRole('button', { name: 'Ask Eye about this version' }));
  await user.type(screen.getByLabelText('Ask the Eye'), 'What does this report say?{Enter}');
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The answer did not match the selected report edition',
  );
  expect(
    screen.queryByText('The selected edition assesses fighting near Kharkiv.'),
  ).not.toBeInTheDocument();
});
