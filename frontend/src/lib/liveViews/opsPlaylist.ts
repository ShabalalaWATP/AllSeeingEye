/**
 * An ops-room playlist: up to eight saved live views or saved areas, each with a caption
 * and a dwell time. An area entry only focuses its saved area; it adds no view state.
 */
import { z } from 'zod';

export const MAX_PLAYLIST_ENTRIES = 8;
export const MIN_DWELL_SECONDS = 5;
export const MAX_DWELL_SECONDS = 3600;
export const DEFAULT_DWELL_SECONDS = 60;
export const MAX_CAPTION = 120;

const entrySchema = z.object({
  kind: z.enum(['view', 'area']),
  id: z.uuid(),
  caption: z.string().max(MAX_CAPTION),
  dwell_seconds: z.number().int().min(MIN_DWELL_SECONDS).max(MAX_DWELL_SECONDS),
});
const playlistSchema = z.object({
  version: z.literal(1),
  entries: z.array(entrySchema).min(1).max(MAX_PLAYLIST_ENTRIES),
});

export type PlaylistEntry = z.infer<typeof entrySchema>;
export type OpsPlaylist = z.infer<typeof playlistSchema>;

export function readPlaylist(payload: unknown): OpsPlaylist {
  const parsed = playlistSchema.safeParse(payload);
  if (!parsed.success) throw new Error('This playlist cannot be played.');
  return parsed.data;
}

/** Clamp a typed dwell time to the accepted range, in whole seconds. */
export function clampDwell(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_DWELL_SECONDS;
  return Math.min(MAX_DWELL_SECONDS, Math.max(MIN_DWELL_SECONDS, Math.round(value)));
}
