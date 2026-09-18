import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api/errors';
import { plainUser, adminUser } from '@/test/fixtures';
import { draft, proof, team } from './llmTestFixtures';
import {
  advanceToAudience,
  advanceToTest,
  openWizard,
  secondTeam,
  mockModelSetupDialog,
} from './ModelSetupTestSupport';

beforeEach(mockModelSetupDialog);

describe('new model popup', () => {
  it('walks through one field at a time, tests explicitly, and saves multiple team assignments together', async () => {
    const view = await openWizard();
    expect(screen.getByRole('dialog')).toBeVisible();
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument();
    expect(view.state.models).toBe(0);
    await advanceToAudience(view);
    expect(view.state.tests).toBe(1);
    expect(view.onApply).not.toHaveBeenCalled();
    await view.user.click(screen.getByLabelText('Specific teams'));
    expect(screen.getByRole('button', { name: 'Save and close' })).toBeDisabled();
    await view.user.click(screen.getByRole('checkbox', { name: `${team.name} Team workspace` }));
    await view.user.click(
      screen.getByRole('checkbox', { name: `${secondTeam.name} Team workspace` }),
    );
    await view.user.click(screen.getByRole('button', { name: 'Save and close' }));
    await waitFor(() => expect(view.onClose).toHaveBeenCalledOnce());
    expect(view.onApply).toHaveBeenCalledWith(
      expect.objectContaining({ model: 'gpt-5.6-luna', tested_config_hash: proof }),
      { scope: 'team', targetIds: [team.id, secondTeam.id] },
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open model setup' })).toHaveFocus();
  });

  it('resumes a tested connection at the audience and supports multiple personal workspaces', async () => {
    const view = await openWizard(
      draft({ is_tested: true, tested_revision: 1, tested_config_hash: proof }),
    );
    expect(screen.getByRole('heading', { name: 'Who should use this model?' })).toBeVisible();
    expect(view.state.tests).toBe(0);
    await view.user.click(screen.getByLabelText('Specific people'));
    await view.user.click(
      screen.getByRole('checkbox', { name: `${plainUser.display_name} ${plainUser.email}` }),
    );
    await view.user.type(screen.getByLabelText('Find people'), adminUser.email);
    await view.user.click(
      screen.getByRole('checkbox', { name: `${adminUser.display_name} ${adminUser.email}` }),
    );
    expect(screen.getByRole('status')).toHaveTextContent('2 selected');
    await view.user.click(screen.getByRole('button', { name: 'Save and close' }));
    expect(view.onApply).toHaveBeenCalledWith(expect.anything(), {
      scope: 'user',
      targetIds: [plainUser.id, adminUser.id],
    });
  });

  it('keeps a tested draft and proof available after an assignment error, then retries', async () => {
    const view = await openWizard(
      draft({ is_tested: true, tested_revision: 1, tested_config_hash: proof }),
    );
    view.onApply.mockRejectedValueOnce(
      new ApiError(409, 'stale_binding', 'The assignment changed.'),
    );
    await view.user.click(screen.getByRole('button', { name: 'Save and close' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Your tested connection is still available to retry.',
    );
    expect(view.onClose).not.toHaveBeenCalled();
    await view.user.click(screen.getByRole('button', { name: 'Save and close' }));
    await waitFor(() => expect(view.onClose).toHaveBeenCalled());
    expect(view.state.tests).toBe(0);
    expect(view.onApply).toHaveBeenLastCalledWith(
      expect.objectContaining({ tested_config_hash: proof }),
      { scope: 'global', targetIds: [] },
    );
  });

  it('invalidates successful proof when the model is changed', async () => {
    const view = await openWizard();
    await advanceToAudience(view);
    await view.user.click(screen.getByRole('button', { name: 'Back' }));
    await view.user.click(screen.getByRole('button', { name: 'Back' }));
    await view.user.click(screen.getByRole('button', { name: 'Back' }));
    await view.user.selectOptions(
      await screen.findByLabelText('Account model'),
      'manual-alternative',
    );
    await view.user.click(screen.getByRole('button', { name: 'Continue' }));
    expect(screen.getByLabelText('Reasoning level')).toHaveValue('');
    await view.user.click(screen.getByRole('button', { name: 'Continue' }));
    expect(screen.queryByRole('button', { name: 'Choose audience' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Test connection' })).toBeVisible();
    expect(view.onApply).not.toHaveBeenCalled();
  });

  it('traps focus and restores the opener on Escape cancellation', async () => {
    await openWizard();
    const modal = screen.getByRole('dialog');
    const close = within(modal).getByRole('button', { name: 'Close model setup' });
    close.focus();
    fireEvent.keyDown(close, { key: 'Tab', shiftKey: true });
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();
    fireEvent.keyDown(screen.getByRole('button', { name: 'Cancel' }), { key: 'Tab' });
    expect(close).toHaveFocus();
    fireEvent(modal, new Event('cancel', { bubbles: true, cancelable: true }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open model setup' })).toHaveFocus();
  });

  it('uses manual Bedrock model entry without account-discovery calls', async () => {
    const view = await openWizard();
    await view.user.type(screen.getByLabelText('Connection name'), 'AWS model');
    await view.user.click(screen.getByText('Provider: OpenAI'));
    await view.user.selectOptions(screen.getByLabelText('Provider'), 'bedrock');
    await view.user.type(screen.getByLabelText('AWS region'), 'eu-west-2');
    await view.user.click(screen.getByRole('button', { name: 'Continue' }));
    await view.user.type(screen.getByLabelText('Bedrock API key'), 'synthetic-bedrock-key');
    await view.user.click(screen.getByRole('button', { name: 'Continue' }));
    await view.user.type(
      screen.getByLabelText('Model or inference profile ID'),
      'openai.gpt-oss-120b-1:0',
    );
    await view.user.click(screen.getByRole('button', { name: 'Continue' }));
    expect(screen.queryByLabelText('Reasoning level')).not.toBeInTheDocument();
    expect(view.state.models).toBe(0);
    await view.user.click(screen.getByRole('button', { name: 'Continue' }));
    await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
    await screen.findByText(/Connection test passed/);
    expect(view.state.saves[0]).toMatchObject({
      provider: 'bedrock',
      reasoning_effort: null,
      model: 'openai.gpt-oss-120b-1:0',
    });
  });

  it('preserves a saved but unassigned draft when setup is cancelled', async () => {
    const view = await openWizard();
    await advanceToTest(view);
    await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
    await screen.findByText(/Connection test passed/);
    expect(screen.getByText(/Closing keeps it available/)).toBeVisible();
    await view.user.click(screen.getByRole('button', { name: 'Close model setup' }));
    expect(view.state.profiles).toHaveLength(1);
    expect(view.onApply).not.toHaveBeenCalled();
  });

  it('runs another provider test only after the administrator explicitly requests it', async () => {
    const view = await openWizard(
      draft({ is_tested: true, tested_revision: 1, tested_config_hash: proof }),
    );
    await view.user.click(screen.getByRole('button', { name: 'Back' }));
    expect(screen.getByRole('button', { name: 'Choose audience' })).toBeVisible();
    expect(view.state.tests).toBe(0);
    await view.user.click(screen.getByRole('button', { name: 'Test again' }));
    await screen.findByText(/Connection test passed in/);
    expect(view.state.tests).toBe(1);
  });
});
