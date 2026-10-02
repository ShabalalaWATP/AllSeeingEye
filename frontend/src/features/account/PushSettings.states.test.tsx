import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { getPushSettings, type PushDevice } from '@/lib/api/webPush';
import { disablePush, enablePush, pushSupported } from '@/lib/browserPush';
import { PushSettings } from './PushSettings';

vi.mock('@/lib/api/webPush', () => ({ getPushSettings: vi.fn() }));
vi.mock('@/lib/browserPush', () => ({
  disablePush: vi.fn(),
  enablePush: vi.fn(),
  pushSupported: vi.fn(),
}));
const device: PushDevice = {
  id: 'browser-1',
  endpoint_hash: 'hash',
  created_at: '2026-09-01T12:00:00Z',
};
const empty = { available: true, public_key: 'public-key', devices: [] };

beforeEach(() => {
  vi.mocked(getPushSettings).mockReset().mockResolvedValue(empty);
  vi.mocked(pushSupported).mockReset().mockReturnValue(true);
  vi.mocked(enablePush).mockReset().mockResolvedValue(device);
  vi.mocked(disablePush).mockReset().mockResolvedValue();
});

it('shows a load failure without an enable control', async () => {
  vi.mocked(getPushSettings).mockRejectedValueOnce(new Error('Unavailable'));
  render(<PushSettings />);
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded');
  expect(
    screen.queryByRole('button', { name: 'Enable push on this browser' }),
  ).not.toBeInTheDocument();
});

it('keeps controls busy while enabling and refreshes the registered device list', async () => {
  let finish!: (value: PushDevice) => void;
  const pending = new Promise<PushDevice>((resolve) => {
    finish = resolve;
  });
  vi.mocked(enablePush).mockReturnValueOnce(pending);
  vi.mocked(getPushSettings)
    .mockResolvedValueOnce(empty)
    .mockResolvedValueOnce({ ...empty, devices: [device] });
  render(<PushSettings />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Enable push on this browser' }));
  expect(enablePush).toHaveBeenCalledWith('public-key', []);
  expect(screen.getByRole('button', { name: 'Updating…' })).toBeDisabled();
  await act(async () => {
    finish(device);
    await pending;
  });
  expect(await screen.findByRole('button', { name: 'Remove browser 1' })).toBeEnabled();
  expect(screen.queryByText('No browsers are subscribed.')).not.toBeInTheDocument();
});

it('lets the user retry permission or registration failure', async () => {
  vi.mocked(enablePush).mockRejectedValueOnce(new Error('Permission denied'));
  render(<PushSettings />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Enable push on this browser' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Check browser permission');
  await user.click(screen.getByRole('button', { name: 'Enable push on this browser' }));
  await waitFor(() => expect(enablePush).toHaveBeenCalledTimes(2));
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('preserves a device after failed removal and supports a successful retry', async () => {
  vi.mocked(getPushSettings).mockResolvedValue({ ...empty, devices: [device] });
  vi.mocked(disablePush).mockRejectedValueOnce(new Error('Unavailable'));
  render(<PushSettings />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Remove browser 1' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('This device could not be removed');
  expect(screen.getByRole('button', { name: 'Remove browser 1' })).toBeEnabled();
  vi.mocked(getPushSettings).mockResolvedValue(empty);
  await user.click(screen.getByRole('button', { name: 'Remove browser 1' }));
  expect(await screen.findByText('No browsers are subscribed.')).toBeVisible();
  expect(disablePush).toHaveBeenLastCalledWith(device);
});
