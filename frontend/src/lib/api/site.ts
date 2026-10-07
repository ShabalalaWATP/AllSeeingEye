import { z } from 'zod';

import { apiCall } from './client';

/** Facts the signed-out pages need about this installation; nothing private. */
export const siteFactsSchema = z.object({
  product_page_enabled: z.boolean(),
});
export type SiteFacts = z.infer<typeof siteFactsSchema>;

export function fetchSiteFacts(): Promise<SiteFacts> {
  return apiCall('/api/site', { schema: siteFactsSchema, auth: false });
}
