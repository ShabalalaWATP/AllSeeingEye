import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { ModelSetupAudience } from './ModelSetupAudience';
import type { ModelSetupAudience as Audience } from './ModelSetupTypes';
import { binding, draft, team } from './llmTestFixtures';
import { plainUser } from '@/test/fixtures';

it('caps multi-selection at 100 while keeping selected items available for deselection', async () => {
  const teams = Array.from({ length: 101 }, (_, index) => ({
    ...team,
    id: `team-${index}`,
    name: `Team ${index + 1}`,
  }));
  function Harness() {
    const [value, setValue] = useState<Audience>({
      scope: 'team',
      targetIds: teams.slice(0, 99).map((entry) => entry.id),
    });
    return (
      <ModelSetupAudience
        value={value}
        onChange={setValue}
        teams={teams}
        users={[]}
        connections={[binding(draft())]}
      />
    );
  }
  const user = userEvent.setup();
  render(<Harness />);
  await user.click(screen.getByRole('checkbox', { name: 'Team 100 Team workspace' }));
  expect(screen.getByRole('status')).toHaveTextContent('100 selected / 100 maximum');
  expect(screen.getByRole('checkbox', { name: 'Team 101 Team workspace' })).toBeDisabled();
  expect(screen.getByRole('checkbox', { name: 'Team 1 Team workspace' })).toBeEnabled();
  await user.click(screen.getByRole('checkbox', { name: 'Team 1 Team workspace' }));
  expect(screen.getByRole('checkbox', { name: 'Team 101 Team workspace' })).toBeEnabled();
  await user.click(screen.getByRole('checkbox', { name: 'Team 101 Team workspace' }));
  expect(screen.getByRole('status')).toHaveTextContent('100 selected / 100 maximum');
  expect(screen.getByRole('checkbox', { name: 'Team 1 Team workspace' })).not.toBeChecked();
  expect(screen.getByRole('checkbox', { name: 'Team 1 Team workspace' })).toBeDisabled();
});

it('explains existing overrides and empty filtered results for both target types', async () => {
  const connections = [
    binding(draft()),
    binding(draft(), team.id),
    { ...binding(draft()), user_id: plainUser.id },
  ];
  function Harness() {
    const [value, setValue] = useState<Audience>({ scope: 'team', targetIds: [team.id] });
    return (
      <ModelSetupAudience
        value={value}
        onChange={setValue}
        teams={[team]}
        users={[plainUser]}
        connections={connections}
      />
    );
  }
  const user = userEvent.setup();
  render(<Harness />);
  expect(screen.getByRole('status')).toHaveTextContent('1 existing overrides will be replaced');
  await user.type(screen.getByLabelText('Find teams'), 'unavailable');
  expect(screen.getByText('No matching teams.')).toBeVisible();
  await user.click(screen.getByLabelText('Specific people'));
  await user.click(
    screen.getByRole('checkbox', { name: `${plainUser.display_name} ${plainUser.email}` }),
  );
  expect(screen.getByRole('status')).toHaveTextContent('1 existing overrides will be replaced');
  await user.type(screen.getByLabelText('Find people'), 'unavailable');
  expect(screen.getByText('No matching people.')).toBeVisible();
  await user.click(screen.getByLabelText('Global default'));
  expect(screen.getByText(/all users and teams without their own override/)).toBeVisible();
});
