import { act, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { plainUser } from '@/test/fixtures';
import { aiPolicy } from '@/test/fixtures.aiUsage';

import { ModelAssignmentMatrix } from './ModelAssignmentMatrix';
import { binding, draft, team } from './llmTestFixtures';

const luna = draft({ is_tested: true });
const sol = draft({ id: 'sol', name: 'OpenAI Sol', is_tested: true });

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

it('prevents repeat writes and holds the row busy until canonical reload finishes', async () => {
  const user = userEvent.setup();
  let finish!: () => void;
  const onSave = vi.fn(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
  );
  const input = { ...props(), onSave };
  const { rerender } = render(<ModelAssignmentMatrix {...input} />);
  await user.selectOptions(
    screen.getByRole('combobox', { name: `Model for ${team.name}` }),
    sol.id,
  );
  const save = screen.getByRole('button', { name: `Save ${team.name}` });
  await user.dblClick(save);
  expect(onSave).toHaveBeenCalledTimes(1);
  expect(save).toBeDisabled();
  expect(
    screen.getByRole('combobox', { name: 'Daily allowance for Global / site' }),
  ).toBeDisabled();
  rerender(
    <ModelAssignmentMatrix {...input} connections={[binding(luna), binding(sol, team.id)]} />,
  );
  await act(async () => {
    finish();
    await Promise.resolve();
  });
  expect(screen.getByRole('combobox', { name: `Model for ${team.name}` })).toHaveValue(sol.id);
  expect(screen.queryByRole('button', { name: `Save ${team.name}` })).not.toBeInTheDocument();
});

it('surfaces stale-write errors even when the parent reloads rows before rejecting', async () => {
  const user = userEvent.setup();
  let fail!: (reason: unknown) => void;
  const onSave = vi.fn(
    () =>
      new Promise<void>((_resolve, reject) => {
        fail = reject;
      }),
  );
  const input = { ...props(), onSave };
  const { rerender } = render(<ModelAssignmentMatrix {...input} />);
  await user.selectOptions(
    screen.getByRole('combobox', { name: `Model for ${team.name}` }),
    sol.id,
  );
  await user.click(screen.getByRole('button', { name: `Save ${team.name}` }));
  rerender(<ModelAssignmentMatrix {...input} connections={[{ ...binding(luna), revision: 2 }]} />);
  await act(async () => {
    fail(new ApiError(409, 'conflict', 'Settings changed. Review and save again.'));
    await Promise.resolve();
  });
  expect(screen.getByRole('alert')).toHaveTextContent(
    `${team.name}: Settings changed. Review and save again.`,
  );
  expect(screen.getByRole('combobox', { name: `Model for ${team.name}` })).toHaveValue('');
});

it('keeps an unsuccessful draft available for retry and clears its error on success', async () => {
  const user = userEvent.setup();
  const input = props();
  input.onSave.mockRejectedValueOnce(new Error('private internal failure'));
  render(<ModelAssignmentMatrix {...input} />);
  await user.selectOptions(
    screen.getByRole('combobox', { name: `Daily allowance for ${team.name}` }),
    'blocked',
  );
  await user.click(screen.getByRole('button', { name: `Save ${team.name}` }));
  expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong. Please try again.');
  expect(screen.queryByText('private internal failure')).not.toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: `Daily allowance for ${team.name}` })).toHaveValue(
    'blocked',
  );
  await user.click(screen.getByRole('button', { name: `Save ${team.name}` }));
  expect(input.onSave).toHaveBeenCalledTimes(2);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('resets unsaved values when authoritative policies or model proof revisions change', async () => {
  const user = userEvent.setup();
  const input = props();
  const { rerender } = render(<ModelAssignmentMatrix {...input} />);
  const getAllowance = () =>
    screen.getByRole('combobox', { name: `Daily allowance for ${team.name}` });
  await user.selectOptions(getAllowance(), 'light');
  rerender(
    <ModelAssignmentMatrix
      {...input}
      policies={[
        aiPolicy({
          scope: 'team',
          target_id: team.id,
          period: 'day',
          request_limit: 250,
          token_limit: 500_000,
          revision: 2,
        }),
      ]}
    />,
  );
  expect(getAllowance()).toHaveValue('standard');
  await user.selectOptions(
    screen.getByRole('combobox', { name: `Model for ${team.name}` }),
    sol.id,
  );
  rerender(
    <ModelAssignmentMatrix
      {...input}
      profiles={[luna, { ...sol, revision: 2, is_tested: false }]}
    />,
  );
  expect(screen.getByRole('combobox', { name: `Model for ${team.name}` })).toHaveValue('');
  expect(screen.queryByRole('button', { name: `Save ${team.name}` })).not.toBeInTheDocument();
});

it('disables assignments without a global model and honours parent busy state', () => {
  const input = props();
  const { rerender } = render(<ModelAssignmentMatrix {...input} connections={[]} />);
  expect(screen.getByRole('combobox', { name: `Model for ${team.name}` })).toBeDisabled();
  expect(screen.getByText('Set the global model first.')).toBeVisible();
  rerender(<ModelAssignmentMatrix {...input} busy />);
  expect(screen.getByRole('combobox', { name: 'Model for Global / site' })).toBeDisabled();
  expect(screen.getByRole('combobox', { name: `Daily allowance for ${team.name}` })).toBeDisabled();
});

it('can cancel draft changes back to an existing custom policy and untested model', async () => {
  const user = userEvent.setup();
  const input = props();
  render(
    <ModelAssignmentMatrix
      {...input}
      profiles={[{ ...luna, is_tested: false }, sol]}
      policies={[aiPolicy({ period: 'day' })]}
    />,
  );
  const model = screen.getByRole('combobox', { name: 'Model for Global / site' });
  const allowance = screen.getByRole('combobox', { name: 'Daily allowance for Global / site' });
  await user.selectOptions(model, sol.id);
  await user.selectOptions(allowance, 'light');
  await user.click(screen.getByRole('button', { name: 'Cancel changes for Global / site' }));
  expect(model).toHaveValue(luna.id);
  expect(allowance).toHaveValue('custom');
  expect(screen.queryByRole('button', { name: 'Save Global / site' })).not.toBeInTheDocument();
  expect(input.onSave).not.toHaveBeenCalled();
});
