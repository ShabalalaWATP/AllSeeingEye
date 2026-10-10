import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('allows a pinned brief subscription to pause without changing its saved brief', async () => {
  const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
  let current = {
    ...schedule,
    name: 'Pinned brief update',
    brief_id: briefId,
    brief_revision: 3,
  };
  let pauseCalls = 0;
  server.use(
    http.get('/api/schedules', () => HttpResponse.json({ items: [current] })),
    http.post('/api/schedules/:id/pause', () => {
      pauseCalls++;
      current = { ...current, enabled: false };
      return HttpResponse.json(current);
    }),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  const row = within(table.getByText('Pinned brief update').closest('tr')!);
  expect(row.getByRole('link', { name: 'Research Brief revision 3' })).toHaveAttribute(
    'href',
    `/research?brief=${briefId}&revision=3`,
  );
  expect(row.getByRole('button', { name: 'Edit' })).toBeEnabled();
  expect(row.getByText(/Edit changes the name and timing/)).toBeVisible();
  expect(row.getByRole('button', { name: 'Pause' })).toBeEnabled();
  await user.click(row.getByRole('button', { name: 'Pause' }));
  await waitFor(() => expect(row.getByRole('button', { name: 'Resume' })).toBeEnabled());
  expect(pauseCalls).toBe(1);
  expect(row.getByText('Paused')).toBeVisible();
  expect(row.getByRole('button', { name: 'Edit' })).toBeEnabled();
  expect(row.getByRole('link', { name: 'Research Brief revision 3' })).toHaveAttribute(
    'href',
    `/research?brief=${briefId}&revision=3`,
  );
  expect(row.getByText(/Edit the Research Brief to change its questions or sources/)).toBeVisible();
});
