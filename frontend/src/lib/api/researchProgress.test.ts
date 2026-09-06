import { afterEach, describe, expect, it, vi } from 'vitest';

import { readResearchProgress } from './researchProgress';

const id = '10000000-0000-4000-8000-000000000001';
const receipt = {
  id,
  stage: 'collecting',
  started_at: '2026-09-06T11:00:00Z',
  updated_at: '2026-09-06T11:01:00Z',
  expires_at: '2026-09-06T11:15:00Z',
  report_id: null,
};
afterEach(() => vi.restoreAllMocks());

describe('research run API', () => {
  it('reads an authenticated receipt with the caller cancellation signal', async () => {
    const fetch = vi.spyOn(window, 'fetch').mockResolvedValue(Response.json(receipt));
    const signal = new AbortController().signal;
    await expect(readResearchProgress(id, signal)).resolves.toEqual(receipt);
    expect((fetch.mock.calls[0]?.[0] as URL).pathname).toBe(`/api/research/runs/${id}`);
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({ signal, credentials: 'include' });
  });
  it('does not turn an initial 404 into a workspace invalidation', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue(
      Response.json({ error: { code: 'not_found', message: 'Not found' } }, { status: 404 }),
    );
    await expect(readResearchProgress(id, new AbortController().signal)).rejects.toMatchObject({
      status: 404,
    });
  });
  it.each([{ stage: 'imaginary' }, { report_id: '../other' }, { expires_at: 'never' }])(
    'rejects malformed receipt %j',
    async (override) => {
      vi.spyOn(window, 'fetch').mockResolvedValue(Response.json({ ...receipt, ...override }));
      await expect(readResearchProgress(id, new AbortController().signal)).rejects.toMatchObject({
        code: 'invalid_response',
      });
    },
  );
  it('rejects an unsafe run id before fetching', async () => {
    const fetch = vi.spyOn(window, 'fetch');
    await expect(
      readResearchProgress('../reports', new AbortController().signal),
    ).rejects.toThrow();
    expect(fetch).not.toHaveBeenCalled();
  });
});
