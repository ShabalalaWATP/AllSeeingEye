import { z } from 'zod';

import { apiCall } from './client';
import type { components } from './types.gen';
import { sourceLicenceSchema } from './sourceLicences';

type ServerCapabilities = components['schemas']['CapabilitiesOut'];
export type Capabilities = Omit<ServerCapabilities, 'ai_research'> &
  Partial<Pick<ServerCapabilities, 'ai_research'>>;
export type SourceLicenceDecision = Capabilities['source_licences'][string];

export const capabilitiesSchema: z.ZodType<Capabilities> = z.object({
  os_maps: z.boolean(),
  os_layers: z.array(z.string()),
  // Older servers may omit readiness; absent remains unknown rather than unavailable.
  ai_research: z.boolean().optional(),
  commercial_use: z.boolean(),
  source_licences: z.record(z.string(), sourceLicenceSchema),
});

export function fetchCapabilities(): Promise<Capabilities> {
  return apiCall('/api/capabilities', { schema: capabilitiesSchema });
}
