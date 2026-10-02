import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useNavigate } from 'react-router';
import { beforeEach, expect, it, vi } from 'vitest';
import {
  getEmailPreferences,
  getSubscriptionEmail,
  saveEmailPreferences,
  saveSubscriptionEmail,
  type EmailPreferences,
} from '@/lib/api/notificationEmail';
import { EmailNotificationSettings } from './EmailNotificationSettings';

vi.mock('@/lib/api/notificationEmail', () => ({
  getEmailPreferences: vi.fn(),
  getSubscriptionEmail: vi.fn(),
  saveEmailPreferences: vi.fn(),
  saveSubscriptionEmail: vi.fn(),
}));
const preferences: EmailPreferences = {
  enabled: false,
  include_names: false,
  confirmed: true,
  available: true,
  destination: 'current@example.invalid',
};

beforeEach(() => {
  vi.mocked(getEmailPreferences).mockReset().mockResolvedValue(preferences);
  vi.mocked(getSubscriptionEmail)
    .mockReset()
    .mockResolvedValue({ policy: 'none', attention: false });
  vi.mocked(saveEmailPreferences).mockReset().mockResolvedValue();
  vi.mocked(saveSubscriptionEmail).mockReset().mockResolvedValue();
});

function mount() {
  render(
    <MemoryRouter>
      <EmailNotificationSettings />
    </MemoryRouter>,
  );
  return userEvent.setup();
}

it('saves account-only preferences and clears the saved status when names are changed', async () => {
  const user = mount();
  await user.click(
    await screen.findByLabelText('Include subscription names (may reveal sensitive topics)'),
  );
  await user.click(screen.getByRole('button', { name: 'Save email preferences' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Email preferences saved');
  expect(saveEmailPreferences).toHaveBeenCalledWith({ enabled: false, include_names: true });
  expect(getSubscriptionEmail).not.toHaveBeenCalled();
  expect(saveSubscriptionEmail).not.toHaveBeenCalled();
  expect(screen.getByText(/Open Email preferences beside a subscription/)).toBeVisible();
  await user.click(
    screen.getByLabelText('Include subscription names (may reveal sensitive topics)'),
  );
  expect(screen.queryByText(/Email preferences saved/)).not.toBeInTheDocument();
});

it.each([false, true])(
  'requires confirmation for opt-in but permits opt-out when enabled=%s',
  async (enabled) => {
    vi.mocked(getEmailPreferences).mockResolvedValue({ ...preferences, enabled, confirmed: false });
    const user = mount();
    const control = await screen.findByLabelText('Allow subscription emails to my account address');
    expect(screen.getByRole('link', { name: 'Security' })).toHaveAttribute(
      'href',
      '/account?section=security',
    );
    if (enabled) {
      expect(control).toBeEnabled();
      await user.click(control);
      expect(control).toBeDisabled();
      await user.click(screen.getByRole('button', { name: 'Save email preferences' }));
      await waitFor(() =>
        expect(saveEmailPreferences).toHaveBeenCalledWith({ enabled: false, include_names: false }),
      );
    } else {
      expect(control).toBeDisabled();
    }
  },
);

it('shows load and save failures without claiming that settings were saved', async () => {
  vi.mocked(getEmailPreferences).mockRejectedValueOnce(new Error('Load unavailable'));
  const first = render(
    <MemoryRouter>
      <EmailNotificationSettings />
    </MemoryRouter>,
  );
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded');
  expect(screen.queryByRole('button', { name: 'Save email preferences' })).not.toBeInTheDocument();
  first.unmount();
  vi.mocked(saveEmailPreferences).mockRejectedValueOnce(new Error('Write unavailable'));
  const user = mount();
  await user.click(await screen.findByRole('button', { name: 'Save email preferences' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be saved');
  expect(screen.queryByText(/Email preferences saved/)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Save email preferences' })).toBeEnabled();
});

it.each(['success', 'failure'])(
  'ignores a late %s after switching subscription settings',
  async (outcome) => {
    let resolve!: (value: EmailPreferences) => void;
    let reject!: (error: Error) => void;
    const pending = new Promise<EmailPreferences>((yes, no) => {
      resolve = yes;
      reject = no;
    });
    vi.mocked(getEmailPreferences).mockReturnValueOnce(pending);
    function NextSubscription() {
      const navigate = useNavigate();
      return (
        <button onClick={() => void navigate('/account?subscription=next')}>
          Next subscription
        </button>
      );
    }
    render(
      <MemoryRouter initialEntries={['/account?subscription=previous']}>
        <NextSubscription />
        <EmailNotificationSettings />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Next subscription' }));
    expect(await screen.findByText('Destination: current@example.invalid')).toBeVisible();
    await act(async () => {
      if (outcome === 'success') resolve({ ...preferences, destination: 'old@example.invalid' });
      else reject(new Error('Old settings unavailable'));
      await pending.catch(() => undefined);
    });
    expect(screen.getByText('Destination: current@example.invalid')).toBeVisible();
    expect(screen.queryByText(/old@example.invalid/)).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  },
);
