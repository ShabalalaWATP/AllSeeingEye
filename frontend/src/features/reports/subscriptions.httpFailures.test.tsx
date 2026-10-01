import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const proxyPage = (status: number) =>
  new HttpResponse('<html><body><h1>Bad Gateway</h1><p>nginx</p></body></html>', {
    status,
    headers: { 'Content-Type': 'text/html' },
  });

it('explains a failed read and recovers through the keyboard-operable retry', async () => {
  let reads = 0;
  server.use(
    http.get('/api/schedules', () => {
      reads += 1;
      return reads === 1 ? proxyPage(502) : HttpResponse.json({ items: [schedule] });
    }),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const alert = await screen.findByText(/The service is temporarily unavailable/);
  expect(alert).toHaveTextContent('Please try again later. Reference: HTTP 502.');
  expect(screen.queryByText(/Bad Gateway|nginx|failed with status/)).not.toBeInTheDocument();
  const retry = screen.getByRole('button', { name: 'Retry subscriptions' });
  retry.focus();
  await user.keyboard('{Enter}');
  const table = await screen.findByRole('table', { name: 'Subscriptions' });
  expect(within(table).getByText(schedule.name)).toBeVisible();
  expect(screen.queryByText(/temporarily unavailable/)).not.toBeInTheDocument();
  expect(reads).toBe(2);
});

it('never replays a failed subscription save and keeps what the user entered', async () => {
  let writes = 0;
  server.use(
    http.post('/api/schedules', () => {
      writes += 1;
      return proxyPage(503);
    }),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.type(form.getByLabelText('Subscription name'), 'Energy watch');
  await user.type(form.getByLabelText('Question'), 'What changed in European energy markets?');
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  expect(await form.findByText(/The service is temporarily unavailable/)).toHaveTextContent(
    'Reference: HTTP 503.',
  );
  await new Promise((resolve) => setTimeout(resolve, 50));
  expect(writes).toBe(1);
  expect(form.getByLabelText('Subscription name')).toHaveValue('Energy watch');
  expect(form.getByLabelText('Question')).toHaveValue('What changed in European energy markets?');

  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() => expect(writes).toBe(2));
});
