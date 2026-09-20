import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { plainUser } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { ModelSetupWizard } from './ModelSetupWizard';
import { mockModelSetupDialog } from './ModelSetupTestSupport';
import { binding, draft, proof, team } from './llmTestFixtures';

beforeEach(() => {
  mockModelSetupDialog();
  applySession('admin');
});

function props() {
  const profile = draft({
    is_tested: true,
    revision: 1,
    tested_revision: 1,
    tested_config_hash: proof,
  });
  return {
    initial: profile,
    profiles: [profile],
    teams: [team],
    users: [plainUser],
    onApply: vi.fn(() => Promise.resolve()),
    onSaved: vi.fn(),
    onClose: vi.fn(),
  };
}

it('requires the first tested model to establish the global default', async () => {
  const value = props();
  const user = userEvent.setup();
  render(<ModelSetupWizard {...value} connections={[]} />);
  expect(screen.getByLabelText('Specific teams')).toBeDisabled();
  expect(screen.getByLabelText('Specific people')).toBeDisabled();
  expect(
    screen.getByText('Set a global default before assigning models to specific teams or people.'),
  ).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Save and close' }));
  expect(value.onApply).toHaveBeenCalledWith(value.initial, { scope: 'global', targetIds: [] });
});

it('blocks a selected targeted assignment if its global prerequisite disappears', async () => {
  const value = props();
  const user = userEvent.setup();
  const view = render(<ModelSetupWizard {...value} connections={[binding(value.initial)]} />);
  await user.click(screen.getByLabelText('Specific people'));
  await user.click(
    screen.getByRole('checkbox', { name: `${plainUser.display_name} ${plainUser.email}` }),
  );
  expect(screen.getByRole('button', { name: 'Save and close' })).toBeEnabled();
  view.rerender(<ModelSetupWizard {...value} connections={[]} />);
  expect(screen.getByRole('button', { name: 'Save and close' })).toBeDisabled();
  await user.click(screen.getByLabelText('Global default'));
  await user.click(screen.getByRole('button', { name: 'Save and close' }));
  expect(value.onApply).toHaveBeenCalledWith(value.initial, { scope: 'global', targetIds: [] });
});
