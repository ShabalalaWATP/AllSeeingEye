/** The maritime, space and cyber boards, computed from the live store. */
import { z } from 'zod';

import { liveEventSchema } from './eventSchemas';
import { apiCall } from './client';

export const tallySchema = z.object({
  key: z.string(),
  count: z.number().int(),
  max_severity: z.number().nullable(),
});
export type Tally = z.infer<typeof tallySchema>;

export const maritimeBoardSchema = z.object({
  warnings_total: z.number().int(),
  located: z.number().int(),
  by_area: z.array(tallySchema),
  by_kind: z.array(tallySchema),
  notable: z.array(liveEventSchema),
  latest: z.array(liveEventSchema),
});
export type MaritimeBoard = z.infer<typeof maritimeBoardSchema>;

export const spaceBoardSchema = z.object({
  stations: z.array(liveEventSchema),
  launches: z.array(liveEventSchema),
  kp: z.number().nullable(),
  kp_level: z.string().nullable(),
  alerts_24h: z.number().int(),
  latest_alerts: z.array(liveEventSchema),
});
export type SpaceBoard = z.infer<typeof spaceBoardSchema>;

export const cyberBoardSchema = z.object({
  outages_24h: z.number().int(),
  outages_by_country: z.array(tallySchema),
  ransomware_7d: z.number().int(),
  ransomware_by_country: z.array(tallySchema),
  ransomware_by_group: z.array(tallySchema),
  kev_7d: z.number().int(),
  latest_outages: z.array(liveEventSchema),
  latest_claims: z.array(liveEventSchema),
  latest_kev: z.array(liveEventSchema),
});
export type CyberBoard = z.infer<typeof cyberBoardSchema>;

export function fetchMaritimeBoard(): Promise<MaritimeBoard> {
  return apiCall('/api/trackers/maritime', { schema: maritimeBoardSchema });
}

export function fetchSpaceBoard(): Promise<SpaceBoard> {
  return apiCall('/api/trackers/space', { schema: spaceBoardSchema });
}

export function fetchCyberBoard(): Promise<CyberBoard> {
  return apiCall('/api/trackers/cyber', { schema: cyberBoardSchema });
}
