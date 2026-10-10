import * as z from 'zod/mini';

import { apiCall } from './client';

/** Facts the signed-out pages need about this installation; nothing private. */
export const siteFactsSchema = z.object({
  product_page_enabled: z.boolean(),
  enterprise_enquiries_enabled: z._default(z.boolean(), false),
  enterprise_enquiry_retention_days: z._default(z.int().check(z.minimum(30), z.maximum(3650)), 365),
});
export type SiteFacts = z.infer<typeof siteFactsSchema>;

export function fetchSiteFacts(): Promise<SiteFacts> {
  return apiCall('/api/site', { schema: siteFactsSchema, auth: false });
}
