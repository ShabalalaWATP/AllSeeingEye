import { z } from 'zod';

import { apiCall } from './client';

export const capabilitiesSchema = z.object({
  os_maps: z.boolean(),
  os_layers: z.array(z.string()),
  // Only whether research can reach a model. Absent means unknown, never "unavailable".
  ai_research: z.boolean().optional(),
});
export type Capabilities = z.infer<typeof capabilitiesSchema>;

export function fetchCapabilities(): Promise<Capabilities> {
  return apiCall('/api/capabilities', { schema: capabilitiesSchema });
}
