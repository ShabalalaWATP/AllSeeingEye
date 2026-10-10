import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type Enquiry = components['schemas']['EnquiryOut'];
export type EnquiryStatus = components['schemas']['EnquiryStatus'];
export type EnquiryPage = components['schemas']['EnquiriesOut'];
export const ENQUIRY_PAGE_SIZE = 25;

const enquirySchema = z.object({
  id: z.uuid(),
  name: z.string(),
  email: z.string(),
  organisation: z.string(),
  role: z.string(),
  message: z.string(),
  deployment_interest: z.enum(['own_cloud', 'on_premises', 'air_gapped', 'undecided']),
  expected_users: z.enum(['1_10', '11_50', '51_250', '250_plus']),
  status: z.enum(['new', 'contacted', 'closed']),
  created_at: z.string(),
  updated_at: z.string(),
}) satisfies z.ZodType<Enquiry>;
const pageSchema = z.object({
  items: z.array(enquirySchema),
  total: z.number().int().nonnegative(),
}) satisfies z.ZodType<EnquiryPage>;

export function listEnquiries(status: EnquiryStatus, offset: number, signal: AbortSignal) {
  const params = new URLSearchParams({
    status,
    offset: String(offset),
    limit: String(ENQUIRY_PAGE_SIZE),
  });
  return apiCall(`/api/admin/enquiries?${params}`, { schema: pageSchema, signal });
}

export function setEnquiryStatus(id: string, status: EnquiryStatus, signal: AbortSignal) {
  return apiCall(`/api/admin/enquiries/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: { status },
    schema: enquirySchema,
    signal,
  });
}

export function deleteEnquiry(id: string, signal: AbortSignal) {
  return apiSend(`/api/admin/enquiries/${encodeURIComponent(id)}`, { method: 'DELETE', signal });
}
