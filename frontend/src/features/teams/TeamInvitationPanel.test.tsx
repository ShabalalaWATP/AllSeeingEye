import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { server } from '@/test/server';

import { TeamInvitationPanel } from './TeamInvitationPanel';

const TEAM_ID = '11111111-2222-4333-8444-555555555555';
const PERSON_ID = '0f0e0d0c-0b0a-4908-8706-050403020100';
const GENERIC = 'If that username can receive an invitation, it has been sent.';
const emptyPage = { items: [], total: 0, offset: 0, limit: 20, next_offset: null };

beforeEach(() => {
  if (!('createObjectURL' in URL)) {
    Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => undefined });
  }
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:person');
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
  server.use(http.get(`/api/teams/${TEAM_ID}/invitations`, () => HttpResponse.json(emptyPage)));
});

async function openPanel() {
  const user = userEvent.setup();
  render(<TeamInvitationPanel teamId={TEAM_ID} canManage />);
  await user.click(screen.getByText('Invite people'));
  return user;
}

describe('team invitation people picker', () => {
  it('shows directory avatars in search results', async () => {
    server.use(
      http.get('/api/directory/users', () =>
        HttpResponse.json({
          ...emptyPage,
          total: 1,
          items: [
            {
              user_id: PERSON_ID,
              username: 'ada_l',
              display_name: 'Ada Lovelace',
              avatar_url: `/api/directory/users/${PERSON_ID}/avatar?v=0123456789abcdef`,
              job_title: null,
              organisation: 'Analytical Engines',
              biography: null,
              country: null,
              languages: [],
              expertise: [],
              timezone: null,
            },
          ],
        }),
      ),
      http.get(`/api/directory/users/${PERSON_ID}/avatar`, () =>
        HttpResponse.arrayBuffer(new Uint8Array([1]).buffer, {
          headers: { 'Content-Type': 'image/webp' },
        }),
      ),
    );
    const user = await openPanel();
    await user.type(screen.getByRole('textbox', { name: 'Find a person' }), 'Ada');
    await user.click(screen.getByRole('button', { name: 'Search' }));

    const row = (await screen.findByText('Ada Lovelace')).closest('li')!;
    expect(
      await within(row).findByRole('img', { name: 'Avatar for Ada Lovelace' }),
    ).toHaveAttribute('src', 'blob:person');
    expect(within(row).getByText('@ada_l · Analytical Engines')).toBeVisible();
  });

  it('invites an exact username and shows only the generic submission message', async () => {
    let body: unknown;
    server.use(
      http.post(`/api/teams/${TEAM_ID}/invitations/by-username`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ status: 'submitted', message: GENERIC }, { status: 202 });
      }),
    );
    const user = await openPanel();
    const field = screen.getByRole('textbox', { name: 'Exact username' });
    expect(screen.getByRole('button', { name: 'Invite username' })).toBeDisabled();
    await user.type(field, ' quiet_handle ');
    await user.type(screen.getByRole('textbox', { name: 'Optional note' }), 'Join us');
    await user.click(screen.getByRole('button', { name: 'Invite username' }));

    expect(await screen.findByRole('status')).toHaveTextContent(GENERIC);
    expect(body).toEqual({ username: 'quiet_handle', note: 'Join us' });
    expect(field).toHaveValue('');
  });
});
