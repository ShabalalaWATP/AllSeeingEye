import { apiBlob } from '@/lib/api/client';

/** A relayed frame travels through the session, so it becomes an object URL for the image. */
export async function loadCameraFrame(
  path: string,
  requestId: number,
  fetcher: (path: string) => Promise<Blob> = apiBlob,
): Promise<string> {
  const blob = await fetcher(`${path}?_ase_refresh=${Date.now()}-${requestId}`);
  return URL.createObjectURL(blob);
}

export function releaseCameraFrame(url: string | null | undefined): void {
  if (url?.startsWith('blob:')) URL.revokeObjectURL(url);
}
