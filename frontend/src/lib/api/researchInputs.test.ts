import { afterEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';

import { uploadResearchInput } from './researchInputs';
import type { ResearchInputReceipt } from './researchInputs';

function receipt(): ResearchInputReceipt {
  return {
    id: '10000000-0000-4000-8000-000000000001',
    filename: 'notes.txt',
    media_type: 'text/plain',
    sha256: 'a'.repeat(64),
    imported_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 900_000).toISOString(),
    event_count: 1,
    extracted_characters: 3,
    preview: 'text',
    limitations: [],
    previews: [],
  };
}

describe('research input API', () => {
  afterEach(() => vi.restoreAllMocks());

  it('encodes the filename and uses the shared binary request path', async () => {
    const fetch = vi.spyOn(window, 'fetch').mockResolvedValue(Response.json(receipt()));
    const file = new File(['source'], 'name & topic.txt');
    await expect(uploadResearchInput(file, new AbortController().signal)).resolves.toMatchObject({
      event_count: 1,
    });
    const url = fetch.mock.calls[0]?.[0];
    expect(url).toBeInstanceOf(URL);
    expect((url as URL).href).toContain('filename=name%20%26%20topic.txt');
    expect(fetch.mock.calls[0]?.[1]?.body).toBe(file);
  });

  it('rejects unsupported preview encoding rather than loading an arbitrary image URL', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue(
      Response.json({
        ...receipt(),
        previews: [
          { seconds: 0, sha256: 'a'.repeat(64), png_base64: 'https://example.test/track' },
        ],
      }),
    );
    await expect(
      uploadResearchInput(new File(['x'], 'x.png'), new AbortController().signal),
    ).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('discards an upload receipt when the account changes before it returns', async () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    vi.spyOn(window, 'fetch').mockImplementation(() => {
      useAuthStore.getState().setSession(tokenFor(adminUser));
      return Promise.resolve(Response.json(receipt()));
    });
    await expect(
      uploadResearchInput(new File(['x'], 'x.txt'), new AbortController().signal),
    ).rejects.toMatchObject({ code: 'access_changed' });
  });
});
