import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';

import { assistantAnswerSchema, type AssistantAnswer } from '@/lib/api/assistant';

import { eyeAnswer } from './assistantFixture';
import { EyeAnswer, answerWithReferences } from './EyeAnswer';

function show(answer: AssistantAnswer) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={['/research']}>
      <Routes>
        <Route path="/research" element={<EyeAnswer answer={answer} />} />
        <Route path="/" element={<p>Map home</p>} />
      </Routes>
    </MemoryRouter>,
  );
  return user;
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'clipboard');
});

it('copies the answer with references, or says the clipboard is unavailable', async () => {
  const writeText = vi.fn(() => Promise.resolve());
  const user = show(eyeAnswer);
  // user-event installs its own clipboard during setup, so replace it afterwards.
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
  await user.click(screen.getByRole('button', { name: 'Copy answer with references' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Copied with references.');
  expect(writeText).toHaveBeenCalledWith(answerWithReferences(eyeAnswer));

  writeText.mockImplementationOnce(() => Promise.reject(new Error('denied')));
  await user.click(screen.getByRole('button', { name: 'Copy answer with references' }));
  expect(await screen.findByText('Clipboard unavailable.')).toBeInTheDocument();
});

it('opens the cited evidence and sends a located record to the map', async () => {
  const user = show(eyeAnswer);
  await user.click(
    screen.getByRole('button', { name: 'View evidence E1: Example vessel position' }),
  );
  const details = screen.getByText(/Evidence and coverage/).closest('details')!;
  expect(details).toHaveAttribute('open');
  await user.click(within(details).getByRole('button', { name: 'Show on map' }));
  expect(await screen.findByText('Map home')).toBeInTheDocument();
});

it('describes a frozen report answer without map actions for report claims', () => {
  const answer = assistantAnswerSchema.parse({
    ...eyeAnswer,
    scope: { mode: 'report', bbox: null, selected: null },
    report: {
      id: 'b6f0a6e4-1d4b-4c5a-9f2e-0b4a5c7d8e91',
      version_id: 'c7a1b2d3-4e5f-4a6b-8c9d-0e1f2a3b4c5d',
      version: 3,
      title: 'Baltic shipping update',
      data_cutoff: null,
    },
    sources: [
      { ...eyeAnswer.sources[0]!, id: 'C1', kind: 'report_claim', grade: null, observed_at: null },
    ],
    paragraphs: [{ kind: 'inference', text: 'Traffic is likely to recover.', citations: ['C1'] }],
    interpretation: {
      ...eyeAnswer.interpretation,
      countries: ['EE', 'LV'],
      since: '2026-09-01T00:00:00Z',
      until: '2026-09-10T00:00:00Z',
      source_categories: ['maritime', 'news', 'conflict', 'cyber'],
      notes: ['Report scope only.'],
    },
    coverage: { ...eyeAnswer.coverage, selected_count: 1, source_count: 1, capped: false },
  });
  show(answer);
  const scope = screen.getByLabelText('Search interpretation');
  expect(scope).toHaveTextContent('Report: Baltic shipping update · Version 3');
  expect(scope).toHaveTextContent('Data cutoff: unavailable');
  expect(scope).toHaveTextContent('Countries: EE, LV');
  expect(scope).toHaveTextContent('Sources: 4 types');
  expect(screen.getByRole('link', { name: 'Open this frozen report version' })).toHaveAttribute(
    'href',
    `/reports/${answer.report!.id}?version=3`,
  );
  expect(screen.getByText('Assessment')).toBeInTheDocument();
  expect(screen.getByText(/1 record · 1 source group/)).toBeInTheDocument();
  expect(screen.getByText('Publication time unknown')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Show on map' })).not.toBeInTheDocument();
  expect(answerWithReferences(answer)).toContain(
    'Baltic shipping update · Version 3 · Data cutoff unavailable',
  );
});
