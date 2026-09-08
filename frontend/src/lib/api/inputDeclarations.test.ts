import { expect, it, vi } from 'vitest';
import { fetchDeclarationTargets, declareInputProvenance } from './inputDeclarations';
const parent = '10000000-0000-4000-8000-000000000001';
const derived = '10000000-0000-4000-8000-000000000002';
it('retains original passage metadata and derived receipt lineage through the real API boundary', async () => {
  const fetch = vi.spyOn(window, 'fetch');
  fetch.mockResolvedValueOnce(
    Response.json({
      input_id: parent,
      sha256: 'a'.repeat(64),
      expires_at: '2026-09-08T12:00:00Z',
      targets: [
        {
          event_id: 'event',
          content_hash: 'b'.repeat(64),
          title: 'Original',
          summary: null,
          language: 'fa',
        },
      ],
    }),
  );
  const targets = await fetchDeclarationTargets(parent, new AbortController().signal);
  expect(targets.targets[0]).toMatchObject({
    title: 'Original',
    transformations: [],
    source_dates: [],
  });
  fetch.mockResolvedValueOnce(
    Response.json({
      id: derived,
      parent_input_id: parent,
      filename: 'notes.txt',
      media_type: 'text/plain',
      sha256: 'a'.repeat(64),
      imported_at: '2026-09-08T11:45:00Z',
      expires_at: '2026-09-08T12:00:00Z',
      event_count: 1,
      extracted_characters: 8,
      preview: 'Original',
      limitations: [],
    }),
  );
  const body = { sha256: targets.sha256, declarations: [] };
  const receipt = await declareInputProvenance(parent, body, new AbortController().signal);
  expect(receipt.parent_input_id).toBe(parent);
  expect(fetch.mock.calls[1]?.[1]?.method).toBe('POST');
  expect(JSON.parse(fetch.mock.calls[1]?.[1]?.body as string)).toEqual(body);
});
it('rejects malformed declaration target dates before exposing source text', async () => {
  vi.spyOn(window, 'fetch').mockResolvedValue(
    Response.json({
      input_id: parent,
      sha256: 'a'.repeat(64),
      expires_at: 'not-a-date',
      targets: [],
    }),
  );
  await expect(fetchDeclarationTargets(parent, new AbortController().signal)).rejects.toMatchObject(
    { code: 'invalid_response' },
  );
});
