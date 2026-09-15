import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const summary = {
  id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
  revision: 4,
  owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
  team_id: null,
  title: 'Baltic shipping disruption',
  schema_version: 1,
  origin: 'authored',
  published: false,
  created_at: '2026-09-14T10:00:00Z',
  revised_at: '2026-09-14T11:00:00Z',
};

it('lists saved briefs with links to their exact revision', async () => {
  server.use(
    http.get('/api/research/briefs', () =>
      HttpResponse.json({ items: [summary], limit: 50, offset: 0 }),
    ),
  );
  renderApp('/research?brief=library', 'user');
  const link = await screen.findByRole('link', {
    name: 'Baltic shipping disruption (revision 4)',
  });
  expect(link).toHaveAttribute('href', `/research?brief=${summary.id}&revision=4`);
  expect(screen.getByRole('link', { name: 'Create a new brief' })).toHaveAttribute(
    'href',
    '/research?brief=new',
  );
  expect(screen.queryByText('No saved briefs yet.')).not.toBeInTheDocument();
});

it('says when there are no briefs and retries after a failed load', async () => {
  let calls = 0;
  server.use(
    http.get('/api/research/briefs', () => {
      calls += 1;
      if (calls === 1) return HttpResponse.json({ detail: 'Unavailable' }, { status: 503 });
      return HttpResponse.json({ items: [], limit: 50, offset: 0 });
    }),
  );
  const { user } = renderApp('/research?brief=library', 'user');
  const alert = await screen.findByRole('alert');
  await user.click(within(alert).getByRole('button', { name: 'Retry briefs' }));
  expect(await screen.findByText('No saved briefs yet.')).toBeInTheDocument();
  expect(calls).toBe(2);
});
