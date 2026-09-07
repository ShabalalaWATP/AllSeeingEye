import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { plainUser } from '@/test/fixtures';
import { draft, binding } from './llmTestFixtures';
import { LlmPersonalConnections } from './LlmPersonalConnections';
it('shows missing metadata honestly while retaining a deliberate reset path', async () => {
  const onReset = vi.fn();
  const onReplace = vi.fn();
  const user = userEvent.setup();
  render(
    <LlmPersonalConnections
      bindings={[{ ...binding(draft()), user_id: plainUser.id }]}
      profiles={[]}
      users={[]}
      disabled={false}
      onReset={onReset}
      onReplace={onReplace}
    />,
  );
  expect(screen.getByText('User unavailable')).toBeVisible();
  expect(screen.getByText(/Connection unavailable.*provider default/)).toBeVisible();
  expect(
    screen.queryByRole('button', { name: 'Replace personal connection' }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Use global connection' }));
  await user.click(screen.getByRole('button', { name: 'Keep personal override' }));
  expect(onReset).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: 'Confirm personal reset' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Use global connection' }));
  await user.click(screen.getByRole('button', { name: 'Confirm personal reset' }));
  expect(onReset).toHaveBeenCalledWith(plainUser.id);
});
it('identifies inactive accounts and preserves the personal audience when replacing', async () => {
  const profile = draft({ reasoning_effort: null });
  const onReplace = vi.fn();
  const props = {
    bindings: [{ ...binding(profile), user_id: plainUser.id }],
    profiles: [profile],
    users: [{ ...plainUser, is_active: false }],
    disabled: false,
    onReset: vi.fn(),
    onReplace,
  };
  const { rerender } = render(<LlmPersonalConnections {...props} />);
  expect(screen.getByText(/inactive/)).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Replace personal connection' }));
  expect(onReplace).toHaveBeenCalledWith(profile, plainUser.id);
  rerender(<LlmPersonalConnections {...props} disabled />);
  expect(screen.getByRole('button', { name: 'Replace personal connection' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Use global connection' })).toBeDisabled();
});
