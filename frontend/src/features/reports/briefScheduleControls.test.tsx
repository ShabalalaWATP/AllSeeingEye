import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('allows a pinned brief subscription to pause without changing its saved brief', async () => {
  const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
  let pauseCalls = 0;
  server.use(
    http.get('/api/schedules', () =>
      HttpResponse.json({
        items: [
          {
            ...schedule,
            name: 'Pinned brief update',
            brief_id: briefId,
            brief_revision: 3,
          },
        ],
      }),
    ),
    http.post('/api/schedules/:id/pause', () => {
      pauseCalls++;
      return HttpResponse.json({
        ...schedule,
        name: 'Pinned brief update',
        brief_id: briefId,
        brief_revision: 3,
        enabled: false,
      });
    }),
  );
  const { user } = renderApp('/subscriptions', 'user');
  const table = within(await screen.findByRole('table', { name: 'Subscriptions' }));
  const row = within(table.getByText('Pinned brief update').closest('tr')!);
  expect(row.getByRole('link', { name: 'Research Brief revision 3' })).toHaveAttribute(
    'href',
    `/research?brief=${briefId}&revision=3`,
  );
  expect(row.getByRole('button', { name: 'Edit' })).toBeDisabled();
  expect(row.getByRole('button', { name: 'Pause' })).toBeEnabled();
  await user.click(row.getByRole('button', { name: 'Pause' }));
  expect(pauseCalls).toBe(1);
  expect(row.getByText(/Edit the Research Brief to change its questions or sources/)).toBeVisible();
});
