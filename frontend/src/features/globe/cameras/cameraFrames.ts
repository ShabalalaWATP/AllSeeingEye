import { apiBlob, type CallOptions } from '@/lib/api/client';

type FrameFetcher = (path: string, options?: CallOptions) => Promise<Blob>;

/** A relayed frame travels through the session, so it becomes an object URL for the image. */
export async function loadCameraFrame(
  path: string,
  requestId: number,
  { signal, fetcher = apiBlob }: { signal?: AbortSignal; fetcher?: FrameFetcher } = {},
): Promise<string> {
  const blob = await fetcher(
    `${path}?_ase_refresh=${Date.now()}-${requestId}`,
    signal ? { signal } : {},
  );
  // Never mint an object URL for a request the caller has already abandoned.
  signal?.throwIfAborted();
  return URL.createObjectURL(blob);
}

export function releaseCameraFrame(url: string | null | undefined): void {
  if (url?.startsWith('blob:')) URL.revokeObjectURL(url);
}
