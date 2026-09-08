import { expect, it, vi } from 'vitest';
import {
  confirmFirmsConnection,
  fetchFirmsConnection,
  removeFirmsConnection,
  saveFirmsDraft,
  testFirmsDraft,
} from './firmsConnection';
import type { FirmsConnection } from './firmsConnection';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';

// Synthetic input for mocked requests only; never an operational credential.
const fixtureKey = 'x'.repeat(32);
function status(): FirmsConnection {
  return {
    revision: 1,
    active_revision: 0,
    configured: false,
    credential_origin: 'none',
    environment_disabled: false,
    encryption_available: true,
    area: 'world',
    draft_present: true,
    draft_expires_at: '2026-09-08T12:15:00Z',
    tested_at: '2026-09-08T12:00:00Z',
    test_generation: 1,
    test_ok: true,
  };
}
it('retains only masked metadata and sends revisions on each connection mutation', async () => {
  const fetch = vi
    .spyOn(window, 'fetch')
    .mockImplementation(() => Promise.resolve(Response.json({ ...status(), api_key: fixtureKey })));
  const signal = new AbortController().signal;
  expect(await fetchFirmsConnection(signal)).not.toHaveProperty('api_key');
  await saveFirmsDraft({ api_key: fixtureKey, expected_revision: 0 }, signal);
  expect(fetch.mock.calls[1]?.[1]?.method).toBe('PUT');
  expect(JSON.parse(fetch.mock.calls[1]?.[1]?.body as string)).toEqual({
    api_key: fixtureKey,
    expected_revision: 0,
  });
  fetch.mockResolvedValueOnce(
    Response.json({ status: status(), ok: true, fetched: 0, message: 'Passed' }),
  );
  await testFirmsDraft(1, signal);
  expect(JSON.parse(fetch.mock.calls[2]?.[1]?.body as string)).toEqual({ expected_revision: 1 });
  await confirmFirmsConnection({ expected_revision: 1, test_generation: 1 }, signal);
  expect(JSON.parse(fetch.mock.calls[3]?.[1]?.body as string)).toEqual({
    expected_revision: 1,
    test_generation: 1,
  });
  await removeFirmsConnection(1, signal);
  expect(fetch.mock.calls[4]?.[1]?.method).toBe('DELETE');
  expect(JSON.parse(fetch.mock.calls[4]?.[1]?.body as string)).toEqual({ expected_revision: 1 });
});
it('rejects malformed expiry metadata instead of enabling confirmation', async () => {
  vi.spyOn(window, 'fetch').mockResolvedValue(
    Response.json({ ...status(), draft_expires_at: 'not-a-date' }),
  );
  await expect(fetchFirmsConnection(new AbortController().signal)).rejects.toMatchObject({
    code: 'invalid_response',
  });
});
it('discards connection mutation output if authority changes while the server responds', async () => {
  useAuthStore.getState().setSession(tokenFor(adminUser));
  vi.spyOn(window, 'fetch').mockImplementation(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    return Promise.resolve(Response.json(status()));
  });
  await expect(
    confirmFirmsConnection(
      { expected_revision: 1, test_generation: 1 },
      new AbortController().signal,
    ),
  ).rejects.toMatchObject({ code: 'access_changed' });
});
