import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { TeamInvitation } from '@/lib/api/teamInvitations';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { TeamInvitationPanel } from './TeamInvitationPanel';

const TEAM_ID = '11111111-2222-4333-8444-555555555555';
const PERSON_ID = '0f0e0d0c-0b0a-4908-8706-050403020100';
const OTHER_ID = '0f0e0d0c-0b0a-4908-8706-0504030201ff';

function page<T>(items: T[]) {
  return { items, total: items.length, offset: 0, limit: 20, next_offset: null };
}

function invitation(overrides: Partial<TeamInvitation> = {}): TeamInvitation {
  return {
    id: '22222222-2222-4333-8444-555555555555',
    team_id: TEAM_ID,
    recipient_id: PERSON_ID,
    inviter_id: OTHER_ID,
    role: 'member',
    note: null,
    status: 'pending',
    created_at: '2026-09-10T10:00:00Z',
    expires_at: '2026-09-20T10:00:00Z',
    responded_at: null,
    revision: 2,
    team_name: 'Northern desk',
    inviter_display_name: 'Mina Manager',
    recipient_display_name: 'Ada Lovelace',
    recipient_username: 'ada_l',
    ...overrides,
  };
}

function person(id: string, name: string, organisation: string | null) {
  return {
    user_id: id,
    username: name.toLowerCase().replace(' ', '_'),
    display_name: name,
    avatar_url: null,
    job_title: null,
    organisation,
    biography: null,
    country: null,
    languages: [],
    expertise: [],
    timezone: null,
  };
}

async function open(pending: TeamInvitation[] = []) {
  server.use(http.get(`/api/teams/${TEAM_ID}/invitations`, () => HttpResponse.json(page(pending))));
  const user = userEvent.setup();
  render(<TeamInvitationPanel teamId={TEAM_ID} canManage />);
  await user.click(screen.getByText('Invite people'));
  return user;
}

describe('team invitation panel states', () => {
  it('renders nothing for people who cannot manage the team', () => {
    const { container } = render(<TeamInvitationPanel teamId={TEAM_ID} canManage={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('lists pending invitations with fallbacks and withdraws one by revision', async () => {
    let withdrawn = '';
    server.use(
      http.delete(`/api/teams/${TEAM_ID}/invitations/:id`, ({ request }) => {
        withdrawn = new URL(request.url).search;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = await open([
      invitation(),
      invitation({
        id: '33333333-2222-4333-8444-555555555555',
        recipient_display_name: null,
        recipient_username: null,
        expires_at: 'never',
      }),
    ]);
    const section = await screen.findByRole('region', { name: 'Pending invitations (2)' });
    expect(within(section).getByText(/Ada Lovelace/)).toHaveTextContent('(@ada_l)');
    const fallback = within(section)
      .getByText(/Directory account/)
      .closest('li')!;
    expect(within(fallback).getByText('expiry unavailable')).toBeInTheDocument();
    expect(fallback).not.toHaveTextContent('(@');

    await user.click(within(section).getAllByRole('button', { name: 'Withdraw' })[0]!);
    expect(await screen.findByRole('status')).toHaveTextContent('Invitation withdrawn.');
    expect(withdrawn).toBe('?expected_revision=2');
    expect(screen.getByRole('region', { name: 'Pending invitations (1)' })).toBeInTheDocument();
  });

  it('keeps a pending invitation when withdrawal fails', async () => {
    server.use(
      http.delete(`/api/teams/${TEAM_ID}/invitations/:id`, () =>
        apiError(409, 'conflict', 'The invitation has already been answered.'),
      ),
    );
    const user = await open([invitation()]);
    await user.click(await screen.findByRole('button', { name: 'Withdraw' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('already been answered');
    expect(screen.getByRole('region', { name: 'Pending invitations (1)' })).toBeInTheDocument();
  });

  it('reports a failure to load pending invitations', async () => {
    server.use(
      http.get(`/api/teams/${TEAM_ID}/invitations`, () =>
        apiError(403, 'forbidden', 'Team management access is required.'),
      ),
    );
    const user = userEvent.setup();
    render(<TeamInvitationPanel teamId={TEAM_ID} canManage />);
    await user.click(screen.getByText('Invite people'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Team management access');
  });

  it('stops showing the controls once the panel is closed again', async () => {
    let loads = 0;
    server.use(
      http.get(`/api/teams/${TEAM_ID}/invitations`, () => {
        loads += 1;
        return HttpResponse.json(page([]));
      }),
    );
    const user = userEvent.setup();
    render(<TeamInvitationPanel teamId={TEAM_ID} canManage />);
    await user.click(screen.getByText('Invite people'));
    await waitFor(() => {
      expect(loads).toBe(1);
    });
    await user.click(screen.getByText('Invite people'));
    await waitFor(() => {
      expect(screen.queryByRole('textbox', { name: 'Find a person' })).not.toBeInTheDocument();
    });
    expect(loads).toBe(1);
  });

  it('explains an empty search and a search failure', async () => {
    const user = await open();
    server.use(http.get('/api/directory/users', () => HttpResponse.json(page([]))));
    await user.type(screen.getByRole('textbox', { name: 'Find a person' }), 'Zed');
    await user.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByText('No discoverable accounts matched.')).toBeInTheDocument();

    server.use(
      http.get('/api/directory/users', () => apiError(500, 'server_error', 'Directory offline.')),
    );
    await user.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Directory offline.');
    expect(screen.queryByText('No discoverable accounts matched.')).not.toBeInTheDocument();
  });

  it('rejects a whitespace-padded query that is too short', async () => {
    const user = await open();
    const field = screen.getByRole('textbox', { name: 'Find a person' });
    await user.type(field, 'a ');
    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled();
    fireEvent.submit(screen.getByRole('form', { name: 'Search operator directory' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('at least two characters');
  });

  it('marks already invited people and invites a new person with a note', async () => {
    let body: unknown;
    let pending: TeamInvitation[] = [invitation()];
    server.use(
      http.get(`/api/teams/${TEAM_ID}/invitations`, () => HttpResponse.json(page(pending))),
      http.get('/api/directory/users', () =>
        HttpResponse.json(
          page([
            person(PERSON_ID, 'Ada Lovelace', 'Analytical Engines'),
            person(OTHER_ID, 'Grace Hopper', null),
          ]),
        ),
      ),
      http.post(`/api/teams/${TEAM_ID}/invitations`, async ({ request }) => {
        body = await request.json();
        const created = invitation({
          id: '44444444-2222-4333-8444-555555555555',
          recipient_id: OTHER_ID,
        });
        pending = [...pending, created];
        return HttpResponse.json(created, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    render(<TeamInvitationPanel teamId={TEAM_ID} canManage />);
    await user.click(screen.getByText('Invite people'));
    await screen.findByRole('region', { name: 'Pending invitations (1)' });
    await user.type(screen.getByRole('textbox', { name: 'Find a person' }), 'desk');
    await user.click(screen.getByRole('button', { name: 'Search' }));

    const ada = (await screen.findByText('Ada Lovelace', { selector: 'p' })).closest('li')!;
    expect(within(ada).getByRole('button', { name: 'Invited' })).toBeDisabled();
    const grace = screen.getByText('Grace Hopper', { selector: 'p' }).closest('li')!;
    expect(within(grace).getByText('@grace_hopper')).toBeInTheDocument();
    await user.type(screen.getByRole('textbox', { name: 'Optional note' }), 'Welcome');
    await user.click(within(grace).getByRole('button', { name: 'Invite as member' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Invitation sent.');
    expect(body).toEqual({ recipient_id: OTHER_ID, note: 'Welcome' });
    expect(await within(grace).findByRole('button', { name: 'Invited' })).toBeDisabled();
    expect(screen.getByRole('textbox', { name: 'Optional note' })).toHaveValue('');
  });

  it('reports failed directory and username invitations', async () => {
    server.use(
      http.get('/api/directory/users', () =>
        HttpResponse.json(page([person(OTHER_ID, 'Grace Hopper', null)])),
      ),
      http.post(`/api/teams/${TEAM_ID}/invitations`, () =>
        apiError(422, 'invalid_request', 'The team is archived.'),
      ),
      http.post(`/api/teams/${TEAM_ID}/invitations/by-username`, () =>
        apiError(429, 'rate_limited', 'Slow down.', undefined, { 'Retry-After': '30' }),
      ),
    );
    const user = await open();
    await user.type(screen.getByRole('textbox', { name: 'Find a person' }), 'Grace');
    await user.click(screen.getByRole('button', { name: 'Search' }));
    await user.click(await screen.findByRole('button', { name: 'Invite as member' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The team is archived.');

    await user.type(screen.getByRole('textbox', { name: 'Exact username' }), 'grace_h');
    await user.click(screen.getByRole('button', { name: 'Invite username' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts.');
    expect(screen.getByRole('textbox', { name: 'Exact username' })).toHaveValue('grace_h');
  });
});
