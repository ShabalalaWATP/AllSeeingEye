import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import type { DirectoryProfile as Profile } from '@/lib/api/directoryProfile';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';
import { DirectoryProfile } from './DirectoryProfile';

const initial: Profile = {
  user_id: '0f0e0d0c-0b0a-4908-8706-050403020100',
  username: null,
  job_title: null,
  organisation: null,
  biography: null,
  country: null,
  languages: [],
  expertise: [],
  timezone: null,
  is_discoverable: false,
  visible_fields: [],
  avatar_url: null,
  revision: 1,
  updated_at: null,
};

it('preserves separators and spaces while typing and normalises lists only when saving', async () => {
  const writes: Record<string, unknown>[] = [];
  server.use(
    http.get('/api/me/directory-profile', () => HttpResponse.json(initial)),
    http.patch('/api/me/directory-profile', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      writes.push(body);
      return HttpResponse.json({ ...initial, ...body, revision: 2 });
    }),
  );
  const user = userEvent.setup();
  render(<DirectoryProfile />);
  const languages = await screen.findByRole('textbox', { name: 'Languages' });
  const expertise = screen.getByRole('textbox', { name: 'Expertise' });
  await user.type(languages, 'en, fr, en, ');
  await user.type(expertise, 'naval analysis, aviation');
  expect(languages).toHaveValue('en, fr, en, ');
  expect(expertise).toHaveValue('naval analysis, aviation');
  await user.click(screen.getByRole('button', { name: 'Save directory profile' }));
  await screen.findByText('Directory profile saved.');
  expect(writes[0]).toMatchObject({
    languages: ['en', 'fr'],
    expertise: ['naval analysis', 'aviation'],
  });
  expect(languages).toHaveValue('en, fr');
});

it('preserves local edits on conflict and explicitly reapplies them over the latest unchanged fields', async () => {
  const latest = {
    ...initial,
    job_title: 'Remote title',
    organisation: 'Remote organisation',
    revision: 2,
  };
  let reads = 0;
  const writes: Record<string, unknown>[] = [];
  server.use(
    http.get('/api/me/directory-profile', () =>
      HttpResponse.json(++reads === 1 ? initial : latest),
    ),
    http.patch('/api/me/directory-profile', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      writes.push(body);
      if (body.expected_revision === 1)
        return apiError(
          409,
          'conflict',
          'The directory profile changed. Reload it before saving again.',
        );
      return HttpResponse.json({ ...latest, ...body, revision: 3 });
    }),
  );
  const user = userEvent.setup();
  render(<DirectoryProfile />);
  await user.type(await screen.findByRole('textbox', { name: 'Job title' }), 'Local title');
  await user.type(screen.getByRole('textbox', { name: 'Languages' }), 'en, fr, ');
  await user.click(screen.getByRole('button', { name: 'Save directory profile' }));
  const keep = await screen.findByRole('button', { name: 'Keep my edits over latest profile' });
  expect(screen.getByRole('textbox', { name: 'Job title' })).toHaveValue('Local title');
  expect(screen.getByRole('textbox', { name: 'Languages' })).toHaveValue('en, fr, ');
  expect(screen.getByRole('button', { name: 'Save directory profile' })).toBeDisabled();
  await user.click(keep);
  expect(screen.getByRole('textbox', { name: 'Organisation' })).toHaveValue('Remote organisation');
  expect(screen.getByRole('textbox', { name: 'Job title' })).toHaveValue('Local title');
  await user.click(screen.getByRole('button', { name: 'Save directory profile' }));
  await screen.findByText('Directory profile saved.');
  expect(writes[1]).toMatchObject({
    job_title: 'Local title',
    organisation: 'Remote organisation',
    languages: ['en', 'fr'],
    expected_revision: 2,
  });
  await waitFor(() => expect(reads).toBe(2));
});

it('recovers a failed conflict refresh without losing text and can explicitly discard to the latest profile', async () => {
  let reads = 0;
  server.use(
    http.get('/api/me/directory-profile', () => {
      reads += 1;
      if (reads === 2) return apiError(503, 'unavailable', 'Please try again.');
      return HttpResponse.json(
        reads === 1 ? initial : { ...initial, languages: ['de'], revision: 2 },
      );
    }),
    http.patch('/api/me/directory-profile', () => apiError(409, 'conflict', 'Profile changed.')),
  );
  const user = userEvent.setup();
  render(<DirectoryProfile />);
  const languages = await screen.findByRole('textbox', { name: 'Languages' });
  await user.type(languages, 'en, fr, ');
  await user.click(screen.getByRole('button', { name: 'Save directory profile' }));
  await screen.findByText(/Could not load the latest profile. Your edits are kept./);
  expect(languages).toHaveValue('en, fr, ');
  expect(screen.getByRole('button', { name: 'Save directory profile' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Retry loading latest profile' }));
  await user.click(
    await screen.findByRole('button', { name: 'Discard my edits and use latest profile' }),
  );
  expect(languages).toHaveValue('de');
  expect(screen.getByRole('button', { name: 'Save directory profile' })).toBeDisabled();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  await user.type(languages, ', fr');
  await user.click(screen.getByRole('button', { name: 'Reset' }));
  expect(languages).toHaveValue('de');
});

it('still checks the latest revision if another session saves again during reconciliation', async () => {
  let reads = 0;
  const revisions: unknown[] = [];
  server.use(
    http.get('/api/me/directory-profile', () =>
      HttpResponse.json({ ...initial, revision: ++reads }),
    ),
    http.patch('/api/me/directory-profile', async ({ request }) => {
      revisions.push(((await request.json()) as Record<string, unknown>).expected_revision);
      return apiError(409, 'conflict', 'Profile changed again.');
    }),
  );
  const user = userEvent.setup();
  render(<DirectoryProfile />);
  await user.type(await screen.findByRole('textbox', { name: 'Expertise' }), 'naval analysis');
  await user.click(screen.getByRole('button', { name: 'Save directory profile' }));
  await user.click(
    await screen.findByRole('button', { name: 'Keep my edits over latest profile' }),
  );
  await user.click(screen.getByRole('button', { name: 'Save directory profile' }));
  await screen.findByRole('button', { name: 'Keep my edits over latest profile' });
  expect(revisions).toEqual([1, 2]);
  expect(screen.getByRole('textbox', { name: 'Expertise' })).toHaveValue('naval analysis');
});
