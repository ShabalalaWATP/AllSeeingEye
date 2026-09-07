import { apiBlob } from './client';
export type MapImageUse = 'standard' | 'noncommercial' | 'licensed';
export interface MapImageRequest {
  png_base64: string;
  include_annotations: boolean;
  use_basis: MapImageUse;
  permitted_use: string;
}
export function fetchMapImagePackage(
  view: string,
  revision: string,
  body: MapImageRequest,
  signal: AbortSignal,
) {
  return apiBlob(
    `/api/map/views/${encodeURIComponent(view)}/revisions/${encodeURIComponent(revision)}/image-package`,
    {
      method: 'POST',
      body,
      signal,
    },
  );
}
/** Bounded local canvas bytes only. Never fetches an image URL. */
export async function mapPngBase64(blob: Blob, signal: AbortSignal): Promise<string> {
  signal.throwIfAborted();
  if (blob.type !== 'image/png' || !blob.size || blob.size > 8 * 1024 * 1024)
    throw new Error('The map must be a PNG image no larger than 8 MiB.');
  const bytes = new Uint8Array(await blob.arrayBuffer());
  signal.throwIfAborted();
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 8192)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
  signal.throwIfAborted();
  return btoa(binary);
}
