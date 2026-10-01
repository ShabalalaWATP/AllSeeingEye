/**
 * Invitation expiry reads the same in every browser: the app's date format and the signed-in
 * account's time zone, never whatever locale the browser happens to report (KAN-102).
 */
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { TeamInvitation } from '@/lib/api/teamInvitations';
import { useAuthStore } from '@/stores/auth';
import { useProfileStore } from '@/stores/profile';
import { plainUser } from '@/test/fixtures';
import { defaultProfile } from '@/test/handlers.profile';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { TeamInvitationPanel } from './TeamInvitationPanel';

const TEAM_ID = '11111111-2222-4333-8444-555555555555';
const pending: TeamInvitation = {
  id: '22222222-2222-4333-8444-555555555555',
  team_id: TEAM_ID,
  recipient_id: '0f0e0d0c-0b0a-4908-8706-050403020100',
  inviter_id: '0f0e0d0c-0b0a-4908-8706-0504030201ff',
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
};

/** Pretend the browser reports German, so any locale-default formatting shows up. */
beforeEach(() => {
  const german = (options?: Intl.DateTimeFormatOptions) =>
    function (this: Date, locales?: Intl.LocalesArgument, given?: Intl.DateTimeFormatOptions) {
      return new Intl.DateTimeFormat(locales ?? 'de-DE', given ?? options).format(this);
    };
  vi.spyOn(Date.prototype, 'toLocaleDateString').mockImplementation(german());
  vi.spyOn(Date.prototype, 'toLocaleString').mockImplementation(
    german({ dateStyle: 'short', timeStyle: 'medium' }),
  );
  server.use(
    http.get(`/api/teams/${TEAM_ID}/invitations`, () =>
      HttpResponse.json({ items: [pending], total: 1, offset: 0, limit: 20, next_offset: null }),
    ),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
  useProfileStore.setState({ owner: null, profile: null });
  useAuthStore.getState().clearSession();
});

async function openPanel() {
  render(<TeamInvitationPanel teamId={TEAM_ID} canManage />);
  await userEvent.setup().click(screen.getByText('Invite people'));
}

describe('team invitation expiry in a non-UK browser', () => {
  it('uses the app date format in UTC by default', async () => {
    await openPanel();
    expect(await screen.findByText('expires 20/09/2026, 10:00 UTC')).toBeInTheDocument();
  });

  it("follows the signed-in account's time zone and date format", async () => {
    applySession('user');
    useProfileStore.setState({
      owner: plainUser.id,
      profile: { ...defaultProfile, timezone: 'Europe/London', date_format: 'iso' },
    });
    await openPanel();
    expect(await screen.findByText('expires 2026-09-20 11:00 Europe/London')).toBeInTheDocument();
  });

  it('ignores a profile loaded for a different account', async () => {
    applySession('admin');
    useProfileStore.setState({
      owner: plainUser.id,
      profile: { ...defaultProfile, timezone: 'Asia/Tokyo' },
    });
    await openPanel();
    expect(await screen.findByText('expires 20/09/2026, 10:00 UTC')).toBeInTheDocument();
  });
});
