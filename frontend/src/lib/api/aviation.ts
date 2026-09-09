/** The aviation tracker: the board against baselines and the GNSS interference map. */
import { z } from 'zod';

import { liveEventSchema } from './eventSchemas';
import { apiCall } from './client';

export const countryActivitySchema = z.object({
  iso: z.string(),
  count: z.number().int(),
  baseline: z.number().nullable(),
  ratio: z.number().nullable(),
});
export type CountryActivity = z.infer<typeof countryActivitySchema>;

export const areaActivitySchema = z.object({
  id: z.string(),
  name: z.string(),
  count: z.number().int(),
  military: z.number().int(),
  baseline: z.number().nullable(),
});
export type AreaActivity = z.infer<typeof areaActivitySchema>;

export const aviationBoardSchema = z.object({
  military_total: z.number().int(),
  interesting: z.number().int(),
  ladd: z.number().int(),
  pia: z.number().int(),
  by_country: z.array(countryActivitySchema),
  emergencies: z.array(liveEventSchema),
  areas: z.array(areaActivitySchema),
  jam_amber: z.number().int(),
  jam_red: z.number().int(),
  jam_updated_at: z.string().nullable(),
});
export type AviationBoard = z.infer<typeof aviationBoardSchema>;

export const jamCellSchema = z.object({
  lon: z.number(),
  lat: z.number(),
  size: z.number(),
  good: z.number().int(),
  bad: z.number().int(),
  percent_bad: z.number(),
  level: z.enum(['green', 'amber', 'red']),
});
export type JamCell = z.infer<typeof jamCellSchema>;

export const jamMapSchema = z.object({
  cells: z.array(jamCellSchema),
  updated_at: z.string().nullable(),
  limited: z.boolean().optional(),
});
export type JamMap = z.infer<typeof jamMapSchema>;

export function fetchAviationBoard(): Promise<AviationBoard> {
  return apiCall('/api/trackers/aviation', { schema: aviationBoardSchema });
}

export function fetchJamMap(signal?: AbortSignal): Promise<JamMap> {
  return apiCall('/api/trackers/aviation/jamming', {
    schema: jamMapSchema,
    ...(signal ? { signal } : {}),
  });
}
