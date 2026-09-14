import hosts from './cameraMediaHosts.json';
import { z } from 'zod';
import { apiCall } from './client';
import type { components } from './types.gen';

export type Camera = components['schemas']['CameraOut'];
export type CameraCatalogue = components['schemas']['CameraCatalogueOut'];
export type CameraProvider = Camera['provider'];

const FRAME_PATH = /^\/api\/cameras\/frames\/[a-z][a-z0-9-]{0,39}\/[A-Za-z0-9_-]{1,40}\.jpg$/;

/** Same-origin relay paths for the providers that only serve images inline. */
export function isCameraFramePath(value: string | null | undefined): boolean {
  return typeof value === 'string' && FRAME_PATH.test(value);
}

/** Restrict browser requests as well as validating the server's public catalogue. */
export function isCameraImageUrl(value: string | null | undefined): boolean {
  try {
    if (!value) return false;
    if (isCameraFramePath(value)) return true;
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port || url.hash)
      return false;
    if (url.hostname === 's3-eu-west-1.amazonaws.com')
      return /^\/jamcams\.tfl\.gov\.uk\/[\w.-]+\.jpg$/i.test(url.pathname) && !url.search;
    if (['weathercam.digitraffic.fi', 'tdcctv.data.one.gov.hk'].includes(url.hostname))
      return !url.search && /^\/[\w.-]+\.jpg$/i.test(url.pathname);
    return hosts.media.includes(url.hostname);
  } catch {
    return false;
  }
}

const cameraSchema: z.ZodType<Camera> = z.object({
  id: z.string().max(200),
  provider: z.string().min(1).max(100),
  title: z.string().max(500),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  snapshot_url: z
    .string()
    .nullable()
    .refine((value) => value === null || isCameraImageUrl(value)),
  stream_url: z.string().nullable().default(null),
  stream_type: z.enum(['hls', 'mp4', 'mjpeg', 'iframe']).nullable().default(null),
  external_url: z
    .url()
    .nullable()
    .default(null)
    .refine((value) => value === null || isCameraWebsite(value)),
  coordinate_precision: z.enum(['exact', 'approximate']).default('exact'),
  source_url: z.url().refine(isCameraWebsite),
  attribution: z.string().max(1000),
  captured_at: z.string().nullable(),
});
export const cameraCatalogueSchema: z.ZodType<CameraCatalogue> = z.object({
  cameras: z.array(cameraSchema).max(75000),
  providers: z
    .array(
      z.object({
        id: z.string().min(1).max(100),
        name: z.string(),
        status: z.enum(['available', 'stale', 'unavailable', 'not_loaded']),
        count: z.number().int().nonnegative(),
        fetched_at: z.string().nullable(),
        message: z.string().nullable(),
      }),
    )
    .max(100),
  fetched_at: z.string(),
});
export function fetchCameras(signal: AbortSignal, provider?: string): Promise<CameraCatalogue> {
  return apiCall(`/api/cameras${provider ? `?provider=${encodeURIComponent(provider)}` : ''}`, {
    signal,
    schema: cameraCatalogueSchema,
  });
}

export function isCameraStreamUrl(value: string | null | undefined, iframe = false): boolean {
  if (!value) return false;
  try {
    const url = new URL(value);
    return (
      url.protocol === 'https:' &&
      !url.username &&
      !url.password &&
      !url.port &&
      url.hostname !== 's3-eu-west-1.amazonaws.com' &&
      (iframe ? hosts.frames : hosts.media).includes(url.hostname)
    );
  } catch {
    return false;
  }
}

function isCameraWebsite(value: string): boolean {
  try {
    const u = new URL(value);
    return (
      ['http:', 'https:'].includes(u.protocol) &&
      !u.username &&
      !u.password &&
      !u.port &&
      u.hostname.includes('.') &&
      !/^[\d.]+$/.test(u.hostname) &&
      !u.hostname.endsWith('.local') &&
      !u.hostname.endsWith('.localhost')
    );
  } catch {
    return false;
  }
}
