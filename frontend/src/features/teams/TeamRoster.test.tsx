import { act, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { manager, roster, setupTeams } from '@/test/fixtures.teams';

let compact = true;
let changed: (() => void) | undefined;
beforeEach(() => {
  const original = window.matchMedia.bind(window);
  vi.spyOn(window, 'matchMedia').mockImplementation((query) => {
    const media = original(query);
    if (query.includes('max-width: 639px')) {
      Object.defineProperty(media, 'matches', { get: () => compact });
      media.addEventListener = (
        _type: string,
        listener: EventListenerOrEventListenerObject | null,
      ) => {
        changed = listener as () => void;
      };
      media.removeEventListener = () => {
        changed = undefined;
      };
    }
    return media;
  });
});
afterEach(() => {
  compact = true;
  changed = undefined;
});

async function member(name: string) {
  const list = await screen.findByRole('list', { name: 'Team members' });
  const row = within(list).getByText(name).closest('li');
  if (!row) throw new Error('Missing member');
  return within(row);
}

describe('compact team roster', () => {
  it('labels member identity and both roles without duplicate desktop rows', async () => {
    setupTeams(manager);
    const managerRow = await member('Mina Manager');
    expect(managerRow.getByText('manager@example.com')).toBeVisible();
    expect(managerRow.getByText('Account')).toBeVisible();
    expect(managerRow.getByText('Team role')).toBeVisible();
    expect(managerRow.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('table', { name: 'Team members' })).not.toBeInTheDocument();
    expect(screen.getAllByText('Mina Manager')).toHaveLength(1);
  });

  it('keeps membership removal scoped and requires confirmation on mobile', async () => {
    const { user, writes } = setupTeams(manager);
    const userRow = await member('Uma User');
    await user.click(userRow.getByRole('button', { name: 'Remove member' }));
    expect(writes).toHaveLength(0);
    await user.click(userRow.getByRole('button', { name: 'Cancel' }));
    expect(writes).toHaveLength(0);
    await user.click(userRow.getByRole('button', { name: 'Remove member' }));
    await user.click(userRow.getByRole('button', { name: 'Confirm remove member' }));
    await waitFor(() => {
      expect(writes).toEqual([{ method: 'DELETE', userId: roster.members[1]?.user_id }]);
    });
  });

  it('switches back to the semantic desktop table when the viewport widens', async () => {
    setupTeams(manager);
    await member('Uma User');
    act(() => {
      compact = false;
      changed?.();
    });
    expect(screen.getByRole('table', { name: 'Team members' })).toBeVisible();
    expect(screen.queryByRole('list', { name: 'Team members' })).not.toBeInTheDocument();
    expect(screen.getAllByText('Uma User')).toHaveLength(1);
  });
});
