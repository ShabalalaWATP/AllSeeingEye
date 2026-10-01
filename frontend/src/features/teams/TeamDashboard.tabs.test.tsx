import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';

import { plainUser } from '@/test/fixtures';
import { roster } from '@/test/fixtures.teams';

import { TeamDashboard, type TeamDashboardTab } from './TeamDashboard';
import type { TeamCapabilities } from './teamCapabilities';

const capabilities: TeamCapabilities = {
  isAdmin: false,
  isMember: true,
  isManager: false,
  teamIsActive: true,
  canCreateTeam: true,
  canManageMembers: false,
  canManageTeam: false,
  canLeave: true,
};

function Harness({ initial = 'members' }: { initial?: TeamDashboardTab }) {
  const [tab, setTab] = useState<TeamDashboardTab>(initial);
  return (
    <TeamDashboard
      detail={roster}
      user={plainUser}
      capabilities={capabilities}
      activeTab={tab}
      onTabChange={setTab}
      members={<p>Roster content</p>}
    />
  );
}

describe('TeamDashboard tabs', () => {
  it('groups the tabs in a labelled tablist with a single tab stop', () => {
    render(<Harness />);
    const list = screen.getByRole('tablist', { name: 'Team workspace sections' });
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(4);
    for (const tab of tabs) expect(list).toContainElement(tab);
    const selected = screen.getByRole('tab', { name: /Members/ });
    expect(selected).toHaveAttribute('aria-selected', 'true');
    expect(selected).toHaveAttribute('tabindex', '0');
    for (const tab of tabs.filter((item) => item !== selected)) {
      expect(tab).toHaveAttribute('tabindex', '-1');
      expect(tab).toHaveAttribute('aria-selected', 'false');
    }
  });

  it('only points aria-controls at the rendered panel, which the selected tab labels', () => {
    render(<Harness />);
    for (const tab of screen.getAllByRole('tab')) {
      const controls = tab.getAttribute('aria-controls');
      if (tab.getAttribute('aria-selected') === 'true') {
        expect(controls).not.toBeNull();
        expect(document.getElementById(controls ?? '')).not.toBeNull();
      } else {
        expect(controls).toBeNull();
      }
    }
    expect(screen.getByRole('tabpanel', { name: /Members/ })).toHaveTextContent('Roster content');
  });

  it('moves selection and focus with the arrow, Home and End keys', async () => {
    const user = userEvent.setup();
    render(<Harness initial="research" />);
    screen.getByRole('tab', { name: /Research/ }).focus();

    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: /Board/ })).toHaveFocus();
    expect(screen.getByRole('tab', { name: /Board/ })).toHaveAttribute('aria-selected', 'true');

    await user.keyboard('{ArrowRight}{ArrowRight}');
    expect(screen.getByRole('tab', { name: /Overview/ })).toHaveFocus();

    await user.keyboard('{ArrowLeft}');
    expect(screen.getByRole('tab', { name: /Members/ })).toHaveFocus();

    await user.keyboard('{Home}');
    expect(screen.getByRole('tab', { name: /Overview/ })).toHaveFocus();

    await user.keyboard('{End}');
    const members = screen.getByRole('tab', { name: /Members/ });
    expect(members).toHaveFocus();
    expect(members).toHaveAttribute('aria-selected', 'true');
    expect(members).toHaveAttribute('tabindex', '0');
  });
});
