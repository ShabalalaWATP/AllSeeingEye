import { act, renderHook } from '@testing-library/react';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';

import {
  applyLlmConnection,
  fetchLlmModels,
  fetchLlmProfiles,
  resetTeamLlmConnection,
  resetUserLlmConnection,
} from './llm';

afterEach(() => vi.restoreAllMocks());
describe('AI connection boundary', () => {
  it('rejects an unbounded model list before it reaches the picker', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue(
      Response.json({ models: Array.from({ length: 1001 }, () => 'model') }),
    );
    await expect(fetchLlmModels('55555555-5555-4555-8555-555555555555')).rejects.toMatchObject({
      code: 'invalid_response',
    });
  });

  it('rejects a malformed profile test state', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue(
      Response.json({ items: [{ id: 'x', is_tested: 'yes' }], encryption_available: true }),
    );
    await expect(fetchLlmProfiles()).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('discards a late activation receipt when the account changes', async () => {
    useAuthStore.getState().setSession(tokenFor(adminUser));
    const input = {
      team_id: null,
      profile_id: '55555555-5555-4555-8555-555555555555',
      expected_profile_revision: 2,
      tested_config_hash: 'a'.repeat(64),
      expected_binding_revision: 3,
    };
    const fetch = vi.spyOn(window, 'fetch').mockImplementation(() => {
      useAuthStore.getState().setSession(tokenFor(plainUser));
      return Promise.resolve(
        Response.json({
          team_id: null,
          profile_id: input.profile_id,
          profile_revision: 2,
          tested_config_hash: input.tested_config_hash,
          activated_at: new Date().toISOString(),
          activated_by: adminUser.id,
          revision: 4,
        }),
      );
    });
    await expect(applyLlmConnection(input)).rejects.toMatchObject({ code: 'access_changed' });
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({
      method: 'PUT',
      credentials: 'include',
      body: JSON.stringify(input),
    });
  });
});

it.each(['apply', 'team reset', 'personal reset'])(
  'aborts %s before a late 401 can replay under another account',
  async (operation) => {
    useAuthStore.getState().setSession(tokenFor(adminUser));
    const hook = renderHook(() => useScopedRequest());
    const signal = hook.result.current();
    let resolve!: (value: Response) => void;
    const fetch = vi.spyOn(window, 'fetch').mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const input = {
      team_id: null,
      profile_id: '55555555-5555-4555-8555-555555555555',
      expected_profile_revision: 1,
      tested_config_hash: 'a'.repeat(64),
      expected_binding_revision: null,
    };
    const pending =
      operation === 'apply'
        ? applyLlmConnection(input, signal)
        : operation === 'team reset'
          ? resetTeamLlmConnection(plainUser.id, 1, signal)
          : resetUserLlmConnection(plainUser.id, 1, signal);
    const rejected = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    act(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
    expect(signal.aborted).toBe(true);
    resolve(new Response(null, { status: 401 }));
    await rejected;
    expect(fetch).toHaveBeenCalledTimes(1);
    hook.unmount();
  },
);
