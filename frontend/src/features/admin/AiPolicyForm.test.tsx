import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { AiPolicy } from '@/lib/api/aiUsage';
import { aiPolicy, teamId } from '@/test/fixtures.aiUsage';
import { adminUser, plainUser } from '@/test/fixtures';
import { team } from '@/test/fixtures.teams';

import { AiPolicyForm } from './AiPolicyForm';

const teams = [{ ...team, id: teamId, name: 'Northern desk' }];
const missingId = '99999999-9999-4999-8999-999999999999';

function mount(editing: AiPolicy | null, saved = true) {
  const onSave = vi.fn(() => Promise.resolve(saved));
  const onCancel = vi.fn();
  const onInvalid = vi.fn();
  const user = userEvent.setup();
  render(
    <AiPolicyForm
      users={[adminUser, plainUser]}
      teams={teams}
      editing={editing}
      busy={false}
      onSave={onSave}
      onCancel={onCancel}
      onInvalid={onInvalid}
    />,
  );
  return { user, onSave, onCancel, onInvalid };
}

describe('AiPolicyForm', () => {
  it('creates a user policy and resets the form afterwards', async () => {
    const { user, onSave } = mount(null);
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Scope'), 'user');
    const account = screen.getByLabelText('Account');
    expect(screen.getByRole('option', { name: 'Choose an account' })).toBeInTheDocument();
    await user.selectOptions(account, plainUser.id);
    await user.selectOptions(screen.getByLabelText('Reset'), 'day');
    await user.type(screen.getByLabelText('Requests'), '5');
    await user.type(screen.getByLabelText('Tokens'), '500');
    await user.click(screen.getByRole('button', { name: 'Add policy' }));

    expect(onSave).toHaveBeenCalledWith({
      scope: 'user',
      target_id: plainUser.id,
      period: 'day',
      request_limit: 5,
      token_limit: 500,
      enabled: true,
    });
    expect(await screen.findByLabelText('Scope')).toHaveValue('global');
    expect(screen.getByLabelText('Requests')).toHaveValue('');
    expect(screen.queryByLabelText('Account')).not.toBeInTheDocument();
  });

  it('keeps the entered values when saving fails', async () => {
    const { user, onSave } = mount(null, false);
    await user.selectOptions(screen.getByLabelText('Scope'), 'team');
    expect(screen.getByRole('option', { name: 'Choose a team' })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Team'), teamId);
    await user.type(screen.getByLabelText('Requests'), '3');
    await user.click(screen.getByRole('button', { name: 'Add policy' }));
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Team')).toHaveValue(teamId);
    expect(screen.getByLabelText('Requests')).toHaveValue('3');
  });

  it('rejects an invalid request limit', async () => {
    const { user, onSave, onInvalid } = mount(null);
    await user.type(screen.getByLabelText('Requests'), '-2');
    await user.click(screen.getByRole('button', { name: 'Add policy' }));
    expect(onInvalid).toHaveBeenCalledWith(
      'Limits must be whole numbers, zero or blank for unlimited.',
    );
    expect(onSave).not.toHaveBeenCalled();
  });

  it('edits an existing policy for an unavailable team without resetting', async () => {
    const policy = aiPolicy({
      scope: 'team',
      target_id: missingId,
      period: 'week',
      request_limit: null,
      token_limit: 2000,
    });
    const { user, onSave, onCancel } = mount(policy);
    expect(screen.getByLabelText('Team')).toHaveValue(missingId);
    expect(screen.getByRole('option', { name: 'Unavailable team' })).toBeInTheDocument();
    expect(screen.getByLabelText('Requests')).toHaveValue('');
    expect(screen.getByLabelText('Tokens')).toHaveValue('2000');
    await user.click(screen.getByRole('button', { name: 'Save policy' }));
    expect(onSave).toHaveBeenCalledWith({
      scope: 'team',
      target_id: missingId,
      period: 'week',
      request_limit: null,
      token_limit: 2000,
      enabled: true,
    });
    expect(screen.getByLabelText('Tokens')).toHaveValue('2000');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('labels an unavailable account target', () => {
    mount(aiPolicy({ scope: 'user', target_id: missingId }));
    expect(screen.getByLabelText('Account')).toHaveValue(missingId);
    expect(screen.getByRole('option', { name: 'Unavailable account' })).toBeInTheDocument();
  });

  it('starts on the target the administrator previewed', async () => {
    const onSave = vi.fn(() => Promise.resolve(true));
    const user = userEvent.setup();
    render(
      <AiPolicyForm
        users={[adminUser, plainUser]}
        teams={teams}
        editing={null}
        prefill={{ scope: 'team', targetId: teamId }}
        busy={false}
        onSave={onSave}
        onCancel={vi.fn()}
        onInvalid={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('Scope')).toHaveValue('team');
    expect(screen.getByLabelText('Team')).toHaveValue(teamId);
    await user.type(screen.getByLabelText('Tokens'), '300000');
    await user.click(screen.getByRole('button', { name: 'Add policy' }));
    expect(onSave).toHaveBeenCalledWith({
      scope: 'team',
      target_id: teamId,
      period: 'month',
      request_limit: null,
      token_limit: 300000,
      enabled: true,
    });
  });
});
