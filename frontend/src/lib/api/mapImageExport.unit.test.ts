import { beforeEach, expect, it, vi } from 'vitest';
import { apiBlob } from './client';
import { fetchMapImagePackage, mapPngBase64 } from './mapImageExport';
vi.mock('./client', () => ({ apiBlob: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
it('encodes identifiers and sends explicit options through the authenticated client', async () => {
  const signal = new AbortController().signal;
  const body = {
    png_base64: 'abc',
    include_annotations: false,
    use_basis: 'standard' as const,
    permitted_use: '',
  };
  await fetchMapImagePackage('view/a', 'rev/b', body, signal);
  expect(apiBlob).toHaveBeenCalledWith('/api/map/views/view%2Fa/revisions/rev%2Fb/image-package', {
    method: 'POST',
    body,
    signal,
  });
});
it('encodes bounded PNG bytes and honours abort after the asynchronous read', async () => {
  const controller = new AbortController();
  const buffer = new Uint8Array([137, 80, 78, 71]).buffer;
  const blob = { type: 'image/png', size: 4, arrayBuffer: () => Promise.resolve(buffer) } as Blob;
  expect(await mapPngBase64(blob, controller.signal)).toBe('iVBORw==');
  const interrupted = {
    type: 'image/png',
    size: 4,
    arrayBuffer: () => {
      controller.abort();
      return Promise.resolve(buffer);
    },
  } as Blob;
  await expect(mapPngBase64(interrupted, controller.signal)).rejects.toThrow();
});
it('rejects unsupported, empty and oversized images before reading bytes', async () => {
  const arrayBuffer = vi.fn();
  for (const metadata of [
    { type: 'text/plain', size: 3 },
    { type: 'image/png', size: 0 },
    { type: 'image/png', size: 8 * 1024 * 1024 + 1 },
  ])
    await expect(
      mapPngBase64({ ...metadata, arrayBuffer } as unknown as Blob, new AbortController().signal),
    ).rejects.toThrow('PNG');
  expect(arrayBuffer).not.toHaveBeenCalled();
});
