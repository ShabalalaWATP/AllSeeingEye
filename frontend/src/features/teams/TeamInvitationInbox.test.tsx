import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import type { TeamInvitation } from '@/lib/api/teamInvitations';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { TeamInvitationInbox } from './TeamInvitationInbox';

const TEAM_ID = '44444444-4444-4444-8444-444444444444';
const USER_ID = '0f0e0d0c-0b0a-4908-8706-050403020100';

function invitation(overrides: Partial<TeamInvitation> = {}): TeamInvitation {
  return {
    id: '11111111-2222-4333-8444-555555555555',
    team_id: TEAM_ID,
    recipient_id: USER_ID,
    inviter_id: USER_ID,
    role: 'member',
    note: null,
    status: 'pending',
    created_at: '2026-09-10T10:00:00Z',
    expires_at: '2026-09-20T10:00:00Z',
    responded_at: null,
    revision: 3,
    team_name: 'Northern desk',
    inviter_display_name: 'Mina Manager',
    recipient_display_name: null,
    recipient_username: null,
    ...overrides,
  };
}

function page(items: TeamInvitation[]) {
  return { items, total: items.length, offset: 0, limit: 20, next_offset: null };
}

function mount(items: TeamInvitation[], onAccepted = vi.fn(() => Promise.resolve())) {
  server.use(http.get('/api/me/team-invitations', () => HttpResponse.json(page(items))));
  const user = userEvent.setup();
  render(<TeamInvitationInbox onAccepted={onAccepted} />);
  return { user, onAccepted };
}

describe('TeamInvitationInbox', () => {
  it('loads nothing until opened and shows the empty state for non-pending invitations', async () => {
    const { user } = mount([invitation({ status: 'accepted' })]);
    expect(screen.queryByText('No pending team invitations.')).not.toBeInTheDocument();
    await user.click(screen.getByText('Team invitations'));
    expect(await screen.findByText('No pending team invitations.')).toBeInTheDocument();
    await user.click(screen.getByText('Team invitations'));
    await waitFor(() => {
      expect(screen.queryByText('No pending team invitations.')).not.toBeInTheDocument();
    });
  });

  it('lists pending invitations with fallbacks for missing names and dates', async () => {
    const { user } = mount([
      invitation({ note: 'Join the night shift' }),
      invitation({
        id: '22222222-2222-4333-8444-555555555555',
        team_name: null,
        inviter_display_name: null,
        expires_at: 'not-a-date',
      }),
    ]);
    await user.click(screen.getByText('Team invitations'));
    expect(await screen.findByText('Northern desk')).toBeInTheDocument();
    expect(screen.getByText('Join the night shift')).toBeInTheDocument();
    expect(screen.getByText(/Invited by Mina Manager/)).toBeInTheDocument();
    const fallback = screen.getByText('Team workspace').closest('li')!;
    expect(within(fallback).getByText(/Invited by a team manager/)).toBeInTheDocument();
    expect(within(fallback).getByText(/date unavailable/)).toBeInTheDocument();
  });

  it('accepts an invitation with its revision and reloads the team list', async () => {
    let body: unknown;
    server.use(
      http.post('/api/me/team-invitations/:id/accept', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(invitation({ status: 'accepted', revision: 4 }));
      }),
    );
    const { user, onAccepted } = mount([invitation()]);
    await user.click(screen.getByText('Team invitations'));
    await user.click(await screen.findByRole('button', { name: 'Accept' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Invitation accepted.');
    expect(body).toEqual({ expected_revision: 3 });
    expect(onAccepted).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('Northern desk')).not.toBeInTheDocument();
    expect(screen.getByText('No pending team invitations.')).toBeInTheDocument();
  });

  it('declines an invitation without reloading teams', async () => {
    server.use(
      http.post('/api/me/team-invitations/:id/decline', () =>
        HttpResponse.json(invitation({ status: 'declined', revision: 4 })),
      ),
    );
    const { user, onAccepted } = mount([invitation()]);
    await user.click(screen.getByText('Team invitations'));
    await user.click(await screen.findByRole('button', { name: 'Decline' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Invitation declined.');
    expect(onAccepted).not.toHaveBeenCalled();
  });

  it('reports a stale response and reloads the current invitations', async () => {
    let loads = 0;
    server.use(
      http.get('/api/me/team-invitations', () => {
        loads += 1;
        return HttpResponse.json(page([invitation()]));
      }),
      http.post('/api/me/team-invitations/:id/decline', () =>
        apiError(409, 'conflict', 'The invitation changed. Refresh and try again.'),
      ),
    );
    const user = userEvent.setup();
    render(<TeamInvitationInbox onAccepted={() => Promise.resolve()} />);
    await user.click(screen.getByText('Team invitations'));
    await user.click(await screen.findByRole('button', { name: 'Decline' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The invitation changed.');
    expect(loads).toBe(2);
    expect(screen.getByText('Northern desk')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows a load failure instead of the empty state', async () => {
    server.use(
      http.get('/api/me/team-invitations', () =>
        apiError(500, 'server_error', 'Invitations unavailable.'),
      ),
    );
    const user = userEvent.setup();
    render(<TeamInvitationInbox onAccepted={() => Promise.resolve()} />);
    await user.click(screen.getByText('Team invitations'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invitations unavailable.');
    expect(screen.queryByText('No pending team invitations.')).not.toBeInTheDocument();
  });
});
