import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type Camera = components['schemas']['CameraOut'];
export type CameraCatalogue = components['schemas']['CameraCatalogueOut'];
export type CameraProvider = Camera['provider'];

/** Restrict browser requests as well as validating the server's public catalogue. */
export function isCameraImageUrl(value: string): boolean {
  try {
    const url = new URL(value);
    if (
      url.protocol !== 'https:' ||
      url.username ||
      url.password ||
      url.port ||
      url.search ||
      url.hash
    )
      return false;
    return (
      (url.hostname === 's3-eu-west-1.amazonaws.com' &&
        /^\/jamcams\.tfl\.gov\.uk\/[\w.-]+\.jpg$/i.test(url.pathname)) ||
      (url.hostname === 'tdcctv.data.one.gov.hk' && /^\/[\w.-]+\.jpg$/i.test(url.pathname)) ||
      (url.hostname === 'weathercam.digitraffic.fi' && /^\/[\w.-]+\.jpg$/i.test(url.pathname))
    );
  } catch {
    return false;
  }
}

const cameraSchema: z.ZodType<Camera> = z.object({
  id: z.string().max(200),
  provider: z.enum(['tfl', 'hongkong', 'fintraffic']),
  title: z.string().max(500),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  snapshot_url: z.string().refine(isCameraImageUrl),
  source_url: z.url().refine((value) => new URL(value).protocol === 'https:'),
  attribution: z.string().max(1000),
  captured_at: z.string().nullable(),
});
export const cameraCatalogueSchema: z.ZodType<CameraCatalogue> = z.object({
  cameras: z.array(cameraSchema).max(5000),
  providers: z
    .array(
      z.object({
        id: z.enum(['tfl', 'hongkong', 'fintraffic']),
        name: z.string(),
        status: z.enum(['available', 'stale', 'unavailable']),
        count: z.number().int().nonnegative(),
        fetched_at: z.string().nullable(),
        message: z.string().nullable(),
      }),
    )
    .max(3),
  fetched_at: z.string(),
});
export function fetchCameras(signal: AbortSignal): Promise<CameraCatalogue> {
  return apiCall('/api/cameras', { signal, schema: cameraCatalogueSchema });
}
