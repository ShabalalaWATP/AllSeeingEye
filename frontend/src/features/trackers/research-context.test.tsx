import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('opens conflict research as an editable draft without starting collection', async () => {
  let writes = 0;
  server.use(
    http.post('/api/reports', () => {
      writes += 1;
      return HttpResponse.json({}, { status: 500 });
    }),
  );
  const { user } = renderApp('/trackers/conflicts/ukraine', 'user');
  const link = await screen.findByRole('link', { name: 'Research this conflict' });
  const destination = new URL(link.getAttribute('href') ?? '', 'http://local.test');
  expect(destination.pathname).toBe('/research');
  expect(destination.searchParams.get('question')).toContain('supports or challenges');
  await user.click(link);
  const question = await screen.findByLabelText('Your question');
  await waitFor(() => expect(question).toHaveValue(destination.searchParams.get('question')));
  expect(screen.getByRole('button', { name: 'Start research' })).toBeVisible();
  expect(writes).toBe(0);
});

it('offers evidence-specific research from tracker rows and hazard context', async () => {
  renderApp('/trackers/disasters/earthquake', 'user');
  const link = await screen.findByRole('link', { name: 'Research this hazard' });
  expect(
    new URL(link.getAttribute('href') ?? '', 'http://local.test').searchParams.get('question'),
  ).toContain('location, timing');
  const eventLinks = await screen.findAllByRole('link', { name: /^Research this report:/ });
  expect(eventLinks.length).toBeGreaterThan(0);
  for (const eventLink of eventLinks) {
    expect(new URL(eventLink.getAttribute('href') ?? '', 'http://local.test').pathname).toBe(
      '/research',
    );
  }
});
