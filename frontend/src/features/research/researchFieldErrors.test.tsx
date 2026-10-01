import { screen, waitFor, within } from '@testing-library/react';
import { http } from 'msw';
import { expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function startResearch(fields: Record<string, string>) {
  let posts = 0;
  server.use(
    http.post('/api/report-jobs', () => {
      posts += 1;
      return apiError(422, 'validation_error', 'The request is invalid.', fields);
    }),
  );
  const view = renderApp('/research?question=What%20changed%20in%20Ukraine%3F&country=ua', 'user');
  const start = await screen.findByRole('button', { name: 'Start research' });
  await waitFor(() => expect(start).toBeEnabled());
  await view.user.click(start);
  return { ...view, posts: () => posts };
}

it('shows a rejected question beside the question field and focuses it from the summary', async () => {
  const { user, posts } = await startResearch({
    'report.question': 'Ask about one topic at a time.',
    'report.countries.0': 'Unknown nation.',
  });
  const summary = await screen.findByRole('alert', { name: 'Check these fields and try again:' });
  expect(summary).toHaveFocus();
  const question = screen.getByLabelText('Your question');
  expect(question).toHaveAttribute('aria-invalid', 'true');
  expect(question).toHaveAccessibleDescription('Ask about one topic at a time.');
  expect(question).toHaveValue('What changed in Ukraine?');
  expect(screen.queryByText('The request is invalid.')).not.toBeInTheDocument();

  await user.click(within(summary).getByRole('link', { name: /Your question/ }));
  expect(question).toHaveFocus();
  await user.click(within(summary).getByRole('link', { name: /Where to look: Unknown nation/ }));
  expect(document.getElementById('research-quick-scope')).toContainElement(
    document.activeElement as HTMLElement,
  );
  expect(posts()).toBe(1);
});

it('lists unmatched research paths under the generic message', async () => {
  await startResearch({ 'report.research_candidate_hypotheses.0': 'Too long.' });
  const summary = await screen.findByRole('alert', { name: 'The request is invalid.' });
  expect(summary).toHaveTextContent('Research candidate hypotheses item 1: Too long.');
});
