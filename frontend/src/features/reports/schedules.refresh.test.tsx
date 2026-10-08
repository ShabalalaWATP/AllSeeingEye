import { screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('keeps the subscription list mounted while it refreshes after a change', async () => {
  let current = { ...schedule, enabled: true };
  let paused = false;
  let readsAfter = 0;
  server.use(
    http.get('/api/schedules', async () => {
      if (paused) {
        readsAfter += 1;
        await delay(300);
      }
      return HttpResponse.json({ items: [current] });
    }),
    http.post('/api/schedules/:id/pause', () => {
      paused = true;
      current = { ...current, enabled: false };
      return HttpResponse.json(current);
    }),
  );
  const { user } = renderApp('/research/recurring', 'user');
  const table = await screen.findByRole('table', { name: 'Subscriptions' });
  await user.click(within(table).getByRole('button', { name: 'Pause' }));
  await waitFor(() => expect(readsAfter).toBe(1));
  expect(screen.getByRole('table', { name: 'Subscriptions' })).toBe(table);
  expect(await within(table).findByRole('button', { name: 'Resume' })).toBeVisible();
  expect(screen.getByRole('table', { name: 'Subscriptions' })).toBe(table);
});
