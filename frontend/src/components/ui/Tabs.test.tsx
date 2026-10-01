import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { expectNoAxeViolations } from '@/test/axe';
import { files, read } from '@/test/themeContrast';

import { nextTabIndex, Tabs, tabPanelProps } from './Tabs';

const LINKS = [
  { to: '/research', label: 'New research' },
  { to: '/research/saved', label: 'Saved research' },
  { to: '/research/jobs', label: 'Research progress' },
];

type Section = 'members' | 'board' | 'research';
const PANELS = [
  { id: 'members', label: 'Members', detail: 'Who can see the work' },
  { id: 'board', label: 'Board' },
  { id: 'research', label: 'Research' },
] as const;

function Panels() {
  const [active, setActive] = useState<Section>('members');
  return (
    <main>
      <h1>Team</h1>
      <Tabs
        label="Team sections"
        tabs={PANELS}
        activeTab={active}
        onTabChange={setActive}
        idPrefix="team"
      />
      <div {...tabPanelProps('team', active)}>{active} panel</div>
    </main>
  );
}

describe('Tabs as route views', () => {
  it('marks the current view and keeps a parent tab exact when a sibling extends it', () => {
    render(
      <MemoryRouter initialEntries={['/research/jobs/42']}>
        <Tabs label="Research" links={LINKS} />
      </MemoryRouter>,
    );
    const nav = screen.getByRole('navigation', { name: 'Research' });
    expect(nav).toContainElement(screen.getByRole('link', { name: 'Research progress' }));
    expect(screen.getByRole('link', { name: 'Research progress' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: 'New research' })).not.toHaveAttribute('aria-current');
  });
});

describe('Tabs as panel switches', () => {
  it('has one tab stop, wraps with the arrow keys and labels the panel by its tab', async () => {
    const user = userEvent.setup();
    render(<Panels />);
    const members = screen.getByRole('tab', { name: /Members/ });
    expect(screen.getByRole('tablist', { name: 'Team sections' })).toBeInTheDocument();
    expect(members).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('tab', { name: 'Board' })).toHaveAttribute('tabindex', '-1');
    expect(screen.getByRole('tabpanel', { name: /Members/ })).toHaveTextContent('members panel');
    members.focus();
    await user.keyboard('{ArrowLeft}');
    expect(screen.getByRole('tab', { name: 'Research' })).toHaveFocus();
    expect(screen.getByRole('tab', { name: 'Research' })).toHaveAttribute('aria-selected', 'true');
    await user.keyboard('{Home}');
    expect(members).toHaveFocus();
    await user.keyboard('{End}{ArrowRight}');
    expect(members).toHaveAttribute('aria-controls', 'team-panel-members');
    await user.keyboard('a');
    expect(members).toHaveFocus();
    await expectNoAxeViolations();
  });

  it('is the only tablist, apart from the radio planner', () => {
    // The planner's two steps disable Results until there is a result and restore focus
    // across its own panel swap, inside the map instrument's fixed styling.
    const own = files.filter(
      (file) =>
        file.endsWith('.tsx') &&
        !file.endsWith('.test.tsx') &&
        file !== 'components/ui/Tabs.tsx' &&
        read(file).includes('role="tablist"'),
    );
    expect(own).toEqual(['components/maps/RfPlannerTabs.tsx']);
  });

  it('moves through indices only for navigation keys', () => {
    expect(nextTabIndex('ArrowRight', 2, 3)).toBe(0);
    expect(nextTabIndex('ArrowLeft', 0, 3)).toBe(2);
    expect(nextTabIndex('End', 0, 3)).toBe(2);
    expect(nextTabIndex('Enter', 1, 3)).toBeNull();
  });
});
