import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import { plainUser } from '@/test/fixtures';
import { aiPolicy } from '@/test/fixtures.aiUsage';

import { ModelAssignmentMatrix } from './ModelAssignmentMatrix';
import { binding, draft, team } from './llmTestFixtures';

const luna = draft({ is_tested: true });
const sol = draft({
  id: '88888888-8888-4888-8888-888888888888',
  name: 'OpenAI Sol',
  model: 'gpt-5.6-sol',
  is_tested: true,
});

function props() {
  return {
    profiles: [luna, sol],
    connections: [binding(luna)],
    policies: [],
    teams: [team],
    users: [plainUser],
    busy: false,
    onSave: vi.fn().mockResolvedValue(undefined),
  };
}

it('shows the live default and stages model and allowance changes until the row is saved', async () => {
  const user = userEvent.setup();
  const input = props();
  render(<ModelAssignmentMatrix {...input} />);
  const model = screen.getByRole('combobox', { name: `Model for ${team.name}` });
  expect(model).toHaveValue('');
  expect(within(model).getByRole('option', { name: 'Use default (OpenAI Luna)' })).toBeVisible();
  expect(screen.queryByRole('button', { name: `Save ${team.name}` })).not.toBeInTheDocument();
  await user.selectOptions(model, sol.id);
  await user.selectOptions(
    screen.getByRole('combobox', { name: `Daily allowance for ${team.name}` }),
    'intensive',
  );
  expect(input.onSave).not.toHaveBeenCalled();
  expect(screen.getByText('1,000 requests · 2,000,000 tokens per day')).toBeVisible();
  await user.click(screen.getByRole('button', { name: `Save ${team.name}` }));
  expect(input.onSave).toHaveBeenCalledExactlyOnceWith({
    scope: 'team',
    targetId: team.id,
    modelId: sol.id,
    preset: 'intensive',
  });
});

it('sends only a changed model and preserves custom daily, weekly and monthly policies', async () => {
  const user = userEvent.setup();
  const input = props();
  render(
    <ModelAssignmentMatrix
      {...input}
      policies={[
        aiPolicy({ scope: 'team', target_id: team.id, period: 'day' }),
        aiPolicy({
          id: 'weekly',
          scope: 'team',
          target_id: team.id,
          period: 'week',
          token_limit: 4_000,
        }),
        aiPolicy({
          id: 'monthly',
          scope: 'team',
          target_id: team.id,
          period: 'month',
          request_limit: null,
        }),
      ]}
    />,
  );
  const allowance = screen.getByRole('combobox', { name: `Daily allowance for ${team.name}` });
  expect(allowance).toHaveValue('custom');
  expect(within(allowance).getByRole('option', { name: 'Custom (existing)' })).toBeDisabled();
  expect(screen.getByText('Weekly: 10 requests · 4,000 tokens')).toBeVisible();
  expect(screen.getByText('Monthly: no separate request cap · 1,000 tokens')).toBeVisible();
  await user.selectOptions(
    screen.getByRole('combobox', { name: `Model for ${team.name}` }),
    sol.id,
  );
  await user.click(screen.getByRole('button', { name: `Save ${team.name}` }));
  expect(input.onSave).toHaveBeenCalledExactlyOnceWith({
    scope: 'team',
    targetId: team.id,
    modelId: sol.id,
  });
});

it('removes a personal override and daily cap explicitly, retaining global policy semantics', async () => {
  const user = userEvent.setup();
  const input = props();
  render(
    <ModelAssignmentMatrix
      {...input}
      connections={[binding(luna), { ...binding(sol), user_id: plainUser.id }]}
      policies={[
        aiPolicy({
          scope: 'user',
          target_id: plainUser.id,
          period: 'day',
          request_limit: 50,
          token_limit: 100_000,
        }),
      ]}
    />,
  );
  await user.click(screen.getByRole('button', { name: 'Users (1)' }));
  expect(screen.getByText(/User caps cover all their requests, including team work/)).toBeVisible();
  const allowance = screen.getByRole('combobox', {
    name: `Daily allowance for ${plainUser.display_name}`,
  });
  expect(allowance).toHaveValue('light');
  await user.selectOptions(allowance, 'inherit');
  await user.selectOptions(
    screen.getByRole('combobox', { name: `Model for ${plainUser.display_name}` }),
    '',
  );
  await user.click(screen.getByRole('button', { name: `Save ${plainUser.display_name}` }));
  expect(input.onSave).toHaveBeenCalledExactlyOnceWith({
    scope: 'user',
    targetId: plainUser.id,
    modelId: null,
    preset: 'inherit',
  });
});

it('offers only tested text models and preserves the current untested assignment', async () => {
  const user = userEvent.setup();
  const input = props();
  const untested = { ...luna, is_tested: false };
  const embeddings = draft({
    id: 'embeddings',
    name: 'Embeddings',
    roles: ['embeddings'],
    is_tested: true,
  });
  render(<ModelAssignmentMatrix {...input} profiles={[untested, sol, embeddings]} />);
  const globalModel = screen.getByRole('combobox', { name: 'Model for Global / site' });
  expect(globalModel).toHaveValue(luna.id);
  expect(
    within(globalModel).getByRole('option', { name: 'OpenAI Luna · test required' }),
  ).toBeDisabled();
  expect(
    within(globalModel).queryByRole('option', { name: /Use default|Embeddings/ }),
  ).not.toBeInTheDocument();
  const teamModel = screen.getByRole('combobox', { name: `Model for ${team.name}` });
  expect(within(teamModel).queryByRole('option', { name: 'OpenAI Luna' })).not.toBeInTheDocument();
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Daily allowance for Global / site' }),
    'power',
  );
  await user.click(screen.getByRole('button', { name: 'Save Global / site' }));
  expect(input.onSave).toHaveBeenCalledExactlyOnceWith({
    scope: 'global',
    targetId: null,
    preset: 'power',
  });
});

it('excludes tested profiles missing required text roles while preserving a current assignment', () => {
  const legacy = draft({ name: 'Legacy planner', is_tested: true, roles: ['direction'] });
  render(
    <ModelAssignmentMatrix {...props()} profiles={[legacy, sol]} connections={[binding(legacy)]} />,
  );
  const globalModel = screen.getByRole('combobox', { name: 'Model for Global / site' });
  expect(globalModel).toHaveValue(legacy.id);
  expect(within(globalModel).getByRole('option', { name: /Legacy planner/ })).toBeDisabled();
  expect(within(globalModel).getByRole('option', { name: sol.name })).toBeEnabled();
  const teamModel = screen.getByRole('combobox', { name: `Model for ${team.name}` });
  expect(
    within(teamModel).queryByRole('option', { name: 'Legacy planner' }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Save Global / site' })).not.toBeInTheDocument();
});

it('searches active teams and users by name or email, keeping the global row visible', async () => {
  const user = userEvent.setup();
  const input = props();
  render(
    <ModelAssignmentMatrix
      {...input}
      teams={[team, { ...team, id: 'archived', name: 'Archived', is_active: false }]}
      users={[
        plainUser,
        { ...plainUser, id: 'inactive', display_name: 'Inactive', is_active: false },
      ]}
    />,
  );
  expect(screen.queryByText('Archived')).not.toBeInTheDocument();
  await user.type(screen.getByRole('searchbox', { name: 'Search teams' }), 'unknown');
  expect(
    screen.queryByRole('combobox', { name: `Model for ${team.name}` }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: 'Model for Global / site' })).toBeVisible();
  expect(screen.getByText('No matches. Try another search.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Users (1)' }));
  expect(screen.queryByText('Inactive')).not.toBeInTheDocument();
  await user.type(
    screen.getByRole('searchbox', { name: 'Search users' }),
    plainUser.email.toUpperCase(),
  );
  expect(
    screen.getByRole('combobox', { name: `Model for ${plainUser.display_name}` }),
  ).toBeVisible();
});

it('shows missing global assignment and active-audience empty states honestly', () => {
  render(
    <ModelAssignmentMatrix {...props()} profiles={[]} connections={[]} teams={[]} users={[]} />,
  );
  expect(screen.getByRole('combobox', { name: 'Model for Global / site' })).toHaveValue('');
  expect(screen.getByText('No active teams yet.')).toBeVisible();
});
