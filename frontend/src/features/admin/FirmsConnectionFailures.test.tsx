import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/firmsConnection';
import { testSource } from '@/lib/api/sourceControls';
import { ApiError } from '@/lib/api/errors';
import { useFirmsConnection } from './useFirmsConnection';
import { FirmsConnectionPanel } from './FirmsConnectionPanel';
vi.mock('@/lib/api/firmsConnection', () => ({
  FIRMS_ID: 'firms_viirs_noaa20',
  fetchFirmsConnection: vi.fn(),
  saveFirmsDraft: vi.fn(),
  testFirmsDraft: vi.fn(),
  confirmFirmsConnection: vi.fn(),
  removeFirmsConnection: vi.fn(),
}));
vi.mock('@/lib/api/sourceControls', () => ({ testSource: vi.fn() }));
const key = 'synthetic-map-key-1234';
function status(overrides: Partial<api.FirmsConnection> = {}): api.FirmsConnection {
  return {
    revision: 3,
    active_revision: 1,
    configured: true,
    credential_origin: 'database',
    environment_disabled: false,
    encryption_available: true,
    area: 'world',
    draft_present: true,
    draft_expires_at: new Date(Date.now() + 900_000).toISOString(),
    tested_at: null,
    test_generation: 0,
    test_ok: false,
    ...overrides,
  };
}
beforeEach(() => {
  vi.mocked(api.fetchFirmsConnection).mockResolvedValue(status());
  vi.mocked(api.testFirmsDraft).mockResolvedValue({
    status: status(),
    ok: false,
    fetched: 0,
    message: key,
  });
});
async function open() {
  render(<FirmsConnectionPanel />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Manage FIRMS connection' }));
  await screen.findByText('Key configured (hidden)');
  return user;
}
it('offers retry after status failure and never displays arbitrary service messages', async () => {
  vi.mocked(api.fetchFirmsConnection).mockRejectedValueOnce(new ApiError(500, 'unavailable', key));
  render(<FirmsConnectionPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Manage FIRMS connection' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Retry FIRMS status' }));
  expect(await screen.findByText('Key configured (hidden)')).toBeVisible();
  expect(screen.queryByText(key)).not.toBeInTheDocument();
});
it('leaves failed draft tests inactive and permits retry without asking for the saved key', async () => {
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Test saved FIRMS draft' }));
  expect(await screen.findByText(/draft did not pass the bounded NASA/)).toBeVisible();
  expect(
    screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }),
  ).toBeDisabled();
  expect(api.saveFirmsDraft).not.toHaveBeenCalled();
  expect(screen.queryByText(key)).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Test saved FIRMS draft' }));
  expect(api.testFirmsDraft).toHaveBeenCalledTimes(2);
});
it('rejects a test response for a different draft revision', async () => {
  vi.mocked(api.testFirmsDraft).mockResolvedValue({
    status: status({
      revision: 9,
      test_ok: true,
      test_generation: 1,
      tested_at: new Date().toISOString(),
    }),
    ok: true,
    fetched: 1,
    message: key,
  });
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Test saved FIRMS draft' }));
  expect(await screen.findByText(/connection changed or its test expired/)).toBeVisible();
  expect(
    screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }),
  ).toBeDisabled();
});
it.each([401, 403, 422, 429])(
  'handles HTTP %s without echoing a secret-bearing error message',
  async (httpStatus) => {
    vi.mocked(api.testFirmsDraft).mockRejectedValue(new ApiError(httpStatus, 'failure', key));
    const user = await open();
    await user.click(screen.getByRole('button', { name: 'Test saved FIRMS draft' }));
    expect(await screen.findByRole('alert')).toBeVisible();
    expect(screen.queryByText(key)).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }),
    ).toBeDisabled();
  },
);
it('shows an expired stored proof and requires another test', async () => {
  vi.mocked(api.fetchFirmsConnection).mockResolvedValue(
    status({
      test_ok: true,
      test_generation: 1,
      tested_at: '2000-01-01T00:00:00Z',
      draft_expires_at: '2000-01-01T00:00:00Z',
    }),
  );
  await open();
  expect(screen.getByText(/test or draft has expired/)).toBeVisible();
  expect(
    screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }),
  ).toBeDisabled();
});
it('does not use an unsuccessful current-connection test as activation proof', async () => {
  vi.mocked(testSource).mockResolvedValue({ ok: false, fetched: 0, capped: false, message: key });
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Test current FIRMS connection' }));
  expect(await screen.findByText(/current connection test failed/)).toBeVisible();
  expect(screen.queryByText(key)).not.toBeInTheDocument();
});
it('cancels loading and discards a late status response', async () => {
  let finish!: (value: api.FirmsConnection) => void;
  vi.mocked(api.fetchFirmsConnection).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<FirmsConnectionPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Manage FIRMS connection' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Cancel FIRMS request' }));
  await act(async () => {
    finish(status());
    await Promise.resolve();
  });
  expect(screen.queryByText('Key configured (hidden)')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Retry FIRMS status' })).toBeEnabled();
});
it('drops a test result after closing the connection panel', async () => {
  let finish!: (value: api.FirmsConnectionTest) => void;
  vi.mocked(api.testFirmsDraft).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Test saved FIRMS draft' }));
  await waitFor(() => expect(api.testFirmsDraft).toHaveBeenCalled());
  await user.click(screen.getByRole('button', { name: 'Close FIRMS connection' }));
  await act(async () => {
    finish({ status: status(), ok: true, fetched: 1, message: key });
    await Promise.resolve();
  });
  expect(vi.mocked(api.testFirmsDraft).mock.calls[0]?.[1].aborted).toBe(true);
  expect(screen.queryByLabelText('FIRMS connection settings')).not.toBeInTheDocument();
});

it('automatically withdraws confirmation when the exact draft deadline passes', async () => {
  vi.useFakeTimers();
  try {
    const proven = status({
      tested_at: new Date().toISOString(),
      test_ok: true,
      test_generation: 1,
    });
    vi.mocked(api.testFirmsDraft).mockResolvedValue({
      status: proven,
      ok: true,
      fetched: 1,
      message: 'Passed',
    });
    const { result } = renderHook(() => useFirmsConnection());
    await act(async () => {
      await Promise.resolve();
    });
    await act(async () => {
      await result.current.run('draft');
    });
    expect(result.current.canConfirm).toBe(true);
    act(() => {
      vi.advanceTimersByTime(900_001);
    });
    expect(result.current.canConfirm).toBe(false);
    expect(result.current.proofExpired).toBe(true);
    expect(api.confirmFirmsConnection).not.toHaveBeenCalled();
  } finally {
    vi.useRealTimers();
  }
});
