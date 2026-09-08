import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeAll, beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '@/test/render';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import * as api from '@/lib/api/firmsConnection';
import { testSource } from '@/lib/api/sourceControls';
import { ApiError } from '@/lib/api/errors';
vi.mock('@/lib/api/firmsConnection', () => ({
  FIRMS_ID: 'firms_viirs_noaa20',
  fetchFirmsConnection: vi.fn(),
  saveFirmsDraft: vi.fn(),
  testFirmsDraft: vi.fn(),
  confirmFirmsConnection: vi.fn(),
  removeFirmsConnection: vi.fn(),
}));
vi.mock('@/lib/api/sourceControls', () => ({ testSource: vi.fn(), activateSource: vi.fn() }));
beforeAll(async () => {
  await import('./AdminSourcesPage');
});
const key = 'test-only-map-key-123456';
function status(overrides: Partial<api.FirmsConnection> = {}): api.FirmsConnection {
  return {
    revision: 0,
    active_revision: 0,
    configured: false,
    credential_origin: 'none',
    environment_disabled: false,
    encryption_available: true,
    area: 'world',
    draft_present: false,
    draft_expires_at: null,
    tested_at: null,
    test_generation: 0,
    test_ok: false,
    ...overrides,
  };
}
function draft() {
  return status({
    revision: 1,
    draft_present: true,
    draft_expires_at: new Date(Date.now() + 900_000).toISOString(),
  });
}
function proven() {
  return { ...draft(), tested_at: new Date().toISOString(), test_generation: 1, test_ok: true };
}
beforeEach(() => {
  vi.mocked(api.fetchFirmsConnection).mockResolvedValue(status());
  vi.mocked(api.saveFirmsDraft).mockResolvedValue(draft());
  vi.mocked(api.testFirmsDraft).mockResolvedValue({
    status: proven(),
    ok: true,
    fetched: 2,
    message: 'Passed',
  });
  vi.mocked(api.confirmFirmsConnection).mockResolvedValue(
    status({ revision: 2, active_revision: 2, configured: true, credential_origin: 'database' }),
  );
});
async function open() {
  const view = renderApp('/admin/sources', 'admin');
  await view.user.click(await screen.findByRole('button', { name: 'Manage FIRMS connection' }));
  await screen.findByText('No key configured');
  return view;
}
async function testDraft() {
  fireEvent.change(screen.getByLabelText('NASA FIRMS MAP_KEY'), { target: { value: key } });
  fireEvent.click(screen.getByRole('button', { name: 'Save draft and test' }));
  await screen.findByText(/Draft test passed/);
}
it('tests a masked draft then confirms its exact revision and proof globally, without enabling the source', async () => {
  const { user } = await open();
  expect(
    screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }),
  ).toBeDisabled();
  await testDraft();
  expect(screen.getByLabelText('NASA FIRMS MAP_KEY')).toHaveAttribute('type', 'password');
  expect(screen.getByLabelText('NASA FIRMS MAP_KEY')).toHaveValue('');
  expect(api.saveFirmsDraft).toHaveBeenCalledWith(
    { api_key: key, expected_revision: 0 },
    expect.any(AbortSignal),
  );
  expect(api.testFirmsDraft).toHaveBeenCalledWith(1, expect.any(AbortSignal));
  await user.click(screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }));
  expect(
    await screen.findByText(/FIRMS connection confirmed for all users and teams/),
  ).toBeVisible();
  expect(api.confirmFirmsConnection).toHaveBeenCalledWith(
    { expected_revision: 1, test_generation: 1 },
    expect.any(AbortSignal),
  );
  expect(screen.getByText('Key configured (hidden)')).toBeVisible();
  expect(screen.queryByText(key)).not.toBeInTheDocument();
});
it('invalidates confirmation when the operator edits the key and ignores an aborted late test', async () => {
  await open();
  await testDraft();
  fireEvent.change(screen.getByLabelText('NASA FIRMS MAP_KEY'), {
    target: { value: 'replacement-key-1234' },
  });
  expect(
    screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }),
  ).toBeDisabled();
  let finish!: (value: api.FirmsConnectionTest) => void;
  vi.mocked(api.testFirmsDraft).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Save draft and test' }));
  await waitFor(() => expect(api.testFirmsDraft).toHaveBeenCalledTimes(2));
  fireEvent.click(screen.getByRole('button', { name: 'Cancel FIRMS request' }));
  await act(async () => {
    finish({ status: proven(), ok: true, fetched: 1, message: key });
    await Promise.resolve();
  });
  expect(vi.mocked(api.testFirmsDraft).mock.calls[1]?.[1].aborted).toBe(true);
  expect(
    screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }),
  ).toBeDisabled();
  expect(screen.queryByText(key)).not.toBeInTheDocument();
});
it('wipes key entry and aborts pending requests when workspace authority changes', async () => {
  const { user } = await open();
  fireEvent.change(screen.getByLabelText('NASA FIRMS MAP_KEY'), { target: { value: key } });
  act(() => invalidateWorkspaceAccess());
  await waitFor(() =>
    expect(screen.queryByLabelText('NASA FIRMS MAP_KEY')).not.toBeInTheDocument(),
  );
  expect(vi.mocked(api.fetchFirmsConnection).mock.calls[0]?.[0].aborted).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Manage FIRMS connection' }));
  expect(await screen.findByLabelText('NASA FIRMS MAP_KEY')).toHaveValue('');
});
it('rejects invalid key syntax locally and never echoes failed server payloads', async () => {
  await open();
  fireEvent.change(screen.getByLabelText('NASA FIRMS MAP_KEY'), { target: { value: 'bad key' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save draft and test' }));
  expect(await screen.findByText(/Enter a MAP_KEY containing/)).toBeVisible();
  expect(api.saveFirmsDraft).not.toHaveBeenCalled();
  vi.mocked(api.saveFirmsDraft).mockRejectedValue(new ApiError(500, 'failure', key));
  fireEvent.change(screen.getByLabelText('NASA FIRMS MAP_KEY'), { target: { value: key } });
  fireEvent.click(screen.getByRole('button', { name: 'Save draft and test' }));
  expect(await screen.findByText(/Refresh the status before trying again/)).toBeVisible();
  expect(screen.queryByText(key)).not.toBeInTheDocument();
  expect(screen.getByLabelText('NASA FIRMS MAP_KEY')).toHaveValue('');
});
it('does not confirm after proof expiry even before the display clock ticks', async () => {
  await open();
  await testDraft();
  const later = Date.now() + 900_001;
  vi.spyOn(Date, 'now').mockReturnValue(later);
  fireEvent.click(screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }));
  expect(
    await screen.findByText('This test has expired. Test the draft again before confirming.'),
  ).toBeVisible();
  expect(api.confirmFirmsConnection).not.toHaveBeenCalled();
});
it('keeps environment credentials and encryption-unavailable setup read-only', async () => {
  vi.mocked(api.fetchFirmsConnection).mockResolvedValue(
    status({
      credential_origin: 'environment',
      encryption_available: false,
      environment_disabled: true,
      area: '20,40,60,70',
    }),
  );
  await open();
  expect(screen.queryByLabelText('NASA FIRMS MAP_KEY')).not.toBeInTheDocument();
  expect(screen.getByText(/environment MAP_KEY takes precedence/)).toBeVisible();
  expect(screen.getByText(/Encrypted credential storage is unavailable/)).toBeVisible();
  expect(screen.getByText('20,40,60,70')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Test current FIRMS connection' })).toBeDisabled();
});
it('tests the current connection without allowing that result to confirm a draft', async () => {
  vi.mocked(api.fetchFirmsConnection).mockResolvedValue(
    status({ configured: true, credential_origin: 'database' }),
  );
  vi.mocked(testSource).mockResolvedValue({ ok: true, fetched: 3, capped: true, message: key });
  const { user } = renderApp('/admin/sources', 'admin');
  await user.click(await screen.findByRole('button', { name: 'Manage FIRMS connection' }));
  await user.click(await screen.findByRole('button', { name: 'Test current FIRMS connection' }));
  expect(await screen.findByText(/Current connection test passed: 3\+/)).toBeVisible();
  expect(
    screen.getByRole('button', { name: 'Confirm FIRMS connection for everyone' }),
  ).toBeDisabled();
  expect(screen.queryByText(key)).not.toBeInTheDocument();
});
it('requires explicit removal review before clearing the stored connection and draft', async () => {
  vi.mocked(api.fetchFirmsConnection).mockResolvedValue(
    status({ configured: true, credential_origin: 'database', revision: 3 }),
  );
  vi.mocked(api.removeFirmsConnection).mockResolvedValue(status({ revision: 4 }));
  const { user } = renderApp('/admin/sources', 'admin');
  await user.click(await screen.findByRole('button', { name: 'Manage FIRMS connection' }));
  await user.click(await screen.findByRole('button', { name: 'Remove stored FIRMS connection' }));
  expect(api.removeFirmsConnection).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Keep connection' }));
  expect(
    screen.queryByRole('button', { name: 'Confirm removal of FIRMS connection' }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Remove stored FIRMS connection' }));
  await user.click(screen.getByRole('button', { name: 'Confirm removal of FIRMS connection' }));
  expect(await screen.findByText(/Stored connection and draft removed/)).toBeVisible();
  expect(api.removeFirmsConnection).toHaveBeenCalledWith(3, expect.any(AbortSignal));
});
it('does not expose the connection workspace to a non-administrator', async () => {
  renderApp('/admin/sources', 'user');
  await screen.findByText('Admin access required');
  expect(screen.queryByRole('button', { name: 'Manage FIRMS connection' })).not.toBeInTheDocument();
  expect(api.fetchFirmsConnection).not.toHaveBeenCalled();
});
